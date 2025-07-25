from dataclasses import dataclass, fields, is_dataclass

import pytest

from rad.reader._reader import KeyWords, Reader, _snake_to_camel, rad


class TestKeyWords:
    class ExampleKeyWords(KeyWords):
        """
        Test class for KeyWords enumeration.
        """

        KEY_ONE: str = "keyOne"
        KEY_TWO: str = "keyTwo"

    @dataclass
    class ExampleSchema:
        foo: str
        bar: str = rad()
        baz_box: str = rad()
        baz: str = rad("$baz")

    def test_reader_name(self):
        """
        Test that a reader name is generated for each keyword.
        """
        assert self.ExampleKeyWords.KEY_ONE.reader_name == "key_one" == self.ExampleKeyWords.KEY_ONE.name.lower()
        assert self.ExampleKeyWords.KEY_TWO.reader_name == "key_two" == self.ExampleKeyWords.KEY_TWO.name.lower()

    @pytest.mark.parametrize(
        "data",
        [
            {"keyOne": "value1", "keyTwo": "value2", "otherKey": "value3"},
            {"keyOne": "value1", "otherKey": "value3"},
            {"keyTwo": "value2", "otherKey": "value3"},
            {"otherKey": "value3"},
            {"key_one": "value1", "key_two": "value2", "other_key": "value3"},
        ],
    )
    def test_extract(self, data):
        assert self.ExampleKeyWords.extract(data) == {
            self.ExampleKeyWords.KEY_ONE.reader_name: data.get("keyOne"),
            self.ExampleKeyWords.KEY_TWO.reader_name: data.get("keyTwo"),
        }

    def test_new(self):
        """
        Test that a new KeyWords enumeration can be created from a schema.
        """
        NewKeyWords = KeyWords.new(self.ExampleSchema)
        assert NewKeyWords.__members__ == {
            "BAR": "bar",
            "BAZ_BOX": "bazBox",
            "BAZ": "$baz",
        }
        assert issubclass(NewKeyWords, KeyWords)


class TestSchema:
    class ExampleSchema(Reader):
        foo: str
        bar: str = rad()
        baz_box: str = rad()
        baz: str = rad("$baz")

    def test_schema(self):
        """
        Test that the schema is correctly defined and fields are set up.
        """
        assert set(field.name for field in fields(Reader)) == {"name", "suffix", "manager"}

        assert set(field.name for field in fields(self.ExampleSchema)) == {
            "name",
            "suffix",
            "manager",
            "foo",
            "bar",
            "baz_box",
            "baz",
        }
        assert self.ExampleSchema.KeyWords.__members__ == {
            "BAR": "bar",
            "BAZ_BOX": "bazBox",
            "BAZ": "$baz",
        }
        assert issubclass(self.ExampleSchema.KeyWords, KeyWords)
        assert is_dataclass(self.ExampleSchema)

    @pytest.mark.parametrize(
        "data",
        [
            {"bar": "value1", "bazBox": "value2", "$baz": "value3"},
            {"bar": "value1", "bazBox": "value2"},
            {"bar": "value1"},
            {"bar": "value1", "bazBox": "value2", "$baz": "value3", "test": "other"},
        ],
    )
    @pytest.mark.parametrize(
        "kwargs",
        [
            {},
            {"suffix": "test_suffix"},
        ],
    )
    def test_extract(self, data, manager, kwargs):
        """
        Test that we can extract data
        """

        extract = self.ExampleSchema.extract("test_name", data, manager, foo="test_foo", **kwargs)
        assert extract.name == "test_name"
        assert extract.suffix == kwargs.get("suffix", None)
        assert extract.foo == "test_foo"

        for field in fields(self.ExampleSchema):
            if "schema_key" in field.metadata:
                key = field.metadata["schema_key"]
                if key is None:
                    key = _snake_to_camel(field.name)
                assert getattr(extract, field.name) == data.get(key, None), f"Failed for {field.name} with key {key}"

        assert extract.manager == manager
        assert extract.address in manager
        assert manager[extract.address] is extract

    @pytest.mark.parametrize(
        "suffix",
        [
            None,
            "test_suffix",
            "another_suffix",
        ],
    )
    def test_address(self, suffix, manager):
        """
        Test that the address is correctly formed.
        """
        address_parts = ["test_name"]
        if suffix:
            address_parts.append(suffix)
        instance = self.ExampleSchema(
            name="test_name",
            suffix=suffix,
            foo="test_foo",
            bar="test_bar",
            baz_box="test_baz_box",
            baz="test_baz",
            manager=manager,
        )
        assert instance.address == "@".join(address_parts)

        assert instance.address in manager
        assert manager[instance.address] is instance

    def test_resolve(self, manager, new_manager):
        """
        Test that the resolve method works correctly.
        """
        instance = self.ExampleSchema(
            name="test_name",
            suffix=None,
            foo="test_foo",
            bar="test_bar",
            baz_box="test_baz_box",
            baz="test_baz",
            manager=manager,
        )

        assert len(new_manager) == 0
        assert new_manager is not manager

        new_instance = instance.resolve(new_manager)

        assert len(new_manager) == 1
        assert instance.manager is manager

        assert instance.address in new_manager
        assert new_manager[instance.address] is not instance
        assert new_manager[instance.address] is new_instance

        assert new_instance.manager is new_manager
        assert new_instance.name == instance.name
        assert new_instance.suffix == instance.suffix
        assert new_instance.foo == instance.foo
        assert new_instance.bar == instance.bar
        assert new_instance.baz_box == instance.baz_box
        assert new_instance.baz == instance.baz

    def test_merge(self, manager):
        """
        Test that the merge method raises NotImplementedError.
        """
        instance = self.ExampleSchema(
            name="test_name",
            suffix=None,
            foo="test_foo",
            bar="test_bar",
            baz_box="test_baz_box",
            baz="test_baz",
            manager=manager,
        )

        with pytest.raises(NotImplementedError, match="Merge method is not implemented for ExampleSchema schema."):
            instance.merge(instance)
