from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ._basic import Basic
from ._reader import ValueKeys, rad

if TYPE_CHECKING:
    from ._manager import Manager
    from ._type import Array, Object


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
        prefix: str | None = None,
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
        prefix
            An optional prefix to append to the schema's address.
        kwargs
            Additional keyword arguments.

        Returns
        -------
            A Schema instance.
        """
        if (reader := cls.Selectors.reader(cls, data)) is None:
            return super().extract(name=name, data=data, manager=manager, prefix=prefix, **kwargs)

        return reader.extract(name=name, data=data, manager=manager, prefix=prefix, **kwargs)

    def __post_init__(self):
        """
        Post-initialization to process definitions
        """
        from ._link import Ref

        super().__post_init__()

        if self.definitions is not None:
            if isinstance(self.definitions, Ref):
                with self.manager.lock():
                    self.definitions = self.definitions.resolve().definitions
            elif self.Selectors.REF in self.definitions:
                self.definitions = Schema.extract(data=self._simplify(self.definitions), **self._sub_reader_kwargs("definitions"))
            elif isinstance(self.definitions, Mapping):
                self.definitions = {
                    key: Schema.extract(data=self._simplify(value), **self._sub_reader_kwargs(f"definitions/{key}"))
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

        if self.all_of is not None:
            self.all_of = [
                Schema.extract(data=self._simplify(item), **self._sub_reader_kwargs(f"all_of_{index}"))
                for index, item in enumerate(self.all_of)
            ]

    def resolve(self) -> Object | Array:
        """
        Specialized resolve method for allOf schemas
        """
        if len(self.all_of) == 0:
            raise self.ResolutionError("No schemas to resolve in 'allOf'.")

        data = self.all_of[0].resolve().data
        data.update(self.data)
        del data[self.KeyWords.ALL_OF]

        resolved = type(self).extract(data=data, **self.non_data)

        for item in self.all_of[1:]:
            resolved.merge(item.resolve())

        return resolved.resolve()


class AnyOf(Schema):
    """
    Schema for 'anyOf' keyword.
    """

    any_of: list[Schema] = rad()

    def __post_init__(self):
        """Post-initialization to process any_of list."""
        super().__post_init__()

        self.any_of = [
            Schema.extract(data=self._simplify(item), **self._sub_reader_kwargs(f"any_of_{index}"))
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

        self.not_ = Schema.extract(data=self._simplify(self.not_), **self._sub_reader_kwargs("not"))

    def merge(self, other: Not):
        """
        Merge another Not schema into this one.

        Parameters
        ----------
        other
            The other Not schema instance to merge.
        """
        if not isinstance(other, Not):
            raise self.MergeError(f"Cannot merge {type(other)} into Not schema.")

        self.not_.merge(other.not_)


class OneOf(Schema):
    """
    Schema for 'oneOf' keyword.
    """

    one_of: list[Schema] = rad()

    def __post_init__(self):
        """Post-initialization to process one_of list."""
        super().__post_init__()

        self.one_of = [
            Schema.extract(data=self._simplify(item), **self._sub_reader_kwargs(f"one_of_{index}"))
            for index, item in enumerate(self.one_of)
        ]
