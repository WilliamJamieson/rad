from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, RootModel


class RadDataModel(BaseModel):
    _tag_uri: ClassVar[str | None] = None

    model_config = ConfigDict(
        protected_namespaces=(),
    )

    def to_asdf_tree(self):
        """Convert to an ASDF tree, stopping at tags"""

        tree = dict(self)

        for field_name, field in tree.items():
            if isinstance(field, RadDataModel) and field._tag_uri is not None:
                tree[field_name] = field.to_asdf_tree()

            if isinstance(field, dict):
                for key, value in field.items():
                    if isinstance(value, RadDataModel) and value._tag_uri is not None:
                        field[key] = value.to_asdf_tree()

            if isinstance(field, list):
                for index, value in enumerate(field):
                    if isinstance(value, RadDataModel) and value._tag_uri is not None:
                        field[index] = value.to_asdf_tree()

            if isinstance(field, RootModel):
                tree[field_name] = field.root

            if isinstance(field, Enum):
                tree[field_name] = field.value

        return tree
