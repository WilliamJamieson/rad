from dataclasses import is_dataclass

import pytest

from rad.reader._basic import Basic
from rad.reader._link import Ref
from rad.reader._reader import KeyWords
from rad.reader._schema import AllOf, AnyOf, Not, OneOf, Schema
from rad.reader._type import Null, Numeric, Object, String


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
            suffix=None,
        )

        assert isinstance(schema_, Basic)
        assert isinstance(schema_, Schema)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.suffix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.definitions, dict)
        assert schema_.definitions
        assert len(schema_.definitions) == 3

        for key, item in schema_.definitions.items():
            assert item.name == key
            assert item.suffix == "definitions@test_id"

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
            suffix=None,
        )

        assert isinstance(schema_, Schema)
        assert schema_.name == "test_id"
        assert schema_.suffix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.definitions, Ref)
        assert schema_.definitions.ref == "http://example.com/ref_schema"
        assert schema_.definitions.name == "definitions"
        assert schema_.definitions.suffix == "test_id"

        assert schema_.definitions.address in manager
        assert manager[schema_.definitions.address] is schema_.definitions

        assert len(manager) == 3  # schema + archive + definitions ref

    def test_extract_bad_definitons(self, basic_data, manager):
        with pytest.raises(Schema.UnreadableDataError, match=r"Expected 'definitions' to be a Mapping or a \$ref, got.*"):
            Schema.extract(
                name=None,
                data={**basic_data, **{"definitions": "invalid"}},
                manager=manager,
                suffix=None,
            )

    def test_extract_enum(self, basic_data, enum_data, manager):
        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **enum_data},
            manager=manager,
            suffix=None,
        )

        assert isinstance(schema_, Schema)
        assert schema_.name == "test_id"
        assert schema_.suffix is None

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
            suffix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, AllOf)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.suffix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.all_of, list)
        assert schema_.all_of
        assert len(schema_.all_of) == 2

        for index, item in enumerate(schema_.all_of):
            assert isinstance(item, Object)
            assert item.name == f"all_of_{index}"
            assert item.suffix == "test_id"
            assert item.address in manager
            assert manager[item.address] is item

        assert len(manager) == 8  # schema + archive + 2 all_of_items + 2 object properties + 2 pattern properties


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
            suffix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, AnyOf)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.suffix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.any_of, list)
        assert schema_.any_of
        assert len(schema_.any_of) == 2

        for index, item in enumerate(schema_.any_of):
            assert isinstance(item, String | Null)
            assert item.name == f"any_of_{index}"
            assert item.suffix == "test_id"
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
            suffix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, Not)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.suffix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.not_, Object)
        assert schema_.not_.name == "not"
        assert schema_.not_.suffix == "test_id"
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
            suffix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, OneOf)
        assert is_dataclass(schema_)
        assert schema_.name == "test_id"
        assert schema_.suffix is None

        assert schema_.manager is manager
        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.one_of, list)
        assert schema_.one_of
        assert len(schema_.one_of) == 2

        for index, item in enumerate(schema_.one_of):
            assert isinstance(item, String | Numeric)
            assert item.name == f"one_of_{index}"
            assert item.suffix == "test_id"
            assert item.address in manager
            assert manager[item.address] is item

        assert len(manager) == 4  # schema + archive + 2 one_of_items
