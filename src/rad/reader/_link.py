from __future__ import annotations

from abc import abstractmethod
from re import match
from typing import TYPE_CHECKING, Self

from ._reader import rad
from ._schema import Schema

if TYPE_CHECKING:
    pass


class Link(Schema):
    """
    Type for links in the reader.
    """

    class LinkError(KeyError):
        """Base class for link-related errors."""

    EXTERNAL_LINKS = frozenset(
        (
            r"tag:stsci.edu:asdf/time/time-1.*",
            r"tag:stsci.edu:asdf/core/ndarray-1.*",
            r"tag:stsci.edu:asdf/unit/quantity-1.*",
            r"tag:stsci.edu:asdf/unit/unit-1.*",
            r"tag:astropy.org:astropy/units/unit-1.*",
            r"tag:astropy.org:astropy/table/table-1.*",
            r"tag:stsci.edu:gwcs/wcs-*",
            r"http://stsci.edu/schemas/asdf/time/time-1.*",
        )
    )

    @property
    def is_external(self) -> bool:
        """
        Check if the link is external.

        Returns
        -------
            True if the link is external, False otherwise.
        """
        for pattern in self.EXTERNAL_LINKS:
            if match(pattern, self.link):
                return True

        return False

    def resolve(self) -> Self:
        """
        Resolve the link schema by extracting the address from the manager.

        Parameters
        ----------
        manager
            The manager to resolve the link against.

        Returns
        -------
            The resolved link schema instance.
        """
        if self.is_external:
            return super().resolve()

        if self.link in self.manager:
            return self.manager[self.link].resolve()

        raise self.LinkError(f"Link '{self.link}' not found in schema data.")

    @property
    @abstractmethod
    def link(self) -> str:
        """
        The link address for the schema.

        Returns
        -------
            The link address.
        """


class Ref(Link):
    """
    Type $ref schema for the reader.
    """

    ref: str = rad("$ref")

    @property
    def link(self) -> str:
        """
        The link address for the schema.

        Returns
        -------
            The link address.
        """
        if match(r".*#/definitions$", self.ref):
            return self.ref.split("#/definitions")[0]

        return self.ref

    def merge(self, other: Ref) -> Ref:
        """
        Merge another schema into this

        Parameters
        ----------
        other
            The other schema instance to merge

        Returns
        -------
            The merged schema instance.
        """
        if self.ref is None and other.ref is None:
            raise self.LinkError(f"Ref must be internal '{self.link}'.")

        if self.ref is None:
            self.ref = other.ref


class Tag(Link):
    """
    Type tag schema for the reader.
    """

    tag: str = rad()

    @property
    def link(self) -> str:
        """
        The link address for the schema.

        Returns
        -------
            The link address.
        """
        return self.tag

    def merge(self, other: Schema) -> Schema:
        """
        Merge another schema into this Tag schema.

        Parameters
        ----------
        other
            The other schema instance to merge

        Returns
        -------
            The merged schema instance.
        """
        if not self.is_external:
            raise self.LinkError(f"Tag must be external '{self.link}'.")

        self = other
