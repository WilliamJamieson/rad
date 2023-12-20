from __future__ import annotations

import importlib.resources
from typing import Any

import yaml
from datamodel_code_generator.parser.jsonschema import JsonSchemaObject

from rad import resources

__all__ = ["RadSchemaObject"]

TAG_URI_MAP = {
    tag["tag_uri"]: tag["schema_uri"]
    for tag in yaml.safe_load(
        (importlib.resources.files(resources) / "manifests" / "datamodels-1.0.yaml").read_bytes(),
    )["tags"]
}


class RadSchemaObject(JsonSchemaObject):
    """Modifications to the JsonSchemaObject to support reading Rad schemas"""

    items: list[RadSchemaObject] | RadSchemaObject | bool | None = None
    additionalProperties: RadSchemaObject | bool | None = None
    patternProperties: dict[str, RadSchemaObject] | None = None
    oneOf: list[RadSchemaObject] = []
    anyOf: list[RadSchemaObject] = []
    allOf: list[RadSchemaObject] = []
    properties: dict[str, RadSchemaObject | bool] | None = None
    tag: str | None = None
    astropy_type: str | None = None

    def model_post_init(self, __context: Any) -> None:
        """Custom post processing for RadSchemaObject"""

        # Turn tags into references
        if self.tag is not None:
            if self.tag in TAG_URI_MAP:
                if self.ref is None:
                    self.ref = TAG_URI_MAP[self.tag]
                else:
                    raise ValueError("Cannot set both tag and ref")

        # Handle external reference (this is a bit of a hack)
        if self.astropy_type is not None:
            self.custom_type_path = self.astropy_type
            self.allOf = []


RadSchemaObject.model_rebuild()
