from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ._basic import Basic
from ._reader import ValueKeys, rad

if TYPE_CHECKING:
    from ._manager import Manager


class Schema(Basic):
    """
    Main reader object
    """

    definitions: dict[str, Schema] | None = rad()
    enum: list[str] | None = rad()

    class Selectors(ValueKeys):
        """
        Enumeration for schema selectors.
        """

        ALL_OF = "allOf"
        ANY_OF = "anyOf"
        NOT = "not"
        ONE_OF = "oneOf"
        TYPE = "type"
        REF = "$ref"
        TAG = "tag"

        @classmethod
        def reader(cls, object_type: type[object], data: dict[str, any]) -> type[Schema] | None:
            """
            Get the reader class for a given selector value.

            Parameters
            ----------
            object_type
                The type of the object to read.

            data
                The data dictionary to determine the schema class.

            Returns
            -------
                The schema class corresponding to the value.
            """
            from ._link import Ref, Tag
            from ._type import Type

            if sum(True for key in cls if data.get(key) is not None) > 1:
                raise cls.UnhandledKeyError(
                    f"Multiple schema selectors found in data: {', '.join(key for key in cls if data.get(key) is not None)}."
                )

            if cls.TYPE in data and not issubclass(object_type, Type):
                return Type

            if cls.ALL_OF in data and not issubclass(object_type, AllOf):
                return AllOf

            if cls.ANY_OF in data and not issubclass(object_type, AnyOf):
                return AnyOf

            if cls.NOT in data and not issubclass(object_type, Not):
                return Not

            if cls.ONE_OF in data and not issubclass(object_type, OneOf):
                return OneOf

            if cls.REF in data and not issubclass(object_type, Ref):
                return Ref

            if cls.TAG in data and not issubclass(object_type, Tag):
                return Tag

            return None

    @classmethod
    def extract(
        cls,
        name: str | None,
        data: dict[str, Any] | None,
        manager: Manager,
        suffix: str | None = None,
        **kwargs,
    ) -> Schema:
        """
        Extract a schema instance from a dictionary.

        Parameters
        ----------
        name
            The name of the schema.
        data
            The data dictionary to extract the schema from.
        manager
            The manager to register the schema with.
        suffix
            An optional suffix to append to the schema name.
        kwargs
            Additional keyword arguments.

        Returns
        -------
            A Schema instance.
        """
        if (reader := cls.Selectors.reader(cls, data)) is None:
            return super().extract(name=name, data=data, manager=manager, suffix=suffix, **kwargs)

        return reader.extract(name=name, data=data, manager=manager, suffix=suffix, **kwargs)

    def __post_init__(self):
        """
        Post-initialization to process definitions
        """
        super().__post_init__()

        if self.definitions is not None:
            if self.Selectors.REF in self.definitions:
                self.definitions = Schema.extract(
                    name="definitions", data=self.definitions, manager=self.manager, suffix=self.address
                )
            elif isinstance(self.definitions, Mapping):
                self.definitions = {
                    key: Schema.extract(name=key, data=value, manager=self.manager, suffix=f"definitions@{self.address}")
                    for key, value in self.definitions.items()
                }
            else:
                raise self.UnreadableDataError(f"Expected 'definitions' to be a Mapping or a $ref, got {type(self.definitions)}.")


class AllOf(Schema):
    """
    Schema for 'allOf' keyword.
    """

    all_of: list[Schema] = rad()

    def __post_init__(self):
        """Post-initialization to process all_of list."""
        super().__post_init__()

        self.all_of = [
            Schema.extract(name=f"all_of_{index}", data=item, manager=self.manager, suffix=self.address)
            for index, item in enumerate(self.all_of)
        ]


class AnyOf(Schema):
    """
    Schema for 'anyOf' keyword.
    """

    any_of: list[Schema] = rad()

    def __post_init__(self):
        """Post-initialization to process any_of list."""
        super().__post_init__()

        self.any_of = [
            Schema.extract(name=f"any_of_{index}", data=item, manager=self.manager, suffix=self.address)
            for index, item in enumerate(self.any_of)
        ]


class Not(Schema):
    """
    Schema for 'not' keyword.
    """

    not_: Schema = rad("not")

    def __post_init__(self):
        """Post-initialization to process not_ list."""
        super().__post_init__()

        self.not_ = Schema.extract(name="not", data=self.not_, manager=self.manager, suffix=self.address)


class OneOf(Schema):
    """
    Schema for 'oneOf' keyword.
    """

    one_of: list[Schema] = rad()

    def __post_init__(self):
        """Post-initialization to process one_of list."""
        super().__post_init__()

        self.one_of = [
            Schema.extract(name=f"one_of_{index}", data=item, manager=self.manager, suffix=self.address)
            for index, item in enumerate(self.one_of)
        ]
