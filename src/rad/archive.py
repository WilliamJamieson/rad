import json
from pathlib import Path

from rad.reader import Manager

manager = Manager.from_rad()
save = Path(__file__).parent.parent.parent / "archive.json"

resolved = []
for address in list(manager.keys()):
    schema = manager[address]
    if hasattr(schema, "archive_meta") and schema.archive_meta is not None:
        print(f"Resolving {address} with archive_meta")
        resolved.append(manager.archive_data(address))

with save.open("w") as f:
    json.dump(resolved, f, indent=2)
