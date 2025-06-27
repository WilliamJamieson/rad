from dataclasses import is_dataclass

from rad.node._reader._basic import ArchiveCatalog, Basic, Metadata, Rad, Root
from rad.node._reader._reader import KeyWords


class TestRoot:
    def test_keywords(self):
        """
        Test that the Root schema has the correct keywords.
        """
        assert Root.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
        }
        assert issubclass(Root.KeyWords, KeyWords)

    def test_extract(self, root_data):
        """
        Test that the Root schema can be extracted from a dictionary.
        """
        root = Root.extract(
            name=None,
            data=root_data,
            suffix=None,
        )
        assert isinstance(root, Root)
        assert is_dataclass(root)
        assert root.id == "test_id"
        assert root.schema == "http://example.com/schema"
        assert root.suffix is None

    def test_name(self, root_data):
        """
        Test that the Root schema sets the name correctly.
        """
        root = Root.extract(
            name="test_root",
            data=root_data,
            suffix=None,
        )
        assert root.name == root.id
        assert root.id == "test_id"


class TestMetadata:
    def test_keywords(self):
        """
        Test that the Metadata schema has the correct keywords.
        """
        assert Metadata.KeyWords.__members__ == {
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
        }
        assert issubclass(Metadata.KeyWords, KeyWords)

    def test_extract(self, metadata_data):
        """
        Test that the Metadata schema can be extracted from a dictionary.
        """
        metadata = Metadata.extract(
            name=None,
            data=metadata_data,
            suffix=None,
        )
        assert isinstance(metadata, Metadata)
        assert is_dataclass(metadata)
        assert metadata.title == "Test Title"
        assert metadata.description == "Test Description"
        assert metadata.default == "Test Default"
        assert metadata.suffix is None


class TestArchiveCatalog:
    def test_keywords(self):
        """
        Test that the ArchiveCatalog schema has the correct keywords.
        """
        assert ArchiveCatalog.KeyWords.__members__ == {
            "DATATYPE": "datatype",
            "DESTINATION": "destination",
            "PATH_PREFIX": "path_prefix",
        }
        assert issubclass(ArchiveCatalog.KeyWords, KeyWords)

    def test_extract(self, archive_catalog_data):
        """
        Test that the ArchiveCatalog schema can be extracted from a dictionary.
        """
        archive_catalog = ArchiveCatalog.extract(
            name=None,
            data=archive_catalog_data,
            suffix=None,
        )
        assert isinstance(archive_catalog, ArchiveCatalog)
        assert is_dataclass(archive_catalog)
        assert archive_catalog.datatype == "Test DataType"
        assert archive_catalog.destination == ["destination1", "destination2"]
        assert archive_catalog.path_prefix == "Test Path Prefix"
        assert archive_catalog.suffix is None


class TestRad:
    def test_keywords(self):
        """
        Test that the Rad schema has the correct keywords.
        """
        assert Rad.KeyWords.__members__ == {
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
        }
        assert issubclass(Rad.KeyWords, KeyWords)

    def test_extract(self, rad_data):
        """
        Test that the Rad schema can be extracted from a dictionary.
        """
        rad = Rad.extract(
            name=None,
            data=rad_data,
            suffix=None,
        )
        assert isinstance(rad, Rad)
        assert is_dataclass(rad)
        assert rad.archive_catalog is not None
        assert isinstance(rad.archive_catalog, ArchiveCatalog)
        assert rad.unit == "Test Unit"
        assert rad.datamodel_name == "Test DataModel Name"
        assert rad.archive_meta == "Test Archive Meta"
        assert rad.suffix is None


class TestBasic:
    def test_keywords(self):
        """
        Test that the Basic schema has the correct keywords.
        """
        assert Basic.KeyWords.__members__ == {
            "ID": "id",
            "SCHEMA": "$schema",
            "TITLE": "title",
            "DESCRIPTION": "description",
            "DEFAULT": "default",
            "ARCHIVE_CATALOG": "archive_catalog",
            "UNIT": "unit",
            "DATAMODEL_NAME": "datamodel_name",
            "ARCHIVE_META": "archive_meta",
        }
        assert issubclass(Basic.KeyWords, KeyWords)

    def test_extract(self, basic_data):
        """
        Test that the Basic schema can be extracted from a dictionary.
        """
        basic = Basic.extract(
            name=None,
            data=basic_data,
            suffix=None,
        )
        assert isinstance(basic, Basic)
        assert isinstance(basic, Root)
        assert isinstance(basic, Metadata)
        assert isinstance(basic, Rad)
        assert is_dataclass(basic)
        assert basic.id == "test_id"
        assert basic.schema == "http://example.com/schema"
        assert basic.title == "Test Title"
        assert basic.description == "Test Description"
        assert basic.default == "Test Default"

        assert basic.unit == "Test Unit"
        assert basic.datamodel_name == "Test DataModel Name"
        assert basic.archive_meta == "Test Archive Meta"

        assert isinstance(basic.archive_catalog, ArchiveCatalog)
        assert basic.archive_catalog.datatype == "Test DataType"
        assert basic.archive_catalog.destination == ["destination1", "destination2"]
        assert basic.archive_catalog.path_prefix == "Test Path Prefix"

        assert basic.name == "test_id"
        assert basic.suffix is None
