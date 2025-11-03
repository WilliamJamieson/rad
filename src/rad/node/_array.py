"""
Base classes for RAD data nodes.
"""

from __future__ import annotations

from collections.abc import MutableSequence
from types import GenericAlias
from typing import Self, TypeVar

from asdf.lazy_nodes import AsdfListNode

from ._node import Node

__all__ = ("ArrayNode",)

_ArrayItem = TypeVar("_ArrayItem")


class ArrayNode(MutableSequence[_ArrayItem], Node[list[_ArrayItem]]):
    """
    Base class for handling all "array" (list-like) data nodes for RAD schemas.
    """

    __slots__ = ()

    def __init__(
        self,
        node: list[_ArrayItem] | AsdfListNode | Self | None = None,
        *,
        read_tag: str | None = None,
        parent: Node | None = None,
        wrapper: type | GenericAlias | None = None,
    ):
        super().__init__(node, read_tag=read_tag, parent=parent, wrapper=wrapper)

        if node is None:
            self._data = []
        elif isinstance(node, list | AsdfListNode):
            self._data = node
        elif isinstance(node, ArrayNode):
            self._data = node._data
        else:
            raise ValueError("Initializer only accepts lists")

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = value

    def __delitem__(self, index) -> None:
        del self._data[index]

    def __len__(self) -> int:
        return len(self._data)

    def insert(self, index, value):
        self._data.insert(index, value)

    def __asdf_traverse__(self) -> list[_ArrayItem]:
        return list(self)

    def __setattr__(self, key, value):
        if key in Node.__slots__:
            Node.__dict__[key].__set__(self, value)
        else:
            raise AttributeError(f"Cannot set attribute {key}, only allowed are {Node.__slots__}")

    def __eq__(self, other):
        if isinstance(other, ArrayNode):
            return self._data == other.data
        elif isinstance(other, list | AsdfListNode):
            return self._data == other
        else:
            return False

    @property
    def data(self) -> list[_ArrayItem]:
        """Legacy API to get the underlying data for this node"""
        return self._data
