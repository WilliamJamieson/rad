"""
ASDF Converters for the RAD Node classes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from asdf.extension import Converter, Extension

import rad

from ._node import ArrayNode, ObjectNode

if TYPE_CHECKING:
    from typing import ClassVar


__all__ = ("NodeExtension",)


class NodeConverter(Converter):
    """
    Base class for all RAD converters

    Note:
        This base class is only intended to provide serialization support for RAD
        Node classes. Deserialization of the RAD Node classes directly will not
        supported within RAD. The actual tagged objects-> the data model classes
        will implement both the tagging of the ASDF tree and the deserialization
        from those tags as they tags are only associated with the top level of the
        ASDF tree representing the data model.
    """

    @property
    def tags(self) -> list[str]:
        return []

    # The select_tag method must be implemented returning None in order to enable
    #    ASDF serialization support without tagging the result in the ASDF tree.
    #    Written to the file
    def select_tag(self, obj: ObjectNode | ArrayNode, tags: list[str], ctx) -> None:
        return None

    # These converters will not support deserialization into the Node classes meaning
    #    round trip support is not provided for the Node classes directly.
    def from_yaml_tree(self, node: dict, tag: str, ctx) -> ObjectNode:
        raise NotImplementedError(f"Deserialization is not implemented for {type(self).__name__}")


class ObjectNodeConverter(NodeConverter):
    """
    Converter for all subclasses of ObjectNode.
    """

    @property
    def types(self) -> list[type[ObjectNode]]:
        return list(ObjectNode.sub_classes())

    def to_yaml_tree(self, obj: ObjectNode, tag: str, ctx) -> dict:
        return dict(obj._data)


class ArrayNodeConverter(NodeConverter):
    """
    Converter for all subclasses of ArrayNode.
    """

    @property
    def types(self) -> list[type[ArrayNode]]:
        return list(ArrayNode.sub_classes())

    def to_yaml_tree(self, obj: ArrayNode, tag: str, ctx) -> list:
        return list(obj.data)


class NodeExtension(Extension):
    """
    ASDF Extension for RAD Node classes.

    The extension URI is simply the RAD version number as we are simply providing transparent serialization
    of the nodes into their core data structures without deserialization support.
    """

    extension_uri: ClassVar[str] = (
        f"asdf://stsci.edu/datamodels/roman/extensions/nodes-{'.'.join(rad.__version__.split('.')[:3])}"
    )
    tags: ClassVar[list[str]] = []
    converters: ClassVar[list[NodeConverter]] = [converter() for converter in NodeConverter.__subclasses__()]
