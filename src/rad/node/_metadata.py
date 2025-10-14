"""
Metadata classes for Annotating RAD properties.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ("ArchiveCatalog", "Metadata")


@dataclass(frozen=True, kw_only=True)
class Metadata:
    """
    Metadata for annotating RAD properties
    """

    title: str | None = None
    description: str | None = None

    archive_catalog: ArchiveCatalog | None = None


@dataclass(frozen=True, kw_only=True)
class ArchiveCatalog:
    """
    Metadata for annotationing a property that includes archive catalog information.
    """

    datatype: str
    destination: tuple[str, ...]
