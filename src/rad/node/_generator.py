from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent, indent
from typing import TYPE_CHECKING

from asdf.schema import load_schema

from rad.node._utils import name_from_uri

if TYPE_CHECKING:
    from typing import Any


class BaseStub(ABC):
    """
    Base class for all stub
    """

    @property
    @abstractmethod
    def has_text(self) -> bool:
        pass

    @abstractmethod
    def text(self) -> str:
        pass


@dataclass
class StubImport(BaseStub):
    modules: set[str]
    from_: dict[str, set[str]]

    @property
    def has_text(self):
        return bool(self.modules) or bool(self.from_)

    def text(self) -> str:
        text = ""
        for module in sorted(self.modules):
            text += f"import {module}\n"
        for from_, imports in sorted(self.from_.items()):
            text += f"from {from_} import {', '.join(sorted(imports))}\n"
        return text

    @classmethod
    def empty(cls) -> StubImport:
        return cls(set(), {})

    def update(self, other: StubImport) -> None:
        self.modules |= other.modules

        for from_, imports in other.from_.items():
            if from_ not in self.from_:
                self.from_[from_] = set()

            self.from_[from_] |= imports


@dataclass
class StubImports(BaseStub):
    python: StubImport
    package: StubImport
    rad: StubImport
    subs: StubImport

    @property
    def has_text(self):
        return self.python.has_text or self.package.has_text or self.rad.has_text or self.subs.has_text

    def text(self):
        text = "from __future__ import annotations\n\n"

        if self.python.has_text:
            text += f"{self.python.text()}\n"
        if self.package.has_text:
            text += f"{self.package.text()}\n"
        if self.rad.has_text:
            text += f"{self.rad.text()}\n"
        if self.subs.has_text:
            text += f"{self.subs.text()}\n"

        return text

    @classmethod
    def empty(cls) -> StubImports:
        return cls(StubImport.empty(), StubImport.empty(), StubImport.empty(), StubImport.empty())

    @classmethod
    def alias(cls) -> StubImports:
        imports = cls.empty()
        imports.python.from_["typing"] = {"TypeAlias"}
        return imports

    def update(self, other: StubImports) -> None:
        self.python.update(other.python)
        self.package.update(other.package)
        self.rad.update(other.rad)
        self.subs.update(other.subs)


@dataclass
class StubObject(BaseStub):
    name: str


