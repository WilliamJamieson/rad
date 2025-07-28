from dataclasses import is_dataclass

import pytest

from rad.reader._basic import Basic
from rad.reader._link import Ref
from rad.reader._reader import KeyWords
from rad.reader._schema import AllOf, AnyOf, Not, OneOf, Schema
from rad.reader._type import Array, Null, Numeric, Object, String


class TestSchema:
    def test_keywords(self):
        """
        Test that the Schema schema has the correct keywords.
        """

        assert Schema.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
        }
        assert issubclass(Schema.KeyWords, KeyWords)

    def test_extract_definitions(self, basic_data, definitions_data, manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **definitions_data},
            manager=manager,
            prefix=None,
        )

        assert isinstance(schema_, Basic)
        assert isinstance(schema_, Schema)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.prefix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.definitions, dict)
        assert schema_.definitions
        assert len(schema_.definitions) == 3

        for key, item in schema_.definitions.items():
            assert item.name == f"definitions/{key}"
            assert item.prefix == "test_id"

        assert "test_string" in schema_.definitions
        string = schema_.definitions["test_string"]
        assert isinstance(string, String)
        assert string.address in manager
        assert manager[string.address] is string

        assert "test_number" in schema_.definitions
        number = schema_.definitions["test_number"]
        assert isinstance(number, Numeric)
        assert number.address in manager
        assert manager[number.address] is number

        assert "test_object" in schema_.definitions
        object_ = schema_.definitions["test_object"]
        assert isinstance(object_, Object)
        assert object_.address in manager
        assert manager[object_.address] is object_

        print(list(manager.keys()))
        assert len(manager) == 7  # schema + catalog + 3 definitions + 2 object properties

    def test_extract_ref_definitions(self, basic_data, definitions_ref_data, manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **definitions_ref_data},
            manager=manager,
            prefix=None,
        )

        assert isinstance(schema_, Schema)
        assert schema_.name == "test_id"
        assert schema_.prefix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.definitions, Ref)
        assert schema_.definitions.ref == "http://example.com/ref_schema"
        assert schema_.definitions.name == "definitions"
        assert schema_.definitions.prefix == "test_id"

        assert schema_.definitions.address in manager
        assert manager[schema_.definitions.address] is schema_.definitions

        assert len(manager) == 3  # schema + archive + definitions ref

    def test_extract_bad_definitons(self, basic_data, manager):
        with pytest.raises(Schema.UnreadableDataError, match=r"Expected 'definitions' to be a Mapping or a \$ref, got.*"):
            Schema.extract(
                name=None,
                data={**basic_data, **{"definitions": "invalid"}},
                manager=manager,
                prefix=None,
            )

    def test_extract_enum(self, basic_data, enum_data, manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **enum_data},
            manager=manager,
            prefix=None,
        )

        assert isinstance(schema_, Schema)
        assert schema_.name == "test_id"
        assert schema_.prefix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.enum, list)
        assert schema_.enum
        assert len(schema_.enum) == 3
        assert schema_.enum == ["value1", "value2", "value3"]

        assert len(manager) == 2  # schema + archive


