import os
import yaml

from pathlib import Path

def get_schemas():
    schemas = Path(__file__).absolute().parent.parent / "src" / "rad" / "resources" / "schemas"

    return schemas.glob("**/*.yaml")


def get_contents(schema: Path):
    with open(schema) as f:
        return yaml.safe_load(f)


def extract_data(data_key: str, properties: dict):
    return {key: prop.get(data_key, None) for key, prop in properties.items()}


def get_data(data_key: str):
    data = {}
    for schema in get_schemas():
        contents = get_contents(schema)

        data[contents["id"]] = extract_data(data_key, contents.get("properties", {}))

    return data


if __name__ == "__main__":
    print(get_data("archive_catalog"))
    print(get_data("sdf"))
