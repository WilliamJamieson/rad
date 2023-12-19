from pathlib import Path

from datamodel_code_generator import DataModelType, PythonVersion
from datamodel_code_generator.model import get_data_model_types

from rad.pydantic.parser import AsdfSchemaParser

path = Path(__file__).parent.parent / "resources" / "schemas"


def class_name_generator(name: str) -> str:
    return name


data_model_types = get_data_model_types(DataModelType.PydanticV2BaseModel, target_python_version=PythonVersion.PY_311)
parser = AsdfSchemaParser(
    path,
    data_model_type=data_model_types.data_model,
    data_model_root_type=data_model_types.root_model,
    data_model_field_type=data_model_types.field_model,
    data_type_manager_type=data_model_types.data_type_manager,
    dump_resolve_reference_action=data_model_types.dump_resolve_reference_action,
    use_annotated=True,
    field_constraints=True,
    custom_class_name_generator=class_name_generator,
)
result = parser.parse()

write_path = Path(__file__).parent / "_generated"
write_path.mkdir(exist_ok=True)


def make_file_path(name: tuple[str]) -> Path:
    file_path = write_path
    for sub_path in name[:-1]:
        file_path = file_path / sub_path
        file_path.mkdir(exist_ok=True)

    return file_path / name[-1]


for name, file in result.items():
    with make_file_path(name).open("w") as f:
        f.write(file.body)
