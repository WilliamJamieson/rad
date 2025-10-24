"""
Implementation of automatic code generation based on the RAD ASDF schemas.
"""

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

from rad import node

from . import _mixins as mixins
from ._base import ArrayNode, ObjectNode
from ._metadata import ArchiveCatalog, Metadata
from ._utils import name_from_uri

if TYPE_CHECKING:
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
    Base class for all for code generation entities.
    """

    @abstractmethod
    def text(self) -> str:
        """Generate the text that will be written to a code file."""


@dataclass
class Import(Base):
    """
    Class to manage the imports required for the generated code to function.

    Attributes
    ----------
    items : dict[str, set[str]]
        A dictionary mapping module names to sets of type names to import from those modules.
            from <key> import <value1>, <value2>, ...
        Note that the values are a set so we don't duplicate imports.
    """

    items: dict[str, set[str]]

    def text(self) -> str:
        # Start all modules with future annotations import
        #   This allows us to use type hints freely without worrying about
        #   having to turn some into a string.
        text = "from __future__ import annotations\n\n"

        # Add the imports sorted by module and type name
        for item, imports in sorted(self.items.items()):
            text += f"from {item} import {', '.join(sorted(imports))}\n"
        return text

    def add_import(self, module: str, type_: str) -> None:
        """
        Add import to the import tracking

        This produces an import statement of equivalent to:
            from <module> import <type_>

        Parameters
        ----------
        module
            The module key to import from
        type_
            The type name to import from the module
        """
        # Bail out for if we are trying to import from the current module,
        #   this will happen when a schema references a definition inside itself.
        #   It is simpler to just detect this case and skip adding an import.
        if module == ".":
            return

        # If the module is not already present, add it
        if module not in self.items:
            self.items[module] = set()

        # Include the type in the module's import set
        self.items[module].add(type_)

    def relative_import(self, target_path: Path, current_path: Path, type_: str) -> None:
        """
        Compute the import statement for a relative import of a module

        Parameters
        ----------
        target_path
            The path to the target module's file location
        current_path
            The path to the current module's file location
        type_
            The type to import from the target module
        """
        # Compute the relative module paths
        path = _relative_path(target_path, current_path)

        # Convert the convert the relative path to a module import string
        module = path.as_posix().replace("..", "").replace("/", ".")
        self.add_import(module, type_)

    @classmethod
    def empty(cls) -> Import:
        """
        Initialize an empty Import object
        """
        return cls({})

    def any(self) -> None:
        """
        Add the `from typing import Any` statement
        """
        self.add_import("typing", "Any")

    def type_alias(self) -> None:
        """
        Add the `from typing import TypeAlias` statement
        """
        self.add_import("typing", "TypeAlias")

    def annotated(self) -> None:
        """
        Add the `from typing import Annotated` statement
        """
        self.add_import("typing", "Annotated")

    def literal(self) -> None:
        """
        Add the `from typing import Literal` statement
        """
        self.add_import("typing", "Literal")

    def proxy(self) -> None:
        """
        Add the `from types import MappingProxyType` statement
        """
        self.add_import("types", "MappingProxyType")

    def dtype(self, dtype: str) -> None:
        """
        Add the `from numpy import <dtype>` statement
            e.g. `from numpy import float32`

        Parameters
        ----------
        dtype
            The string name of the numpy dtype to import
        """
        self.add_import("numpy", dtype)

    def ndarray(self) -> None:
        """Add the `from numpy import ndarray` statement"""
        self.add_import("numpy", "ndarray")

    def ndarray_type(self) -> None:
        """Add the `from numpy.typing import NDArray` statement"""
        self.add_import("numpy.typing", "NDArray")

    def time(self) -> None:
        """Add the `from astropy.time import Time` statement"""
        self.add_import("astropy.time", "Time")

    def unit(self) -> None:
        """Add the `from astropy.units import Unit` statement"""
        self.add_import("astropy.units", "Unit")

    def quantity(self) -> None:
        """Add the `from astropy.units import Quantity` statement"""
        self.add_import("astropy.units", "Quantity")

    def table(self) -> None:
        """Add the `from astropy.table import Table` statement"""
        self.add_import("astropy.table", "Table")

    def wcs(self) -> None:
        """Add the `from gwcs import WCS` statement"""
        self.add_import("gwcs", "WCS")

    def object_node(self) -> None:
        """Add the `from rad.node import ObjectNode` statement"""
        self.add_import(node.__name__, ObjectNode.__name__)

    def array_node(self) -> None:
        """Add the `from rad.node import ArrayNode` statement"""
        self.add_import(node.__name__, ArrayNode.__name__)

    def metadata(self) -> None:
        """Add the `from rad.node import Metadata` statement"""
        self.add_import(node.__name__, Metadata.__name__)

    def archive_catalog(self) -> None:
        """
        Add the `from rad.node import ArchiveCatalog` statement
        """
        self.add_import(node.__name__, ArchiveCatalog.__name__)

    def mixin(self, mixin: str) -> None:
        """
        Add the `from rad.node._mixins import <mixin>` statement

        Parameters
        ----------
        mixin
            The string name of the mixin to import
        """

        self.add_import(mixins.__name__, mixin)


@dataclass
class TypeAnnotation(Base):
    """
    Class to represent a type Annotation with optional arguments.
        e.g. `<type>[<argument1> | <argument2> | ...]`
    Note this assumes that the list of arguments are unioned (or-ed) together, rather than
        multiple arguments annotating `<type>` like `<type>[<argument1>, <argument2>, ...]`

    Attributes
    ----------
    type : str
        The main type name
    argument : TypeAnnotation | list[TypeAnnotation] | None
        The argument(s) to the type, if any. These need to be TypeAnnotation objects themselves.

    """

    type: str
    argument: TypeAnnotation | list[TypeAnnotation] | None = None

    def text(self):
        text = self.type

        # Check if we have arguments to include included otherwise we won't add the brackets
        if self.argument:
            # We assume a list of arguments below so we need to convert a single argument into a list
            if not isinstance(self.argument, list):
                self.argument = [self.argument]

            # Join the arguments with a pipe to indicate union (if there is just one there will be no pipe)
            text += f"[{' | '.join(arg.text() for arg in self.argument)}]"

        return text


@dataclass
class Type(Base, ABC):
    """
    Base class for handling things that will be a "type"

    Attributes
    ----------
    name : str
        The name of the type (usually the class or annotation name, but it can
        be a simple key to store the type under)
    """

    name: str

    @property
    @abstractmethod
    def annotation(self) -> Annotation:
        """
        The annotation representation of this type. That would be used to reference
        this type as a type hint in the code base.
        """
        pass

    @staticmethod
    def extract_docs(schema: dict[str, Any]) -> tuple[str | None, str | None]:
        """
        Pull the documentation related strings out of the schema

        Parameters
        ----------
        schema
            The schema dictionary to extract the docs from
        Returns
        -------
        tuple[str | None, str | None]
            The title and description strings, dedented, or None if not present
        """
        title: str | None = schema.get("title")
        if title is not None:
            # Remove any indentation from the title that may be present
            #    in the raw yaml file due to formatting
            title = dedent(title)

        description: str | None = schema.get("description")
        if description is not None:
            # Remove any indentation from the description that may be present
            #    in the raw yaml file due to formatting
            description = dedent(description)

        return title, description

    @staticmethod
    def class_name(name: str) -> str:
        """
        Turn a snake case name into a PascalCase class name which is our convention
        for class names.

        Parameters
        ----------
        name
            The snake case name to convert

        Returns
        str
            The PascalCase version of the name
        """
        return "".join([p.capitalize() for p in name.split("_")])

    @staticmethod
    def _sanitize_name(name: str) -> tuple[str, str]:
        """
        Strip out any bits of the name which place the name as invalid python
        syntax

        This function is ad hoc and only handles known issues in the RAD schemas
        so far. Meaning if we find more issues we will need to update this function.

        Handled Cases:
        - "pass" is a reserved keyword in Python so we rename it to "pass_"
        - "~" is not allowed in Python identifiers so we replace it with "_tilde_"

        Parameters
        ----------
        name
            The name to sanitize

        Returns
        -------
        tuple[str, str]
            The original name and the sanitized version
        """
        # Some of the schemas in RAD use "pass" as a property name which is
        #   a reserved keyword in Python, so we need to rename it to "pass_"
        if name == "pass":
            return name, "pass_"

        # Some of the schemas in RAD use "~" in property names which is not
        #   allowed in Python identifiers so we need to replace it with "_tilde_"
        new_name = name.replace("~", "_tilde_")

        # Note in most cases these will be the same but we return both for
        #   clarity
        return name, new_name


@dataclass
class Annotation(Type):
    """
    Class to handle the representation of an annotated type hint. That is
        `Annotated[<type>, <additional info on type>]`

    This is useful for pulling in documentation on the actual properties from the
    schema into the type hints. At run time it is possible to access this information
    by using the `get_type_hints` function from the `typing` module with the `include_extras=True`
    argument.

    Attributes
    ----------
    annotations : list[TypeAnnotation]
        The list of TypeAnnotation objects that make up the unioned type hint.

    title : str | None
        The title documentation for this annotation, if any.
    description : str | None
        The description documentation for this annotation, if any.
    datatype : str | None
        The archive_catalog datatype for this annotation, if any.
    destination : list[str] | None
        The archive_catalog destination list for this annotation, if any.
    """

    annotations: list[TypeAnnotation]

    title: str | None = None
    description: str | None = None
    datatype: str | None = None
    destination: list[str] | None = None

    @classmethod
    def empty(cls, type_: str | None = None) -> Annotation:
        """
        Create an empty Annotation object (one with no metadata)

        Parameters
        ----------
        type_, optional
            The name of the type to be used, by default it is the "Any" type

        Returns
        -------
            An empty Annotation object
        """
        type_ = type_ or "Any"
        return cls(name=type_, annotations=[TypeAnnotation(type_)])

    @property
    def is_annotated(self) -> bool:
        """Check if the annotation has any metadata."""
        return bool(self.title) or bool(self.description) or bool(self.datatype) or bool(self.destination)

    @property
    def has_archive_catalog(self) -> bool:
        """Check if the annotation has archive_catalog metadata."""
        return bool(self.datatype) or bool(self.destination)

    def _add_annotated(self, text: str) -> str:
        """
        Generated the `Annotated[<text>, ...]` text if there is any metadata to include.

        Parameters
        ----------
        text
            The main type text to annotate
        Returns
        -------
            The annotated text, with metadata included if present or simply the text if no metadata

        """
        if self.is_annotated:
            meta = []

            if self.title:
                meta.append(f"title={self.title!r}")

            if self.description:
                meta.append(f"description={self.description!r}")

            if self.has_archive_catalog:
                archive = []

                if self.datatype:
                    archive.append(f"datatype={self.datatype!r}")

                if self.destination:
                    archive.append(f"destination={tuple(self.destination)!r}")

                meta.append(f"archive_catalog=ArchiveCatalog({', '.join(archive)})")

            return f"Annotated[{text}, Metadata({', '.join(meta)})]"

        return text

    def text(self):
        # If there are no type annotations, we default to Any
        if not self.annotations:
            text = "Any"
        else:
            # Union all the type annotations together
            #    Note that if there is just one annotation there will be no pipe added
            text = " | ".join([ann.text() for ann in self.annotations])

        # Wrap the text in Annotated if we have any metadata to include
        return self._add_annotated(text)

    @property
    def annotation(self):
        return self

    @staticmethod
    def extract_archive_catalog(schema: dict[str, Any]) -> tuple[str | None, list[str] | None]:
        """
        From a schema extract the archive_catalog information if present.

        Parameters
        ----------
        schema
            The schema dictionary to extract the archive_catalog info from

        Returns
        -------
        type | None, list[str] | None
            The datatype and destination list, or None if not present
        """
        archive_catalog = schema.get("archive_catalog")
        if not archive_catalog:
            return None, None

        return archive_catalog.get("datatype"), archive_catalog.get("destination")

    def apply_imports(self, module: Module) -> None:
        """
        Apply the necessary imports to the module based on the annotation's metadata.

        Parameters
        ----------
        module
            The module object to apply the imports to
        """
        # This is true if there is any metadata to include
        #   which means we need to import Annotated and Metadata imports
        if self.is_annotated:
            module.imports.annotated()
            module.imports.metadata()

        # This is true if there is archive_catalog metadata to include
        #   Note that this implies is_annotated is also true
        if self.has_archive_catalog:
            module.imports.archive_catalog()

        # If there are no annotations we need to import Any
        if not self.annotations:
            module.imports.any()

    @classmethod
    def _from_metadata(cls, name: str, schema: dict[str, Any], annotations: list[TypeAnnotation], module: Module) -> Annotation:
        """
        Finalize construction of the type from a schema by finding and including
        any metadata and telling the module in question to add imports as needed.

        Parameters
        ----------
        name
            The name of the annotation
        schema
            The schema dictionary to extract metadata from
        annotations
            The list of TypeAnnotation objects that make up the annotation
        module
            The module object to apply the imports to

        Returns
        -------
            The constructed Annotation object with the metadata from the schema included

        Side Effects
        ------------
            Modifies the module to include any necessary imports for the metadata

        Raises
        ------
        ValueError
            Does a sanity check to ensure that the name matches the schema id if present
        """
        # Pull out the metadata from the schema
        title, description = cls.extract_docs(schema)
        datatype, destination = cls.extract_archive_catalog(schema)

        # Sanity check the schema id if present
        if "id" in schema:
            if module.type != name:
                raise ValueError(f"Schema id '{schema['id']}' does not match expected annotation name '{name}'")

        # Construct the annotation object
        annotation = cls(
            name=name,
            annotations=annotations,
            title=title,
            description=description,
            datatype=datatype,
            destination=destination,
        )
        # Apply the necessary imports to the module
        annotation.apply_imports(module)

        return annotation

    @staticmethod
    def _formulate_literal(enum: list[Any], type_: type, module: Module) -> list[TypeAnnotation]:
        """
        Handle the case where we have an enumeration of all possible values for type in the schemas

        Parameters
        ----------
        enum
            The list of enumerated values from the schema
        type_
            The Python type expected for the enumerated values, this is so we can format them correctly
            in the generated code.
        """
        module.imports.literal()
        # Note that the `type_(e)!r` gives us the exact representation of the value in code. If this
        #   was an int for example we would get `'1'` in the generated code without the `!r` part
        return [TypeAnnotation("Literal", TypeAnnotation(", ".join([f"{type_(e)!r}" for e in enum])))]

    @classmethod
    def from_schema_scalar(cls, name: str, schema: dict[str, Any], module: Module) -> Annotation:
        """
        Generate an Annotation from a schema that represents a scalar type.

        Handles the following types:
        - string
        - integer
        - number
        - boolean
        - null

        Parameters
        ----------
        name
            The name of the annotation
        schema
            The schema dictionary to generate the annotation from
        module
            The module object to apply the imports to which will hold the annotation

        Returns
        -------
            The constructed Annotation object

        Raises
        ------
        ValueError
            If the schema type is unsupported or if a boolean enum value is invalid
        """
        # Pull out the enum if present
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

                # Boolean has a weird quirk that makes the literal formulation do weird things so we convert
                #   the enum values to actual booleans here
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
        """
        Generate an Annotation from a schema that represents a tagged type.

        Handles a select set of external tags, this will need to be expanded as more
        tags are supported:
        - tag:stsci.edu:asdf/time/time-1.*
        - tag:astropy.org:astropy/table/table-1.*
        - tag:stsci.edu:gwcs/wcs-*
        - tag:stsci.edu:asdf/core/ndarray-1.*
        - tag:stsci.edu:asdf/unit/unit-1.*
        - tag:astropy.org:astropy/units/unit-1.*
        - tag:stsci.edu:asdf/unit/quantity-1.*

        Note that it will fall back to `Any` for unsupported tags. This will make the
        generated code unable to properly initialize a fake object for testing for the
        keyword in question.

        Parameters
        ----------
        name
            The name of the annotation
        schema
            The schema dictionary to generate the annotation from
        module
            The module object to apply the imports to which will hold the annotation
        package
            The package object representing the overall code generation context

        Returns
        -------
            The constructed Annotation object

        Raises
        ------
        ValueError
            If the schema tag is unsupported or invalid
        """
        # Sanity check the tag presence
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

                # The schemas should always have a datatype for ndarrays
                if not dtype:
                    raise ValueError(f"Schema for {name} ndarray tag must have a datatype")

                # Convert the ASDF datatype to a numpy dtype and then to a string to write an import
                #   from
                np_dtype = asdf_datatype_to_numpy_dtype(dtype).type.__name__
                module.imports.dtype(np_dtype)

                # If we have an ndim specified we need to include that in the annotation as a tuple with ints listed
                # for each dimension, otherwise we use the NDArray typing
                if (ndim := schema.get("ndim")) is None:
                    module.imports.ndarray_type()
                    # The NDArray[<dtype>] is simply an alias to `ndarray[tuple[int, ...], <dtype>]`
                    annotations = [TypeAnnotation("NDArray", [TypeAnnotation(np_dtype)])]
                else:
                    module.imports.ndarray()
                    # This produces the annotation `ndarray[tuple[int, int, ..., int], <dtype>]` with the number
                    #   of `int` entries in the tuple equal to ndim
                    annotations = [TypeAnnotation("ndarray", [TypeAnnotation(f"tuple[{', '.join(['int'] * ndim)}], {np_dtype}")])]

            case "tag:stsci.edu:asdf/unit/unit-1.*" | "tag:astropy.org:astropy/units/unit-1.*":
                module.imports.unit()

                annotations = [TypeAnnotation("Unit", [TypeAnnotation(f'"{u}"')]) for u in schema.get("enum", [])]
                # If we don't have any enumerated units we just use Unit
                if not annotations:
                    annotations = [TypeAnnotation("Unit")]

            case "tag:stsci.edu:asdf/unit/quantity-1.*":
                module.imports.quantity()
                # The unit must be defined for Quantity in the schema so we can just reuse this constructor for
                # it as well
                arguments = cls.from_schema_tag(f"{name}Unit", schema.get("unit", {}), module, package).annotations
                annotations = [TypeAnnotation("Quantity", arguments)]

            case _:
                module.imports.any()
                annotations = [TypeAnnotation("Any")]

        # Finalize the construction with metadata
        return cls._from_metadata(name=name, schema=schema, annotations=annotations, module=module)

    @classmethod
    def from_schema_array(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Annotation:
        """
        Generate an Annotation from a schema that represents an array type.

        Parameters
        ----------
        name
            The name of the annotation
        schema
            The schema dictionary
        module
            The module object to apply the imports to which will hold the annotation
        package
            The package object representing the overall code generation context

        Returns
        -------
            The constructed Annotation object

        Raises
        ------
        ValueError
            If the schema is not of type array or if the items schema is invalid
        """
        # Add the array import
        module.imports.array_node()

        # Sanity check the schema type
        if schema.get("type") != "array":
            raise ValueError(f"Schema for {name} is not of type array")

        items = schema.get("items")
        if items is None:
            # Items is required for arrays
            module.imports.any()

            arguments = [TypeAnnotation("Any")]
        else:
            # For the argument to the ArrayNode we need to process the items schema
            annotation = module.process(f"{name}Item", items, package).annotation

            # Sanity check
            if annotation.is_annotated:
                raise ValueError(f"Items of array for {name} cannot have metadata")

            arguments = annotation.annotations

        annotations = [TypeAnnotation(ArrayNode.__name__, arguments)]
        return cls._from_metadata(name=name, schema=schema, annotations=annotations, module=module)

    @classmethod
    def from_schema_anyof(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Annotation:
        """
        Generate an Annotation from a schema that represents an anyOf type.

        Parameters
        ----------
        name
            The name of the annotation
        schema
            The schema dictionary
        module
            The module object to apply the imports to which will hold the annotation
        package
            The package object representing the overall code generation context

        Returns
        -------
            The constructed Annotation object

        Raises
        ------
        ValueError
            If the schema is not a valid anyOf
        """
        # Sanity check the anyOf presence
        if "anyOf" not in schema or not isinstance(schema["anyOf"], list) or not schema["anyOf"]:
            raise ValueError(f"Schema for {name} has invalid anyOf")

        # An anyOf is really a union of the types from the subschemas
        annotations = []
        for index, subschema in enumerate(schema["anyOf"]):
            ann = module.process(f"{name}_{index}", subschema, package).annotation
            if ann.is_annotated:
                raise ValueError(f"Subschema {index} of anyOf for {name} cannot have metadata")
            annotations.extend(ann.annotations)

        return cls._from_metadata(name=name, annotations=annotations, schema=schema, module=module)


@dataclass
class Class(Type):
    """
    Class to represent a generated class based on a schema object.

    Attributes
    ----------
    bases : list[str] | None
        The list of base classes for this class, if any.
    docs : str | None
        The documentation string for this class, if any.
    properties : dict[str, Annotation]
        The dictionary of property names to their Annotations.
    required : list[str] | None
        The list of required property names for this class, if any.
    alias : dict[str, str] | None
        A mapping from a sanitized alias of a property name to its original name in the schema.
        --> This will allow the generated class to have valid Python identifiers while
            transparently mapping back to the original schema names in the underlying data
            storage layer.
    uri : str | None
        The URI of the schema this class was generated from, if any.
    tag : str | None
        The tag for the schema this class was generated from, if any.
    """

    bases: list[str] | None
    docs: str | None
    properties: dict[str, Annotation]
    required: list[str] | None
    alias: dict[str, str] | None = None
    uri: str | None = None
    tag: str | None = None

    @property
    def annotation(self):
        return Annotation.empty(self.name)

    @property
    def type(self) -> str:
        """The type name of the class."""
        return self.name

    @property
    def dependencies(self) -> set[str]:
        """
        The set of class names that this class depends on via its properties.
        """
        deps = set()
        for annotation in self.properties.values():
            for ann in annotation.annotations:
                deps.add(ann.type)

        return deps | set(self.bases or [])

    @classmethod
    def empty(cls, name: str) -> Class:
        """
        Create an empty Class object

        Parameters
        ----------
        name
            The name of the class

        Returns
        -------
            An empty Class object
        """
        return cls(name=name, bases=None, docs=None, properties={}, required=None)

    def text(self):
        # Start with the class definition line
        text = f"class {self.name}"

        # Add to that line the base classes if we have any
        #   if none we default to ObjectNode
        if self.bases:
            text += f"({', '.join(self.bases)}):\n"
        else:
            text += f"({ObjectNode.__name__}):\n"

        body = ""
        # Add the docstring if we have any
        #    Note this will be indented inside the class definition
        if self.docs:
            body += '"""\n'
            body += dedent(self.docs)
            body += '"""\n\n'

        # Add the schema URI if we have one
        if self.uri:
            body += f"__uri__ = {self.uri!r}\n"

        # Add the schema tag if we have one
        if self.tag:
            body += f"__tag__ = {self.tag!r}\n"

        # Add the required properties tuple
        if self.required:
            body += f"__required__ = {tuple(sorted(set(self.required)))}\n"

        if self.properties:
            body += f"__keywords__ = {tuple(sorted(self.properties.keys()))}\n"

        # Add the Alias mapping if we have any
        if self.alias:
            # Add the alias dictionary if we have any syntax overrides
            body += f"__alias__ = MappingProxyType({self.alias})\n"

        # Add in a newline after all the __<object schema attributes>__ for the object
        if any([self.uri, self.tag, self.required, self.properties, self.alias]):
            body += "\n"

        # Add all the properties with their annotations
        #   These are simply type hints of the form:
        #     `<name>: <annotation>`
        for name, annotation in sorted(self.properties.items()):
            body += f"{name}: {annotation.text()}\n"

        if self.properties:
            body += "\n"
        # If there is no body content we need to add a pass statement
        body = body if body else "pass\n"

        return text + indent(body, "    ")

    def add_property(self, name: str, annotation: Annotation, module: Module) -> None:
        """
        Add a property to the class, handling any syntax issues with the name.

        Parameters
        ----------
        name
            The name of the property to add
        annotation
            The Annotation object representing the property's type
        module
            The module object to apply any necessary imports to

        Raises
        ------
        ValueError
            If the property already exists in the class
        """
        bad_name, good_name = self._sanitize_name(name)

        if good_name in self.properties:
            raise ValueError(f"Property '{name}' already exists in class '{self.name}'")

        if bad_name != good_name:
            if self.alias is None:
                self.alias = {}

            module.imports.proxy()
            # Note for syntax overrides we still want to define the hint so its
            #   available from the class object, the property hint is only accessible
            #   on an instance of the class
            self.alias[good_name] = bad_name
            self.properties[good_name] = annotation
        else:
            self.properties[name] = annotation

    def add_mixin(self, module: Module) -> None:
        """
        Add a mixin to the class if a corresponding mixin exists.

        Parameters
        ----------
        module
            The module object to apply any necessary imports to
        """

        # Check if a mixin exists for this class
        if (mixin_name := f"{self.name}Mixin") in mixins.__all__:
            # Initialize the bases list if needed
            if self.bases is None:
                self.bases = []

            # Add the mixin import and add it to the bases
            module.imports.mixin(mixin_name)
            self.bases.append(mixin_name)

    @classmethod
    def _from_metadata(cls, name: str, schema: dict[str, Any], module: Module) -> Class:
        """
        Create a basic Class object with no internal information from the schema

        Parameters
        ----------
        name
            The name of the class
        schema
            The schema dictionary to extract documentation from
        module
            The module object to apply the imports to which will hold the class

        Returns
        -------
            The constructed Class object

        Raises
        ------
        ValueError
            Does a sanity check to ensure that the name matches the schema id if present
        """
        # Sanity check the schema id if present
        if "id" in schema:
            if module.type != name:
                raise ValueError(f"Schema id '{schema['id']}' does not match expected class name '{name}'")

        # Pull out the documentation from the schema
        title, description = cls.extract_docs(schema)

        # Turn the docs into a single docstring
        docs = ""
        if title:
            docs += f"{title}\n"

        if description:
            # If no title but have a description we don't indent
            docs += f"{indent(description, '    ') if docs else description}\n"

        # Find an set of required properties
        required = [cls._sanitize_name(name)[1] for name in schema.get("required", [])]

        # Construct the class object
        class_ = cls(
            name=name,
            bases=None,
            docs=docs if docs else None,
            properties={},
            required=required or None,
            alias=None,
        )
        # Add the class to the module
        module.add(class_)

        # Add any mixin if it exists
        class_.add_mixin(module)

        return class_

    @classmethod
    def from_schema_object(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Class:
        """
        Generate a Class from a schema that represents an object type.

        Parameters
        ----------
        name
            The name of the class
        schema
            The schema dictionary
        module
            The module object to apply the imports to which will hold the class
        package
            The package object representing the overall code generation context

        Returns
        -------
            The constructed Class object
        """
        # There is no "AllOf" here so it must be the start of an inheritance chain,
        #   so its base class is ObjectNode
        module.imports.object_node()

        # Construct the basic class from the metadata
        class_ = cls._from_metadata(name=name, schema=schema, module=module)

        # Add all the properties from the schema
        for prop_name, prop_schema in schema.get("properties", {}).items():
            cls_name = cls.class_name(prop_name)
            class_.add_property(prop_name, module.process(f"{name}_{cls_name}", prop_schema, package).annotation, module)

        # Read in the pattern properties
        pattern_properties = {}
        for index, (pattern, pattern_schema) in enumerate(schema.get("patternProperties", {}).items()):
            cls_name = f"PatternProperty{index}"
            pattern_properties[pattern] = module.process(f"{name}_{cls_name}", pattern_schema, package).annotation

        # Use the required properties to ensure all required properties are present
        if pattern_properties:
            # Look at all required properties and see if they are present
            for required in class_.required or []:
                # If the required property is not present, we need to add it
                if required not in class_.properties:
                    # Look through the pattern properties to see if it matches any of the patterns
                    for pattern, annotation in pattern_properties.items():
                        if match(pattern, required):
                            # If we have a match, add the property with the corresponding annotation
                            class_.add_property(required, annotation, module)
                            break
                    else:
                        # If we didn't break from the loop, no pattern matched, so we default to Any
                        module.imports.any()
                        class_.add_property(required, Annotation.empty(), module)

        return class_

    @classmethod
    def from_schema_allof(cls, name: str, schema: dict[str, Any], module: Module, package: Package) -> Class | Type:
        """
        Generate a Class from a schema that represents an allOf type.

        Parameters
        ----------
        name
            The name of the class
        schema
            The schema dictionary
        module
            The module object to apply the imports to which will hold the class
        package
            The package object representing the overall code generation context

        Returns
        -------
            The constructed Class object

        Raises
        ------
        ValueError
            If the schema is not an allOf
        """
        # Sanity check the allOf presence
        if "allOf" not in schema:
            raise ValueError(f"Schema for {name} has invalid allOf")
        all_of = schema["allOf"]

        # Bail out early if there is only one subschema
        # this is really just a pass-through for json schema
        # logic but we can just pretend its not there
        if len(all_of) == 1:
            # Copy the current schema and remove allOf
            new_schema = deepcopy(schema)
            del new_schema["allOf"]

            # Merge the contents of the subschema into the new schema
            new_schema.update(all_of[0])

            # Reprocess the new schema
            return module.process(name, new_schema, package)

        # Construct the basic class from the metadata
        class_ = cls._from_metadata(name=name, schema=schema, module=module)

        bases = []
        for index, sub_schema in enumerate(all_of):
            # Bail out for when we have a tag and some other things, those
            #   should all be simple restrictions on the tag type
            if "tag" in sub_schema:
                # If there is a "tag" along with other things we bail out
                #  and just reprocess the whole schema as if it was the tag
                #  this is mostly for the tables in the source catalog related
                #  schemas
                new_schema = deepcopy(schema)
                del new_schema["allOf"]
                new_schema.update(sub_schema)

                # Note we remove the class_ from the module since we are restarting
                #   the processing
                del module.classes[class_.name]
                return module.process(name, new_schema, package)

            # If we have a "not" we bail out and return an Any annotation
            #    This logic does not easily translate to Python type hints
            if "not" in sub_schema:
                module.imports.any()

                del module.classes[class_.name]
                return Annotation.empty()

            type_ = module.process(f"{name}_allOf{index}", sub_schema, package)
            if not isinstance(type_, Class | Module):
                raise ValueError(f"Subschema {index} of allOf for {name} must be an object")

            bases.append(type_.type)

        # Reverse the bases, our convention is to list the `$ref` first which means
        #   which means the modification classes come after. Since we combine using
        #   multiple inheritance we need to reverse the order to have the modification
        #   so their type hints override the `$ref` ones.
        class_.bases = bases[::-1]

        return class_


class File(Base, ABC):
    """
    Base class for all objects that will turn into files on disk.
    """

    @property
    @abstractmethod
    def file_path(self) -> Path:
        """Path to the actual file on disk."""

    @property
    @abstractmethod
    def path(self) -> Path:
        """Path to items inside the file (so it may have the file name without its suffix)"""

    @property
    def local_import(self) -> str:
        """The local import path for this file."""
        return f".{self.path.stem}"

    def write(self, base_path: Path, ruff_format: bool = True) -> None:
        """
        Write the contents of the file to disk.

        Parameters
        ----------
        base_path
            The base path to write the file to
        ruff_format
            Whether to run `ruff format` on the file after writing it, by default True
            This significantly slows testing of the code generation so we disable it
            during tests.
        """
        # Build the path to the file and make sure the parent directories exist
        path = base_path / self.file_path
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            f.write(self.text())

        # Format the file with ruff if requested (requires ruff to be installed and on PATH env variable)
        if ruff_format:
            run(["ruff", "format", str(path)])  # noqa: S603, S607


@dataclass
class Module(Type, File):
    """
    Class to represent a generated module based on a schema object.

    Attributes
    ----------
    imports : Import
        The Import object representing the imports for this module.
    annotations : dict[str, Annotation]
        The dictionary of annotation names to their Annotations.
    classes : dict[str, Class]
        The dictionary of class names to their Classes.
    """

    imports: Import
    annotations: dict[str, Annotation]
    classes: dict[str, Class]

    @property
    def uri(self) -> str:
        """
        Modules are all named using their URI as they will all correspond to a schema loaded from a URI.

        The code model is each module corresponds one-to-one with a schema, so the module name is the schema URI.
        """
        return self.name

    @property
    def type(self) -> str:
        """
        The type name of the module, derived from the URI.

        Each module only has one public type that it provides, which is the one the schema for the
        module ultimately defines.
        """
        type_ = "".join([p.capitalize() for p in name_from_uri(self.uri).split("_")])
        if "reference_files" in self.uri:
            type_ += "Ref"
        return type_

    @property
    def annotation(self):
        """
        The annotation for the module's primary type.

        This should ultimately just be its name
        """
        return Annotation.empty(self.type)

    @property
    def path(self) -> Path:
        # Remove the version suffix
        path = self.uri.rsplit("-", 1)[0]

        # Remove the base URI
        path = path.split("asdf://stsci.edu/datamodels/roman/schemas/")[-1]

        # Prepend an underscore to make the module a private module
        #   All external imports of the resulting code should go through the
        #   package __init__.py files that define the public API.
        if len(split := path.rsplit("/", 1)) == 1:
            path = f"_{path}"
        else:
            path = f"{split[0]}/_{split[1]}"

        # Add the .py suffix
        return Path(f"{path}.py")

    @property
    def file_path(self) -> Path:
        # For modules the file path is just the path
        return self.path

    @property
    def class_order(self) -> list[Class]:
        """
        List the classes in the module in order such that dependencies of a class
        (including its annotations) appear before the class itself.

        This allows us to run `get_type_hints` on a class at class creation time
        rather than class initialization time. This has the benefit of also ensuring
        that the generated module will not have issues when Python attempts to import
        it even if `get_type_hints` is not called on any of the classes.
        """
        classes: list[Class] = []
        for cls in self.classes.values():
            for index, existing in enumerate(classes):
                if cls.name in existing.dependencies:
                    classes.insert(index, cls)
                    break
            else:
                classes.append(cls)

        return classes

    def text(self) -> str:
        # Start with the auto-generated file warning
        text = dedent(
            f"""\
            \"\"\"
            This module was auto-generated by the RAD code generator based on the schema with URI:
                {self.uri}

            DO NOT EDIT THIS FILE DIRECTLY. Instead, modify the schema and reinstall RAD to
            regenerate this file.
            \"\"\"
            """
        )

        # Add import statements at top of the file
        text += f"{self.imports.text()}\n"

        # Add the __all__ definition for the public API of the module
        text += f"__all__ = ('{self.type}',)\n"
        text += f"__uri__ = {self.uri!r}\n\n"

        # Add all the type aliases first, this is necessary if we have things that
        #    are from schemas that define a decorated scalar type
        if self.annotations:
            for name, annotation in self.annotations.items():
                # Note that these themselves are type aliases so we mark them as such
                text += f"{name}: TypeAlias = {annotation.text()}\n"
            text += "\n"

        # Add all the classes next
        if self.classes:
            # Add them in an order that allows python to read the file
            for cls in self.class_order:
                text += f"{cls.text()}\n"

        return text

    def get_class(self, name: str) -> Class:
        """
        Get a class from a name, turining it into the PascalCase class name if needed.
        """
        name = self.class_name(name)
        return self.classes[name]

    @classmethod
    def empty(cls, uri: str, package: Package) -> Module:
        """
        Create an empty Module object
        """
        module = cls(
            name=uri,
            imports=Import.empty(),
            annotations={},
            classes={},
        )
        # Add the module to the package
        package.add_module(module)

        return module

    def add(self, type_: Annotation | Class) -> None:
        """
        Add something processed from a schema to the module.
        """
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
        """
        Add an import to another module we are building.
        """
        # Get the module paths without the .py suffix
        target_path = module.path.parent / module.path.stem
        current_path = self.path.parent / self.path.stem

        self.imports.relative_import(target_path, current_path, type_ or module.type)

    @classmethod
    def from_schema(cls, schema: dict[str, Any], package: Package) -> Module:
        """
        Build a Module object from a schema dictionary.

        Parameters
        ----------
        schema
            The schema dictionary to build the module from
        package
            The package object representing the overall code generation context
        Returns
        -------
            The constructed Module object
        """
        # Sanity check the schema id presence, we only can process RAD schemas
        uri = schema.get("id")
        if not uri or not uri.startswith("asdf://stsci.edu/datamodels/roman/schemas/"):
            raise ValueError(f"Schema id '{uri}' is not a valid RAD schema URI")

        # Create the module and add it to the package. This allows for recursive
        #   referencing to the module itself while building it.
        module = cls.empty(uri, package)

        # Process through and add all definitions first
        if definitions := schema.get("definitions"):
            for def_name, def_schema in definitions.items():
                # Note that if the definition is a class it will add itself to the module
                definition = module.process(cls._sanitize_name(cls.class_name(def_name))[1], def_schema, package)

                # If the definition is an annotation we need to add it ourselves
                if isinstance(definition, Annotation):
                    module.add(definition)

        # Process the main information in the schema to fill in the module
        output = module.process(module.type, schema, package)

        # Annotations do not add themselves to the module automatically so we need to do it here
        if isinstance(output, Annotation):
            module.add(output)

        # If we have any annotations we need to add the TypeAlias import so we can mark them as such
        if module.annotations:
            module.imports.type_alias()

        # Finally apply the schema URI to the module's primary class if it exists
        module.apply_uris(uri)

        return module

    def process(self, name: str, schema: dict[str, Any], package: Package) -> Type:
        """
        The main schema parsing function that will process a schema dictionary

        Every time we need to process one level deeper into the schema we call this function
        This is basically a dispatcher that looks at the schema and decides what to do with it,
        sending it off to the appropriate constructor function.

        Parameters
        ----------
        name
            The name of the type to create from the schema
        schema
            The schema dictionary to process
        package
            The package object representing the overall code generation context

        Returns
        -------
            The constructed Type object
        """
        type_ = schema.get("type")

        # If no type declaration is present we need to look for other schema constructs
        #    Currently RAD only uses anyOf, allOf, $ref, and tag in this case
        #    There is a fall back to Any if nothing is found
        if not type_:
            # I make the assumption that there is only one of these constructs present
            #    The ordering here should not matter if it does we need to revisit this logic
            if "anyOf" in schema:
                return Annotation.from_schema_anyof(name, schema, self, package)

            if "allOf" in schema:
                return Class.from_schema_allof(name, schema, self, package)

            if "$ref" in schema:
                # Note this is why pass the package around everywhere, so if we
                #   need to reference another schema/module we can find it.
                return package.resolve_ref(schema, self)

            if "tag" in schema:
                return Annotation.from_schema_tag(name, schema, self, package)

            # Fall back to Any if nothing else is found
            self.imports.any()
            return Annotation.empty()

        # Now if we do have a type we dispatch based on it
        #   Note we have an actual value so we can structurally match it
        match type_:
            case "string" | "number" | "integer" | "boolean" | "null":
                return Annotation.from_schema_scalar(name, schema, self)

            case "array":
                return Annotation.from_schema_array(name, schema, self, package)

            case "tag":
                return Annotation.from_schema_tag(name, schema, self, package)

            case "object":
                return Class.from_schema_object(name, schema, self, package)

            case _:
                # Something has gone very wrong if we get here
                raise ValueError(f"Schema for {name} has unsupported type '{type_}'")

    def apply_uris(self, schema_uri: str, tag_uri: str | None = None) -> None:
        """
        Apply the schema URI and tag URI to the module's primary class if it exists.

        Parameters
        ----------
        schema_uri
            The schema URI to apply
        tag_uri
            The tag URI to apply
        """
        if self.type in self.classes:
            class_ = self.classes[self.type]
            class_.uri = schema_uri
            class_.tag = tag_uri


@dataclass
class Init(File):
    """
    Class to represent a generated __init__.py file at each level of a package.

    Attributes
    ----------
    modules : dict[str, Module]
        The dictionary of module URIs to their Modules.
    imports : Import
        The Import object representing the imports for this init file.
    inits : dict[Path, Init]
        The dictionary of sub-package paths to their Init objects.
    module_path : Path
        The path to this package/module. (where the __init__.py will live)
    """

    modules: dict[str, Module]
    imports: Import
    inits: dict[Path, Init]
    module_path: Path

    @property
    def path(self) -> Path:
        return self.module_path

    @property
    def file_path(self) -> Path:
        # note here we have the __init__.py that we need to include
        return self.module_path / "__init__.py"

    @classmethod
    def empty(cls, path: Path) -> Init:
        """
        Create an empty Init object
        """
        return cls(modules={}, imports=Import.empty(), inits={}, module_path=path)

    def add_module(self, module: Module) -> None:
        """
        Add a module to this init file.
        """
        self.modules[module.uri] = module
        self.imports.add_import(module.local_import, module.type)

    def add_init(self, init: Init) -> None:
        """
        Add a sub-package using its Init object.
        """
        self.inits[init.module_path] = init

    @property
    def api(self) -> list[str]:
        """Figure out the __all__ for the public API of this package."""
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

        # Add import statements at top of the file
        text = f"{self.imports.text()}\n"

        # Add the __all__ definition for the public API of the package
        text += "__all__ = (\n"
        text += indent(",\n".join([f'"{entry}"' for entry in api]), "    ")
        text += "\n)\n"

        return text


@dataclass
class Package:
    """
    Represents the overall package being generated being generated from the schemas

    Attributes
    ----------
    modules : dict[str, Module]
        The dictionary of module URIs to their Modules.
    """

    modules: dict[str, Module]

    @classmethod
    def empty(cls) -> Package:
        """
        Create an empty Package object
        """
        return cls(modules={})

    def add_module(self, module: Module) -> None:
        """
        Add a module to the package.
        """
        if module.uri in self.modules:
            raise ValueError(f"Module '{module.uri}' already exists in package")

        self.modules[module.uri] = module

    def add_ref(self, uri: str) -> Module:
        """Add a module based on a URI reference to a schema."""

        # Bail out early since we already have it
        #   This is needed when we are doing recursive references within the
        #   same schema as otherwise we can get infinite recursion
        if uri in self.modules:
            return self.modules[uri]

        # Sanity check the URI that it is for RAD
        if not uri.startswith("asdf://stsci.edu/datamodels/roman/schemas/"):
            raise ValueError(f"Schema id '{uri}' is not a valid RAD schema URI")

        # Use asdf to load the schema from the URI and pass it to the module constructor
        # As part of that it will add itself to the package
        schema = load_schema(uri)
        return Module.from_schema(schema, self)

    def get_uri(self, uri: str) -> Module:
        """Get a module based on a URI reference to a schema."""

        # If the URI is not present we need to add it like it was a ref
        if uri not in self.modules:
            self.add_ref(uri)

        return self.modules[uri]

    def resolve_ref(self, schema: dict[str, Any], module: Module) -> Module | Class:
        """
        Resolve a $ref in a schema to the corresponding Module or Class.
        """
        uri: str | None = schema.get("$ref")
        if not uri:
            raise ValueError(f"Schema $ref '{uri}' is not a valid RAD schema URI")

        # Handle the case where we are referencing a definition within a schema
        if "#/definitions/" in uri:
            def_uri, def_name = uri.split("#/definitions/", 1)
            ref_module = self.get_uri(def_uri)
            class_ = ref_module.get_class(def_name)
            module.import_module(ref_module, class_.type)
            return class_

        # Otherwise its a reference to a whole schema/module
        #  so we just get the module
        ref = self.get_uri(uri)

        # Make sure to add an import to the ref_module to the module calling it
        module.import_module(ref)

        return ref

    @classmethod
    def from_manifest(cls, uri: str) -> Package:
        """
        Create a StubFiles object from a schema manifest

        Parameters
        ----------
        uri
            The URI to the manifest schema

        Returns
        -------
            The constructed Package object
        """
        package = cls.empty()
        manifest = load_schema(uri)

        for item in manifest["tags"]:
            schema_uri = item["schema_uri"]
            tag_uri = item["tag_uri"]
            module = package.add_ref(schema_uri)
            module.apply_uris(schema_uri, tag_uri)

        return package

    @property
    def sub_packages(self) -> dict[Path, Init]:
        """
        Find the sub-packages for this package organized by path

        Returns
        -------
            A dictionary of sub-package paths to their Init objects
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
        """
        Write all the modules and init files to disk.

        Parameters
        ----------
        base_path
            The base path to write the package to
        ruff_format
            Whether to run `ruff format` on the files after writing them, by default True

        """
        # Write all the modules
        for module in self.modules.values():
            module.write(base_path, ruff_format=ruff_format)

        # Write all the __init__.py files to turn the directories into packages
        for init in self.sub_packages.values():
            init.write(base_path, ruff_format=ruff_format)
