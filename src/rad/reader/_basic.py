from __future__ import annotations

from typing import Any

from ._reader import Reader, rad

__all__ = ("Basic",)


class Root(Reader):
    """
    Root schema for the reader.
        See: https://json-schema.org/draft-04/draft-zyp-json-schema-04
    """

    id: str | None = rad()
    schema: str | None = rad("$schema")


class Metadata(Reader):
    """
    Metadata schema for the reader.
        See: https://json-schema.org/draft-04/draft-fge-json-schema-validation-00#rfc.section.6
    """

    title: str | None = rad()
    description: str | None = rad()
    default: str | None = rad()


class ArchiveCatalog(Reader):
    """
    Read archive information for MAST
    """

    datatype: str | None = rad()
    destination: list[str] | None = rad()
    path_prefix: str | None = rad("path_prefix")

    def _archive_data(self) -> dict[str, Any]:
        data = {
            "datatype": self.datatype,
            "destination": self.destination,
        }
        if self.path_prefix is not None:
            data["path_prefix"] = self.path_prefix

        return data


class Rad(Reader):
    """
    Custom information for RAD
    """

    archive_catalog: ArchiveCatalog | None = rad("archive_catalog")
    unit: str | None = rad()
    datamodel_name: str | None = rad("datamodel_name")
    archive_meta: str | None = rad("archive_meta")

    def __post_init__(self) -> None:
        """
        Post-initialization method to set the archive metadata.
        """
        if self.archive_catalog is not None:
            self.archive_catalog = ArchiveCatalog.extract(self.simplify(self.archive_catalog))

    def _archive_data(self) -> dict[str, Any] | None:
        data = {"archive_meta": self.archive_meta} if self.archive_meta else None

        if self.archive_catalog is not None:
            data = data or {}
            data.update(self.archive_catalog._archive_data())

        return data


class Basic(Root, Metadata, Rad):
    """Basic schema for the reader."""