@dataclass
class StubAlias(StubObject):
    type_: str | None

    @property
    def has_text(self):
        return bool(self.type_)

    def text(self):
        text = ""
        if self.type_:
            text += f"{self.name}: TypeAlias = {self.type_}\n"

        return text

    @classmethod
    def empty(cls, name: str) -> StubAlias:
        return cls(name, None)

    @classmethod
    def from_schema_scalar(cls, name: str, schema: dict[str, Any], stub: StubFile, stubs: StubFiles) -> StubAlias | StubEnum:
        type_ = schema.get("type")
        match type_:
            case "string":
                if "enum" in schema:
                    return StubEnum.from_schema_enum(name, schema, stub)

                return cls(name, "str")
            case "number":
                return cls(name, "float")
            case "integer":
                if "enum" in schema:
                    stub.imports.python.update(StubImport(set(), {"typing": {"Literal"}}))

                    return cls(name, f"Literal[{', '.join([str(v) for v in schema['enum']])}]")
                return cls(name, "int")
            case "boolean":
                return cls(name, "bool")
            case "null":
                return cls(name, "None")
            case "array":
                stub.imports.rad.update(StubImport(set(), {"rad._node": {"LNode"}}))

                items = schema.get("items")
                if items is None:
                    stub.imports.python.update(StubImport(set(), {"typing": {"Any"}}))

                    return cls(name, "LNode[Any]")

                if (item_type_ := stub.process_schema(f"{name}Item", items, stubs).type_) is None:
                    stub.imports.python.update(StubImport(set(), {"typing": {"Any"}}))

                return cls(name, f"LNode[{item_type_ or 'Any'}]")
            case _:
                raise ValueError(f"Unknown scalar type: {type_}")

    @classmethod
    def from_schema_anyof(cls, name: str, schema: dict[str, Any], stub: StubFile, stubs: StubFiles) -> StubAlias:
        if "anyOf" not in schema:
            raise ValueError("Schema must have an anyOf")

        types = []
        for sub_schema in schema["anyOf"]:
            if type_ := stub.process_schema("Base", sub_schema, stubs).type_:
                types.append(type_)

        if not types:
            stub.imports.python.update(StubImport(set(), {"typing": {"Any"}}))

        return cls(name, " | ".join(sorted(set(types))) if types else "Any")

    @classmethod
    def from_schema_tag(cls, name: str, schema: dict[str, Any], stub: StubFile, stubs: StubFiles) -> StubAlias:
        tag = schema.get("tag")
        if tag is None:
            raise ValueError("Schema must have a tag")

        match tag:
            case "tag:stsci.edu:asdf/time/time-1.*":
                stub.imports.package.update(StubImport(set(), {"astropy.time": {"Time"}}))
                return cls(name, "Time")

            case "tag:stsci.edu:asdf/core/ndarray-1.*":
                datatype = f"np.{schema['datatype']}"
                stub.imports.package.update(StubImport(set(), {"numpy": {datatype}, "numpy.typing": {"NDArray"}}))
                return cls(name, f"NDArray[{datatype}]")

            case "tag:stsci.edu:asdf/unit/unit-1.*" | "tag:astropy.org:astropy/units/unit-1.*":
                stub.imports.package.update(StubImport(set(), {"astropy.units": {"Unit"}}))
                unit = " |".join([f'Unit("{u}")' for u in schema.get("enum", [])])
                if not unit:
                    unit = "Unit"
                return cls(name, unit)

            case "tag:stsci.edu:asdf/unit/quantity-1.*":
                stub.imports.package.update(StubImport(set(), {"astropy.units": {"Quantity"}}))
                unit_alias = cls.from_schema_tag(f"{name}Unit", schema["unit"], stub, stubs)
                return cls(name, f"Quantity[{unit_alias.type_}]")

            case "tag:astropy.org:astropy/table/table-1.*":
                stub.imports.package.update(StubImport(set(), {"astropy.table": {"Table"}}))
                return cls(name, "Table")

            case "tag:stsci.edu:gwcs/wcs-*":
                stub.imports.package.update(StubImport(set(), {"gwcs": {"WCS"}}))
                return cls(name, "WCS")

            case _:
                stub.imports.python.update(StubImport(set(), {"typing": {"Any"}}))
                return cls(name, "Any")


@dataclass
class StubEnum(StubObject):
    values: list[str]
    docs: str | None = None

    @property
    def type_(self) -> str:
        return self.name

    @property
    def has_text(self):
        return bool(self.name) or bool(self.values)

    @staticmethod
    def _name_from_value(value: str) -> str:
        return value.upper().replace("/", "_").replace("-", "_")

    def text(self):
        text = f"class {self.name}(StrEnum):\n"

        if self.docs:
            text += indent('"""\n', "    ")
            text += indent(f"{self.docs}\n", "    ")
            text += indent('"""\n\n', "    ")

        for value in self.values:
            text += indent(f'{self._name_from_value(value)} = "{value}"\n', "    ")

        return text

    @classmethod
    def from_schema_enum(cls, name: str, schema: dict[str, Any], stub: StubFile) -> StubEnum | StubAlias:
        if "enum" not in schema:
            raise ValueError("Schema must have an enum")

        if schema.get("type") != "string":
            raise ValueError("Schema enum must be of type string")

        # Determine the docstring
        docs = dedent(schema.get("title", ""))
        if description := dedent(schema.get("description", "")):
            docs += f"\n\n{description}"

        values = schema["enum"]
        if "id" not in schema:
            stub.imports.python.update(StubImport(set(), {"typing": {"Literal"}}))
            return StubAlias(name, f"Literal[{', '.join([repr(v) for v in values])}]")

        stub.imports.python.update(StubImport(set(), {"enum": {"StrEnum"}}))

        enum_ = cls(name, values, docs)
        stub.add_class(enum_)

        return enum_


