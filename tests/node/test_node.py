from __future__ import annotations

from types import MappingProxyType
from typing import GenericAlias

import pytest
from asdf.lazy_nodes import AsdfDictNode, AsdfListNode

from rad.node import ArrayNode, ObjectNode


@pytest.fixture(params=[ArrayNode, ObjectNode])
def node_class(request) -> type[ArrayNode] | type[ObjectNode]:
    return request.param


@pytest.fixture(params=[ArrayNode, ObjectNode])
def parent_node(request) -> type[ArrayNode] | type[ObjectNode]:
    return request.param()


@pytest.fixture(params=[True, False])
def node_data(node_class, request) -> list | dict | None:
    if node_class is ArrayNode:
        return [1, 2, 3] if request.param else None
    else:
        return {"key1": "value1", "key2": "value2"} if request.param else None


@pytest.fixture
def tag() -> str:
    return "tag:example.com,2024:example"


@pytest.fixture(params=[True, False])
def read_tag(tag, request) -> str | None:
    return tag if request.param else None


@pytest.fixture(params=[None, (int | float)])
def wrapper(request) -> type | GenericAlias | None:
    return request.param


@pytest.fixture
def node_instance(node_class, node_data, read_tag, parent_node, wrapper) -> ArrayNode | ObjectNode:
    return node_class(node_data, read_tag=read_tag, parent=parent_node, wrapper=wrapper)


@pytest.fixture(params=[True, False])
def node_subclass(node_class, tag, request) -> type[ArrayNode] | type[ObjectNode]:
    if request.param:

        class SubNode(node_class):  # type: ignore[misc]
            __slots__ = ()
            __tag__ = tag

        return SubNode

    return node_class


@pytest.fixture(params=[True, False])
def parent_node_subclass(parent_node, tag, request) -> type[ArrayNode] | type[ObjectNode]:
    if request.param:

        class SubNode(type(parent_node)):  # type: ignore[misc]
            __slots__ = ()
            __tag__ = tag

        return SubNode

    return type(parent_node)


