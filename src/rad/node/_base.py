"""
Base classes for RAD data nodes.
"""

from __future__ import annotations

from abc import abstractmethod
from inspect import isclass
from types import GenericAlias, UnionType
from typing import TYPE_CHECKING, Any, Literal, Self, Union, get_args, get_origin

import numpy as np
from astropy import coordinates
from astropy import units as u
from astropy.modeling import models
from astropy.table import Table
from astropy.time import Time
from gwcs import coordinate_frames
from gwcs.wcs import WCS

__all__ = ("Node",)

_NOSTR = "?"
_NONUM = -999999
_NOBOOL = False


class _NotSetType:
    pass


_NotSet = _NotSetType()


class Node:
    """
    Class to provide the common API for all Node objects
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
    _parent: Node | None

    __uri__: str | None = None
    __tag__: str | None = None

    def __init__(self, *args, read_tag: str | None = None, parent: Node | None = None, **kwargs):
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

    def copy(self, parent: Node | None = None) -> Node:
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

            if annotation is Time:
                return self._find_time_default(minimal=minimal, **kwargs)

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

    def _find_time_default(self, *, minimal: bool = False, **kwargs) -> Time | _NotSetType:
        """
        Find in the default value for an astropy Time key.

        Parameters
        ----------
        minimal : bool, optional
            If True, fill in the minimal default values.

        Returns
        -------
        Time | _NotSet
            The default value for the given key.
        """

        if minimal:
            return _NotSet

        return Time("2020-01-01T00:00:00.0", format="isot", scale="utc")

    def _find_wcs_default(self, *, minimal: bool = False, **kwargs) -> WCS | _NotSetType:
        """
        Find in the default value for a WCS key.

        Parameters
        ----------
        minimal : bool, optional
            If True, fill in the minimal default values.

        Returns
        -------
        Any | _NotSet
            The default value for the given key.
        """

        if minimal:
            return _NotSet

        pixelshift = models.Shift(-500) & models.Shift(-500)
        pixelscale = models.Scale(0.1 / 3600.0) & models.Scale(0.1 / 3600.0)  # 0.1 arcsec/pixel
        tangent_projection = models.Pix2Sky_TAN()
        celestial_rotation = models.RotateNative2Celestial(30.0, 45.0, 180.0)

        det2sky = pixelshift | pixelscale | tangent_projection | celestial_rotation

        detector_frame = coordinate_frames.Frame2D(name="detector", axes_names=("x", "y"), unit=(u.pix, u.pix))
        sky_frame = coordinate_frames.CelestialFrame(reference_frame=coordinates.ICRS(), name="icrs", unit=(u.deg, u.deg))
        return WCS(
            [
                (detector_frame, det2sky),
                (sky_frame, None),
            ]
        )

    def _find_table_default(self, *, minimal: bool = False, **kwargs) -> Table | _NotSetType:
        """
        Find in the default value for an astropy Table key.

        Parameters
        ----------
        minimal : bool, optional
            If True, fill in the minimal default values.

        Returns
        -------
        Table | _NotSet
            The default value for the given key.
        """

        if minimal:
            return _NotSet

        return Table()

    def _find_unit_default(self, type_: GenericAlias, **kwargs) -> u.Unit:
        """
        Find in the default value for an astropy Unit key.

        Parameters
        ----------
        type_ : GenericAlias
            The type to find the default value for.

        Returns
        -------
        u.Unit
            The default value for the given key.
        """

        if get_origin(type_) is not u.Unit:
            raise ValueError(f"Cannot find Unit default for type {type_}")

        # There maybe more than one possible unit string, just take the first
        unit_str = get_args(type_)[0]
        return u.Unit(unit_str)

    def _find_quantity_default(self, type_: GenericAlias, **kwargs) -> u.Quantity:
        """
        Find in the default value for an astropy Quantity key.

        Parameters
        ----------
        type_ : GenericAlias
            The type to find the default value for.

        Returns
        -------
        u.Quantity
            The default value for the given key.
        """

        if get_origin(type_) is not u.Quantity:
            raise ValueError(f"Cannot find Quantity default for type {type_}")

        # There maybe more than one possible unit string, just take the first
        unit_str = get_args(type_)[0]
        unit = u.Unit(unit_str)

        return 1.0 * unit
