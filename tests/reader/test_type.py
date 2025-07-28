from dataclasses import is_dataclass

import pytest

from rad.reader._basic import Basic
from rad.reader._reader import KeyWords, Reader
from rad.reader._schema import Schema
from rad.reader._type import Array, Boolean, Null, Numeric, Object, String, Type


class TestType:
    def test_keywords(self):
        """
        Test that the Basic schema has the correct keywords.
        """
        assert Type.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "TYPE": "type",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
        }
        assert issubclass(Type.KeyWords, KeyWords)

    def test_type_key_failure(self, basic_data, manager):
        """
        Test that the Type schema cannot be extracted from a dictionary without a type.
        """
        with pytest.raises(Type.TypeKeys.UnhandledKeyError, match="Unhandled type value: .*"):
            Type.extract(
                name=None,
                data={**basic_data, "type": "unsupported_type"},
                manager=manager,
                prefix=None,
            )

    def test_extract_failure(self, basic_data, manager):
        """
        Test that the Type schema cannot be extracted from a dictionary without a type.
        """
        with pytest.raises(Type.UnreadableDataError, match="Missing 'type' key in data."):
            Type.extract(
                name=None,
                data=basic_data,
                manager=manager,
                prefix=None,
            )


class TestArray:
    def test_keywords(self):
        """
        Test that the Basic schema has the correct keywords.
        """
        assert Array.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "TYPE": "type",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
            "ITEMS": "items",
            "ADDITIONAL_ITEMS": "additionalItems",
            "MAX_ITEMS": "maxItems",
            "MIN_ITEMS": "minItems",
            "UNIQUE_ITEMS": "uniqueItems",
        }
        assert issubclass(Array.KeyWords, KeyWords)

    def test_single_item_extract(self, basic_data, single_item_array_data, manager):
        """
        Test that the Type schema can be extracted from a dictionary.
        """
        type_ = Schema.extract(
            name=None,
            data={**basic_data, **single_item_array_data},
            manager=manager,
            prefix=None,
        )
        assert isinstance(type_, Type)
        assert isinstance(type_, Array)
        assert is_dataclass(type_)
        assert type_.type == "array"
        assert type_.name == "test_id"
        assert type_.prefix is None

        assert type_.manager is manager
        assert type_.address in manager
        assert manager[type_.address] is type_

        assert isinstance(type_.items, list)
        assert len(type_.items) == 1
        item = type_.items[0]
        assert isinstance(item, String)
        assert item.type == "string"
        assert item.name == "items"
        assert item.prefix == "test_id"
        assert item.address in manager
        assert manager[item.address] is type_.items[0]

        assert type_.additional_items is None
        assert type_.max_items is None
        assert type_.min_items is None
        assert type_.unique_items is None

        assert len(manager) == 3  # schema + archive + single_item_array

    def test_multi_item_extract(self, basic_data, multi_item_array_data, manager):
        """
        Test that the Type schema can be extracted from a dictionary.
        """
        type_ = Schema.extract(
            name=None,
            data={**basic_data, **multi_item_array_data},
            manager=manager,
            prefix=None,
        )
        assert isinstance(type_, Type)
        assert isinstance(type_, Array)
        assert is_dataclass(type_)
        assert type_.type == "array"
        assert type_.name == "test_id"
        assert type_.prefix is None

        assert type_.manager is manager
        assert type_.address in manager
        assert manager[type_.address] is type_

        assert isinstance(type_.items, list)
        assert len(type_.items) == 2

        assert isinstance(type_.items[0], Type)
        assert isinstance(type_.items[0], String)
        assert type_.items[0].type == "string"
        assert type_.items[0].name == "item_0"
        assert type_.items[0].prefix == "test_id"
        assert type_.items[0].address in manager
        assert manager[type_.items[0].address] is type_.items[0]

        assert isinstance(type_.items[1], Type)
        assert isinstance(type_.items[1], Numeric)
        assert type_.items[1].type == "number"
        assert type_.items[1].name == "item_1"
        assert type_.items[1].prefix == "test_id"
        assert type_.items[1].address in manager
        assert manager[type_.items[1].address] is type_.items[1]

        assert type_.additional_items is None
        assert type_.max_items is None
        assert type_.min_items is None
        assert type_.unique_items is None

        assert len(manager) == 4  # schema + archive + 2 multi_item_array_items

    def test_extract_failure(self, basic_data, manager):
        with pytest.raises(Reader.UnreadableDataError, match=r"Expected 'items' to be a list, dict, or Schema instance, got.*"):
            Schema.extract(
                name=None,
                data={
                    **basic_data,
                    "type": "array",
                    "items": Basic(
                        name="foo",
                        prefix=None,
                        id="bar",
                        schema="baz",
                        title="Foo",
                        description="A foo item",
                        default=None,
                        archive_catalog=None,
                        unit=None,
                        datamodel_name=None,
                        archive_meta=None,
                        manager=manager,
                    ),
                },
                manager=manager,
                prefix=None,
            )


