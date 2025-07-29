from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from dataclasses import Field, dataclass, field, fields
from enum import EnumMeta, StrEnum, unique
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from ._manager import Manager

__all__ = ("Reader", "ValueKeys", "rad")


def rad(schema_key: str | None = None, **kwargs) -> Field:
    """Create a dataclass field with schema metadata.

    Parameters
    ----------
    schema_key, optional
        The key to use for the schema metadata, by default None

    Returns
    -------
        A dataclass field with the specified metadata.
    """
    metadata = kwargs.pop("metadata", {})
    metadata["schema_key"] = schema_key
    return field(metadata=metadata, **kwargs)


def _snake_to_camel(snake_case_string: str) -> str:
    """
    Converts a snake_case string to camelCase.

    Args:
        snake_case_string (str): The string in snake_case format.

    Returns:
        str: The converted string in camelCase format.
    """
    words = snake_case_string.split("_")
    # Capitalize the first letter of each word except the first one
    camel_case_words = [words[0]] + [word.capitalize() for word in words[1:]]
    return "".join(camel_case_words)


@unique
class KeyWords(StrEnum):
    """Enumeration of the keywords used in the schema component"""

    @property
    def reader_name(self) -> str:
        """Get the reader name for the keyword."""
        return self.name.lower()

    @classmethod
    def extract(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract the keywords from the data dictionary.

        Parameters
        ----------
        data:
            The data dictionary to extract the keywords from

        Returns
        -------
            A dictionary with the keywords as keys and their values.
        """
        return {key.reader_name: data.get(key) for key in cls}

    @classmethod
    def new(cls, schema: Reader) -> type[KeyWords]:
        """
        Create a new enumeration for the schema's keywords.

        Parameters
        ----------
        schema:
            The schema to create the keywords for

        Returns
        -------
            A new enumeration class with the schema's keywords.
        """
        key_words: list[tuple[str, str]] = []
        for field_ in fields(schema):
            if "schema_key" in field_.metadata:
                name = field_.name.upper()
                schema_key = field_.metadata["schema_key"]

                if schema_key is None:
                    schema_key = _snake_to_camel(field_.name)

                key_words.append((name, schema_key))

        return unique(cls("KeyWords", key_words))


@dataclass
class Reader(ABC):
    """
    Base class for schema metadata reading

    Attributes
    ----------
    name:
        The name of the schema
    prefix:
        The prefix used to identify the schema this is a subschemaA
    """

    name: str
    prefix: str | None
    manager: Manager

    class UnreadableDataError(ValueError):
        """Exception raised when the data cannot be read by the schema."""

    class ResolutionError(ValueError):
        """Exception raised when the schema cannot be resolved."""

    class MergeError(ValueError):
        """Exception raised when the schema cannot be merged."""

    @property
    def address(self) -> str:
        """Get the address of the schema within the rad schemas."""
        address = self.name
        if self.prefix:
            address = f"{self.prefix}{'#' if '#' not in self.prefix else ''}/{address}"

        return address

    @property
    @abstractmethod
    def KeyWords(self) -> type[KeyWords]:
        """
        Get the enumeration for the schema's syntax keywords

        Note
        ----
        This is only an abstract property so that subclasses are forced to implement it,
        it is intended to a subclass of `KeyWords` that defined within the parser object.
        """

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        cls = dataclass(cls)
        cls.KeyWords = KeyWords.new(cls)

    def __post_init__(self):
        """
        Post-initialization to process definitions
        """
        self.manager.register(self)

    @property
    def data(self) -> dict[str, Any]:
        """
        Get the data representation of the schema.

        Returns
        -------
            A dictionary representation of the schema.
        """
        data = {}
        for field_ in fields(self):
            if "schema_key" in field_.metadata:
                name = field_.metadata.get("schema_key", None)
                if name is None:
                    name = _snake_to_camel(field_.name)
                data[name] = getattr(self, field_.name)

        return data

    @property
    def non_data(self) -> dict[str, Any]:
        """
        Get the non-data representation of the schema.

        Returns
        -------
            A dictionary representation of the schema excluding data fields.
        """

        data = {}
        for field_ in fields(self):
            if "schema_key" not in field_.metadata:
                data[field_.name] = getattr(self, field_.name)

        return data

    def _sub_reader_kwargs(self, name: str) -> dict[str, Any]:
        """
        Get the keyword arguments for a sub-reader.

        Returns
        -------
            A dictionary representation of the sub-reader's keyword arguments.
        """
        kwargs = self.non_data
        kwargs["name"] = name
        kwargs["prefix"] = self.address

        return kwargs

    def _simplify(self, value: Any) -> dict[str, Any]:
        """
        Simplify the value to a dictionary representation.

        Parameters
        ----------
        value:
            The value to simplify

        Returns
        -------
            A dictionary representation of the value.
        """
        if isinstance(value, Reader):
            return value.data

        return value

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
        return cls(name=name, prefix=prefix, manager=manager, **cls.KeyWords.extract(data), **kwargs)

    def re_extract(self, data: dict[str, Any], manager: Manager) -> Self:
        """
        Re-extract the schema instance from the manager.

        Parameters
        ----------
        data:
            The data dictionary to re-extract the schema from
        manager:
            The manager to re-extract the schema from

        Returns
        -------
            A new instance of the schema class.
        """
        kwargs = self.non_data
        kwargs["manager"] = manager

        return type(self).extract(data=data, **kwargs)

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
        data = {}
        for key, value in self.data.items():
            if isinstance(value, Reader):
                data[key] = value.resolve()
            else:
                data[key] = value

        return type(self).extract(data=data, **self.non_data)

    def merge(self, other: Self):
        """
        Merge another schema instance into this one.

        Parameters
        ----------
        other:
            The other schema instance to merge
        """
        raise NotImplementedError(f"Merge method is not implemented for {type(self).__name__} schema.")


class _AbstractStrEnumMeta(ABCMeta, EnumMeta): ...


class ValueKeys(ABC, StrEnum, metaclass=_AbstractStrEnumMeta):
    """Abstract base class for value keys in schemas."""

    class UnhandledKeyError(ValueError):
        """Exception raised when an unhandled key is encountered in the schema."""

    @classmethod
    @abstractmethod
    def reader(cls, data: dict[str, Any]) -> type[Reader]:
        """
        Select the schema class based on the value.

        Parameters
        ----------
        data
            The data dictionary to determine the schema class.

        Returns
        -------
            The schema class corresponding to the value.
        """
