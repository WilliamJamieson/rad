from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Self

from ._manager import Manager
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
    def extract(cls, name: str, data: dict[str, Any], manager: Manager, prefix: str | None = None, **kwargs) -> Self:
        """
        Extract a schema instance from a dictionary.

        Parameters
        ----------
        name:
            The name of the schema
        data:
            The data dictionary to read the schema from
        manager:
            The manager to register the schema with
        prefix:
            The prefix used to identify the schema this is a subschema

        Returns
        -------
            An instance of the schema class.
        """
        if cls is Type:
            if "type" not in data:
                raise cls.UnreadableDataError("Missing 'type' key in data.")

            return cls.TypeKeys.reader(data).extract(name=name, data=data, manager=manager, prefix=prefix, **kwargs)
        return super().extract(name=name, data=data, manager=manager, prefix=prefix, **kwargs)


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
        self.type = self.TypeKeys.ARRAY.value

        if isinstance(self.items, Sequence):
            self.items = [
                Schema.extract(data=self._simplify(item), **self._sub_reader_kwargs(f"item_{index}"))
                for index, item in enumerate(self.items)
            ]
        elif isinstance(self.items, Mapping):
            self.items = [Schema.extract(data=self._simplify(self.items), **self._sub_reader_kwargs("items"))]
        elif self.items is not None:
            raise self.UnreadableDataError(f"Expected 'items' to be a list, dict, or Schema instance, got {type(self.items)}.")

    def resolve(self) -> Self:
        """
        Resolve the schema instance against the manager.

        Parameters
        ----------
        manager:
            The manager to resolve the schema against

        Returns
        -------
            The resolved schema instance.
        """
        resolved = super().resolve()

        if isinstance(resolved.items, Sequence):
            resolved.items = [item.resolve() for item in resolved.items]
        elif isinstance(resolved.items, Schema):
            resolved.items = resolved.items.resolve()

        return type(self).extract(data=resolved.data, **self.non_data)

    def merge(self, other: Array):
        """
        Merge another Array schema into this one.

        Parameters
        ----------
        other
            The Array schema to merge with this one.
        """
        if not isinstance(other, Array):
            raise self.MergeError(f"Cannot merge non-Array schema: {type(other)}.")

        if self.items is not None or other.items is not None:
            self.items = (self.items or []) + (other.items or [])

        if self.additional_items is not None and other.additional_items is not None:
            self.additional_items = self.additional_items or other.additional_items
        elif self.additional_items is None and other.additional_items is not None:
            self.additional_items = other.additional_items

        if self.min_items is not None and other.min_items is not None:
            self.min_items = max(self.min_items, other.min_items)
        elif self.min_items is None and other.min_items is not None:
            self.min_items = other.min_items

        if self.max_items is not None and other.max_items is not None:
            self.max_items = max(self.max_items, other.max_items)
        elif self.max_items is None and other.max_items is not None:
            self.max_items = other.max_items


class Boolean(Type):
    """Boolean schema for the region"""

    def __post_init__(self):
        """
        Post-initialization to ensure properties are processed correctly.
        """
        super().__post_init__()
        self.type = self.TypeKeys.BOOLEAN.value


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

    def __post_init__(self):
        """
        Post-initialization to ensure properties are processed correctly.
        """
        super().__post_init__()
        self.type = self.TypeKeys.NUMBER.value


