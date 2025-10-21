from pathlib import Path
from textwrap import dedent

import pytest
from asdf import config_context
from asdf.resource import DirectoryResourceMapping
from asdf.schema import _load_schema_cached

from rad.node._generator import Annotation, Base, Class, Import, Module, Package, Type, TypeAnnotation


@pytest.fixture(scope="module")
def test_schemas():
    """Return the path to the test schemas"""
    resource_mapping = DirectoryResourceMapping(
        Path(__file__).parent / "test_schemas", "asdf://stsci.edu/datamodels/roman/schemas/test_schemas/", recursive=True
    )
    with config_context() as config:
        config.add_resource_mapping(resource_mapping)

        yield config

    _load_schema_cached.cache_clear()


class TestImport:
    """Test the Import tracking class"""

    def test_empty(self):
        """Test creating an empty Import"""
        empty = Import.empty()

        assert isinstance(empty, Import)
        assert isinstance(empty, Base)
        assert empty.items == {}

    def test_text(self):
        """Test the text generation of the Import"""
        import_ = Import(items={"module_a": {"Alpha", "Beta"}, "package.module_b": {"Gamma"}})
        truth = dedent(
            """\
            from __future__ import annotations

            from module_a import Alpha, Beta
            from package.module_b import Gamma
            """
        )

        assert import_.text() == truth

    def test_add_import(self):
        """Test adding imports"""
        import_ = Import.empty()
        import_.add_import("module_a", "Alpha")
        import_.add_import("module_a", "Beta")
        import_.add_import("package.module_b", "Gamma")
        import_.add_import("module_a", "Alpha")  # Duplicate, should be ignored

        assert import_.items == {"module_a": {"Alpha", "Beta"}, "package.module_b": {"Gamma"}}

    def test_relative_import(self):
        """Test adding relative imports"""
        import_ = Import.empty()
        import_.relative_import(Path("foo"), Path("spam"), "Alpha")
        import_.relative_import(Path("foo/bar"), Path("spam/eggs"), "Beta")
        import_.relative_import(Path("foo/bar"), Path("spam/eggs/ham"), "Gamma")

        assert import_.items == {".foo": {"Alpha"}, "..foo.bar": {"Beta"}, "...foo.bar": {"Gamma"}}

    def test_any(self):
        """Test adding Any import"""
        import_ = Import.empty()
        import_.any()

        assert import_.items == {"typing": {"Any"}}

    def test_type_alias(self):
        """Test adding TypeAlias import"""
        import_ = Import.empty()
        import_.type_alias()

        assert import_.items == {"typing": {"TypeAlias"}}

    def test_annotated(self):
        """Test adding Annotated import"""
        import_ = Import.empty()
        import_.annotated()

        assert import_.items == {"typing": {"Annotated"}}

    def test_literal(self):
        """Test adding Literal import"""
        import_ = Import.empty()
        import_.literal()

        assert import_.items == {"typing": {"Literal"}}

    def test_dtype(self):
        """Test adding dtype import"""
        import_ = Import.empty()
        import_.dtype("dtype")

        assert import_.items == {"numpy": {"dtype"}}

    def test_ndarray(self):
        """Test adding ndarrayimport"""
        import_ = Import.empty()
        import_.ndarray()

        assert import_.items == {"numpy": {"ndarray"}}

    def test_ndarray_type(self):
        """Test adding NDArray import"""
        import_ = Import.empty()
        import_.ndarray_type()

        assert import_.items == {"numpy.typing": {"NDArray"}}

    def test_time(self):
        """Test adding Time import"""
        import_ = Import.empty()
        import_.time()

        assert import_.items == {"astropy.time": {"Time"}}

    def test_unit(self):
        """Test adding Unit import"""
        import_ = Import.empty()
        import_.unit()

        assert import_.items == {"astropy.units": {"Unit"}}

    def test_quantity(self):
        """Test adding Quantity import"""
        import_ = Import.empty()
        import_.quantity()

        assert import_.items == {"astropy.units": {"Quantity"}}

    def test_table(self):
        """Test adding Table import"""
        import_ = Import.empty()
        import_.table()

        assert import_.items == {"astropy.table": {"Table"}}

    def test_wcs(self):
        """Test adding WCS import"""
        import_ = Import.empty()
        import_.wcs()

        assert import_.items == {"gwcs": {"WCS"}}

    def test_object_node(self):
        """Test adding ObjectNode import"""
        import_ = Import.empty()
        import_.object_node()

        assert import_.items == {"rad.node": {"ObjectNode"}}

    def test_array_node(self):
        """Test adding ArrayNode import"""
        import_ = Import.empty()
        import_.array_node()

        assert import_.items == {"rad.node": {"ArrayNode"}}

    def test_metadata(self):
        """Test adding Metadata import"""
        import_ = Import.empty()
        import_.metadata()

        assert import_.items == {"rad.node": {"Metadata"}}

    def test_archive_catalog(self):
        """Test adding ArchiveCatalog import"""
        import_ = Import.empty()
        import_.archive_catalog()

        assert import_.items == {"rad.node": {"ArchiveCatalog"}}