class TestAllOf:
    def test_keywords(self):
        """
        Test that the AllOf schema has the correct keywords.
        """

        assert AllOf.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
            "ALL_OF": "allOf",
        }
        assert issubclass(AllOf.KeyWords, KeyWords)

    def test_extract(self, basic_data, all_of_data, manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **all_of_data},
            manager=manager,
            prefix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, AllOf)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.prefix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.all_of, list)
        assert schema_.all_of
        assert len(schema_.all_of) == 2

        for index, item in enumerate(schema_.all_of):
            assert isinstance(item, Object)
            assert item.name == f"all_of_{index}"
            assert item.prefix == "test_id"
            assert item.address in manager
            assert manager[item.address] is item

        assert len(manager) == 8  # schema + archive + 2 all_of_items + 2 object properties + 2 pattern properties

    def test_resolve_object_pattern_object(self, basic_data, all_of_data, manager, new_manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **all_of_data},
            manager=manager,
            prefix=None,
        )

        assert len(new_manager) == 0
        resolved = schema_.resolve(new_manager)

        assert len(new_manager) == 6  # schema + archive + 2 object properties + 2 pattern properties
        assert resolved.address in new_manager
        assert new_manager[resolved.address] is resolved
        assert resolved.manager is new_manager

        assert schema_.name == resolved.name
        assert schema_.prefix == resolved.prefix
        assert schema_.address == resolved.address

        assert type(resolved) is Object
        assert set(resolved.properties.keys()) == set(schema_.all_of[0].properties.keys())
        assert set(resolved.pattern_properties.keys()) == set(schema_.all_of[1].pattern_properties.keys())
        assert resolved.required == schema_.all_of[0].required
        assert resolved.additional_properties is False

    def test_resolve_object_object(self, basic_data, all_of_object_object_data, manager, new_manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **all_of_object_object_data},
            manager=manager,
            prefix=None,
        )

        assert len(new_manager) == 0
        resolved = schema_.resolve(new_manager)

        assert len(new_manager) == 5  # schema + archive + 2 object properties + 1 object property
        assert resolved.address in new_manager
        assert new_manager[resolved.address] is resolved
        assert resolved.manager is new_manager

        assert schema_.name == resolved.name
        assert schema_.prefix == resolved.prefix
        assert schema_.address == resolved.address

        assert type(resolved) is Object
        assert len(resolved.properties) == len(schema_.all_of[0].properties) + len(schema_.all_of[1].properties)
        for key in schema_.all_of[0].properties:
            assert key in resolved.properties
        for key in schema_.all_of[1].properties:
            assert key in resolved.properties
        assert set(resolved.required) == set(schema_.all_of[0].required + schema_.all_of[1].required)

    def test_resolve_array(self, basic_data, all_of_array_data, manager, new_manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **all_of_array_data},
            manager=manager,
            prefix=None,
        )
        assert len(schema_.all_of) == 2

        assert len(new_manager) == 0
        resolved = schema_.resolve(new_manager)

        assert len(new_manager) == 5  # schema + archive + 2 array items + 1 array item
        assert resolved.address in new_manager
        assert new_manager[resolved.address] is resolved
        assert resolved.manager is new_manager
        assert resolved.address == schema_.address

        assert schema_.name == resolved.name
        assert schema_.prefix == resolved.prefix
        assert schema_.address == resolved.address

        assert type(resolved) is Array
        assert len(resolved.items) == len(schema_.all_of[0].items) + len(schema_.all_of[1].items)
        assert resolved.items[0].type == "string"
        assert resolved.items[1].type == "string"
        assert resolved.items[2].type == "number"


class TestAnyOf:
    def test_keywords(self):
        """
        Test that the AnyOf schema has the correct keywords.
        """

        assert AnyOf.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
            "ANY_OF": "anyOf",
        }
        assert issubclass(AnyOf.KeyWords, KeyWords)

    def test_extract(self, basic_data, any_of_data, manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **any_of_data},
            manager=manager,
            prefix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, AnyOf)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.prefix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.any_of, list)
        assert schema_.any_of
        assert len(schema_.any_of) == 2

        for index, item in enumerate(schema_.any_of):
            assert isinstance(item, String | Null)
            assert item.name == f"any_of_{index}"
            assert item.prefix == "test_id"
            assert item.address in manager
            assert manager[item.address] is item

        assert len(manager) == 4  # schema + archive + 2 any_of_items


class TestNot:
    def test_keywords(self):
        """
        Test that the Not schema has the correct keywords.
        """

        assert Not.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
            "NOT_": "not",
        }
        assert issubclass(Not.KeyWords, KeyWords)

    def test_extract(self, basic_data, not_data, manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **not_data},
            manager=manager,
            prefix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, Not)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.prefix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.not_, Object)
        assert schema_.not_.name == "not"
        assert schema_.not_.prefix == "test_id"
        assert schema_.not_.address in manager
        assert manager[schema_.not_.address] is schema_.not_

        assert len(manager) == 5  # schema + archive + not_item + 2 object properties


class TestOneOf:
    def test_keywords(self):
        """
        Test that the OneOf schema has the correct keywords.
        """

        assert OneOf.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "DEFINITIONS": "definitions",
            "ENUM": "enum",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
            "ONE_OF": "oneOf",
        }
        assert issubclass(OneOf.KeyWords, KeyWords)

    def test_extract(self, basic_data, one_of_data, manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **one_of_data},
            manager=manager,
            prefix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, OneOf)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.prefix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.one_of, list)
        assert schema_.one_of
        assert len(schema_.one_of) == 2

        for index, item in enumerate(schema_.one_of):
            assert isinstance(item, String | Numeric)
            assert item.name == f"one_of_{index}"
            assert item.prefix == "test_id"
            assert item.address in manager
            assert manager[item.address] is item

        assert len(manager) == 4  # schema + archive + 2 one_of_items