class TestBoolean:
    def test_keywords(self):
        """
        Test that the Basic schema has the correct keywords.
        """
        assert Boolean.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "TYPE": "type",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
        }
        assert issubclass(Boolean.KeyWords, KeyWords)

    def test_extract(self, basic_data, boolean_data, manager):
        """
        Test that the Boolean schema can be extracted from a dictionary.
        """
        type_ = Schema.extract(
            name=None,
            data={**basic_data, **boolean_data},
            manager=manager,
            prefix=None,
        )
        assert isinstance(type_, Type)
        assert isinstance(type_, Boolean)
        assert is_dataclass(type_)
        assert type_.type == "boolean"
        assert type_.name == "test_id"
        assert type_.prefix is None

        assert type_.manager is manager
        assert type_.address in manager
        assert manager[type_.address] is type_
        assert len(manager) == 2  # schema + archive


class TestNumeric:
    def test_keywords(self):
        """
        Test that the Basic schema has the correct keywords.
        """
        assert Numeric.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "TYPE": "type",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
            "MINIMUM": "minimum",
            "MAXIMUM": "maximum",
            "EXCLUSIVE_MINIMUM": "exclusiveMinimum",
            "EXCLUSIVE_MAXIMUM": "exclusiveMaximum",
            "MULTIPLE_OF": "multipleOf",
        }
        assert issubclass(Numeric.KeyWords, KeyWords)

    def test_extract_integer(self, basic_data, integer_data, manager):
        """
        Test that the Numeric schema can be extracted from a dictionary.
        """
        type_ = Schema.extract(
            name=None,
            data={**basic_data, **integer_data},
            manager=manager,
            prefix=None,
        )
        assert isinstance(type_, Type)
        assert isinstance(type_, Numeric)
        assert is_dataclass(type_)
        assert type_.type == "integer"
        assert type_.name == "test_id"
        assert type_.prefix is None

        assert type_.minimum is None
        assert type_.maximum is None
        assert type_.exclusive_minimum is None
        assert type_.exclusive_maximum is None
        assert type_.multiple_of is None

        assert type_.manager is manager
        assert type_.address in manager
        assert manager[type_.address] is type_
        assert len(manager) == 2  # schema + archive

    def test_extract_number(self, basic_data, number_data, manager):
        """
        Test that the Numeric schema can be extracted from a dictionary.
        """
        type_ = Schema.extract(
            name=None,
            data={**basic_data, **number_data},
            manager=manager,
            prefix=None,
        )
        assert isinstance(type_, Type)
        assert isinstance(type_, Numeric)
        assert is_dataclass(type_)
        assert type_.type == "number"
        assert type_.name == "test_id"
        assert type_.prefix is None

        assert type_.minimum is None
        assert type_.maximum is None
        assert type_.exclusive_minimum is None
        assert type_.exclusive_maximum is None
        assert type_.multiple_of is None

        assert type_.manager is manager
        assert type_.address in manager
        assert manager[type_.address] is type_
        assert len(manager) == 2  # schema + archive


class TestNull:
    def test_keywords(self):
        """
        Test that the Basic schema has the correct keywords.
        """
        assert Null.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "TYPE": "type",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
        }
        assert issubclass(Null.KeyWords, KeyWords)

    def test_extract(self, basic_data, null_data, manager):
        """
        Test that the Null schema can be extracted from a dictionary.
        """
        type_ = Schema.extract(
            name=None,
            data={**basic_data, **null_data},
            manager=manager,
            prefix=None,
        )
        assert isinstance(type_, Type)
        assert isinstance(type_, Null)
        assert is_dataclass(type_)
        assert type_.type == "null"
        assert type_.name == "test_id"
        assert type_.prefix is None

        assert type_.manager is manager
        assert type_.address in manager
        assert manager[type_.address] is type_
        assert len(manager) == 2  # schema + archive


