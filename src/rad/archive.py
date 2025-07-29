import json
from dataclasses import asdict
from pathlib import Path

import asdf
import yaml

from rad.reader import Manager, Schema

_LATEST_PATHS = tuple((Path(__file__).parent.parent.parent.absolute() / "latest").glob("**/*.yaml"))
_LATEST_URIS = tuple(yaml.safe_load(latest_path.read_bytes())["id"] for latest_path in _LATEST_PATHS)
_CURRENT_CONTENT = {uri: asdf.get_config().resource_manager[uri] for uri in _LATEST_URIS}
_CURRENT_RESOURCES = {uri: yaml.safe_load(content) for uri, content in _CURRENT_CONTENT.items()}

manager = Manager(schemas={})
for latest_uri in _LATEST_URIS:
    Schema.extract(name=None, data=_CURRENT_RESOURCES[latest_uri], manager=manager)


save = Path(__file__).parent.parent.parent / "archive.json"
resolved = {}
for address, schema in manager.items():
    if hasattr(schema, "archive_meta") and schema.archive_meta is not None:
        print(f"Resolving {address} with archive_meta")
        resolved[address] = asdict(manager.resolve(address))


def _filter(data: dict) -> dict:
    if isinstance(data, dict):
        new = {}
        for key, value in data.items():
            if value is None:
                continue
            if key in ("name", "prefix", "schema", "id"):
                continue
            if isinstance(value, Manager):
                continue
            new[key] = _filter(value)

        return new

    if isinstance(data, list):
        return [_filter(item) for item in data]

    return data


class Flag(Exception):
    pass


def _archive_catalog_filter(data: dict) -> dict:
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "archive_catalog" and value:
                raise Flag("")

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                _archive_catalog_filter(item)


# import pprint
# with save.open("w") as f:
#     pprint.pp(_filter(resolved), stream=f)


print(f"Saving {len(resolved)} schemas to {save}")
with save.open("w") as f:
    json.dump(_filter(resolved), f, indent=2)
