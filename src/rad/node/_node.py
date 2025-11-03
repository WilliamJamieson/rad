"""
Base classes for RAD data nodes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import GenericAlias
from typing import Generic, Protocol, Self, TypeVar

__all__ = ("Node",)


class _SupportsCopy(Protocol):
    def copy(self) -> Self: ...


_NodeData = TypeVar("_NodeData", bound=_SupportsCopy)


class Node(Generic[_NodeData], ABC):
    """
    Class to provide the common API for all Node objects
    """

    __slots__ = ("_data", "_parent", "_read_tag", "_wrapper")

    _data: _NodeData
    _read_tag: str | None
    _parent: Node | None
    _wrapper: type | GenericAlias | None

    __uri__: str | None = None
    __tag__: str | None = None

    def __init__(
        self, *args, read_tag: str | None = None, parent: Node | None = None, wrapper: type | GenericAlias | None = None
    ):
        self._read_tag = read_tag
        self._parent = parent
        self._wrapper = wrapper

    def copy(self, *, parent: Node | None = None, wrapper: type | GenericAlias | None = None) -> Node:
        """
        Create a copy of this node
        """
        instance = type(self).__new__(type(self))
        instance._data = self._data.copy()

        instance._read_tag = self._read_tag
        instance._parent = self._parent if parent is None else parent
        instance._wrapper = self._wrapper if wrapper is None else wrapper

        return instance

    @property
    def is_current(self) -> bool:
        """
        Check if the version of this node matches the schema version.

        Note this recurses up the node tree to the root to determine the currentness.
        -> if no read_tag -> check parent
            - If no parent this is current  (read_tag = None, parent = None) -> True
            - If parent exists, check parent's is_current() (read_tag = None, parent != None)) -> parent.is_current()
        -> if read_tag exists but no __tag__ -> check parent
            - If no parent this is current  (read_tag != None, __tag__ = None, parent = None) -> True
            - If parent exists, check parent's is_current() (read_tag != None, __tag__ = None, parent != None) -> parent.is_current()
        -> if read_tag and __tag__ exist -> compare them directly
            - If they match, this is current -> (read_tag != None, __tag__ != None, read_tag == __tag__) -> True
            - If they don't match, this is not current -> (read_tag != None, __tag__ != None, read_tag != __tag__) -> False

        read_tag will only be set by ASDF when reading in data at the top level datamodel. This
            datamodel will be a subclass of some node class with a specific __tag__ defined.
            --> This means that read_tag should be None for the most part except for when a
                root node is being created from ASDF data. In this case, if the read_tag
                matches the __tag__ of the node class, then everything under that node is considered
                current and can be automatically wrapped.  Otherwise we have a version mismatch
                and so automatic wrapping may not be safe.
        """
        if self._read_tag is None or self.__tag__ is None:
            return self._parent is None or self._parent.is_current
        else:
            return self._read_tag == self.__tag__

    # @classmethod
    # def sub_classes(cls) -> set[type[Self]]:
    #     """
    #     Get all subclasses of a NodeClass class.

    #     This recursively gathers all the subclasses of this class. It excludes
    #     any classes with "Model" in the name as those are the data model classes
    #     and not considered node classes, though they do inherit from the node
    #     classes.

    #     This is used to gather all the node classes so they can be registered with
    #     the ASDF converters. Note that one MUST import all the node classes we want
    #     support before calling this method in the converter as ASDF will cache the
    #     supported types upon loading the ASDF extension.
    #     """
    #     subclasses = {cls}

    #     for subclass in cls.__subclasses__():
    #         if "Model" not in subclass.__name__:
    #             subclasses.add(subclass)
    #             subclasses.update(subclass.sub_classes())

    #     return subclasses

    @abstractmethod
    def __asdf_traverse__(self):
        """
        ASDF traverse method for things like info/search
        """