class TestTypeAnnotation:
    """Test the TypeAnnotation class for a single type"""

    def test_minimal(self):
        """Test creating a minimal TypeAnnotation"""
        ann = TypeAnnotation("foo")

        assert isinstance(ann, TypeAnnotation)
        assert isinstance(ann, Base)
        assert ann.type == "foo"
        assert ann.argument is None

    @pytest.mark.parametrize(
        "argument,truth",
        [
            (None, "foo"),
            (TypeAnnotation("Bar"), "foo[Bar]"),
            ([TypeAnnotation("Bar"), TypeAnnotation("Baz")], "foo[Bar | Baz]"),
        ],
    )
    def test_text(self, argument, truth):
        """Test a TypeAnnotation with an argument"""

        ann = TypeAnnotation("foo", argument=argument)

        assert ann.type == "foo"
        assert ann.argument == argument

        assert ann.text() == truth


class TestAnnotation:
    """Test the Annotation class"""

    def test_empty(self):
        """Test creating a minimal Annotation"""
        ann = Annotation.empty("foo")

        assert isinstance(ann, Annotation)
        assert isinstance(ann, Type)
        assert ann.name == "foo"
        assert ann.annotations == [TypeAnnotation("foo")]
        assert ann.title is None
        assert ann.description is None
        assert ann.datatype is None
        assert ann.destination is None

        assert ann.text() == "foo"

    @pytest.mark.parametrize(
        "annotations,title,description,datatype,destination,truth",
        [
            ([], None, None, None, None, "Any"),
            ([TypeAnnotation("foo")], None, None, None, None, "foo"),
            ([TypeAnnotation("foo", TypeAnnotation("Bar"))], None, None, None, None, "foo[Bar]"),
            ([TypeAnnotation("foo")], "A title", None, None, None, "Annotated[foo, Metadata(title='A title')]"),
            (
                [TypeAnnotation("foo", [TypeAnnotation("Bar"), TypeAnnotation("Baz")])],
                "A title",
                None,
                None,
                None,
                "Annotated[foo[Bar | Baz], Metadata(title='A title')]",
            ),
            ([TypeAnnotation("foo")], None, "A description", None, None, "Annotated[foo, Metadata(description='A description')]"),
            (
                [TypeAnnotation("foo")],
                "A title",
                "A description",
                None,
                None,
                "Annotated[foo, Metadata(title='A title', description='A description')]",
            ),
            (
                [TypeAnnotation("foo", TypeAnnotation("Bar"))],
                "A title",
                "A description",
                None,
                None,
                "Annotated[foo[Bar], Metadata(title='A title', description='A description')]",
            ),
            (
                [TypeAnnotation("foo", TypeAnnotation("Bar")), TypeAnnotation("spam", TypeAnnotation("Eggs"))],
                "A title",
                "A description",
                None,
                None,
                "Annotated[foo[Bar] | spam[Eggs], Metadata(title='A title', description='A description')]",
            ),
            (
                [TypeAnnotation("foo")],
                None,
                None,
                "dtype",
                None,
                "Annotated[foo, Metadata(archive_catalog=ArchiveCatalog(datatype='dtype'))]",
            ),
            (
                [TypeAnnotation("foo")],
                None,
                None,
                None,
                ["place_1", "place_2"],
                "Annotated[foo, Metadata(archive_catalog=ArchiveCatalog(destination=('place_1', 'place_2')))]",
            ),
            (
                [TypeAnnotation("foo", [TypeAnnotation("Bar"), TypeAnnotation("Baz")])],
                "A title",
                "A description",
                "dtype",
                ["place_1", "place_2"],
                "Annotated[foo[Bar | Baz], Metadata(title='A title', description='A description', archive_catalog=ArchiveCatalog(datatype='dtype', destination=('place_1', 'place_2')))]",
            ),
        ],
    )
    def test_text(self, annotations, title, description, datatype, destination, truth):
        """Test an Annotation with metadata"""

        ann = Annotation(
            "name", annotations=annotations, title=title, description=description, datatype=datatype, destination=destination
        )

        assert ann.name == "name"
        assert ann.annotations == annotations
        assert ann.title == title
        assert ann.description == description
        assert ann.datatype == datatype
        assert ann.destination == destination

        assert ann.text() == truth
        assert ann.annotation is ann


