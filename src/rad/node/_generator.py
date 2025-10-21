from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from re import match
from subprocess import run
from sys import version_info
from textwrap import dedent, indent
from typing import TYPE_CHECKING

from asdf.schema import load_schema
from asdf.tags.core.ndarray import asdf_datatype_to_numpy_dtype

from . import _mixins as mixins
from ._utils import name_from_uri

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any

# Pathlib `walk_up` was added in Python 3.12 otherwise we need to use os.path.relpath
# The Pathlib formulation is supperior so we should make it clear that's our preferred
# approach when we can drop support for Python 3.11
if version_info >= (3, 12):

    def _relative_path(target: Path, current: Path) -> Path:
        """
        Relative path from current to target
        """
        # MyPy is picking up the signature issue because it assumes that we are
        # in the lowest supported version of Python (3.11) by this package. So
        # It will complain that `walk_up` is not a valid argument.
        return target.relative_to(current, walk_up=True)  # type: ignore[call-arg]
else:
    from os.path import relpath

    def _relative_path(target: Path, current: Path) -> Path:
        """
        Relative path from current to target
        """
        return Path(relpath(target.as_posix(), current.as_posix()))


class Base(ABC):
    """
    Base class for all stub
    """

    @abstractmethod
    def text(self) -> str:
        pass


@dataclass
class Import(Base):
    items: dict[str, set[str]]

    def text(self) -> str:
        text = "from __future__ import annotations\n\n"
        for item, imports in sorted(self.items.items()):
            text += f"from {item} import {', '.join(sorted(imports))}\n"
        return text

    def add_import(self, module: str, type_: str) -> None:
        if module == ".":
            return

        if module not in self.items:
            self.items[module] = set()

        self.items[module].add(type_)

    def relative_import(self, target_path: Path, current_path: Path, type_: str) -> None:
        # Compute the relative module paths
        path = _relative_path(target_path, current_path)

        # Convert the convert the relative path to a module import string
        module = path.as_posix().replace("..", "").replace("/", ".")
        self.add_import(module, type_)

    @classmethod
    def empty(cls) -> Import:
        return cls({})

    def any(self) -> None:
        self.add_import("typing", "Any")

    def type_alias(self) -> None:
        self.add_import("typing", "TypeAlias")

    def annotated(self) -> None:
        self.add_import("typing", "Annotated")

    def literal(self) -> None:
        self.add_import("typing", "Literal")

    def dtype(self, dtype: str) -> None:
        self.add_import("numpy", dtype)

    def ndarray(self) -> None:
        self.add_import("numpy", "ndarray")

    def ndarray_type(self) -> None:
        self.add_import("numpy.typing", "NDArray")

    def time(self) -> None:
        self.add_import("astropy.time", "Time")

    def unit(self) -> None:
        self.add_import("astropy.units", "Unit")

    def quantity(self) -> None:
        self.add_import("astropy.units", "Quantity")

    def table(self) -> None:
        self.add_import("astropy.table", "Table")

    def wcs(self) -> None:
        self.add_import("gwcs", "WCS")

    def object_node(self) -> None:
        self.add_import("rad.node", "ObjectNode")

    def array_node(self) -> None:
        self.add_import("rad.node", "ArrayNode")

    def metadata(self) -> None:
        self.add_import("rad.node", "Metadata")

    def mixin(self, mixin: str) -> None:
        self.add_import("rad.node._mixins", mixin)

    def archive_catalog(self) -> None:
        self.add_import("rad.node", "ArchiveCatalog")


@dataclass
class TypeAnnotation(Base):
    type: str
    argument: TypeAnnotation | list[TypeAnnotation] | None = None

    def text(self) -> str:
        text = self.type

        if self.argument:
            if not isinstance(self.argument, list):
                self.argument = [self.argument]
            text += f"[{' | '.join(arg.text() for arg in self.argument)}]"

        return text


