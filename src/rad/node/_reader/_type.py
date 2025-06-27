from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Self

from ._reader import ValueKeys, rad
from ._schema import Schema

__all__ = ("Type",)


class Type(Schema):
    """
    Type schema for the reader.
        See: https://json-schema.org/draft-04/draft-zyp-json-schema-04#rfc.section.3.5
    """

    type: str | None = rad()

    class TypeKeys(ValueKeys):
        ARRAY = "array"
        BOOLEAN = "boolean"
        INTEGER = "integer"
        NUMBER = "number"
        NULL = "null"
        OBJECT = "object"
        STRING = "string"

        @classmethod
        def reader(cls, data: dict[str, Any]) -> type[Type]:
            """
            Get the reader class for a given type value.

            Parameters
            ----------
            data
                The data dictionary to determine the schema class.

            Returns
            -------
                The schema class corresponding to the value.
            """
            match data.get("type"):
                case cls.ARRAY:
                    return Array
                case cls.BOOLEAN:
                    return Boolean
                case cls.INTEGER | cls.NUMBER:
                    return Numeric
                case cls.NULL:
                    return Null
                case cls.OBJECT:
                    return Object
                case cls.STRING:
                    return String

            raise cls.UnhandledKeyError(f"Unhandled type value: {data.get('type')}.")

    @classmethod
    def extract(cls, name: str, data: dict[str, Any], suffix: str | None = None, **kwargs) -> Self:
        """
        Extract a schema instance from a dictionary.

        Parameters
        ----------
        name:
            The name of the schema
        data:
            The data dictionary to read the schema from
        suffix:
            The suffix used to identify the schema this is a subschema

        Returns
        -------
            An instance of the schema class.
        """
        if cls is Type:
            if "type" not in data:
                raise cls.UnreadableDataError("Missing 'type' key in data.")

            return cls.TypeKeys.reader(data).extract(name=name, data=data, suffix=suffix, **kwargs)
        return super().extract(name=name, data=data, suffix=suffix, **kwargs)


class Array(Type):
    """
    Array schema for the reader.
        See: https://json-schema.org/draft-04/draft-zyp-json-schema-04#rfc.section.3.5.1
    """

    items: list[Schema] | Schema | None = rad()
    # These are not useful for the parser's application, but are part of the
    #   JSON-schema draft-04 specification, so are included for completeness.
    additional_items: bool | None = rad()
    min_items: int | None = rad()
    max_items: int | None = rad()
    unique_items: bool | None = rad()

    def __post_init__(self) -> None:
        """
        Post-initialization to finish processing the items
        """
        super().__post_init__()

        if isinstance(self.items, Sequence):
            self.items = [
                Schema.extract(name=f"item_{index}", data=item, suffix=self.address) for index, item in enumerate(self.items)
            ]
        elif isinstance(self.items, Mapping):
            self.items = Schema.extract(name="items", data=self.items, suffix=self.address)
        elif not isinstance(self.items, Schema):
            raise self.UnreadableDataError(f"Expected 'items' to be a list, dict, or Schema instance, got {type(self.items)}.")


class Boolean(Type):
    """Boolean schema for the region"""


class Numeric(Type):
    """
    Numeric schema for the reader.
        See: https://json-schema.org/draft-04/draft-fge-json-schema-validation-00#rfc.section.5.1
    """

    # These are not useful for the parser's application, but are part of the
    #   JSON-schema draft-04 specification, so are included for completeness.
    minimum: float | None = rad()
    maximum: float | None = rad()
    exclusive_minimum: bool | None = rad()
    exclusive_maximum: bool | None = rad()
    multiple_of: float | None = rad()


class Null(Type):
    """
    Null schema for the reader.
        Note: In JSON Schema Draft-04, null types do not have specific keys.
    """


class Object(Type):
    """
    Object schema for the reader.
        See: https://json-schema.org/draft-04/draft-fge-json-schema-validation-00#rfc.section.5.4
    """

    properties: dict[str, Schema] | None = rad()
    pattern_properties: dict[str, Schema] | None = rad()
    required: list[str] | None = rad()
    additional_properties: bool | None = rad()
    # These are not useful for the parser's application, but are part of the
    #   JSON-schema draft-04 specification, so are included for completeness.
    max_properties: int | None = rad()
    min_properties: int | None = rad()
    dependencies: dict[str, Any] | None = rad()

    def __post_init__(self):
        """
        Post-initialization to ensure properties are processed correctly.
        """
        super().__post_init__()

        if self.properties is not None:
            self.properties = {
                key: Schema.extract(name=key, data=value, suffix=self.address) for key, value in self.properties.items()
            }

        if self.pattern_properties is not None:
            self.pattern_properties = {
                key: Schema.extract(name=f"pattern[{key}]", data=value, suffix=self.address)
                for key, value in self.pattern_properties.items()
            }


class String(Type):
    """
    String schema for the reader.
        See: https://json-schema.org/draft-04/draft-fge-json-schema-validation-00#rfc.section.5.2
    """

    pattern: str | None = rad()
    min_length: int | None = rad()
    max_length: int | None = rad()