class TestNode:
    """
    Test the underlying node class's functionality via its two subclasses, ArrayNode and ObjectNode.
    """

    def test_init(self, node_class):
        """Test the initialization of the node class"""

        # Test Default Initialization
        node = node_class()
        assert node._read_tag is None
        assert node._parent is None
        assert node._wrapper is None

        # Test Initialization with read_tag and parent
        read_tag = "tag:example.com,2024:example"
        parent_node = node_class()
        node = node_class(read_tag=read_tag, parent=parent_node, wrapper=(int | float))
        assert node._read_tag == read_tag
        assert node._parent is parent_node
        # ObjectNodes do not use external wrappers so it does not pass it through
        #   into the constructor of the Node base class.
        if node_class is ArrayNode:
            assert node._wrapper == (int | float)
        else:
            assert node._wrapper is None

    def test_is_slotted(self, node_class):
        """Test that the node object is slotted"""

        node = node_class()
        with pytest.raises(AttributeError, match=r".* attribute .*__dict__.*"):
            # Attempt to access __dict__ directly, slotted classes do not have __dict__
            node.__dict__  # noqa: B018

    @pytest.mark.parametrize("new_parent", [ArrayNode(), ObjectNode()])
    def test_copy(self, node_class, node_instance, node_data, read_tag, parent_node, new_parent, wrapper):
        """Test the copy method of the node class"""

        # No parent change
        node_copy = node_instance.copy()
        assert isinstance(node_copy, node_class)
        assert node_copy is not node_instance
        assert node_copy._read_tag is node_instance._read_tag
        assert node_copy._read_tag is read_tag
        assert node_copy._parent is node_instance._parent
        assert node_copy._parent is parent_node
        if node_class is ArrayNode:
            assert node_copy._wrapper is node_instance._wrapper
            assert node_copy._wrapper is wrapper
        else:
            assert node_copy._wrapper is None

        if node_data is None:
            if node_class is ArrayNode:
                assert node_copy._data == [] == node_instance._data
            else:
                assert node_copy._data == {} == node_instance._data
        else:
            assert node_instance._data is node_data
            assert node_copy._data is not node_instance._data
            assert node_copy._data == node_instance._data == node_data

        # Parent change
        assert new_parent is not parent_node
        node_change = node_instance.copy(parent=new_parent)
        assert isinstance(node_change, node_class)
        assert node_change is not node_instance
        assert node_change._read_tag is node_instance._read_tag
        assert node_change._read_tag is read_tag
        assert node_change._parent is new_parent
        assert node_change._parent is not node_instance._parent
        if node_class is ArrayNode:
            assert node_change._wrapper is node_instance._wrapper
            assert node_change._wrapper is wrapper
        else:
            assert node_change._wrapper is None
        assert node_change._data == node_instance._data

    def test_is_current(self, node_class, node_subclass, tag, parent_node, parent_node_subclass):
        """Test the is_current method of the node class"""

        # Case 1: No __tag__ on subclass
        if node_subclass is node_class:
            assert node_subclass.__tag__ is None

            # Case 1a: No read_tag, no parent
            assert node_subclass().is_current is True

            # Case 1b: read_tag=tag, no parent
            assert node_subclass(read_tag=tag).is_current is True

            # Case 1c: read_tag!=tag, no parent
            assert node_subclass(read_tag="tag:my/new/tag").is_current is True

            if parent_node_subclass is type(parent_node):
                assert parent_node_subclass.__tag__ is None

                # Case 1d: No read_tag, with parent with no __tag__
                assert node_subclass(parent=parent_node).is_current is True
                assert node_subclass(parent=type(parent_node)(read_tag="tag:my/new/tag")).is_current is True
            else:
                assert parent_node_subclass.__tag__ is tag

                # Case 1e: No read_tag, with parent with __tag__ but no read_tag
                assert node_subclass(parent=parent_node_subclass()).is_current is True

                # Case 1f: No read_tag, with parent with __tag__ and read_tag=tag
                assert node_subclass(parent=parent_node_subclass(read_tag=tag)).is_current is True

                # Case 1g: No read_tag, with parent with __tag__ and read_tag!=tag
                assert node_subclass(parent=parent_node_subclass(read_tag="tag:my/new/tag")).is_current is False

        # Case 2: __tag__ on subclass
        else:
            assert node_subclass.__tag__ is tag

            # Case 2a: No read_tag, no parent
            assert node_subclass().is_current is True

            # Case 2b: read_tag=tag (any parent state)
            assert node_subclass(read_tag=tag).is_current is True
            assert node_subclass(read_tag=tag, parent=parent_node).is_current is True
            assert node_subclass(read_tag=tag, parent=parent_node_subclass()).is_current is True

            # Case 2c: read_tag!=tag (any parent state)
            assert node_subclass(read_tag="tag:my/new/tag").is_current is False
            assert node_subclass(read_tag="tag:my/new/tag", parent=parent_node).is_current is False
            assert node_subclass(read_tag="tag:my/new/tag", parent=parent_node_subclass()).is_current is False

            if parent_node_subclass is type(parent_node):
                assert parent_node_subclass.__tag__ is None

                # Case 2d: No read_tag, with parent with no __tag__ and no read_tag
                assert node_subclass(parent=parent_node).is_current is True

                # Case 2e: No read_tag, with parent with no __tag__ and any read_tag
                assert node_subclass(parent=type(parent_node)(read_tag="tag:my/new/tag")).is_current is True

            else:
                assert parent_node_subclass.__tag__ is tag

                # Case 2f: No read_tag, with parent with __tag__ but no read_tag
                assert node_subclass(parent=parent_node_subclass()).is_current is True

                # Case 2g: No read_tag, with parent with __tag__ and read_tag=tag
                assert node_subclass(parent=parent_node_subclass(read_tag=tag)).is_current is True

                # Case 2h: No read_tag, with parent with __tag__ and read_tag!=tag
                assert node_subclass(parent=parent_node_subclass(read_tag="tag:my/new/tag")).is_current is False


