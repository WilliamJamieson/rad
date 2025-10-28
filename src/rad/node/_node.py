"""
Base classes for RAD data nodes.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import MutableMapping, MutableSequence
from datetime import datetime
from inspect import isclass
from types import GenericAlias, MappingProxyType, UnionType
from typing import TYPE_CHECKING, Any, Literal, Self, TypeVar, Union, get_args, get_origin, get_type_hints

import numpy as np
from asdf.lazy_nodes import AsdfDictNode, AsdfListNode
from asdf.tags.core import ndarray
from astropy.time import Time

__all__ = ("ArrayNode", "ObjectNode")

_NOSTR = "?"
_NONUM = -999999
_NOBOOL = False


class _NotSetType:
    pass


_NotSet = _NotSetType()


class _NodeMixin:
    """
    Mixin class to provide the common API for all Node objects
    """

    # This is a hack to avoid mypy and __slots__ inheritance issues concerning `_read_tag`
    #    ideally we would just define `_read_tag` like we did below, but mypy gets upset because
    #    __slots__ is defined so that the subclasses will be fully slotted. You can't have the
    #    same slot attributed defined in both parent classes when they are mixed together.
    if TYPE_CHECKING:
        __slots__ = ("_parent", "_read_tag")
    else:
        __slots__ = ()

    _read_tag: str | None
    _parent: _NodeMixin | None

    __uri__: str | None = None
    __tag__: str | None = None

    def __init__(self, *args, read_tag: str | None = None, parent: _NodeMixin | None = None, **kwargs):
        self._read_tag = read_tag
        self._parent = parent

    @abstractmethod
    def __asdf_traverse__(self):
        """
        ASDF traverse method for things like info/search
        """

    @property
    @abstractmethod
    def _node_data(self) -> dict[str, Any] | list[Any]:
        """
        Return the underlying data for this node
        """

    @_node_data.setter
    @abstractmethod
    def _node_data(self, value: Any) -> None:
        """
        Set the underlying data for this node
        """

    def copy(self, parent: _NodeMixin | None = None) -> _NodeMixin:
        """
        Create a copy of this node
        """
        instance = type(self).__new__(type(self))

        instance._read_tag = self._read_tag
        instance._node_data = self._node_data.copy()
        instance._parent = parent or self._parent

        return instance

    def is_current(self) -> bool:
        """
        Check if the version of this node matches the schema version.
        """
        if self._read_tag is None or self.__tag__ is None:
            return self._parent is None or self._parent.is_current()
        else:
            return self._read_tag == self.__tag__

    @classmethod
    def sub_classes(cls) -> set[type[Self]]:
        """
        Get all subclasses of a NodeClass class.

        This recursively gathers all the subclasses of this class. It excludes
        any classes with "Model" in the name as those are the data model classes
        and not considered node classes, though they do inherit from the node
        classes.

        This is used to gather all the node classes so they can be registered with
        the ASDF converters. Note that one MUST import all the node classes we want
        support before calling this method in the converter as ASDF will cache the
        supported types upon loading the ASDF extension.
        """
        subclasses = {cls}

        for subclass in cls.__subclasses__():
            if "Model" not in subclass.__name__:
                subclasses.add(subclass)
                subclasses.update(subclass.sub_classes())

        return subclasses

    @abstractmethod
    def _get_annotation(self, key: Any) -> Any:
        """
        Get the annotation for the given key.
        """

    @abstractmethod
    def __setitem__(self, key, value) -> None:
        pass

    def fill_default(self, key: int | str, *, minimal: bool = False, **kwargs) -> None:
        """
        Fill in the default value for the given key.

        Parameters
        ----------
        key : int | str
            The key to fill the default value for.

        minimal : bool, optional
            If True, fill in the minimal default values.

        Side Effects
        ------------
        The default value for the given key will be set in the node.
        """
        if (value := self._find_custom(str(key), minimal=minimal, **kwargs)) is _NotSet:
            value = self._find_default(self._get_annotation(key), minimal=minimal, **kwargs)

        if value is not _NotSet:
            self[key] = value

    def _find_custom(self, key: str, *, minimal: bool = False, **kwargs) -> Any:
        """
        Find a custom default value for the given key.

        Parameters
        ----------
        key : str
            The key to find the default value for.

        minimal : bool, optional
            If True, fill in the minimal default values.

        Returns
        -------
        Any
            The default value for the given key.
        """
        if hasattr(self, custom_finder := f"_find_default_{key}"):
            return getattr(self, custom_finder)(minimal=minimal, **kwargs)

        return _NotSet

    def _find_default(self, annotation: Any, *, minimal: bool = False, **kwargs) -> Any:
        """
        Find in the default value for the given key.

        Parameters
        ----------
        annotation : Any
            The annotation to find the default value for.

        minimal : bool, optional
            If True, fill in the minimal default values.

        Returns
        -------
        Any
            The default value for the given key.
        """
        if isclass(annotation):
            if annotation is type(None):
                return None

            if issubclass(annotation, int | float | str | bool):
                return self._find_scalar_default(annotation, minimal=minimal)

        origin = get_origin(annotation)
        annotation_args = get_args(annotation)

        if origin is np.ndarray:
            return self._find_ndarray_default(annotation, **kwargs)

        if origin is Literal:
            return self._find_literal_default(annotation, **kwargs)

        # In Python 3.14+ UnionType is an Alias for Union so we can drop the or
        #   check for UnionType in the future
        if origin is Union or origin is UnionType:
            return self._find_default(next(arg for arg in annotation_args if arg is not type(None)), minimal=minimal, **kwargs)

        raise ValueError(f"Cannot find default for key {annotation}, no node annotation found: {annotation}.")

    def _find_scalar_default(
        self, type_: type[int | float | str | bool], *, minimal: bool = False
    ) -> int | float | str | bool | _NotSetType:
        """
        Find in the default value for a scalar key.

        Parameters
        ----------
        type_ : type[int | float | str | bool]
            The type to find the default value for.

        minimal : bool, optional
            If True, fill in the minimal default values.

        Returns
        -------
        int | float | str | bool | _NotSet
            The default value for the given key.
        """

        if minimal:
            return _NotSet

        if type_ is int:
            return int(_NONUM)

        if type_ is float:
            return float(_NONUM)

        if type_ is str:
            return str(_NOSTR)

        if type_ is bool:
            return bool(_NOBOOL)

        raise ValueError(f"Cannot find scalar default for type {type_}")

    def _find_ndarray_default(
        self, type_: GenericAlias, *, shape: tuple[int, ...] | None = None, **kwargs
    ) -> np.ndarray | _NotSetType:
        """
        Find in the default value for an ndarray key.

        Parameters
        ----------
        type_ : GenericAlias
            The type to find the default value for.

        shape : tuple[int, ...] | None, optional
            The shape of the ndarray to create.

        Returns
        -------
        np.ndarray | _NotSet
            The default value for the given key.
        """

        if get_origin(type_) is not np.ndarray:
            raise ValueError(f"Cannot find ndarray default for type {type_}")

        shape_, dtype = get_args(type_)
        if isinstance(dtype, GenericAlias) and get_origin(dtype) is np.dtype:
            dtype = get_args(dtype)[0]

        if get_origin(shape_) is not tuple:
            raise ValueError(f"Cannot find ndarray default for type {type_}, shape is not a tuple")

        dims = get_args(shape_)
        ndims = None if dims[-1] is ... else len(dims)

        if shape is None:
            shape = (1,)
            if ndims is not None:
                shape = shape * ndims

        if ndims is not None and len(shape) != ndims:
            raise ValueError(f"Cannot find ndarray default for type {type_}, shape has incorrect number of dimensions")

        return np.zeros(shape=shape, dtype=dtype)

    def _find_literal_default(self, type_: GenericAlias, **kwargs) -> Any:
        """
        Find in the default value for a Literal key.

        Parameters
        ----------
        type_ : Literal
            The type to find the default value for.

        Returns
        -------
        Any
            The default value for the given key.
        """

        if get_origin(type_) is not Literal:
            raise ValueError(f"Cannot find Literal default for type {type_}")

        # Just return the first option listed
        return get_args(type_)[0]


class ObjectNode(MutableMapping, _NodeMixin):
    """
    Base class for handling all "object" (dict-like) data nodes for RAD schemas.
    """

    __slots__ = ("_data", "_parent", "_read_tag")

    _data: dict[str, Any]

    __required__: tuple[str, ...] = ()
    __keywords__: tuple[str, ...] = ()
    __alias__: MappingProxyType[str, str] = MappingProxyType({})
    __wrappers__: MappingProxyType[str, type[_NodeMixin]] = MappingProxyType({})

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
        cls.__wrappers__ = MappingProxyType(
            {key: type_ for key, type_ in get_type_hints(cls).items() if isclass(type_) and issubclass(type_, _NodeMixin)}
        )

    def __init__(self, node=None, *, read_tag: str | None = None, parent: _NodeMixin | None = None):
        super().__init__(node, read_tag=read_tag, parent=parent)

        # Handle if we are passed different data types
        if node is None:
            self._data = {}
        elif isinstance(node, dict | AsdfDictNode):
            self._data = node
        else:
            raise ValueError("Initializer only accepts dicts")

    def _get_annotation(self, key: str) -> Any:
        """
        Get the annotation for a given keyword

        Parameters
        ----------
        key : str
            The key to get the annotation for.

        Returns
        -------
        Any
            The annotation for the given key.
        """
        if key in self.__keywords__:
            return get_type_hints(type(self)).get(key)

        raise KeyError(f"No such keyword ({key}) found in node: {type(self)}")

    def _in_data(self, key: str) -> bool:
        if key in self.__alias__:
            key = self.__alias__[key]

        return key in self._data

    def _get_data(self, key: str) -> Any:
        if key in self.__alias__:
            key = self.__alias__[key]

        return self._data.get(key)

    def _set_data(self, key: str, value: Any) -> None:
        if key in self.__alias__:
            key = self.__alias__[key]

        self._data[key] = value

    def _wrap(self, key: str, value: Any) -> tuple[Any, bool]:
        """
        Wrap the given key/value pair into the appropriate node.

        Parameters
        ----------
        key : str
            The key to wrap.
        value : Any
            The value to wrap.

        Returns
        -------
        tuple[Any, bool]
            The wrapped value and a boolean indicating if wrapping was performed.
        """
        # Only wrap if we are in the correct version and we have a wrapper defined
        #   for this key
        if self.is_current() and key in self.__wrappers__:
            # If the value is not already wrapped, wrap it
            if not isinstance(value, wrapper := self.__wrappers__[key]):
                return wrapper(value, parent=self), True

            # If the value is already wrapped but has the wrong parent, re-wrap it
            #   with the correct parent being sure to copy it so we don't modify
            #   the original node
            if value._parent is not self:
                return value.copy(parent=self), True

        # Otherwise just return the value as is
        return value, False

    def _get_node(self, key: str) -> Any:
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

    def __getattr__(self, key: str):
        """
        Permit accessing dict keys as attributes, assuming they are legal Python
        variable names.
        """
        # Private values should have already been handled by the __getattribute__ method
        #   bail out if we are falling back on this method
        if key.startswith("_"):
            raise AttributeError(f"No attribute {key}")

        return self._get_node(key)

    def _set_node(self, key: str, value: Any) -> None:
        """
        Set the node value for the given key, wrapping it if necessary.

        Parameters
        ----------
        key : str
            The key to set.
        value : Any

        Side Effects
        ------------
        If the value needs to be wrapped, it will be wrapped before being set.
        """
        # Wrap the value if necessary
        value, _ = self._wrap(key, value)

        self._set_data(key, value)

    def __setattr__(self, key, value):
        """
        Permit assigning dict keys as attributes.
        """
        # Private keys should just be in the normal __dict__
        if key[0] != "_":
            self._set_node(key, value)
        else:
            if key in ObjectNode.__slots__:
                ObjectNode.__dict__[key].__set__(self, value)
            else:
                raise AttributeError(f"Cannot set private attribute {key}, only allowed are {ObjectNode.__slots__}")

    def __delattr__(self, name):
        if name in self.__slots__:
            super().__delattr__(name)

        elif name[0] != "_":
            self.__delitem__(name)

        else:
            raise AttributeError(f"No such attribute ({name}) found in node")

    def _recursive_items(self):
        def recurse(tree, path=None):
            path = path or []  # Avoid mutable default arguments
            if isinstance(tree, ObjectNode | dict | AsdfDictNode):
                for key, val in tree.items():
                    yield from recurse(val, [*path, key])
            elif isinstance(tree, ArrayNode | list | tuple | AsdfListNode):
                for i, val in enumerate(tree):
                    yield from recurse(val, [*path, i])
            elif tree is not None:
                yield (".".join(str(x) for x in path), tree)

        yield from recurse(self)

    def to_flat_dict(self, include_arrays=True, recursive=False):
        """
        Returns a dictionary of all of the schema items as a flat dictionary.

        Each dictionary key is a dot-separated name.  For example, the
        schema element ``meta.observation.date`` will end up in the
        dictionary as::

            { "meta.observation.date": "2012-04-22T03:22:05.432" }

        """

        def convert_val(val):
            """
            Unwrap the tagged scalars if necessary.
            """
            if isinstance(val, datetime):
                return val.isoformat()
            elif isinstance(val, Time):
                return str(val)
            return val

        item_getter = self._recursive_items if recursive else self.items

        if include_arrays:
            return {key: convert_val(val) for (key, val) in item_getter()}
        else:
            return {
                key: convert_val(val) for (key, val) in item_getter() if not isinstance(val, np.ndarray | ndarray.NDArrayType)
            }

    def __asdf_traverse__(self):
        """Asdf traverse method for things like info/search"""
        return dict(self)

    @property
    def _node_data(self) -> dict[str, Any]:
        """Return the underlying data for this node"""
        return self._data

    @_node_data.setter
    def _node_data(self, value: dict[str, Any]) -> None:
        """Set the underlying data for this node"""
        self._data = value

    def __len__(self):
        """Define length of the node"""
        return len(self._data)

    def __getitem__(self, key):
        """Dictionary style access data"""
        try:
            return self._get_node(key)
        except AttributeError as e:
            raise KeyError(f"No such key ({key}) found in node") from e

    def __setitem__(self, key, value):
        """Dictionary style access set data"""
        self._set_node(key, value)

    def __delitem__(self, key):
        """Dictionary style access delete data"""
        if key in self.__alias__:
            key = self.__alias__[key]

        del self._data[key]

    def __dir__(self):
        return set(super().__dir__()) | set(self._data.keys())

    def __iter__(self):
        """Define iteration"""
        return iter(self._data)

    def __repr__(self):
        """Define a representation"""
        return repr(self._data)


_ArrayItem = TypeVar("_ArrayItem")


class ArrayNode(MutableSequence[_ArrayItem], _NodeMixin):
    """

    Base class for handling all "array" (list-like) data nodes for RAD schemas.
    """

    __slots__ = ("_parent", "_read_tag", "data")

    data: list[_ArrayItem]

    def __init__(self, node=None, *, read_tag: str | None = None, parent: _NodeMixin | None = None):
        super().__init__(node=node, read_tag=read_tag, parent=parent)

        if node is None:
            self.data = []
        elif isinstance(node, list | AsdfListNode):
            self.data = node
        elif isinstance(node, self.__class__):
            self.data = node.data
        else:
            raise ValueError("Initializer only accepts lists")

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    def __delitem__(self, index) -> None:
        del self.data[index]

    def __len__(self) -> int:
        return len(self.data)

    def insert(self, index, value):
        self.data.insert(index, value)

    def __asdf_traverse__(self) -> list[_ArrayItem]:
        return list(self)

    @property
    def _node_data(self) -> list[Any]:
        """Return the underlying data for this node"""
        return self.data

    @_node_data.setter
    def _node_data(self, value: list[Any]) -> None:
        """Set the underlying data for this node"""
        self.data = value

    def __setattr__(self, key, value):
        if key in ArrayNode.__slots__:
            ArrayNode.__dict__[key].__set__(self, value)
        else:
            raise AttributeError(f"Cannot set attribute {key}, only allowed are {ArrayNode.__slots__}")

    def __eq__(self, other):
        if isinstance(other, ArrayNode):
            return self.data == other.data
        elif isinstance(other, list | AsdfListNode):
            return self.data == other
        else:
            return False
