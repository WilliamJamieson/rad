from dataclasses import is_dataclass

from rad.node._reader._link import Link, Ref, Tag
from rad.node._reader._reader import KeyWords
from rad.node._reader._schema import AllOf, Schema
from rad.node._reader._type import Object


class TestRef:
    def test_keywords(self):
        """
        Test that the Ref schema has the correct keywords.
        """

        assert Ref.KeyWords.__members__ == {
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
            "REF": "$ref",
        }
        assert issubclass(Ref.KeyWords, KeyWords)

    def test_extract(self, basic_data, top_ref_data, manager):
        """Test that a Ref schema can be extracted correctly from a schema."""

        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **top_ref_data},
            manager=manager,
            suffix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, AllOf)
        assert schema_.name == "test_id"
        assert schema_.suffix is None

        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.all_of, list)
        assert schema_.all_of
        assert len(schema_.all_of) == 1

        ref = schema_.all_of[0]
        assert isinstance(ref, Schema)
        assert isinstance(ref, Link)
        assert isinstance(ref, Ref)
        assert is_dataclass(ref)

        assert ref.name == "all_of_0"
        assert ref.suffix == "test_id"
        assert ref.ref == "http://example.com/ref_schema"

        assert ref.manager is manager
        assert ref.address in manager
        assert manager[ref.address] is ref

        assert len(manager) == 3  # schema + ref + archive_catalog


class TestTag:
    def test_keywords(self):
        """
        Test that the Tag schema has the correct keywords.
        """

        assert Tag.KeyWords.__members__ == {
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
            "TAG": "tag",
        }
        assert issubclass(Tag.KeyWords, KeyWords)

    def test_extract(self, basic_data, tag_data, manager):
        """Test that a Tag schema can be extracted correctly from a schema."""

        schema_ = Schema.extract(
            name=None,
            data={**basic_data, **tag_data},
            manager=manager,
            suffix=None,
        )

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, Object)
        assert schema_.name == "test_id"
        assert schema_.suffix is None

        assert schema_.address in manager
        assert manager[schema_.address] is schema_

        assert isinstance(schema_.properties, dict)
        assert schema_.properties
        assert len(schema_.properties) == 2

        assert "property1" in schema_.properties
        property1 = schema_.properties["property1"]
        assert isinstance(property1, Link)
        assert isinstance(property1, Tag)
        assert is_dataclass(property1)
        assert property1.name == "property1"
        assert property1.suffix == "test_id"
        assert property1.tag == "asdf://test.com/tags/test_tag1"

        assert property1.manager is manager
        assert property1.address in manager
        assert manager[property1.address] is property1

        assert "property2" in schema_.properties
        property2 = schema_.properties["property2"]
        assert isinstance(property2, Link)
        assert isinstance(property2, Tag)
        assert is_dataclass(property2)
        assert property2.name == "property2"
        assert property2.suffix == "test_id"
        assert property2.tag == "asdf://test.com/tags/test_tag2"

        assert property2.manager is manager
        assert property2.address in manager
        assert manager[property2.address] is property2

        assert len(manager) == 4  # schema + property1 + property2 + archive_catalog