class TestClass:
    """Test the Class class"""

    def test_empty(self):
        """Test creating an empty Class"""
        empty = Class.empty("MyClass")

        assert isinstance(empty, Class)
        assert isinstance(empty, Type)
        assert empty.name == "MyClass"
        assert empty.bases is None
        assert empty.docs is None
        assert empty.properties == {}
        assert empty.required is None

    def test_type(self):
        """Test the type property"""
        cls = Class.empty("MyClass")

        assert cls.annotation == Annotation.empty("MyClass")

    @pytest.mark.parametrize(
        "bases,docs,properties,required,truth",
        [
            (
                None,
                None,
                {},
                None,
                dedent("""\
            class MyClass(ObjectNode):
                __required__ = ()

                   """),
            ),
            (
                ["Base1"],
                None,
                {},
                None,
                dedent("""\
            class MyClass(Base1):
                __required__ = ()

                   """),
            ),
            (
                ["Base1", "Base2"],
                "A docstring",
                {},
                None,
                dedent("""\
            class MyClass(Base1, Base2):
                \"\"\"
                A docstring
                \"\"\"

                __required__ = ()

                   """),
            ),
            (
                ["Base1", "Base2"],
                "A docstring",
                {"prop1": Annotation.empty("int"), "prop2": Annotation("str", [TypeAnnotation("str")], title="A string")},
                None,
                dedent("""\
            class MyClass(Base1, Base2):
                \"\"\"
                A docstring
                \"\"\"

                __required__ = ()

                prop1: int
                prop2: Annotated[str, Metadata(title='A string')]

                   """),
            ),
            (
                ["Base1", "Base2"],
                "A docstring",
                {"prop1": Annotation.empty("int"), "prop2": Annotation("str", [TypeAnnotation("str")], title="A string")},
                ["prop1"],
                dedent("""\
            class MyClass(Base1, Base2):
                \"\"\"
                A docstring
                \"\"\"

                __required__ = ('prop1',)

                prop1: int
                prop2: Annotated[str, Metadata(title='A string')]

                   """),
            ),
        ],
    )
    def test_text(self, bases, docs, properties, required, truth):
        cls = Class(
            name="MyClass",
            bases=bases,
            docs=docs,
            properties=properties,
            required=required,
        )

        assert cls.name == "MyClass"
        assert cls.bases == bases
        assert cls.docs == docs
        assert cls.properties == properties
        assert cls.required == required

        assert cls.text() == truth


