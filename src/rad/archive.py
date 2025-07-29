import json
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

resolved = []
for address, schema in manager.items():
    if hasattr(schema, "archive_meta") and schema.archive_meta is not None:
        print(f"Resolving {address} with archive_meta")
        resolved.append(manager.resolve(address).archive_data(address.split("/")[-1].split("-")[0]))

with save.open("w") as f:
    json.dump(resolved, f, indent=2)
