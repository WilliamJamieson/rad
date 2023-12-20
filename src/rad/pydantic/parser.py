from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Any, Callable, DefaultDict, Iterable, Mapping, Sequence
from urllib.parse import ParseResult

import yaml
from asdf.config import get_config
from datamodel_code_generator import InvalidClassNameError, load_yaml
from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.parser.base import get_special_path, title_to_class_name
from datamodel_code_generator.parser.jsonschema import JsonSchemaObject, JsonSchemaParser, get_model_by_path
from datamodel_code_generator.reference import ModelResolver, get_relative_path
from datamodel_code_generator.types import DataType, DataTypeManager, StrictTypes

from rad import resources
from rad.pydantic._adaptors._adaptor_factory import adaptor_factory, has_adaptor

DATAMODELS_MANIFEST_PATH = importlib.resources.files(resources) / "manifests" / "datamodels-1.0.yaml"
DATAMODELS_MANIFEST = yaml.safe_load(DATAMODELS_MANIFEST_PATH.read_bytes())


DATAMODELS_TAG_URI_MAP = {tag["tag_uri"]: tag["schema_uri"] for tag in DATAMODELS_MANIFEST["tags"]}


class AsdfModelResolver(ModelResolver):
    def resolve_ref(self, path: Sequence[str] | str) -> str:
        manager = get_config().resource_manager

        if isinstance(path, str):
            joined_path = path
        else:
            joined_path = self.join_path(path)

        if joined_path in manager:
            resolved_file_path = manager._mappings_by_uri[joined_path]._delegate._uri_to_file[joined_path]

            return get_relative_path(self._base_path, resolved_file_path).as_posix() + "#"

        return super().resolve_ref(path)


def name_from_tag_uri(tag_uri):
    """
    Compute the name of the schema from the tag_uri.

    Parameters
    ----------
    tag_uri : str
        The tag_uri to find the name from
    """
    return tag_uri.split("/")[-1].split("-")[0]


def class_name_from_tag_uri(tag_uri):
    """
    Construct the class name for the STNode class from the tag_uri

    Parameters
    ----------
    tag_uri : str
        The tag_uri found in the RAD manifest

    Returns
    -------
    string name for the class
    """
    tag_name = name_from_tag_uri(tag_uri)
    class_name = "".join([p.capitalize() for p in tag_name.split("_")])
    if tag_uri.startswith("asdf://stsci.edu/datamodels/roman/tags/reference_files/"):
        class_name += "Ref"

    return class_name


class AsdfSchemaObject(JsonSchemaObject):
    items: list[AsdfSchemaObject] | AsdfSchemaObject | bool | None = None
    additionalProperties: AsdfSchemaObject | bool | None = None
    patternProperties: dict[str, AsdfSchemaObject] | None = None
    oneOf: list[AsdfSchemaObject] = []
    anyOf: list[AsdfSchemaObject] = []
    allOf: list[AsdfSchemaObject] = []
    properties: dict[str, AsdfSchemaObject | bool] | None = None
    tag: str | None = None
    astropy_type: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.tag is not None:
            if self.tag in DATAMODELS_TAG_URI_MAP:
                if self.ref is None:
                    self.ref = DATAMODELS_TAG_URI_MAP[self.tag]
                else:
                    raise ValueError("Cannot set both tag and ref")

        if self.astropy_type is not None:
            self.custom_type_path = self.astropy_type
            self.allOf = []


AsdfSchemaObject.model_rebuild()