class TestModule:
    """Test the Module class"""

    def test_empty(self, package):
        """Test creating an empty Module"""
        assert package.modules == {}

        empty = Module.empty("my_uri", package)

        assert isinstance(empty, Module)
        assert isinstance(empty, Type)
        assert empty.name == "my_uri"
        assert empty.imports == Import.empty()
        assert empty.annotations == {}
        assert empty.classes == {}

        assert package.modules == {"my_uri": empty}

    def test_uri(self, package):
        """Test the uri property"""
        module = Module.empty("my_uri", package)

        assert module.uri == "my_uri"

    @pytest.mark.parametrize(
        "uri,truth",
        [
            ("asdf://stsci.edu/datamodels/roman/schemas/my_class-1.0.0", "MyClass"),
            ("asdf://stsci.edu/datamodels/roman/schemas/thing/my_class-1.0.0", "MyClass"),
            ("asdf://stsci.edu/datamodels/roman/schemas/other-1.0.0", "Other"),
            ("asdf://stsci.edu/datamodels/roman/schemas/something/other-1.0.0", "Other"),
            ("asdf://stsci.edu/datamodels/roman/schemas/reference_files/other-1.0.0", "OtherRef"),
        ],
    )
    def test_type(self, uri, truth, package):
        """Test the type property"""
        module = Module.empty(uri, package)
        assert module.type == truth

    def test_annotation(self, package):
        """Test the annotation property"""
        module = Module.empty("asdf://stsci.edu/datamodels/roman/schemas/my_class-1.0.0", package)
        assert module.annotation == Annotation.empty("MyClass")

    @pytest.mark.parametrize(
        "uri,truth",
        [
            ("asdf://stsci.edu/datamodels/roman/schemas/my_class-1.0.0", Path("_my_class.py")),
            ("asdf://stsci.edu/datamodels/roman/schemas/subdir/my_class-1.0.0", Path("subdir/_my_class.py")),
        ],
    )
    def test_path(self, uri, truth, package):
        """Test the path property"""
        module = Module.empty(uri, package)
        assert module.path == truth

    def test_text(self):
        """Test the text generation of the Module"""

        imports = Import(items={"module_a": {"Alpha", "Beta"}, "package.module_b": {"Gamma"}})
        annotations = {
            "my_int": Annotation("int", [TypeAnnotation("int")], title="An integer"),
            "my_str": Annotation("int", [TypeAnnotation("str")], description="A string"),
        }
        classes = {
            "MyClass": Class(
                name="MyClass",
                bases=["Alpha", "Beta"],
                docs="A docstring",
                properties={
                    "prop1": Annotation("Gamma", [TypeAnnotation("Gamma")], title="A property"),
                    "prop2": Annotation("str", [TypeAnnotation("str")]),
                },
                required=["prop1"],
            ),
            "AnotherClass": Class.empty("AnotherClass"),
        }
        name = "asdf://stsci.edu/datamodels/roman/schemas/my_class-1.0.0"
        module = Module(name=name, imports=imports, annotations=annotations, classes=classes)

        truth = dedent(
            """\
            from __future__ import annotations

            from module_a import Alpha, Beta
            from package.module_b import Gamma

            __all__ = ('MyClass',)

            my_int: TypeAlias = Annotated[int, Metadata(title='An integer')]
            my_str: TypeAlias = Annotated[str, Metadata(description='A string')]

            class MyClass(Alpha, Beta):
                \"\"\"
                A docstring
                \"\"\"

                __required__ = ('prop1',)

                prop1: Annotated[Gamma, Metadata(title='A property')]
                prop2: str


            class AnotherClass(ObjectNode):
                __required__ = ()


            """
        )

        assert module.text() == truth

    @pytest.mark.parametrize(
        "schema_type,truth_type",
        [
            ("string", "str"),
            ("integer", "int"),
            ("number", "float"),
            ("boolean", "bool"),
            ("null", "None"),
        ],
    )
    def test_parse_simple_scalar(self, package, schema_type, truth_type):
        """Test parsing a simple scalar schema"""
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_scalar-1.0.0",
            "title": "A simple scalar",
            "description": "This is a scalar schema",
            "type": schema_type,
            "archive_catalog": {"datatype": "nvarchar(20)", "destination": ["str_place"]},
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            f"""\
            from __future__ import annotations

            from rad.node import ArchiveCatalog, Metadata
            from typing import Annotated, TypeAlias

            __all__ = ('SimpleScalar',)

            SimpleScalar: TypeAlias = Annotated[{truth_type}, Metadata(title='A simple scalar', description='This is a scalar schema', archive_catalog=ArchiveCatalog(datatype='nvarchar(20)', destination=('str_place',)))]

            """
        )
        assert module.text() == truth

    @pytest.mark.parametrize(
        "schema_type,enum,truth_type",
        [
            ("string", ["A", "B", "C"], "Literal['A', 'B', 'C']"),
            ("integer", ["-1", "1"], "Literal[-1, 1]"),
            ("number", ["1", "3.14"], "Literal[1.0, 3.14]"),
            ("boolean", ["True"], "Literal[True]"),
            ("boolean", ["False"], "Literal[False]"),
        ],
    )
    def test_parse_simple_scalar_enum(self, package, schema_type, enum, truth_type):
        """Test parsing a simple scalar schema"""
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_scalar-1.0.0",
            "title": "A simple scalar",
            "description": "This is a scalar schema",
            "type": schema_type,
            "enum": enum,
            "archive_catalog": {"datatype": "nvarchar(20)", "destination": ["str_place"]},
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            f"""\
            from __future__ import annotations

            from rad.node import ArchiveCatalog, Metadata
            from typing import Annotated, Literal, TypeAlias

            __all__ = ('SimpleScalar',)

            SimpleScalar: TypeAlias = Annotated[{truth_type}, Metadata(title='A simple scalar', description='This is a scalar schema', archive_catalog=ArchiveCatalog(datatype='nvarchar(20)', destination=('str_place',)))]

            """
        )
        assert module.text() == truth

    def test_parse_simple_array(self, package):
        """Test parsing a simple array schema"""
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_array-1.0.0",
            "title": "A simple array",
            "description": "This is an array schema",
            "type": "array",
            "items": {"type": "integer"},
            "archive_catalog": {"datatype": "int[]", "destination": ["int_place"]},
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            """\
            from __future__ import annotations

            from rad.node import ArchiveCatalog, ArrayNode, Metadata
            from typing import Annotated, TypeAlias

            __all__ = ('SimpleArray',)

            SimpleArray: TypeAlias = Annotated[ArrayNode[int], Metadata(title='A simple array', description='This is an array schema', archive_catalog=ArchiveCatalog(datatype='int[]', destination=('int_place',)))]

            """
        )
        assert module.text() == truth

    def test_parse_simple_nested_array(self, package):
        """Test parsing a simple array schema"""
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_array-1.0.0",
            "title": "A simple array",
            "description": "This is an array schema",
            "type": "array",
            "items": {"type": "array", "items": {"type": "integer"}},
            "archive_catalog": {"datatype": "int[]", "destination": ["int_place"]},
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            """\
            from __future__ import annotations

            from rad.node import ArchiveCatalog, ArrayNode, Metadata
            from typing import Annotated, TypeAlias

            __all__ = ('SimpleArray',)

            SimpleArray: TypeAlias = Annotated[ArrayNode[ArrayNode[int]], Metadata(title='A simple array', description='This is an array schema', archive_catalog=ArchiveCatalog(datatype='int[]', destination=('int_place',)))]

            """
        )
        assert module.text() == truth

    def test_parse_simple_scalar_anyof(self, package):
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_scalar-1.0.0",
            "title": "A simple scalar",
            "description": "This is a scalar schema",
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ],
            "archive_catalog": {"datatype": "nvarchar(20)", "destination": ["str_place"]},
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            """\
            from __future__ import annotations

            from rad.node import ArchiveCatalog, Metadata
            from typing import Annotated, TypeAlias

            __all__ = ('SimpleScalar',)

            SimpleScalar: TypeAlias = Annotated[str | None, Metadata(title='A simple scalar', description='This is a scalar schema', archive_catalog=ArchiveCatalog(datatype='nvarchar(20)', destination=('str_place',)))]

            """
        )
        assert module.text() == truth

    @pytest.mark.parametrize(
        "tag, extra, truth_imports, truth_type",
        [
            (
                "tag:stsci.edu:asdf/time/time-1.*",
                None,
                dedent("""\
                       from __future__ import annotations

                       from astropy.time import Time
                       from rad.node import ArchiveCatalog, Metadata
                       from typing import Annotated, TypeAlias
                       """),
                "Time",
            ),
            (
                "tag:astropy.org:astropy/table/table-1.*",
                None,
                dedent("""\
                       from __future__ import annotations

                       from astropy.table import Table
                       from rad.node import ArchiveCatalog, Metadata
                       from typing import Annotated, TypeAlias
                       """),
                "Table",
            ),
            (
                "tag:stsci.edu:gwcs/wcs-*",
                None,
                dedent("""\
                       from __future__ import annotations

                       from gwcs import WCS
                       from rad.node import ArchiveCatalog, Metadata
                       from typing import Annotated, TypeAlias
                       """),
                "WCS",
            ),
            (
                "tag:stsci.edu:asdf/core/ndarray-1.*",
                {"datatype": "uint16"},
                dedent("""\
                       from __future__ import annotations

                       from numpy import uint16
                       from numpy.typing import NDArray
                       from rad.node import ArchiveCatalog, Metadata
                       from typing import Annotated, TypeAlias
                       """),
                "NDArray[uint16]",
            ),
            (
                "tag:stsci.edu:asdf/core/ndarray-1.*",
                {"datatype": "uint16", "ndim": 3},
                dedent("""\
                       from __future__ import annotations

                       from numpy import ndarray, uint16
                       from rad.node import ArchiveCatalog, Metadata
                       from typing import Annotated, TypeAlias
                       """),
                "ndarray[tuple[int, int, int], uint16]",
            ),
            (
                "tag:stsci.edu:asdf/unit/unit-1.*",
                {"enum": ["Jy", "mJy"]},
                dedent("""\
                       from __future__ import annotations

                       from astropy.units import Unit
                       from rad.node import ArchiveCatalog, Metadata
                       from typing import Annotated, TypeAlias
                       """),
                'Unit["Jy"] | Unit["mJy"]',
            ),
            (
                "tag:astropy.org:astropy/units/unit-1.*",
                {"enum": ["DN"]},
                dedent("""\
                       from __future__ import annotations

                       from astropy.units import Unit
                       from rad.node import ArchiveCatalog, Metadata
                       from typing import Annotated, TypeAlias
                       """),
                'Unit["DN"]',
            ),
            (
                "tag:stsci.edu:asdf/unit/quantity-1.*",
                {"unit": {"tag": "tag:astropy.org:astropy/units/unit-1.*", "enum": ["m"]}},
                dedent("""\
                       from __future__ import annotations

                       from astropy.units import Quantity, Unit
                       from rad.node import ArchiveCatalog, Metadata
                       from typing import Annotated, TypeAlias
                       """),
                'Quantity[Unit["m"]]',
            ),
            (
                "tag:stsci.edu:asdf/roman/schemas/simple_tag-1.0.0",
                None,
                dedent("""\
                       from __future__ import annotations

                       from rad.node import ArchiveCatalog, Metadata
                       from typing import Annotated, Any, TypeAlias
                       """),
                "Any",
            ),
        ],
    )
    def test_parse_simple_tag(self, package, tag, extra, truth_imports, truth_type):
        """Test parsing a simple tag schema"""
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_tag-1.0.0",
            "title": "A simple tag",
            "description": "This is a tag schema",
            "tag": tag,
            "archive_catalog": {"datatype": "nvarchar(20)", "destination": ["str_place"]},
        }
        if extra is not None:
            schema.update(extra)

        module = Module.from_schema(schema, package)

        truth = truth_imports + dedent(
            f"""\

            __all__ = ('SimpleTag',)

            SimpleTag: TypeAlias = Annotated[{truth_type}, Metadata(title='A simple tag', description='This is a tag schema', archive_catalog=ArchiveCatalog(datatype='nvarchar(20)', destination=('str_place',)))]

            """
        )
        assert module.text() == truth

    def test_parse_simple_object(self, package):
        """Test parsing a simple object schema"""
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_object-1.0.0",
            "title": "A simple object",
            "description": "This is an object schema",
            "type": "object",
            "properties": {
                "a": {
                    "type": "integer",
                    "title": "An integer",
                    "archive_catalog": {"datatype": "int", "destination": ["int_place"]},
                },
                "b": {"type": "string", "description": "A string"},
            },
            "required": ["a"],
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            """\
            from __future__ import annotations

            from rad.node import ArchiveCatalog, Metadata, ObjectNode
            from typing import Annotated

            __all__ = ('SimpleObject',)

            class SimpleObject(ObjectNode):
                \"\"\"
                A simple object
                    This is an object schema

                \"\"\"

                __required__ = ('a',)

                a: Annotated[int, Metadata(title='An integer', archive_catalog=ArchiveCatalog(datatype='int', destination=('int_place',)))]
                b: Annotated[str, Metadata(description='A string')]


            """
        )
        assert module.text() == truth

    def test_parse_simple_single_allof(self, package):
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_scalar-1.0.0",
            "title": "A simple scalar",
            "description": "This is a scalar schema",
            "allOf": [
                {"type": "string"},
            ],
            "archive_catalog": {"datatype": "nvarchar(20)", "destination": ["str_place"]},
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            """\
            from __future__ import annotations

            from rad.node import ArchiveCatalog, Metadata
            from typing import Annotated, TypeAlias

            __all__ = ('SimpleScalar',)

            SimpleScalar: TypeAlias = Annotated[str, Metadata(title='A simple scalar', description='This is a scalar schema', archive_catalog=ArchiveCatalog(datatype='nvarchar(20)', destination=('str_place',)))]

            """
        )
        assert module.text() == truth

    def test_parse_simple_tag_allof(self, package):
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_tag_allof-1.0.0",
            "title": "A simple multiple allOf",
            "description": "This is a tag allOf schema",
            "allOf": [
                {
                    "tag": "tag:astropy.org:astropy/table/table-1.*",
                },
                {
                    "type": "object",
                    "properties": {
                        "c": {"type": "number"},
                    },
                },
            ],
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            """\
            from __future__ import annotations

            from astropy.table import Table
            from rad.node import Metadata
            from typing import Annotated, TypeAlias

            __all__ = ('SimpleTagAllof',)

            SimpleTagAllof: TypeAlias = Annotated[Table, Metadata(title='A simple multiple allOf', description='This is a tag allOf schema')]

            """
        )
        assert module.text() == truth

    def test_parse_simple_multiple_allof(self, package):
        schema = {
            "id": "asdf://stsci.edu/datamodels/roman/schemas/simple_multiple_allof-1.0.0",
            "title": "A simple multiple allOf",
            "description": "This is a multiple allOf schema",
            "allOf": [
                {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "integer",
                            "title": "An integer",
                            "archive_catalog": {"datatype": "int", "destination": ["int_place"]},
                        },
                        "b": {"type": "string", "description": "A string"},
                    },
                    "required": ["a"],
                },
                {
                    "type": "object",
                    "properties": {
                        "c": {"type": "number"},
                    },
                },
            ],
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            """\
            from __future__ import annotations

            from rad.node import ArchiveCatalog, Metadata, ObjectNode
            from typing import Annotated

            __all__ = ('SimpleMultipleAllof',)

            class SimpleMultipleAllof_allOf0(ObjectNode):
                __required__ = ('a',)

                a: Annotated[int, Metadata(title='An integer', archive_catalog=ArchiveCatalog(datatype='int', destination=('int_place',)))]
                b: Annotated[str, Metadata(description='A string')]


            class SimpleMultipleAllof_allOf1(ObjectNode):
                __required__ = ()

                c: float


            class SimpleMultipleAllof(SimpleMultipleAllof_allOf1, SimpleMultipleAllof_allOf0):
                \"\"\"
                A simple multiple allOf
                    This is a multiple allOf schema

                \"\"\"

                __required__ = ()


            """
        )
        assert module.text() == truth

    @pytest.mark.usefixtures("test_schemas")
    @pytest.mark.parametrize(
        "uri_fragment, relative_import",
        [
            ("simple_multiple_allof-1.0.0", "from .test_schemas._ref_schema import RefSchema"),
            ("foo/simple_multiple_allof-1.0.0", "from ..test_schemas._ref_schema import RefSchema"),
            ("foo/bar/simple_multiple_allof-1.0.0", "from ...test_schemas._ref_schema import RefSchema"),
        ],
    )
    def test_parse_ref_object_allof(self, package, uri_fragment, relative_import):
        schema = {
            "id": f"asdf://stsci.edu/datamodels/roman/schemas/{uri_fragment}",
            "title": "A simple multiple allOf",
            "description": "This is a multiple allOf schema",
            "allOf": [
                {
                    "$ref": "asdf://stsci.edu/datamodels/roman/schemas/test_schemas/ref_schema-1.0.0",
                },
                {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "integer",
                            "title": "An integer",
                            "archive_catalog": {"datatype": "int", "destination": ["int_place"]},
                        },
                        "b": {"type": "string", "description": "A string"},
                    },
                    "required": ["a"],
                },
            ],
        }
        module = Module.from_schema(schema, package)

        truth = dedent(
            f"""\
            from __future__ import annotations

            {relative_import}
            from rad.node import ArchiveCatalog, Metadata, ObjectNode
            from typing import Annotated

            __all__ = ('SimpleMultipleAllof',)

            class SimpleMultipleAllof_allOf1(ObjectNode):
                __required__ = ('a',)

                a: Annotated[int, Metadata(title='An integer', archive_catalog=ArchiveCatalog(datatype='int', destination=('int_place',)))]
                b: Annotated[str, Metadata(description='A string')]


            class SimpleMultipleAllof(SimpleMultipleAllof_allOf1, RefSchema):
                \"\"\"
                A simple multiple allOf
                    This is a multiple allOf schema

                \"\"\"

                __required__ = ()


            """
        )
        assert module.text() == truth


class TestPackage:
    """Test the Package class"""

    def test_empty(self, package):
        """Test creating an empty Package"""

        assert isinstance(package, Package)
        assert package.modules == {}

    def test_add_ref(self, package, test_schemas):
        ref_uri = "asdf://stsci.edu/datamodels/roman/schemas/test_schemas/ref_schema-1.0.0"

        # Smoke test to make sure the fixture added the test schema
        assert ref_uri in test_schemas.resource_manager

        assert ref_uri not in package.modules
        package.add_ref(ref_uri)
        assert ref_uri in package.modules

        module = package.modules[ref_uri]
        assert isinstance(module, Module)
        assert module.uri == ref_uri

        truth = dedent(
            """\
            from __future__ import annotations

            from rad.node import ObjectNode

            __all__ = ('RefSchema',)

            class RefSchema(ObjectNode):
                \"\"\"
                A schema to use as a $ref example

                \"\"\"

                __required__ = ('prop0', 'prop1', 'prop2')

                prop0: float | None
                prop1: str
                prop2: bool


            """
        )
        assert module.text() == truth
