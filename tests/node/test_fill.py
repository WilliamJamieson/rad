from __future__ import annotations

from typing import Annotated, Literal

import numpy as np
import numpy.typing as npt
import pytest
from astropy import units as u
from astropy.time import Time

from rad.node import ObjectNode
from rad.node._base import _NOBOOL, _NONUM, _NOSTR


class ScalarNode(ObjectNode):
    """A node with scalar values"""

    __uri__ = "asdf://example.com/schemas/test/scalar-1.0.0"
    __required__ = ("int_value", "float_value", "str_value", "bool_value")
    __keywords__ = ("int_value", "float_value", "str_value", "bool_value")

    int_value: int
    float_value: float
    str_value: str
    bool_value: bool


class ScalarOptionalNode(ObjectNode):
    """A node with scalar values"""

    __uri__ = "asdf://example.com/schemas/test/scalar-1.0.0"
    __required__ = ("int_value", "float_value", "str_value", "bool_value")
    __keywords__ = ("int_value", "float_value", "str_value", "bool_value", "none_value")

    int_value: int | None
    float_value: None | float
    str_value: str | None
    bool_value: bool | None
    none_value: None


class CustomScalarNode(ObjectNode):
    """A node with custom scalar defaults"""

    __uri__ = "asdf://example.com/schemas/test/custom-scalar-1.0.0"
    __required__ = ("int_value", "float_value", "str_value", "bool_value")
    __keywords__ = ("int_value", "float_value", "str_value", "bool_value")

    int_value: int
    float_value: float
    str_value: str
    bool_value: bool

    def _find_default_int_value(self, minimal=False, **kwargs):
        return 42

    def _find_default_float_value(self, minimal=False, **kwargs):
        return 3.14

    def _find_default_str_value(self, minimal=False, **kwargs):
        return "custom"

    def _find_default_bool_value(self, minimal=False, **kwargs):
        return True


class NdarrayNode(ObjectNode):
    """A node with ndarray values"""

    __uri__ = "asdf://example.com/schemas/test/ndarray-1.0.0"
    __required__ = ("ndarray_1d", "ndarray_2d", "ndarray_3d", "ndarray_nd")
    __keywords__ = ("ndarray_1d", "ndarray_2d", "ndarray_3d", "ndarray_nd")

    ndarray_1d: np.ndarray[tuple[int], np.float64]
    ndarray_2d: np.ndarray[tuple[int, int], np.int32]
    ndarray_3d: np.ndarray[tuple[int, int, int], np.uint8]
    ndarray_nd: npt.NDArray[np.float32]


class LiteralNode(ObjectNode):
    """A node with Literal values"""

    __uri__ = "asdf://example.com/schemas/test/literal-1.0.0"
    __required__ = ("literal_str", "literal_int", "literal_bool")
    __keywords__ = ("literal_str", "literal_int", "literal_bool")

    literal_str: Literal["a", "b", "c"]
    literal_int: Literal[1, 2, 3]
    literal_bool: Literal[True]


class TimeNode(ObjectNode):
    """A node with Time values"""

    __uri__ = "asdf://example.com/schemas/test/time-1.0.0"
    __required__ = ("time_value",)
    __keywords__ = ("time_value",)

    time_value: Time


@pytest.mark.parametrize(
    "key,type_,expected",
    [
        ("int_value", int, _NONUM),
        ("float_value", float, _NONUM),
        ("str_value", str, _NOSTR),
        ("bool_value", bool, _NOBOOL),
    ],
)
class TestScalarFill:
    """Test Filling of scalars"""

    def test_fill(self, key, type_, expected):
        """Test that filling works for scalars"""
        node = ScalarNode()

        assert key not in node
        node.fill_default(key)
        assert key in node
        assert isinstance(getattr(node, key), type_)
        assert getattr(node, key) == expected

    def test_fill_minimal(self, key, type_, expected):
        """Test that minimal filling does not fill scalars"""
        node = ScalarNode()

        assert key not in node
        node.fill_default(key, minimal=True)
        assert key not in node

    def test_fill_optional(self, key, type_, expected):
        """Test that filling works for optional scalars"""
        node = ScalarOptionalNode()

        assert key not in node
        node.fill_default(key)
        assert key in node
        assert isinstance(getattr(node, key), type_)
        assert getattr(node, key) == expected

        # pure None type does still work
        assert "none_value" not in node
        node.fill_default("none_value")
        assert "none_value" in node
        assert node.none_value is None


@pytest.mark.parametrize(
    "key,type_,expected",
    [
        ("int_value", int, 42),
        ("float_value", float, 3.14),
        ("str_value", str, "custom"),
        ("bool_value", bool, True),
    ],
)
def test_custom_scalar_fill(key, type_, expected):
    """Test that filling works for custom scalars"""
    node = CustomScalarNode()

    assert key not in node
    node.fill_default(key)
    assert key in node
    assert isinstance(getattr(node, key), type_)
    assert getattr(node, key) == expected


@pytest.mark.parametrize(
    "key,ndims,dtype",
    [
        ("ndarray_1d", 1, np.float64),
        ("ndarray_2d", 2, np.int32),
        ("ndarray_3d", 3, np.uint8),
        ("ndarray_nd", 1, np.float32),
    ],
)
@pytest.mark.parametrize("dim_size", [None, 5, 10])
def test_ndarray_fill(key, ndims, dtype, dim_size):
    """Test that filling works for ndarrays"""
    node = NdarrayNode()

    if dim_size is not None:
        shape = (dim_size,) * ndims
    else:
        shape = None

    assert key not in node
    node.fill_default(key, shape=shape)
    assert key in node
    assert isinstance(getattr(node, key), np.ndarray)
    assert getattr(node, key).ndim == ndims
    assert getattr(node, key).dtype == dtype
    if shape is None:
        assert getattr(node, key).shape == (1,) * ndims
    else:
        assert getattr(node, key).shape == shape

    assert np.all(getattr(node, key) == 0)


@pytest.mark.parametrize(
    "key,type_,expected",
    [
        ("literal_str", str, "a"),
        ("literal_int", int, 1),
        ("literal_bool", bool, True),
    ],
)
def test_literal_fill(key, type_, expected):
    """Test that filling works for Literals"""
    node = LiteralNode()

    assert key not in node
    node.fill_default(key)
    assert key in node
    assert isinstance(getattr(node, key), type_)
    assert getattr(node, key) == expected


def test_time_fill():
    """Test that filling works for Time"""
    node = TimeNode()

    assert "time_value" not in node
    node.fill_default("time_value")
    assert "time_value" in node
    assert isinstance(node.time_value, Time)
    assert node.time_value == "2020-01-01 00:00:00.000"


class UnitNode(ObjectNode):
    """A node with Unit values"""

    __uri__ = "asdf://example.com/schemas/test/unit-1.0.0"
    __required__ = ("unit_value",)
    __keywords__ = ("unit_value",)

    unit_value: Annotated[u.Unit, Literal["Jy", "mJy"]]
    quantity_value: Annotated[u.Quantity, tuple[int, int], np.float32, Annotated[u.Unit, Literal["m"]]]