class Null(Type):
    """
    Null schema for the reader.
        Note: In JSON Schema Draft-04, null types do not have specific keys.
    """

    def __post_init__(self):
        """
        Post-initialization to ensure properties are processed correctly.
        """
        super().__post_init__()
        self.type = self.TypeKeys.NULL.value


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
        self.type = self.TypeKeys.OBJECT.value

        if self.properties is not None:
            self.properties = {
                key: Schema.extract(data=self._simplify(value), **self._sub_reader_kwargs(key))
                for key, value in self.properties.items()
            }

        if self.pattern_properties is not None:
            self.pattern_properties = {
                key: Schema.extract(data=self._simplify(value), **self._sub_reader_kwargs(f"pattern[{key}]"))
                for key, value in self.pattern_properties.items()
            }

    def resolve(self) -> Self:
        """
        Resolve the schema instance against the manager.

        Parameters
        ----------
        manager:
            The manager to resolve the schema against

        Returns
        -------
            The resolved schema instance.
        """
        data = self.data
        del data[self.KeyWords.PROPERTIES]
        del data[self.KeyWords.PATTERN_PROPERTIES]

        resolved = type(self).extract(data=data, **self.non_data)

        if self.properties is not None:
            resolved.properties = {key: value.resolve() for key, value in self.properties.items()}

        if self.pattern_properties is not None:
            resolved.pattern_properties = {key: value.resolve() for key, value in self.pattern_properties.items()}

        return resolved

    def merge(self, other: Object):
        """
        Merge another Object schema into this one.

        Parameters
        ----------
        other
            The Object schema to merge with this one.
        """
        if not isinstance(other, Object):
            raise self.MergeError(f"Cannot merge non-Object schema: {type(other)}.")

        if self.properties is not None or other.properties is not None:
            self.properties = self.properties or {}
            for key, value in (other.properties or {}).items():
                if key in self.properties:
                    self.properties[key].merge(value)
                else:
                    self.properties[key] = value

        if self.pattern_properties is not None or other.pattern_properties is not None:
            self.pattern_properties = self.pattern_properties or {}
            for key, value in (other.pattern_properties or {}).items():
                if key in self.pattern_properties:
                    self.pattern_properties[key].merge(value)
                else:
                    self.pattern_properties[key] = value

        if self.required is not None or other.required is not None:
            self.required = list(set(self.required or []) | set(other.required or []))

        if self.additional_properties is not None and other.additional_properties is not None:
            self.additional_properties = self.additional_properties or other.additional_properties
        elif self.additional_properties is None and other.additional_properties is not None:
            self.additional_properties = other.additional_properties

        if self.max_properties is not None and other.max_properties is not None:
            self.max_properties = max(self.max_properties, other.max_properties)
        elif self.max_properties is None and other.max_properties is not None:
            self.max_properties = other.max_properties

        if self.min_properties is not None and other.min_properties is not None:
            self.min_properties = max(self.min_properties, other.min_properties)
        elif self.min_properties is None and other.min_properties is not None:
            self.min_properties = other.min_properties

        if self.dependencies is not None or other.dependencies is not None:
            self.dependencies = {**(self.dependencies or {}), **(other.dependencies or {})}

    def archive_data(self, name: str) -> dict[str, Any] | None:
        data = super().archive_data(name)

        if self.properties is None:
            return data

        properties = []
        for key, schema in self.properties.items():
            entry = schema.archive_data(key)
            if entry is not None:
                properties.append(entry)

        if not properties:
            return data

        data = data or self._archive_data_header(name)
        data["properties"] = properties

        return data


class String(Type):
    """
    String schema for the reader.
        See: https://json-schema.org/draft-04/draft-fge-json-schema-validation-00#rfc.section.5.2
    """

    pattern: str | None = rad()
    min_length: int | None = rad()
    max_length: int | None = rad()

    def __post_init__(self):
        """
        Post-initialization to ensure properties are processed correctly.
        """
        super().__post_init__()
        self.type = self.TypeKeys.STRING.value

    def merge(self, other: String):
        """
        Merge another String schema into this one.

        Parameters
        ----------
        other
            The String schema to merge with this one.
        """
        print(self)
        print(other)
        if not isinstance(other, String):
            raise self.MergeError(f"Cannot merge non-String schema: {type(other)}.")

        if self.pattern is None and other.pattern is not None:
            self.pattern = other.pattern

        if self.min_length is not None and other.min_length is not None:
            self.min_length = max(self.min_length, other.min_length)
        elif self.min_length is None and other.min_length is not None:
            self.min_length = other.min_length

        if self.max_length is not None and other.max_length is not None:
            self.max_length = max(self.max_length, other.max_length)
        elif self.max_length is None and other.max_length is not None:
            self.max_length = other.max_length
