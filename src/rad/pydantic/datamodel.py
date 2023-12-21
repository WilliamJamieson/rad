from pydantic import BaseModel, ConfigDict


class RadDataModel(BaseModel):
    model_config = ConfigDict(
        protected_namespaces=(),
    )
