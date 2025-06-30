import pytest

from rad.node._reader._manager import Manager
from rad.node._reader._reader import Reader, rad


class TestManager:
    class ExampleReader(Reader):
        """
        Example reader for testing purposes.
        """

        foo: str = rad()
        bar: str = rad()

    def test_register_error(self, manager):
        """
        Test that registering a schema with an existing address raises SchemaAddressError.
        """

        # register the example reader via constructor
        reader = self.ExampleReader.extract(name="test_element", data={"foo": "value1", "bar": "value2"}, manager=manager)

        with pytest.raises(Manager.SchemaAddressExistsError, match=r"Schema with address .* already exists."):
            self.ExampleReader.extract(name="test_element", data={"foo": "other1", "bar": "other2"}, manager=manager)

        assert manager["test_element"] is reader
        assert reader.foo == "value1"
        assert reader.bar == "value2"

        assert len(manager) == 1
