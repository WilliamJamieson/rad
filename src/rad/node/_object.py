"""
Base classes for RAD data nodes.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from inspect import isclass
from types import GenericAlias, MappingProxyType
from typing import Any, Self, TypeVar, get_args, get_origin, get_type_hints

from asdf.lazy_nodes import AsdfDictNode

from ._node import Node

__all__ = ("ObjectNode",)


_ObjectEntry = TypeVar("_ObjectEntry")


class ObjectNode(MutableMapping[str, _ObjectEntry | Node], Node[dict[str, _ObjectEntry | Node]]):
    """
    Base class for handling all "object" (dict-like) data nodes for RAD schemas.
    """

    __slots__ = ()

    __required__: tuple[str, ...] = ()
    __keywords__: tuple[str, ...] = ()
    __alias__: MappingProxyType[str, str] = MappingProxyType({})
    __wrappers__: MappingProxyType[str, tuple[type[Node], type | GenericAlias | None]] = MappingProxyType({})

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)

        # Gather up the required, keywords, and alias information recursively from base classes
        required = set(cls.__required__)
        keywords = set(cls.__keywords__)
        alias = dict(cls.__alias__)
        for cls_ in cls.__bases__:
            required.update(set(cls_.__required__))
            keywords.update(set(cls_.__keywords__))
            alias.update(cls_.__alias__)

        cls.__required__ = tuple(sorted(required))
        cls.__keywords__ = tuple(sorted(keywords))
        cls.__alias__ = MappingProxyType(alias)

        # Gather up the wrappers for this class
        wrappers = {}
        for key, type_ in get_type_hints(cls).items():
            if key not in cls.__keywords__:
                continue

            if isclass(type_) and issubclass(type_, Node):
                wrappers[key] = (type_, None)
                continue

            origin = get_origin(type_)
            if isclass(origin) and issubclass(origin, Node):
                type_args = get_args(type_)
                wrappers[key] = (origin, type_args[0] if type_args else None)

        cls.__wrappers__ = MappingProxyType(wrappers)

    def __init__(
        self,
        node: dict[str, Any] | AsdfDictNode | Self | None = None,
        *,
        read_tag: str | None = None,
        parent: Node | None = None,
        wrapper: type | GenericAlias | None = None,
    ):
        super().__init__(node, read_tag=read_tag, parent=parent)

        # Handle if we are passed different data types
        if node is None:
            self._data = {}
        elif isinstance(node, dict | AsdfDictNode):
            self._data = node
        elif isinstance(node, ObjectNode):
            self._data = node._data
        else:
            raise ValueError("Initializer only accepts dict-like objects")

    def _get_key(self, key: str) -> str:
        return self.__alias__.get(key, key)

    def _in_data(self, key: str) -> bool:
        return self._get_key(key) in self._data

    def _get_data(self, key: str):
        return self._data[self._get_key(key)]

    def _set_data(self, key: str, value: _ObjectEntry | Node) -> None:
        self._data[self._get_key(key)] = value

    def _wrap(self, key: str, value: _ObjectEntry | Node):
        """
        Wrap the given key/value pair into the appropriate node.

        Parameters
        ----------
        key
            The key to wrap.
        value
            The value to wrap.

        Returns
        -------
            The wrapped value and a boolean indicating if wrapping was performed.
        """
        # Only wrap if we are in the correct version and we have a wrapper defined
        #   for this key
        if self.is_current and key in self.__wrappers__:
            wrapper, wrapper_args = self.__wrappers__[key]
            # If the value is not already wrapped, wrap it
            if not isinstance(value, wrapper):
                return wrapper(value, parent=self, wrapper=wrapper_args), True

            # If the value is already wrapped but has the wrong parent, re-wrap it
            #   with the correct parent being sure to copy it so we don't modify
            #   the original node
            if value._parent is not self or value._wrapper != wrapper_args:
                return value.copy(parent=self, wrapper=wrapper_args), True

        # Otherwise just return the value as is
        return value, False

    def _get_node(self, key: str):
        """
        Get the node value for the given key, wrapping it if necessary.

        Parameters
        ----------
        key : str
            The key to get.

        Returns
        -------
        Any
            The value for the given key.

        Side Effects
        ------------
        If the value is unwrapped, it will be wrapped and stored back into the node.
        """
        if self._in_data(key):
            value, wrapped = self._wrap(key, self._get_data(key))
            if wrapped:
                self._set_data(key, value)

            return value

        # Raise the correct error for the attribute not being found
        raise AttributeError(f"No such attribute ({key}) found in node: {type(self)}")

    def _set_node(self, key: str, value: _ObjectEntry | Node) -> None:
        """
        Set the node value for the given key, wrapping it if necessary.

        Parameters
        ----------
        key
            The key to set.
        value
            The value to set.

        Side Effects
        ------------
        If the value needs to be wrapped, it will be wrapped before being set.
        """
        # Wrap the value if necessary
        value, _ = self._wrap(key, value)

        self._set_data(key, value)

    def __getattr__(self, key: str):
        """
        Permit accessing dict keys as attributes, assuming they are legal Python
        variable names.
        """
        # Private values should have already been handled by the __getattribute__ method
        #   bail out if we are falling back on this method
        if key.startswith("_"):
            raise AttributeError(f"Cannot access private attribute {key}, only allowed are {Node.__slots__}")

        return self._get_node(key)

    def __setattr__(self, key, value):
        """
        Permit assigning dict keys as attributes.
        """
        # Private keys should just be in the normal __dict__
        if key[0] != "_":
            self._set_node(key, value)
        else:
            if key in Node.__slots__:
                Node.__dict__[key].__set__(self, value)
            else:
                raise AttributeError(f"Cannot set private attribute {key}, only allowed are {Node.__slots__}")

    def __delattr__(self, name: str):
        if name in Node.__slots__:
            super().__delattr__(name)

        elif name[0] != "_":
            if self._in_data(name):
                self.__delitem__(name)
            else:
                raise AttributeError(f"No such attribute ({name}) found in node: {type(self)}")
        else:
            raise AttributeError(f"Private attribute {name} is not allowed, only allowed are {Node.__slots__}")

    def __getitem__(self, key: str):
        """Dictionary style access data"""
        try:
            return self._get_node(key)
        except AttributeError as e:
            raise KeyError(f"No such key ({key}) found in node") from e

    def __setitem__(self, key: str, value: _ObjectEntry | Node):
        """Dictionary style access set data"""
        self._set_node(key, value)

    def __delitem__(self, key: str):
        """Dictionary style access delete data"""
        del self._data[self._get_key(key)]

    def __len__(self):
        """Define length of the node"""
        return len(self._data)

    def __iter__(self):
        """Define iteration"""
        return iter(self._data)

    def __asdf_traverse__(self):
        """Asdf traverse method for things like info/search"""
        return dict(self)

    # def __dir__(self):
    #     return set(super().__dir__()) | set(self._data.keys() | set(self.__keywords__))

    # def __repr__(self):
    #     """Define a representation"""
    #     return repr(self._data)

    # def _recursive_items(self):
    #     from ._array import ArrayNode

    #     def recurse(tree, path=None):
    #         path = path or []  # Avoid mutable default arguments
    #         if isinstance(tree, ObjectNode | dict | AsdfDictNode):
    #             for key, val in tree.items():
    #                 yield from recurse(val, [*path, key])
    #         elif isinstance(tree, ArrayNode | list | tuple | AsdfListNode):
    #             for i, val in enumerate(tree):
    #                 yield from recurse(val, [*path, i])
    #         elif tree is not None:
    #             yield (".".join(str(x) for x in path), tree)

    #     yield from recurse(self)

    # def to_flat_dict(self, include_arrays=True, recursive=False):
    #     """
    #     Returns a dictionary of all of the schema items as a flat dictionary.

    #     Each dictionary key is a dot-separated name.  For example, the
    #     schema element ``meta.observation.date`` will end up in the
    #     dictionary as::

    #         { "meta.observation.date": "2012-04-22T03:22:05.432" }

    #     """

    #     def convert_val(val):
    #         """
    #         Unwrap the tagged scalars if necessary.
    #         """
    #         if isinstance(val, datetime):
    #             return val.isoformat()
    #         elif isinstance(val, Time):
    #             return str(val)
    #         return val

    #     item_getter = self._recursive_items if recursive else self.items

    #     if include_arrays:
    #         return {key: convert_val(val) for (key, val) in item_getter()}
    #     else:
    #         return {
    #             key: convert_val(val) for (key, val) in item_getter() if not isinstance(val, np.ndarray | ndarray.NDArrayType)
    #         }
