from __future__ import annotations

import itertools
from collections.abc import Generator, Mapping
from contextlib import contextmanager

import asdf
import yaml

from ._schema import Schema


class Manager(Mapping[str, Schema]):
    """
    A manager for schemas that allows for easy access and manipulation of schemas.
    It implements the Mapping interface to provide dictionary-like access to schemas.
    """

    MANIFEST_PREFIX = "asdf://stsci.edu/datamodels/roman/manifests/"

    class SchemaAddressExistsError(KeyError):
        """Exception raised when a schema address already exists in the manager."""

        def __init__(self, address: str) -> None:
            super().__init__(f"Schema with address '{address}' already exists.")
            self.address = address

    def __init__(self, schemas: dict[str, Schema]) -> None:
        self._schemas = schemas
        self._lock = False

        self._tag_to_address = self._create_tag_to_address_map()

    def _create_tag_to_address_map(self) -> dict[str, str]:
        resource_manager = asdf.get_config().resource_manager

        tag_to_address = {}
        for entry in itertools.chain(
            *[yaml.safe_load(resource_manager[uri])["tags"] for uri in resource_manager if uri.startswith(self.MANIFEST_PREFIX)]
        ):
            tag_to_address[entry["tag_uri"]] = entry["schema_uri"]

        return tag_to_address

    def __getitem__(self, key: str) -> Schema:
        if key not in self._schemas:
            return self._schemas[self._tag_to_address[key]]
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
        if self._lock:
            return

        if schema.address in self._schemas:
            raise self.SchemaAddressExistsError(schema.address)

        self._schemas[schema.address] = schema

    @contextmanager
    def lock(self) -> Generator[None, None, None]:
        """
        Context manager to lock the manager for modifications.
        This prevents any new schemas from being registered while the lock is active.
        """
        current = self._lock

        self._lock = True
        try:
            yield
        finally:
            self._lock = current
