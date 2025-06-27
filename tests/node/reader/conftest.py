from types import MappingProxyType

import pytest


@pytest.fixture(scope="session")
def root_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide a root data structure for tests.
    """
    return MappingProxyType(
        {
            "id": "test_id",
            "$schema": "http://example.com/schema",
        }
    )


@pytest.fixture(scope="session")
def metadata_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide metadata data structure for tests.
    """
    return MappingProxyType(
        {
            "title": "Test Title",
            "description": "Test Description",
            "default": "Test Default",
        }
    )


@pytest.fixture(scope="session")
def archive_catalog_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide archive catalog data structure for tests.
    """
    return MappingProxyType(
        {
            "datatype": "Test DataType",
            "destination": ["destination1", "destination2"],
            "path_prefix": "Test Path Prefix",
        }
    )


@pytest.fixture(scope="session")
def rad_data(archive_catalog_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide RAD data structure for tests.
    """
    return MappingProxyType(
        {
            "archive_catalog": archive_catalog_data,
            "unit": "Test Unit",
            "datamodel_name": "Test DataModel Name",
            "archive_meta": "Test Archive Meta",
        }
    )


@pytest.fixture(scope="session")
def basic_data(root_data, metadata_data, rad_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide a basic data structure for tests.
    Combines root and metadata data.
    """
    return MappingProxyType(
        {
            **root_data,
            **metadata_data,
            **rad_data,
        }
    )


@pytest.fixture(scope="session")
def string_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide string data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "string",
        }
    )


@pytest.fixture(scope="session")
def number_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide numeric data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "number",
        }
    )


@pytest.fixture(scope="session")
def single_item_array_data(string_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide array data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "array",
            "items": string_data,
        }
    )


@pytest.fixture(scope="session")
def multi_item_array_data(string_data, number_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide array data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "array",
            "items": [
                string_data,
                number_data,
            ],
        }
    )


@pytest.fixture(scope="session")
def boolean_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide boolean data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "boolean",
        }
    )


@pytest.fixture(scope="session")
def integer_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide integer data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "integer",
        }
    )


@pytest.fixture(scope="session")
def null_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide null data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "null",
        }
    )


@pytest.fixture(scope="session")
def object_data(string_data, number_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide object data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "object",
            "properties": {
                "property1": string_data,
                "property2": number_data,
            },
            "required": ["property1"],
        }
    )


@pytest.fixture(scope="session")
def pattern_object_data(string_data, number_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide pattern object data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "object",
            "patternProperties": {
                r"^pattern_.*": string_data,
                r"^pattern_property2$": number_data,
            },
            "additionalProperties": False,
        }
    )


@pytest.fixture(scope="session")
def all_of_data(object_data, pattern_object_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide allOf data structure for tests.
    """

    return MappingProxyType(
        {
            "allOf": [
                object_data,
                pattern_object_data,
            ],
        }
    )


@pytest.fixture(scope="session")
def any_of_data(string_data, null_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide anyOf data structure for tests.
    """
    return MappingProxyType(
        {
            "anyOf": [
                string_data,
                null_data,
            ],
        }
    )


@pytest.fixture(scope="session")
def not_data(object_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide not data structure for tests.
    """
    return MappingProxyType(
        {
            "not": object_data,
        }
    )


@pytest.fixture(scope="session")
def one_of_data(string_data, number_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide oneOf data structure for tests.
    """
    return MappingProxyType(
        {
            "oneOf": [
                string_data,
                number_data,
            ],
        }
    )


@pytest.fixture(scope="session")
def ref_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide $ref data structure for tests.
    """
    return MappingProxyType(
        {
            "$ref": "http://example.com/ref_schema",
        },
    )


@pytest.fixture(scope="session")
def top_ref_data(ref_data) -> MappingProxyType[str, str]:
    """
    Fixture providing a top-level $ref data structure for tests.
    """

    return MappingProxyType(
        {
            "allOf": [
                ref_data,
            ]
        }
    )


@pytest.fixture(scope="session")
def tag_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide tag data structure for tests.
    """
    return MappingProxyType(
        {
            "type": "object",
            "properties": {
                "property1": {
                    "tag": "asdf://test.com/tags/test_tag1",
                },
                "property2": {
                    "tag": "asdf://test.com/tags/test_tag2",
                },
            },
        }
    )


@pytest.fixture(scope="session")
def definitions_data(string_data, number_data, object_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide definitions data structure for tests.
    """
    return MappingProxyType(
        {
            "definitions": {
                "test_string": string_data,
                "test_number": number_data,
                "test_object": object_data,
            },
        }
    )


@pytest.fixture(scope="session")
def definitions_ref_data(ref_data) -> MappingProxyType[str, str]:
    """
    Fixture to provide definitions with $ref data structure for tests.
    """
    return MappingProxyType(
        {
            "definitions": {
                **ref_data,
            },
        }
    )


@pytest.fixture(scope="session")
def enum_data() -> MappingProxyType[str, str]:
    """
    Fixture to provide enum data structure for tests.
    """
    return MappingProxyType(
        {
            "enum": ["value1", "value2", "value3"],
        }
    )