@dataclass
class StubClass(StubObject):
    bases: list[str] | None
    docs: str | None
    properties: dict[str, str]
    required: list[str] | None = None

    @property
    def type_(self) -> str:
        return self.name

    @property
    def has_text(self):
        return bool(self.name) or any(self.bases) or bool(self.docs) or bool(self.properties) or self.imports.has_text

    def text(self):
        if self.bases:
            text = f"class {self.name}({','.join(self.bases)}):\n"
        else:
            text = f"class {self.name}:\n"

        if self.docs:
            text += indent('"""\n', "    ")
            text += indent(f"{self.docs}\n", "    ")
            text += indent('"""\n\n', "    ")

        if self.required:
            text += indent(f"__required__ = {tuple(sorted(set(self.required)))}\n\n", "    ")
        else:
            text += indent("__required__ = ()\n\n", "    ")

        for name, type_ in sorted(self.properties.items()):
            text += indent(f"{name}: {type_}\n", "    ")

        return text

    @classmethod
    def from_schema_object(cls, name: str, schema: dict[str, Any], stub: StubFile, stubs: StubFiles) -> StubClass:
        if "id" in schema:
            if stub.name != name:
                raise ValueError("Schema id does not match the class name")

            stub.name = name

        # Determine the docstring
        docs = dedent(schema.get("title", ""))
        if description := dedent(schema.get("description", "")):
            docs += f"\n\n{description}"

        properties = {}
        for prop_name, prop_schema in schema.get("properties", {}).items():
            cls_name = "".join([p.capitalize() for p in prop_name.split("_")])
            processed = stub.process_schema(cls_name, prop_schema, stubs)
            match processed:
                case StubClass() | StubFile():
                    properties[prop_name] = processed.name
                case StubAlias():
                    if processed.type_ is None:
                        stub.imports.python.update(StubImport(set(), {"typing": {"Any"}}))

                    properties[prop_name] = processed.type_ or "Any"

        stub.imports.rad.update(StubImport(set(), {"rad._node": {"DNode"}}))

        class_ = cls(name, ["DNode"], docs, properties, schema.get("required"))
        stub.add_class(class_)

        return class_

    @classmethod
    def from_schema_allof(
        cls, name: str, schema: dict[str, Any], stub: StubFile, stubs: StubFiles
    ) -> StubClass | StubAlias | StubFile | StubEnum:
        if "allOf" not in schema:
            raise ValueError("Schema must have an allOf")

        if len(schema["allOf"]) == 1:
            return stub.process_schema(name, schema["allOf"][0], stubs)

        bases = []
        object_schema = None
        for sub_schema in schema["allOf"]:
            if "tag" in sub_schema:
                return StubAlias.from_schema_tag(name, sub_schema, stub, stubs)

            if "$ref" in sub_schema:
                bases.append(stub.process_schema("Base", sub_schema, stubs).name)

            if sub_schema.get("type") == "object":
                if object_schema is not None:
                    raise ValueError("Schema can only have one object in allOf")
                object_schema = sub_schema

        class_ = cls.from_schema_object(name, object_schema or {}, stub, stubs)
        class_.bases = bases

        return class_


@dataclass
class StubClasses(BaseStub):
    classes: dict[str, StubClass | StubEnum]

    @property
    def has_text(self):
        return bool(self.classes) and any(cls.has_text for cls in self.classes)

    def text(self):
        text = ""
        for cls in self.classes.values():
            if cls.has_text:
                text += f"{cls.text()}\n\n"
        return text

    @classmethod
    def empty(cls) -> StubClasses:
        return cls({})

    def add_class(self, class_: StubClass | StubEnum) -> None:
        if class_.name in self.classes:
            raise ValueError(f"Class {class_.name} already exists in StubClasses")

        self.classes[class_.name] = class_