class TestObject:
    def test_keywords(self):
        """
        Test that the Basic schema has the correct keywords.
        """
        assert Object.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "TYPE": "type",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
            "PROPERTIES": "properties",
            "PATTERN_PROPERTIES": "patternProperties",
            "ADDITIONAL_PROPERTIES": "additionalProperties",
            "MAX_PROPERTIES": "maxProperties",
            "MIN_PROPERTIES": "minProperties",
            "REQUIRED": "required",
            "DEPENDENCIES": "dependencies",
        }
        assert issubclass(Object.KeyWords, KeyWords)

    def test_extract(self, basic_data, object_data, manager):
        """
        Test that the Object schema can be extracted from a dictionary.
        """
        type_ = Schema.extract(
            name=None,
            data={**basic_data, **object_data},
            manager=manager,
            prefix=None,
        )
        assert isinstance(type_, Type)
        assert isinstance(type_, Object)
        assert is_dataclass(type_)
        assert type_.type == "object"
        assert type_.name == "test_id"
        assert type_.prefix is None

        assert type_.manager is manager
        assert type_.address in manager
        assert manager[type_.address] is type_

        assert type_.properties is not None
        assert isinstance(type_.properties, dict)
        assert len(type_.properties) == 2

        for key, value in type_.properties.items():
            assert isinstance(value, Type)
            assert value.name == key
            assert value.prefix == "test_id"

            assert value.address in manager
            assert manager[value.address] is value

            if key == "property1":
                assert isinstance(value, String)
                assert value.type == "string"
            elif key == "property2":
                assert isinstance(value, Numeric)
                assert value.type == "number"
            else:
                raise AssertionError(f"Unexpected property key: {key}")

        assert type_.pattern_properties is None
        assert type_.required == ["property1"]
        assert type_.additional_properties is None
        assert type_.max_properties is None
        assert type_.min_properties is None
        assert type_.dependencies is None

        assert len(manager) == 4  # schema + archive + 2 object_properties

    def test_pattern_extract(self, basic_data, pattern_object_data, manager):
        """
        Test that the Object schema can be extracted from a dictionary with pattern properties.
        """
        type_ = Type.extract(
            name=None,
            data={**basic_data, **pattern_object_data},
            manager=manager,
            prefix=None,
        )
        assert isinstance(type_, Type)
        assert isinstance(type_, Object)
        assert is_dataclass(type_)
        assert type_.type == "object"
        assert type_.name == "test_id"
        assert type_.prefix is None

        assert type_.manager is manager
        assert type_.address in manager
        assert manager[type_.address] is type_

        assert type_.pattern_properties is not None
        assert isinstance(type_.pattern_properties, dict)
        assert len(type_.pattern_properties) == 2

        for key, value in type_.pattern_properties.items():
            assert value.name == f"pattern[{key}]"
            assert isinstance(value, Type)
            assert value.prefix == "test_id"

            assert value.address in manager
            assert manager[value.address] is value

            if key == "^pattern_.*":
                assert isinstance(value, String)
                assert value.type == "string"
            elif key == "^pattern_property2$":
                assert isinstance(value, Numeric)
                assert value.type == "number"
            else:
                raise AssertionError(f"Unexpected pattern property key: {key}")

        assert type_.properties is None
        assert type_.required is None
        assert type_.additional_properties is False
        assert type_.max_properties is None
        assert type_.min_properties is None
        assert type_.dependencies is None

        assert len(manager) == 4  # schema + archive + 2 pattern_properties


class TestString:
    def test_keywords(self):
        """
        Test that the Basic schema has the correct keywords.
        """
        assert String.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "TYPE": "type",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
            "PATTERN": "pattern",
            "MIN_LENGTH": "minLength",
            "MAX_LENGTH": "maxLength",
        }
        assert issubclass(String.KeyWords, KeyWords)

    def test_extract(self, basic_data, string_data, manager):
        """
        Test that the String schema can be extracted from a dictionary.
        """
        type_ = Schema.extract(
            name=None,
            data={**basic_data, **string_data},
            manager=manager,
            prefix=None,
        )
        assert isinstance(type_, Type)
        assert isinstance(type_, String)
        assert is_dataclass(type_)
        assert type_.type == "string"
        assert type_.name == "test_id"
        assert type_.prefix is None

        assert type_.min_length is None
        assert type_.max_length is None
        assert type_.pattern is None

        assert type_.manager is manager
        assert type_.address in manager
        assert manager[type_.address] is type_
        assert len(manager) == 2  # schema + archive
