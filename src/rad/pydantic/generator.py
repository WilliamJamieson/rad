from datetime import datetime
from pathlib import Path
from textwrap import dedent

from asdf.config import get_config
from datamodel_code_generator import DataModelType, PythonVersion
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.parser.base import Result

from rad.pydantic.parser import RadSchemaParser


def get_rad_schema_path(suffix: str) -> Path:
    manager = get_config().resource_manager

    for resource in manager._resource_mappings:
        if resource.package_name == "rad" and resource.delegate.uri_prefix.endswith(suffix):
            return resource.delegate.root


def create_rad_schema_parser(path: Path) -> RadSchemaParser:
    data_model_types = get_data_model_types(DataModelType.PydanticV2BaseModel, target_python_version=PythonVersion.PY_311)
    return RadSchemaParser(
        path,
        data_model_type=data_model_types.data_model,
        data_model_root_type=data_model_types.root_model,
        data_model_field_type=data_model_types.field_model,
        data_type_manager_type=data_model_types.data_type_manager,
        dump_resolve_reference_action=data_model_types.dump_resolve_reference_action,
        use_annotated=True,
        field_constraints=True,
        base_class="rad.pydantic.datamodel.RadDataModel",
    )


def make_file_path(path: Path, name: tuple[str]) -> Path:
    file_path = path
    for sub_path in name[:-1]:
        file_path = file_path / sub_path
        file_path.mkdir(exist_ok=True)

    return file_path / name[-1]


def create_code(file: Result, version: str, use_timestamp: bool) -> str:
    header = (
        dedent(
            f"""
            # Generated by RAD using generator based on datamodel-code-generator
            #    source schema: {file.source}-{version}.yaml
            #    time stamp:    {datetime.now() if use_timestamp else 'VERSION CONTROLLED'}
            # DO NOT EDIT THIS FILE DIRECTLY!
            """
        ).strip()
        + "\n\n"
    )

    return header + file.body


def write_files(
    path: Path,
    result: dict[tuple[str], Result],
    version: str | None = None,
    use_timestamp: bool = True,
) -> None:
    version = version or "1.0.0"
    for name, file in result.items():
        with make_file_path(path, name).open("w") as f:
            f.write(create_code(file, version, use_timestamp))


def generate_files(
    suffix: str,
    write_path: Path,
    version: str | None = None,
    use_timestamp: bool = True,
):
    schema_path = get_rad_schema_path(suffix)
    parsed_results = create_rad_schema_parser(schema_path).parse()
    write_files(write_path, parsed_results, version, use_timestamp)


if __name__ == "__main__":
    write_path = Path(__file__).parent / "_generated"
    write_path.mkdir(exist_ok=True)

    generate_files("schemas", write_path, use_timestamp=False)
