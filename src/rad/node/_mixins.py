from __future__ import annotations

from typing import ClassVar, Literal

from ._node import ObjectNode

__all__ = ("WfiModeMixin",)


class WfiModeMixin(ObjectNode):
    """
    Extensions to the WfiMode class.
        Adds to indication properties
    """

    __slots__ = ()

    optical_element: str

    # Every optical element is a grating or a filter
    #   There are less gratings than filters so its easier to list out the
    #   gratings.
    _GRATING_OPTICAL_ELEMENTS: ClassVar[frozenset[str]] = frozenset({"GRISM", "PRISM"})

    @property
    def filter(self) -> str | None:
        """
        Returns the filter if it is one, otherwise None
        """
        if self.optical_element in self._GRATING_OPTICAL_ELEMENTS:
            return None
        else:
            return self.optical_element

    @property
    def grating(self) -> Literal["GRISM", "PRISM"] | None:
        """
        Returns the grating if it is one, otherwise None
        """
        if self.optical_element in self._GRATING_OPTICAL_ELEMENTS:
            return self.optical_element  # type: ignore[return-value]
        else:
            return None
