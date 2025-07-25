from __future__ import annotations

from ._reader import rad
from ._schema import Schema


class Link(Schema):
    """
    Type for links in the reader.
    """


class Ref(Link):
    """
    Type $ref schema for the reader.
    """

    ref: str = rad("$ref")


class Tag(Link):
    """
    Type tag schema for the reader.
    """

    tag: str = rad()
