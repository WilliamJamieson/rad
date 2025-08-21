from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from asdf.schema import load_schema
from asdf.treeutil import walk_and_modify


def parse(schema_uri: str) -> dict[str, Any]:
    """
    Parse the schema URI and resolve the `allOf` combiners

    Parameters
    ----------
    schema_uri : str
        The URI of the schema to parse.

    Returns
    -------
    dict[str, Any]
        The parsed schema as a dictionary.
    """

    schema = load_schema(schema_uri, resolve_references=True)

    def deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
        for key, value in source.items():
            if key in target:
                if isinstance(target[key], Mapping):
                    if not isinstance(value, Mapping):
                        raise ValueError(f"Cannot merge non-mapping value {value} into {target[key]}")
                    deep_merge(target[key], value)
                elif isinstance(target[key], list) and isinstance(value, list) and key == "required":
                    target[key].extend(value)
                elif key in ("title", "description"):
                    target[key] += f"\n- {value}"
                elif target[key] != value:
                    raise ValueError(f"{key} has conflicting values: {target[key]} and {value}")
            else:
                target[key] = value

        return target

    def callback(node: dict[str, Any]) -> dict[str, Any]:
        if isinstance(node, Mapping) and "$schema" in node:
            del node["$schema"]
        if isinstance(node, Mapping) and "id" in node:
            del node["id"]
        if isinstance(node, Mapping) and "allOf" in node and "not" not in node["allOf"][0]:
            target = deepcopy(node["allOf"][0])
            for item in node["allOf"][1:]:
                if isinstance(item, Mapping):
                    item = deepcopy(item)
                    if "$schema" in item:
                        del item["$schema"]
                    if "id" in item:
                        del item["id"]
                    target = deep_merge(target, item)
                else:
                    raise ValueError(f"Expected a mapping in allOf, got {item}")

            del node["allOf"]
            return deep_merge(node, target)
        return node

    id_ = schema.get("id")
    meta_ = schema.get("$schema")

    schema = walk_and_modify(schema, callback)
    if id_:
        schema["id"] = id_
    if meta_:
        schema["$schema"] = meta_

    return schema
