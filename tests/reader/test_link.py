from dataclasses import is_dataclass

from rad.reader._link import Link, Ref, Tag
from rad.reader._reader import KeyWords
from rad.reader._schema import AllOf, Schema
from rad.reader._type import Object


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

    def test_extract(self, basic_data, top_ref_data):
        """Test that a Ref schema can be extracted correctly from a schema."""

        schema_ = Schema.extract({**basic_data, **top_ref_data})

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, AllOf)

        assert isinstance(schema_.all_of, list)
        assert schema_.all_of
        assert len(schema_.all_of) == 1

        ref = schema_.all_of[0]
        assert isinstance(ref, Schema)
        assert isinstance(ref, Link)
        assert isinstance(ref, Ref)
        assert is_dataclass(ref)

        assert ref.ref == "http://example.com/ref_schema"


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

    def test_extract(self, basic_data, tag_data):
        """Test that a Tag schema can be extracted correctly from a schema."""

        schema_ = Schema.extract({**basic_data, **tag_data})

        assert isinstance(schema_, Schema)
        assert isinstance(schema_, Object)

        assert isinstance(schema_.properties, dict)
        assert schema_.properties
        assert len(schema_.properties) == 2

        assert "property1" in schema_.properties
        property1 = schema_.properties["property1"]
        assert isinstance(property1, Link)
        assert isinstance(property1, Tag)
        assert is_dataclass(property1)
        assert property1.tag == "asdf://test.com/tags/test_tag1"

        assert "property2" in schema_.properties
        property2 = schema_.properties["property2"]
        assert isinstance(property2, Link)
        assert isinstance(property2, Tag)
        assert is_dataclass(property2)
        assert property2.tag == "asdf://test.com/tags/test_tag2"
