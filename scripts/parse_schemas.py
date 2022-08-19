import os
import yaml

from pathlib import Path

def get_schemas():
    schemas = Path(__file__).absolute().parent.parent / "src" / "rad" / "resources" / "schemas"

    return schemas.glob("**/*.yaml")


def get_contents(schema: Path):
    with open(schema) as f:
        return yaml.safe_load(f)


def extract_data_entry(data_key: str, prop):
    if isinstance(prop, dict):
        if data_key in prop:
            return prop[data_key]
        else:
            data = extract_data(data_key, prop)
            if len(data) > 0:
                return data


def extract_data(data_key: str, properties: dict):
    data = {}
    for key, prop in properties.items():
        if (value := extract_data_entry(data_key, prop)) is not None:
            data[key] = value

    return data


def get_data(data_key: str):
    data = {}
    for schema in get_schemas():
        contents = get_contents(schema)

        if "properties" in contents:
            data_contents = extract_data(data_key, contents["properties"])
            if len(data_contents) > 0:
                data[contents["id"]] = data_contents

    return data


if __name__ == "__main__":#
    archive_catalog = get_data("archive_catalog")
    sdf = get_data("sdf")

    try:
        import flatten_dict

        print("archive_catalog:\n")
        print(flatten_dict.flatten(archive_catalog, 'dot'))
        print("\n")
        print("sdf:\n")
        print(flatten_dict.flatten(sdf, 'dot'))
    except ImportError:
        print("archive_catalog:\n")
        print(archive_catalog)
        print("\n")
        print("sdf:\n")
        print(sdf)
