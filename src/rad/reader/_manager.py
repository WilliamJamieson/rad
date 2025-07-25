from __future__ import annotations

from collections.abc import Mapping

from ._schema import Schema


class Manager(Mapping[str, Schema]):
    """
    A manager for schemas that allows for easy access and manipulation of schemas.
    It implements the Mapping interface to provide dictionary-like access to schemas.
    """

    class SchemaAddressExistsError(KeyError):
        """Exception raised when a schema address already exists in the manager."""

        def __init__(self, address: str) -> None:
            super().__init__(f"Schema with address '{address}' already exists.")
            self.address = address

    def __init__(self, schemas: dict[str, Schema]) -> None:
        self._schemas = schemas

    def __getitem__(self, key: str) -> Schema:
        return self._schemas[key]

    def __iter__(self):
        return iter(self._schemas)

    def __len__(self) -> int:
        return len(self._schemas)

    def register(self, schema: Schema) -> None:
        """
        Register a new schema in the manager.
        If a schema with the same name already exists, it will be replaced.
        """
        if schema.address in self._schemas:
            raise self.SchemaAddressExistsError(schema.address)

        self._schemas[schema.address] = schema