@dataclass
class Type(Base, ABC):
    name: str

    @property
    @abstractmethod
    def annotation(self) -> Annotation:
        pass

    @staticmethod
    def extract_docs(schema: dict[str, Any]) -> tuple[str | None, str | None]:
        title: str | None = schema.get("title")
        if title is not None:
            title = dedent(title)

        description: str | None = schema.get("description")
        if description is not None:
            description = dedent(description)

        return title, description

    @staticmethod
    def class_name(name: str) -> str:
        return "".join([p.capitalize() for p in name.split("_")])

    @staticmethod
    def _sanitize_name(name: str) -> tuple[str, str]:
        if name == "pass":
            return name, "pass_"

        new_name = name.replace("~", "_tilde_")

        return name, new_name


@dataclass
class Annotation(Type):
    annotations: list[TypeAnnotation]

    title: str | None = None
    description: str | None = None
    datatype: str | None = None
    destination: list[str] | None = None

    @classmethod
    def empty(cls, type_: str | None = None) -> Annotation:
        type_ = type_ or "Any"
        return cls(name=type_, annotations=[TypeAnnotation(type_)])

    @property
    def is_annotated(self) -> bool:
        return bool(self.title) or bool(self.description) or bool(self.datatype) or bool(self.destination)

    @property
    def has_archive_catalog(self) -> bool:
        return bool(self.datatype) or bool(self.destination)

    def _add_annotated(self, text: str) -> str:
        if self.title or self.description or self.datatype or self.destination:
            meta = []

            if self.title:
                meta.append(f"title={self.title!r}")

            if self.description:
                meta.append(f"description={self.description!r}")

            if self.datatype or self.destination:
                archive = []

                if self.datatype:
                    archive.append(f"datatype={self.datatype!r}")

                if self.destination:
                    archive.append(f"destination={tuple(self.destination)!r}")

                meta.append(f"archive_catalog=ArchiveCatalog({', '.join(archive)})")

            return f"Annotated[{text}, Metadata({', '.join(meta)})]"

        return text

    def text(self):
        if not self.annotations:
            text = "Any"
        else:
            text = " | ".join([ann.text() for ann in self.annotations])

        return self._add_annotated(text)

    @property
    def annotation(self):
        return self

    @staticmethod
    def extract_archive_catalog(schema: dict[str, Any]) -> tuple[str | None, list[str] | None]:
        archive_catalog = schema.get("archive_catalog")
        if not archive_catalog:
            return None, None

        return archive_catalog.get("datatype"), archive_catalog.get("destination")

    def apply_imports(self, module: Module) -> None:
        if self.is_annotated:
            module.imports.annotated()
            module.imports.metadata()

        if self.has_archive_catalog:
            module.imports.archive_catalog()

        if not self.annotations:
            module.imports.any()

    @classmethod
    def _from_metadata(cls, name: str, schema: dict[str, Any], annotations: list[TypeAnnotation], module: Module) -> Annotation:
        title, description = cls.extract_docs(schema)
        datatype, destination = cls.extract_archive_catalog(schema)

        if "id" in schema:
            if module.type != name:
                raise ValueError(f"Schema id '{schema['id']}' does not match expected annotation name '{name}'")

        annotation = cls(
            name=name,
            annotations=annotations,
            title=title,
            description=description,
            datatype=datatype,
            destination=destination,
        )
        annotation.apply_imports(module)
        return annotation

    @staticmethod
    def _formulate_literal(enum: list[Any], type_: type, module: Module) -> list[TypeAnnotation]:
        module.imports.literal()
        return [TypeAnnotation("Literal", TypeAnnotation(", ".join([f"{type_(e)!r}" for e in enum])))]

    @classmethod
    def from_schema_scalar(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Annotation:
        enum = schema.get("enum")

        match type_ := schema.get("type"):
            case "string":
                annotations = cls._formulate_literal(enum, str, module) if enum else [TypeAnnotation("str")]

                return cls._from_metadata(name=name, schema=schema, annotations=annotations, module=module)
            case "integer":
                annotations = cls._formulate_literal(enum, int, module) if enum else [TypeAnnotation("int")]

                return cls._from_metadata(name=name, schema=schema, annotations=annotations, module=module)
            case "number":
                annotations = cls._formulate_literal(enum, float, module) if enum else [TypeAnnotation("float")]

                return cls._from_metadata(name=name, schema=schema, annotations=annotations, module=module)
            case "boolean":
                bool_enum = []
                for value in enum or []:
                    if value == "True":
                        bool_enum.append(True)
                    elif value == "False":
                        bool_enum.append(False)
                    else:
                        raise ValueError(f"Schema for {name} has invalid boolean enum value '{value}'")
                annotations = cls._formulate_literal(bool_enum, bool, module) if bool_enum else [TypeAnnotation("bool")]

                return cls._from_metadata(name=name, schema=schema, annotations=annotations, module=module)
            case "null":
                return cls._from_metadata(name=name, schema=schema, annotations=[TypeAnnotation("None")], module=module)
            case _:
                raise ValueError(f"Schema for {name} has unsupported type '{type_}'")

    @classmethod
    def from_schema_tag(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Annotation:
        if "tag" not in schema:
            raise ValueError(f"Schema for {name} has invalid tag")

        match schema["tag"]:
            case "tag:stsci.edu:asdf/time/time-1.*":
                module.imports.time()
                annotations = [TypeAnnotation("Time")]

            case "tag:astropy.org:astropy/table/table-1.*":
                module.imports.table()
                annotations = [TypeAnnotation("Table")]

            case "tag:stsci.edu:gwcs/wcs-*":
                module.imports.wcs()
                annotations = [TypeAnnotation("WCS")]

            case "tag:stsci.edu:asdf/core/ndarray-1.*":
                dtype = schema.get("datatype")
                if not dtype:
                    raise ValueError(f"Schema for {name} ndarray tag must have a datatype")

                # Convert the ASDF datatype to a numpy dtype and then to a string to write an import
                #   from
                np_dtype = asdf_datatype_to_numpy_dtype(dtype).type.__name__
                module.imports.dtype(np_dtype)

                if (ndim := schema.get("ndim")) is None:
                    module.imports.ndarray_type()
                    annotations = [TypeAnnotation("NDArray", [TypeAnnotation(np_dtype)])]
                else:
                    module.imports.ndarray()
                    annotations = [TypeAnnotation("ndarray", [TypeAnnotation(f"tuple[{', '.join(['int'] * ndim)}], {np_dtype}")])]

            case "tag:stsci.edu:asdf/unit/unit-1.*" | "tag:astropy.org:astropy/units/unit-1.*":
                module.imports.unit()

                annotations = [TypeAnnotation("Unit", [TypeAnnotation(f'"{u}"')]) for u in schema.get("enum", [])]
                if not annotations:
                    annotations = [TypeAnnotation("Unit")]

            case "tag:stsci.edu:asdf/unit/quantity-1.*":
                module.imports.quantity()
                arguments = cls.from_schema_tag(f"{name}Unit", schema.get("unit", {}), module, package).annotations
                annotations = [TypeAnnotation("Quantity", arguments)]

            case _:
                module.imports.any()
                annotations = [TypeAnnotation("Any")]

        return cls._from_metadata(name=name, schema=schema, annotations=annotations, module=module)

    @classmethod
    def from_schema_array(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Annotation:
        # Add the array import
        module.imports.array_node()

        items = schema.get("items")
        if items is None:
            # Items is required for arrays
            module.imports.any()

            arguments = [TypeAnnotation("Any")]
        else:
            annotation = module.process(f"{name}Item", items, package).annotation
            if annotation.is_annotated or annotation.has_archive_catalog:
                raise ValueError(f"Items of array for {name} cannot be annotated or have archive_catalog")

            arguments = annotation.annotations

        annotations = [TypeAnnotation("ArrayNode", arguments)]
        return cls._from_metadata(name=name, schema=schema, annotations=annotations, module=module)

    @classmethod
    def from_schema_anyof(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Annotation:
        if "anyOf" not in schema or not isinstance(schema["anyOf"], list) or not schema["anyOf"]:
            raise ValueError(f"Schema for {name} has invalid anyOf")

        annotations = []
        for index, subschema in enumerate(schema["anyOf"]):
            ann = module.process(f"{name}_{index}", subschema, package).annotation
            if ann.is_annotated or ann.has_archive_catalog:
                raise ValueError(f"Subschema {index} of anyOf for {name} cannot be annotated or have archive_catalog")
            annotations.extend(ann.annotations)

        return cls._from_metadata(name=name, annotations=annotations, schema=schema, module=module)


@dataclass
class Class(Type):
    bases: list[str] | None
    docs: str | None
    properties: dict[str, Annotation]
    required: list[str] | None
    syntax_override: dict[str, tuple[str, Annotation]] | None = None

    @property
    def annotation(self):
        return Annotation.empty(self.name)

    @property
    def type(self) -> str:
        return self.name

    @classmethod
    def empty(cls, name: str) -> Class:
        return cls(name=name, bases=None, docs=None, properties={}, required=None)

    def text(self):
        text = f"class {self.name}"

        if self.bases:
            text += f"({', '.join(self.bases)}):\n"
        else:
            text += "(ObjectNode):\n"

        if self.docs:
            text += indent('"""\n', "    ")
            text += indent(f"{self.docs}\n", "    ")
            text += indent('"""\n\n', "    ")

        if self.required:
            text += indent(f"__required__ = {tuple(sorted(set(self.required)))}\n\n", "    ")
        else:
            text += indent("__required__ = ()\n\n", "    ")

        for name, annotation in sorted(self.properties.items()):
            text += indent(f"{name}: {annotation.text()}\n", "    ")

        if self.properties:
            text += "\n"

        if self.syntax_override:
            for bad_name, (good_name, annotation) in self.syntax_override.items():
                text += indent(
                    dedent(
                        f"""\
                        @property
                        def {good_name}(self) -> {annotation}:
                            \"\"\"Alias for `{bad_name}` to avoid syntax issues.\"\"\"
                            return self['{bad_name}']
                        """
                    ),
                    "    ",
                )

        return text

    def add_property(self, name: str, annotation: Annotation) -> None:
        bad_name, good_name = self._sanitize_name(name)

        if good_name in self.properties:
            raise ValueError(f"Property '{name}' already exists in class '{self.name}'")

        if bad_name != good_name:
            if self.syntax_override is None:
                self.syntax_override = {}

            self.syntax_override[bad_name] = (good_name, annotation)
        else:
            self.properties[name] = annotation

    def add_mixin(self, module: Module) -> None:
        if (mixin_name := f"{self.name}Mixin") in mixins.__all__:
            if self.bases is None:
                self.bases = []
            module.imports.mixin(mixin_name)
            self.bases.append(mixin_name)

    @classmethod
    def _from_metadata(cls, name: str, schema: dict[str, Any], module: Module) -> Class:
        title, description = cls.extract_docs(schema)

        if "id" in schema:
            if module.type != name:
                raise ValueError(f"Schema id '{schema['id']}' does not match expected class name '{name}'")

        title, description = cls.extract_docs(schema)

        docs = ""
        if title:
            docs += f"{title}\n"

        if description:
            docs += f"{indent(description, '    ') if docs else description}\n"

        required = schema.get("required")

        class_ = cls(
            name=name,
            bases=None,
            docs=docs if docs else None,
            properties={},
            required=required,
            syntax_override=None,
        )
        module.add(class_)

        class_.add_mixin(module)

        return class_

    @classmethod
    def from_schema_object(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Class:
        # There is no "AllOf" here so it must be the start of an inheritance chain,
        #   so its base class is ObjectNode
        module.imports.object_node()

        class_ = cls._from_metadata(name=name, schema=schema, module=module)

        for prop_name, prop_schema in schema.get("properties", {}).items():
            cls_name = cls.class_name(prop_name)
            class_.add_property(prop_name, module.process(f"{name}_{cls_name}", prop_schema, package).annotation)

        pattern_properties = {}
        for index, (pattern, pattern_schema) in enumerate(schema.get("patternProperties", {}).items()):
            cls_name = f"PatternProperty{index}"
            pattern_properties[pattern] = module.process(f"{name}_{cls_name}", pattern_schema, package).annotation

        if pattern_properties:
            for required in schema.get("required", []):
                if required not in class_.properties:
                    for pattern, annotation in pattern_properties.items():
                        if match(pattern, required):
                            class_.add_property(required, annotation)
                            break
                    else:
                        module.imports.any()
                        class_.add_property(required, Annotation.empty())

        return class_

    @classmethod
    def from_schema_allof(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Class | Type:
        if "allOf" not in schema:
            raise ValueError(f"Schema for {name} has invalid allOf")

        all_of = schema["allOf"]
        if len(all_of) == 1:
            new_schema = deepcopy(schema)
            del new_schema["allOf"]
            new_schema.update(all_of[0])

            return module.process(name, new_schema, package)

        class_ = cls._from_metadata(name=name, schema=schema, module=module)

        bases = []
        for index, sub_schema in enumerate(all_of):
            # Bail out for when we have a tag and some other things, those
            #   should all be simple restrictions on the tag type
            if "tag" in sub_schema:
                new_schema = deepcopy(schema)
                del new_schema["allOf"]
                new_schema.update(sub_schema)

                del module.classes[class_.name]
                return module.process(name, new_schema, package)

            if "not" in sub_schema:
                module.imports.any()

                del module.classes[class_.name]
                return Annotation.empty()

            type_ = module.process(f"{name}_allOf{index}", sub_schema, package)
            if not isinstance(type_, Class | Module):
                raise ValueError(f"Subschema {index} of allOf for {name} must be an object")

            bases.append(type_.type)

        class_.bases = bases[::-1]

        return class_


class File(Base, ABC):
    @property
    @abstractmethod
    def file_path(self) -> Path:
        pass

    @property
    @abstractmethod
    def path(self) -> Path:
        pass

    @property
    def local_import(self) -> str:
        return f".{self.path.stem}"

    def write(self, base_path: Path, ruff_format: bool = True) -> None:
        path = base_path / self.file_path
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            f.write(self.text())

        if ruff_format:
            run(["ruff", "format", str(path)])  # noqa: S603, S607


@dataclass
class Module(Type, File):
    imports: Import
    annotations: dict[str, Annotation]
    classes: dict[str, Class]

    @property
    def uri(self) -> str:
        return self.name

    @property
    def type(self) -> str:
        type_ = "".join([p.capitalize() for p in name_from_uri(self.uri).split("_")])
        if "reference_files" in self.uri:
            type_ += "Ref"
        return type_

    @property
    def annotation(self):
        return Annotation.empty(self.type)

    @property
    def path(self) -> Path:
        # Remove the version suffix
        path = self.uri.rsplit("-", 1)[0]

        # Remove the base URI
        path = path.split("asdf://stsci.edu/datamodels/roman/schemas/")[-1]
        if len(split := path.rsplit("/", 1)) == 1:
            path = f"_{path}"
        else:
            path = f"{split[0]}/_{split[1]}"

        # Add the .py suffix
        return Path(f"{path}.py")

    @property
    def file_path(self) -> Path:
        return self.path

    def ordered_classes(self) -> Generator[Class, None, None]:
        independent_classes = []
        for cls in self.classes.values():
            for base in cls.bases or []:
                if base in self.classes:
                    break
            else:
                independent_classes.append(cls.name)

        for name in independent_classes:
            yield self.classes[name]

        dependent_classes: list[str] = []
        for cls in self.classes.values():
            if cls.name not in independent_classes:
                base_indices = set()
                for base in cls.bases or []:
                    if base in dependent_classes:
                        base_indices.add(dependent_classes.index(base) + 1)
                    else:
                        base_indices.add(0)

                insert_index = max(base_indices)
                dependent_classes.insert(insert_index, cls.name)

        for name in dependent_classes:
            yield self.classes[name]

    def text(self) -> str:
        text = f"{self.imports.text()}\n"
        text += f"__all__ = ('{self.type}',)\n\n"

        if self.annotations:
            for name, annotation in self.annotations.items():
                text += f"{name}: TypeAlias = {annotation.text()}\n"
            text += "\n"

        if self.classes:
            for cls in self.ordered_classes():
                text += f"{cls.text()}\n"

        return text

    def get_class(self, name: str) -> Class:
        name = self.class_name(name)
        return self.classes[name]

    @classmethod
    def empty(cls, uri: str, package: Package) -> Module:
        module = cls(
            name=uri,
            imports=Import.empty(),
            annotations={},
            classes={},
        )
        package.add_module(module)

        return module

    def add(self, type_: Annotation | Class) -> None:
        match type_:
            case Annotation():
                if type_.name in self.annotations:
                    raise ValueError(f"Annotation '{type_.name}' already exists in module '{self.uri}'")
                self.annotations[type_.name] = type_
            case Class():
                if type_.name in self.classes:
                    raise ValueError(f"Class '{type_.name}' already exists in module '{self.uri}'")
                self.classes[type_.name] = type_
            case _:
                raise ValueError(f"Cannot add type '{type_}' to module '{self.uri}'")

    def import_module(self, module: Module, type_: str | None = None) -> None:
        # Get the module paths without the .py suffix
        target_path = module.path.parent / module.path.stem
        current_path = self.path.parent / self.path.stem

        self.imports.relative_import(target_path, current_path, type_ or module.type)

    @classmethod
    def from_schema(cls, schema: dict[str, Any], package: Package) -> Module:
        uri = schema.get("id")
        if not uri or not uri.startswith("asdf://stsci.edu/datamodels/roman/schemas/"):
            raise ValueError(f"Schema id '{uri}' is not a valid RAD schema URI")

        module = cls.empty(uri, package)
        if definitions := schema.get("definitions"):
            for def_name, def_schema in definitions.items():
                module.process(cls._sanitize_name(cls.class_name(def_name))[1], def_schema, package)

        output = module.process(module.type, schema, package)

        if isinstance(output, Annotation):
            module.add(output)

        if module.annotations:
            module.imports.type_alias()

        return module

    def process(self, name: str, schema: dict[str, Any], package: Package) -> Type:
        type_ = schema.get("type")
        if not type_:
            if "anyOf" in schema:
                return Annotation.from_schema_anyof(name, schema, self, package)

            elif "allOf" in schema:
                return Class.from_schema_allof(name, schema, self, package)

            elif "$ref" in schema:
                return package.resolve_ref(schema, self)

            elif "tag" in schema:
                return Annotation.from_schema_tag(name, schema, self, package)

            else:
                self.imports.any()
                return Annotation.empty()

        match type_:
            case "string" | "number" | "integer" | "boolean" | "null":
                return Annotation.from_schema_scalar(name, schema, self, package)

            case "array":
                return Annotation.from_schema_array(name, schema, self, package)

            case "tag":
                return Annotation.from_schema_tag(name, schema, self, package)

            case "object":
                return Class.from_schema_object(name, schema, self, package)

            case _:
                raise ValueError(f"Schema for {name} has unsupported type '{type_}'")


@dataclass
class Init(File):
    modules: dict[str, Module]
    imports: Import
    inits: dict[Path, Init]
    module_path: Path

    @property
    def path(self) -> Path:
        return self.module_path

    @property
    def file_path(self) -> Path:
        return self.module_path / "__init__.py"

    @classmethod
    def empty(cls, path: Path) -> Init:
        return cls(modules={}, imports=Import.empty(), inits={}, module_path=path)

    def add_module(self, module: Module) -> None:
        self.modules[module.uri] = module
        self.imports.add_import(module.local_import, module.type)

    def add_init(self, init: Init) -> None:
        self.inits[init.module_path] = init

    @property
    def api(self) -> list[str]:
        api = []

        for module in self.modules.values():
            self.imports.add_import(module.local_import, module.type)
            api.append(module.type)

        for init in self.inits.values():
            for entry in init.api:
                self.imports.add_import(init.local_import, entry)

            api.extend(init.api)

        if len(api) != len(set(api)):
            raise ValueError(f"Duplicate __all__ entries found in package at '{self.module_path}'")

        return sorted(api)

    def text(self):
        api = self.api

        text = f"{self.imports.text()}\n"
        text += "__all__ = (\n"
        text += indent(",\n".join([f'"{entry}"' for entry in api]), "    ")
        text += "\n)\n"

        return text


@dataclass
class Package:
    modules: dict[str, Module]

    @classmethod
    def empty(cls) -> Package:
        return cls(modules={})

    def add_module(self, module: Module) -> None:
        if module.uri in self.modules:
            raise ValueError(f"Module '{module.uri}' already exists in package")

        self.modules[module.uri] = module

    def add_ref(self, uri: str) -> None:
        if uri in self.modules:
            return

        if not uri.startswith("asdf://stsci.edu/datamodels/roman/schemas/"):
            raise ValueError(f"Schema id '{uri}' is not a valid RAD schema URI")

        schema = load_schema(uri)
        Module.from_schema(schema, self)

    def get_uri(self, uri: str) -> Module:
        if uri not in self.modules:
            self.add_ref(uri)

        return self.modules[uri]

    def resolve_ref(self, schema: dict[str, Any], module: Module) -> Module | Class:
        uri: str | None = schema.get("$ref")
        if not uri:
            raise ValueError(f"Schema $ref '{uri}' is not a valid RAD schema URI")

        if "#/definitions/" in uri:
            def_uri, def_name = uri.split("#/definitions/", 1)
            ref_module = self.get_uri(def_uri)
            class_ = ref_module.get_class(def_name)
            module.import_module(ref_module, class_.type)
            return class_

        ref = self.get_uri(uri)
        module.import_module(ref)

        return ref

    @classmethod
    def from_manifest(cls, uri: str) -> Package:
        """
        Create a StubFiles object from a schema manifest
        """
        package = cls.empty()
        manifest = load_schema(uri)

        for item in manifest["tags"]:
            package.add_ref(item["schema_uri"])

        return package

    @property
    def sub_packages(self) -> dict[Path, Init]:
        """
        Find the sub-packages for this package organized by path
        """
        sub_packages: dict[Path, Init] = {}

        def _ensure_init(path: Path, child: Init | None = None) -> None:
            if path not in sub_packages:
                init = Init.empty(path)
                sub_packages[path] = init

                # Insure we don't add the root to itself
                if path.parent != path:
                    _ensure_init(path.parent, init)
            if child:
                sub_packages[path].add_init(child)

        for module in self.modules.values():
            sub_package_path = module.path.parent
            _ensure_init(sub_package_path)
            sub_packages[sub_package_path].add_module(module)

        return sub_packages

    def write(self, base_path: Path, ruff_format: bool = True) -> None:
        for module in self.modules.values():
            module.write(base_path, ruff_format=ruff_format)

        for init in self.sub_packages.values():
            init.write(base_path, ruff_format=ruff_format)