class AsdfSchemaParser(JsonSchemaParser):
    def __init__(
        self,
        source: str | Path | list[Path] | ParseResult,
        *,
        data_model_type: type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: type[DataModel] = pydantic_model.CustomRootType,
        data_type_manager_type: type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: str | None = None,
        additional_imports: list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: DefaultDict[str, dict[str, Any]] | None = None,
        target_python_version: PythonVersion = PythonVersion.PY_37,
        dump_resolve_reference_action: Callable[[Iterable[str]], str] | None = None,
        validation: bool = False,
        field_constraints: bool = False,
        snake_case_field: bool = False,
        strip_default_none: bool = False,
        aliases: Mapping[str, str] | None = None,
        allow_population_by_field_name: bool = False,
        apply_default_values_for_required_fields: bool = False,
        allow_extra_fields: bool = False,
        force_optional_for_required_fields: bool = False,
        class_name: str | None = None,
        use_standard_collections: bool = False,
        base_path: Path | None = None,
        use_schema_description: bool = False,
        use_field_description: bool = False,
        use_default_kwarg: bool = False,
        reuse_model: bool = False,
        encoding: str = "utf-8",
        enum_field_as_literal: LiteralType | None = None,
        use_one_literal_as_default: bool = False,
        set_default_enum_member: bool = False,
        use_subclass_enum: bool = False,
        strict_nullable: bool = False,
        use_generic_container_types: bool = False,
        enable_faux_immutability: bool = False,
        remote_text_cache: DefaultPutDict[str, str] | None = None,
        disable_appending_item_suffix: bool = False,
        strict_types: Sequence[StrictTypes] | None = None,
        empty_enum_field_name: str | None = None,
        custom_class_name_generator: Callable[[str], str] | None = None,
        field_extra_keys: set[str] | None = None,
        field_include_all_keys: bool = False,
        field_extra_keys_without_x_prefix: set[str] | None = None,
        wrap_string_literal: bool | None = None,
        use_title_as_name: bool = False,
        use_operation_id_as_name: bool = False,
        use_unique_items_as_set: bool = False,
        http_headers: Sequence[tuple[str, str]] | None = None,
        http_ignore_tls: bool = False,
        use_annotated: bool = False,
        use_non_positive_negative_number_constrained_types: bool = False,
        original_field_name_delimiter: str | None = None,
        use_double_quotes: bool = False,
        use_union_operator: bool = False,
        allow_responses_without_content: bool = False,
        collapse_root_models: bool = False,
        special_field_name_prefix: str | None = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
        keep_model_order: bool = False,
        known_third_party: list[str] | None = None,
        custom_formatters: list[str] | None = None,
        custom_formatters_kwargs: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            source=source,
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            data_type_manager_type=data_type_manager_type,
            data_model_field_type=data_model_field_type,
            base_class=base_class,
            additional_imports=additional_imports,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            target_python_version=target_python_version,
            dump_resolve_reference_action=dump_resolve_reference_action,
            validation=validation,
            field_constraints=field_constraints,
            snake_case_field=snake_case_field,
            strip_default_none=strip_default_none,
            aliases=aliases,
            allow_population_by_field_name=allow_population_by_field_name,
            apply_default_values_for_required_fields=apply_default_values_for_required_fields,
            allow_extra_fields=allow_extra_fields,
            force_optional_for_required_fields=force_optional_for_required_fields,
            class_name=class_name,
            use_standard_collections=use_standard_collections,
            base_path=base_path,
            use_schema_description=use_schema_description,
            use_field_description=use_field_description,
            use_default_kwarg=use_default_kwarg,
            reuse_model=reuse_model,
            encoding=encoding,
            enum_field_as_literal=enum_field_as_literal,
            use_one_literal_as_default=use_one_literal_as_default,
            set_default_enum_member=set_default_enum_member,
            use_subclass_enum=use_subclass_enum,
            strict_nullable=strict_nullable,
            use_generic_container_types=use_generic_container_types,
            enable_faux_immutability=enable_faux_immutability,
            remote_text_cache=remote_text_cache,
            disable_appending_item_suffix=disable_appending_item_suffix,
            strict_types=strict_types,
            empty_enum_field_name=empty_enum_field_name,
            custom_class_name_generator=custom_class_name_generator,
            field_extra_keys=field_extra_keys,
            field_include_all_keys=field_include_all_keys,
            field_extra_keys_without_x_prefix=field_extra_keys_without_x_prefix,
            wrap_string_literal=wrap_string_literal,
            use_title_as_name=use_title_as_name,
            use_operation_id_as_name=use_operation_id_as_name,
            use_unique_items_as_set=use_unique_items_as_set,
            http_headers=http_headers,
            http_ignore_tls=http_ignore_tls,
            use_annotated=use_annotated,
            use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
            original_field_name_delimiter=original_field_name_delimiter,
            use_double_quotes=use_double_quotes,
            use_union_operator=use_union_operator,
            allow_responses_without_content=allow_responses_without_content,
            collapse_root_models=collapse_root_models,
            special_field_name_prefix=special_field_name_prefix,
            remove_special_field_name_prefix=remove_special_field_name_prefix,
            capitalise_enum_members=capitalise_enum_members,
            keep_model_order=keep_model_order,
            known_third_party=known_third_party,
            custom_formatters=custom_formatters,
            custom_formatters_kwargs=custom_formatters_kwargs,
        )
        self.model_resolver = AsdfModelResolver(
            base_url=self.model_resolver.base_url,
            singular_name_suffix=self.model_resolver.singular_name_suffix,
            aliases=aliases,
            empty_field_name=empty_enum_field_name,
            snake_case_field=snake_case_field,
            custom_class_name_generator=custom_class_name_generator,
            base_path=self.base_path,
            original_field_name_delimiter=original_field_name_delimiter,
            special_field_name_prefix=special_field_name_prefix,
            remove_special_field_name_prefix=remove_special_field_name_prefix,
            capitalise_enum_members=capitalise_enum_members,
        )

    def parse_raw(self) -> None:
        for source, path_parts in self._get_context_source_path_parts():
            self.raw_obj = load_yaml(source.text)
            if self.custom_class_name_generator:
                obj_name = class_name_from_tag_uri(self.raw_obj.get("id", "NoID"))
            else:
                if self.class_name:
                    obj_name = self.class_name
                else:
                    # backward compatible
                    obj_name = self.raw_obj.get("title", "Model")
                    if not self.model_resolver.validate_name(obj_name):
                        obj_name = title_to_class_name(obj_name)
                if not self.model_resolver.validate_name(obj_name):
                    raise InvalidClassNameError(obj_name)
            self._parse_file(self.raw_obj, obj_name, path_parts)

        self._resolve_unparsed_json_pointer()

    def parse_combined_schema(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        target_attribute_name: str,
    ) -> list[DataType]:
        base_object = obj.dict(exclude={target_attribute_name}, exclude_unset=True, by_alias=True)
        combined_schemas: list[JsonSchemaObject] = []
        refs = []
        for index, target_attribute in enumerate(getattr(obj, target_attribute_name, [])):
            if target_attribute.ref:
                combined_schemas.append(target_attribute)
                refs.append(index)
                # TODO: support partial ref
                # {
                #   "type": "integer",
                #   "oneOf": [
                #     { "minimum": 5 },
                #     { "$ref": "#/definitions/positive" }
                #   ],
                #    "definitions": {
                #     "positive": {
                #       "minimum": 0,
                #       "exclusiveMinimum": true
                #     }
                #    }
                # }
            else:
                combined_schemas.append(
                    AsdfSchemaObject.parse_obj(
                        self._deep_merge(
                            base_object,
                            target_attribute.dict(exclude_unset=True, by_alias=True),
                        )
                    )
                )

        parsed_schemas = self.parse_list_item(
            name,
            combined_schemas,
            path,
            obj,
            singular_name=False,
        )
        common_path_keyword = f"{target_attribute_name}Common"
        return [
            self._parse_object_common_part(
                name,
                obj,
                [*get_special_path(common_path_keyword, path), str(i)],
                ignore_duplicate_model=True,
                fields=[],
                base_classes=[d.reference],
                required=[],
            )
            if i in refs and d.reference
            else d
            for i, d in enumerate(parsed_schemas)
        ]

    def parse_raw_obj(
        self,
        name: str,
        raw: dict[str, Any],
        path: list[str],
    ) -> None:
        self.parse_obj(name, AsdfSchemaObject.parse_obj(raw), path)

    @property
    def current_source_path(self) -> Path:
        return self._current_source_path

    @current_source_path.setter
    def current_source_path(self, value: Path) -> None:
        self._current_source_path = Path(str(value).split("-")[0])

    def _parse_file(
        self,
        raw: dict[str, Any],
        obj_name: str,
        path_parts: list[str],
        object_paths: list[str] | None = None,
    ) -> None:
        object_paths = [o for o in object_paths or [] if o]
        if object_paths:
            path = [*path_parts, f"#/{object_paths[0]}", *object_paths[1:]]
        else:
            path = path_parts
        with self.model_resolver.current_root_context(path_parts):
            obj_name = self.model_resolver.add(path, obj_name, unique=False, class_name=True).name
            with self.root_id_context(raw):
                # Some jsonschema docs include attribute self to have include version details
                raw.pop("self", None)
                # parse $id before parsing $ref
                root_obj = AsdfSchemaObject.parse_obj(raw)
                self.parse_id(root_obj, path_parts)
                definitions: dict[Any, Any] | None = None
                for schema_path, split_schema_path in self.schema_paths:
                    try:
                        definitions = get_model_by_path(raw, split_schema_path)
                        if definitions:
                            break
                    except KeyError:
                        continue
                if definitions is None:
                    definitions = {}

                for key, model in definitions.items():
                    obj = AsdfSchemaObject.parse_obj(model)
                    self.parse_id(obj, [*path_parts, schema_path, key])

                if object_paths:
                    models = get_model_by_path(raw, object_paths)
                    model_name = object_paths[-1]
                    self.parse_obj(model_name, AsdfSchemaObject.parse_obj(models), path)
                else:
                    self.parse_obj(obj_name, root_obj, path_parts or ["#"])
                for key, model in definitions.items():
                    path = [*path_parts, schema_path, key]
                    reference = self.model_resolver.get(path)
                    if not reference or not reference.loaded:
                        self.parse_raw_obj(key, model, path)

                key = tuple(path_parts)
                reserved_refs = set(self.reserved_refs.get(key) or [])
                while reserved_refs:
                    for reserved_path in sorted(reserved_refs):
                        reference = self.model_resolver.get(reserved_path)
                        if not reference or reference.loaded:
                            continue
                        object_paths = reserved_path.split("#/", 1)[-1].split("/")
                        path = reserved_path.split("/")
                        models = get_model_by_path(raw, object_paths)
                        model_name = object_paths[-1]
                        self.parse_obj(model_name, AsdfSchemaObject.parse_obj(models), path)
                    previous_reserved_refs = reserved_refs
                    reserved_refs = set(self.reserved_refs.get(key) or [])
                    if previous_reserved_refs == reserved_refs:
                        break

    def get_data_type(self, obj: JsonSchemaObject) -> DataType:
        if has_adaptor(obj):
            return adaptor_factory(obj, self.data_type_manager.data_type())
        return super().get_data_type(obj)

    def parse_item(
        self,
        name: str,
        item: JsonSchemaObject,
        path: list[str],
        singular_name: bool = False,
        parent: JsonSchemaObject | None = None,
    ) -> DataType:
        if has_adaptor(item):
            return adaptor_factory(item, self.data_type_manager.data_type())
        return super().parse_item(name, item, path, singular_name, parent)

    def parse_object(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        singular_name: bool = False,
        unique: bool = True,
    ) -> DataType:
        if has_adaptor(obj):
            return adaptor_factory(obj, self.data_type_manager.data_type())
        return super().parse_object(name, obj, path, singular_name, unique)
