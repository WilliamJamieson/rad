import ast
import sys
from importlib.util import module_from_spec, spec_from_file_location

from rad.node._generator import Package


def test_parse_schema(package, schema_uri):
    """
    Smoke test that a schema can be parsed without error.
    -> and is valid Python syntax.
    """
    package.add_ref(schema_uri)

    for uri, module in package.modules.items():
        text = module.text()
        try:
            ast.parse(text)
        except SyntaxError as e:
            raise AssertionError(f"Syntax error in module {uri}") from e

    # print(package.modules[schema_uri].text())
    # assert False


def test_load_nodes(latest_datamodels_uri, tmp_path):
    """
    Smoke test that we can actually import all the nodes as they are written.
    """
    node_path = tmp_path / "test_rad_nodes"
    package = Package.from_manifest(latest_datamodels_uri)

    package.write(node_path, ruff_format=False)

    spec = spec_from_file_location("test_rad_nodes", node_path / "__init__.py")
    module = module_from_spec(spec)
    sys.modules["test_rad_nodes"] = module
    spec.loader.exec_module(module)