class CustomObjectNodeA(ObjectNode):
    __slots__ = ()

    __required__ = ("key1a",)
    __keywords__ = ("key1a", "key2a")
    __alias__ = MappingProxyType({"key1a": "true_key1a"})

    key1a: str
    key2a: ArrayNode[int]


class CustomObjectNodeB(CustomObjectNodeA):
    __slots__ = ()

    __required__ = ("key1b",)
    __keywords__ = ("key1b", "key2b")
    __alias__ = MappingProxyType({"key1b": "true_key1b"})

    key1b: ObjectNode
    key2b: CustomObjectNodeA


class CustomObjectNodeNoWrap(CustomObjectNodeB):
    __slots__ = ()

    __tag__ = "tag:example.com,2024:nowrapping"


class TestObjectNode:
    """
    Test the ObjectNode class functionality.
    """

    def test_infer_required(self):
        """Test that the required fields are inferred correctly in subclasses"""

        assert CustomObjectNodeA.__required__ == ("key1a",)
        assert CustomObjectNodeB.__required__ == ("key1a", "key1b")

    def test_infer_keywords(self):
        """Test that the keyword fields are inferred correctly in subclasses"""

        assert CustomObjectNodeA.__keywords__ == ("key1a", "key2a")
        assert CustomObjectNodeB.__keywords__ == ("key1a", "key1b", "key2a", "key2b")

    def test_infer_alias(self):
        """Test that the alias mapping is inferred correctly in subclasses"""

        assert dict(CustomObjectNodeA.__alias__) == {"key1a": "true_key1a"}
        assert dict(CustomObjectNodeB.__alias__) == {"key1a": "true_key1a", "key1b": "true_key1b"}

    def test_infer_wrappers(self):
        """Test that the wrappers mapping is inferred correctly in subclasses"""

        assert CustomObjectNodeA.__wrappers__ == {"key2a": (ArrayNode, int)}
        assert CustomObjectNodeB.__wrappers__ == {
            "key2a": (ArrayNode, int),
            "key1b": (ObjectNode, None),
            "key2b": (CustomObjectNodeA, None),
        }

    @pytest.mark.parametrize(
        "data", [None, {"key": "value"}, ObjectNode({"key": "value"}), AsdfDictNode({"key": "value"}), object()]
    )
    def test_init(self, data):
        """Test the initialization of the ObjectNode class"""

        if data is None:
            assert ObjectNode(data)._data == {}
        elif isinstance(data, dict | AsdfDictNode):
            assert ObjectNode(data)._data is data
        elif isinstance(data, ObjectNode):
            assert ObjectNode(data)._data is data._data
        else:
            with pytest.raises(ValueError, match="Initializer only accepts dict-like objects"):
                ObjectNode(data)

    def test_setattr_getattr(self):
        """Test the __setattr__ and __getattr__ functionality of the ObjectNode class"""

        node = ObjectNode()
        # Setting a slotted attribute
        node._read_tag = "tag:example.com,2024:example"
        assert node._read_tag == "tag:example.com,2024:example"

        # Setting a non-slotted attribute
        assert "custom_attr" not in node._data
        node.custom_attr = "custom_value"
        assert node.custom_attr == "custom_value"

        # Ensure error is raised when setting a private non-slotted attribute
        with pytest.raises(AttributeError, match=r"Cannot set private attribute .*, only allowed are .*"):
            node._custom_attr_private = "custom_private_value"

        # Ensure error is raised when getting a private non-slotted attribute
        with pytest.raises(AttributeError, match=r"Cannot access private attribute .*, only allowed are .*"):
            _ = node._custom_attr_private

        # Ensure error is raise when getting a non-existent non-slotted attribute
        with pytest.raises(AttributeError, match=r"No such attribute .* found in node: .*"):
            _ = node.non_existent_attr

    def test_delattr(self):
        """Test the __delattr__ functionality of the ObjectNode class"""
        node = ObjectNode(read_tag="tag:example.com,2024:example")

        # Deleting a public attribute
        node.custom_attr = "custom_value"
        assert node.custom_attr == "custom_value"
        assert "custom_attr" in node._data
        del node.custom_attr
        assert "custom_attr" not in node._data
        with pytest.raises(AttributeError, match=r"No such attribute .* found in node: .*"):
            _ = node.custom_attr

        # Deleting a non-existent public attribute
        assert "non_existent_attr" not in node._data
        with pytest.raises(AttributeError, match=r"No such attribute .* found in node: .*"):
            del node.non_existent_attr

        # Deleting a non-slotted private attribute
        with pytest.raises(AttributeError, match=r"Private attribute .* is not allowed, only allowed are .*"):
            del node._custom_attr_private

        # Deleting a slotted private attribute
        assert node._read_tag == "tag:example.com,2024:example"
        del node._read_tag
        with pytest.raises(AttributeError):
            _ = node._read_tag

    def test_dict_style_access(self):
        """Test the dictionary style access methods of the ObjectNode class"""

        node = ObjectNode()

        # Setting an item
        assert "key1" not in node._data
        node["key1"] = "value1"
        assert "key1" in node._data
        assert node._data["key1"] == "value1"

        # Getting an item
        assert node["key1"] == "value1"

        # Getting a non-existent item
        with pytest.raises(KeyError, match=r"No such key .* found in node"):
            _ = node["non_existent_key"]

        # Deleting an item
        del node["key1"]
        assert "key1" not in node._data
        with pytest.raises(KeyError, match=r"No such key .* found in node"):
            _ = node["key1"]

    def test_private_dict_style_access(self):
        """Test private dictionary style access methods of the ObjectNode class"""
        node = ObjectNode()

        # Setting a private item
        assert "_private_key" not in node._data
        node["_private_key"] = "private_value"
        assert "_private_key" in node._data
        assert node._data["_private_key"] == "private_value"

        # Getting a private item
        assert node["_private_key"] == "private_value"

        # Deleting a private item
        del node["_private_key"]
        assert "_private_key" not in node._data
        with pytest.raises(KeyError, match=r"No such key .* found in node"):
            _ = node["_private_key"]

    def test_mutable_mapping_methods(self):
        """
        Test the mutable mapping methods of the ObjectNode class

        __getitem__, __setitem__, __delitem__ are tested in already in other tests
        """

        node = ObjectNode()

        # Test __len__
        assert len(node) == 0
        node["key1"] = "value1"
        assert len(node) == 1
        node["key2"] = "value2"
        assert len(node) == 2
        del node["key1"]
        assert len(node) == 1

        # Test __iter__
        node["key3"] = "value3"
        node["key4"] = "value4"
        keys = ["key2", "key3", "key4"]
        for key in node:
            assert key == keys.pop(0)

    def test_asdf_traverse(self):
        """Test the __asdf_traverse__ method of the ObjectNode class"""

        node = ObjectNode({"key1": "value1", "key2": "value2"})
        assert node.__asdf_traverse__() == {"key1": "value1", "key2": "value2"}


