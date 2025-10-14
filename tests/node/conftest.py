import pytest

from rad.node._generator import Package


@pytest.fixture
def package() -> Package:
    return Package.empty()
