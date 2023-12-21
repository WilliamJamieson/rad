from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class RadDataModel(BaseModel):
    _tag_uri: ClassVar[str | None] = None

    model_config = ConfigDict(
        protected_namespaces=(),
    )
