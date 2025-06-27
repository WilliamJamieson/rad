from __future__ import annotations

from ._reader import Reader, rad

__all__ = ("Basic",)


class Root(Reader):
    """
    Root schema for the reader.
        See: https://json-schema.org/draft-04/draft-zyp-json-schema-04
    """

    id: str | None = rad()
    schema: str | None = rad("$schema")

    def __post_init__(self) -> None:
        """
        Post-initialization method to set the schema name and suffix.
        """
        if self.id is not None:
            self.name = self.id


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
    destination: str | None = rad()
    path_prefix: str | None = rad("path_prefix")


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
            print(self.archive_catalog)
            self.archive_catalog = ArchiveCatalog.extract(name="archive_catalog", data=self.archive_catalog, suffix=self.address)


class Basic(Root, Metadata, Rad):
    """Basic schema for the reader."""

    def __post_init__(self):
        """Run the post initialization for the parent classes."""
        super().__post_init__()
        super(Metadata, self).__post_init__()