@dataclass
class StubFile(StubObject):
    imports: StubImports
    alias: StubAlias | None
    classes: StubClasses | None
    path: Path

    @property
    def type_(self) -> str:
        return self.name

    @property
    def has_text(self):
        return self.imports.has_text or self.alias.has_text or self.classes.has_text

    def relative_import(self, other: StubFile) -> StubImport:
        # This is python 3.12+
        path = (other.path.parent / other.path.stem).relative_to(self.path.parent / self.path.stem, walk_up=True).as_posix()  # type: ignore[call-arg]
        path = path.replace("..", "").replace("/", ".")

        return StubImport(set(), {path: {other.name}})

    def add_class(self, class_: StubClass | StubEnum) -> None:
        if self.classes is None:
            if self.alias is not None:
                raise ValueError("StubFile cannot have both aliases and classes")

            self.classes = StubClasses.empty()
        self.classes.add_class(class_)

    def text(self):
        text = f"{self.imports.text()}\n"
        text += f'__all__ = ("{self.name}",)\n\n'

        if self.alias is not None:
            text += f"{self.alias.text()}\n"

        if self.classes is not None:
            text += f"\n{self.classes.text()}\n"

        return text

    @classmethod
    def empty(cls, name, path: Path) -> StubFile:
        return cls(name, StubImports.empty(), None, None, path)

    @classmethod
    def from_schema(cls, schema: dict[str, Any], stubs: StubFiles) -> StubFile:
        uri = schema.get("id")
        if not uri:
            raise ValueError("Schema must have an id")

        # Remove the version suffix
        path = uri.rsplit("-", 1)[0]
        # Remove the base URI
        path = path.split("asdf://stsci.edu/datamodels/roman/schemas/")[-1]
        if len(split := path.rsplit("/", 1)) == 1:
            path = f"_{path}"
        else:
            path = f"{split[0]}/_{split[1]}"

        name = "".join([p.capitalize() for p in name_from_uri(uri).split("_")])
        if "reference_files" in uri:
            name += "Ref"

        stub = cls.empty(name, Path(f"{path}.py"))
        processed = stub.process_schema(name, schema, stubs)
        if isinstance(processed, StubAlias):
            stub.alias = processed

        return stub

    def process_schema(self, name: str, schema: dict[str, Any], stubs: StubFiles) -> StubClass | StubAlias | StubFile | StubEnum:
        type_ = schema.get("type")
        if not type_:
            if "anyOf" in schema:
                type_ = "anyOf"
            elif "allOf" in schema:
                type_ = "allOf"
            elif "$ref" in schema:
                type_ = "$ref"
            elif "tag" in schema:
                type_ = "tag"
            else:
                raise ValueError(f"Schema for {name} must have a type, anyOf, or allOf")

        match type_:
            case "object":
                return StubClass.from_schema_object(name, schema, self, stubs)
            case "string" | "number" | "integer" | "boolean" | "null" | "array":
                return StubAlias.from_schema_scalar(name, schema, self, stubs)
            case "allOf":
                return StubClass.from_schema_allof(name, schema, self, stubs)
            case "anyOf":
                return StubAlias.from_schema_anyof(name, schema, self, stubs)
            case "$ref":
                return stubs.schema_ref(schema, self)
            case "tag":
                return StubAlias.from_schema_tag(name, schema, self, stubs)
            case _:
                raise ValueError(f"Unknown schema type: {type_}")

    def write(self, base_path: Path) -> None:
        if not self.has_text:
            raise ValueError("StubFile has no text to write")

        path = base_path / self.path
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            f.write(self.text())


@dataclass
class StubFiles:
    files: dict[str, StubFile]

    def schema_ref(self, schema: dict[str, Any], stub: StubFile) -> StubFile:
        uri = schema.get("$ref")
        if not uri:
            raise ValueError("Schema must have a $ref")

        if uri not in self.files:
            self.add_ref(uri)

        file = self.files[uri]
        stub.imports.subs.update(stub.relative_import(file))

        return file

    def add_ref(self, uri: str) -> None:
        if uri in self.files:
            raise ValueError(f"Schema {uri} already exists in StubFiles")

        print(f"Parsing {uri}")

        schema = load_schema(uri)
        stub = StubFile.from_schema(schema, self)
        self.files[uri] = stub

    @classmethod
    def empty(cls) -> StubFiles:
        return cls({})

    @classmethod
    def from_manifest(cls, uri: str) -> StubFiles:
        """
        Create a StubFiles object from a schema manifest
        """
        stubs = cls.empty()
        manifest = load_schema(uri)

        for item in manifest["tags"]:
            stubs.add_ref(item["schema_uri"])

        return stubs

    def write(self, base_path: Path) -> None:
        for stub in self.files.values():
            stub.write(base_path)


if __name__ == "__main__":
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/source_catalog-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/photometry-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/filename-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/file_date-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/basic-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/telescope-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/origin-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/coordinates-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/sky_background-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/wcsinfo-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/enums/cal_step_flag-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/enums/guidewindow_modes-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/enums/exposure_type-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/exposure-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/meta/common-1.0.0"
    # # uri = "asdf://stsci.edu/datamodels/roman/schemas/wfi_science_raw-1.4.0"
    # uri = "asdf://stsci.edu/datamodels/roman/schemas/wfi_image-1.4.0"
    # stubs = StubFiles({})
    # stubs.add_ref(uri)

    # print(stubs.files[uri].text())

    manifest_uri = "asdf://stsci.edu/datamodels/roman/manifests/datamodels-1.5.0"
    stubs = StubFiles.from_manifest(manifest_uri)
    for uri, stub in stubs.files.items():
        print(f"{uri} -> {stub.path}")

    stubs.write(Path(__file__).parent / "nodes")