class TestArrayNode:
    """
    Test the ArrayNode class functionality.
    """

    @pytest.mark.parametrize("data", [None, ["value"], ArrayNode(["value"]), AsdfListNode(["value"]), object()])
    def test_init(self, data):
        """Test the initialization of the ArrayNode class"""
        if data is None:
            assert ArrayNode(data)._data == []
        elif isinstance(data, list | AsdfListNode):
            assert ArrayNode(data)._data is data
        elif isinstance(data, ArrayNode):
            assert ArrayNode(data)._data is data._data
        else:
            with pytest.raises(ValueError, match="Initializer only accepts lists"):
                ArrayNode(data)

    def test_gettiem_setitem(self):
        """Test the __getitem__ and __setitem__ methods of the ArrayNode class"""

        node = ArrayNode(["initial_value"])

        # Getting an item
        assert node[0] == "initial_value"

        # Setting/getting an item
        node[0] = "new_value"
        assert node[0] == "new_value"

    def test_list_style_access(self):
        """Test the list style access methods of the ArrayNode class"""

        node = ArrayNode()

        # Appending an item
        node.append("append_value")
        assert node[0] == "append_value"

        # Getting an item
        assert node[0] == "append_value"

        # Deleting an item
        del node[0]
        assert len(node) == 0

        # Inserting an item
        node.insert(0, "insert_value")
        assert node[0] == "insert_value"

    def test_asdf_traverse(self):
        """Test the __asdf_traverse__ method of the ArrayNode class"""

        node = ArrayNode(["value1", "value2", "value3"])
        assert node.__asdf_traverse__() == ["value1", "value2", "value3"]

    def test_setattr(self):
        """Test the __setattr__ functionality of the ArrayNode class"""
        node = ArrayNode()

        # Setting a slotted attribute
        node._read_tag = "tag:example.com,2024:example"
        node._parent = ObjectNode()

        # Ensure error is raised when setting a private non-slotted attribute
        with pytest.raises(AttributeError, match=r"Cannot set attribute .*, only allowed are .*"):
            node._custom_attr_private = "custom_private_value"

    def test_data(self):
        """Test that the data is stored correctly in the ArrayNode class"""

        data = ["value1", "value2", "value3"]
        node = ArrayNode(data)
        assert node._data is data
        assert node._data is node.data

    def test_eq(self):
        """Test the equality method of the ArrayNode class"""

        data = ["value1", "value2", "value3"]
        node = ArrayNode(data)

        # Equality with another ArrayNode
        other_node = ArrayNode(["value1", "value2", "value3"])
        assert node == other_node

        different_node = ArrayNode(["value1", "value2"])
        assert node != different_node

        # Equality with a list
        other_list = ["value1", "value2", "value3"]
        assert node == other_list

        different_list = ["value1", "value2"]
        assert node != different_list

        # Equality with an AsdfListNode
        other_asdf_node = AsdfListNode(["value1", "value2", "value3"])
        assert node == other_asdf_node

        different_asdf_node = AsdfListNode(["value1", "value2"])
        assert node != different_asdf_node

        # Equality with other types
        assert node != "not_a_node"
        assert node != 12345


@pytest.fixture(params=[ArrayNode, CustomObjectNodeA])
def wrapped_node_class(request) -> type[ArrayNode] | type[CustomObjectNodeA]:
    return request.param


@pytest.fixture
def base_data(wrapped_node_class) -> list | dict:
    if wrapped_node_class is ArrayNode:
        return [1, 2, 3]
    else:
        return {"subkey1": "subvalue1"}


@pytest.fixture
def wrapped_parameter(wrapped_node_class) -> str:
    if wrapped_node_class is ArrayNode:
        return "key2a"
    else:
        return "key2b"


@pytest.mark.parametrize("accessor_mode", ["setattr", "getattr", "setitem", "getitem"])
class TestObjectNodeWrapping:
    """
    Test the ObjectNode class's automatic wrapping behavior.
    """

    def make_node_value(self, accessor_mode, key, data, read_tag=None):
        node_class = CustomObjectNodeB if read_tag is None else CustomObjectNodeNoWrap

        # If we are wrapping via getting the item from the node, we need to
        #   initialize the node with the data already in place
        if accessor_mode in ("getattr", "getitem"):
            node = node_class({key: data}, read_tag=read_tag)
            assert node._data[key] is data

            # Use the __getattr__ to retrieve the value (which may trigger wrapping)
            if accessor_mode == "getattr":
                return node, getattr(node, key)

            # Use the __getitem__ to retrieve the value (which may trigger wrapping)
            return node, node[key]

        # Otherwise we are wrapping via setting the item on the node, so we
        #   initialize an empty node and then set the data
        node = node_class(read_tag=read_tag)
        assert key not in node._data

        # Use the __setattr__ to set the value (which may trigger wrapping)
        if accessor_mode == "setattr":
            setattr(node, key, data)
        # Use the __setitem__ to set the value (which may trigger wrapping)
        else:
            node[key] = data

        # Note we access the data directly so we can be sure we are isolating
        #   the wrapping behavior on set from the retrieval behavior
        return node, node._data[key]

    def test_wrapping(self, accessor_mode, base_data, wrapped_node_class, wrapped_parameter):
        """Test that the ObjectNode correctly wraps unwrapped values based on __wrappers__"""

        assert not isinstance(base_data, wrapped_node_class)
        node, value = self.make_node_value(accessor_mode, wrapped_parameter, base_data)

        assert not isinstance(base_data, wrapped_node_class)
        assert isinstance(node._data[wrapped_parameter], wrapped_node_class)
        assert isinstance(value, wrapped_node_class)
        assert value == base_data
        assert value._data is base_data
        assert value._parent is node
        if wrapped_node_class is ArrayNode:
            assert value._wrapper is int
        else:
            assert value._wrapper is None

    def test_rewrapping(self, accessor_mode, base_data, wrapped_node_class, wrapped_parameter):
        """Test that the ObjectNode re-wrapps already wrapped node values"""

        original_data = wrapped_node_class(base_data)
        assert original_data._parent is None
        assert original_data._wrapper is None

        node, value = self.make_node_value(accessor_mode, wrapped_parameter, original_data)

        assert original_data._parent is None
        assert original_data._wrapper is None

        assert value is not original_data
        assert value == original_data

        assert value._data is not original_data._data
        assert value._parent is node
        if wrapped_node_class is ArrayNode:
            assert value._wrapper is int
        else:
            assert value._wrapper is None

    def test_no_secondary_wrapping(self, accessor_mode, base_data, wrapped_node_class, wrapped_parameter):
        """Test that the ObjectNode does not re-wrap already properly wrapped values"""

        assert not isinstance(base_data, wrapped_node_class)
        node, truth = self.make_node_value(accessor_mode, wrapped_parameter, base_data)

        # Pull the value again through the wrapping functionality
        if accessor_mode in ("getattr", "setattr"):
            value = getattr(node, wrapped_parameter)
        else:
            value = node[wrapped_parameter]

        # Ensure that we did not modify anything on the second access
        assert value is truth

    def test_no_wrapping(self, accessor_mode, base_data, wrapped_node_class, wrapped_parameter):
        """Test that the ObjectNode with mismatched read_tag does not wrap values"""

        assert not isinstance(base_data, wrapped_node_class)
        node, value = self.make_node_value(accessor_mode, wrapped_parameter, base_data, read_tag="tag:Other,2024:version")

        assert not isinstance(base_data, wrapped_node_class)

        assert not isinstance(node._data[wrapped_parameter], wrapped_node_class)
        assert not isinstance(value, wrapped_node_class)
        assert value is base_data

    def test_no_rewrapping(self, accessor_mode, base_data, wrapped_node_class, wrapped_parameter):
        """Test that the ObjectNode with mismatched read_tag does not re-wrap values"""

        original_data = wrapped_node_class(base_data)
        assert original_data._parent is None
        assert original_data._wrapper is None

        _, value = self.make_node_value(accessor_mode, wrapped_parameter, original_data, read_tag="tag:Other,2024:version")

        assert original_data._parent is None
        assert original_data._wrapper is None

        assert value is original_data
