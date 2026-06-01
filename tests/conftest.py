"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


def load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES / name
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)
    return json.loads(text)


@pytest.fixture
def user_schema() -> dict[str, Any]:
    return load_fixture("user_schema.json")


@pytest.fixture
def nested_schema() -> dict[str, Any]:
    return load_fixture("nested_schema.json")


@pytest.fixture
def openapi_spec() -> dict[str, Any]:
    return load_fixture("openapi_spec.yaml")


@pytest.fixture
def anyof_schema() -> dict[str, Any]:
    return load_fixture("anyof_schema.json")


@pytest.fixture
def allof_schema() -> dict[str, Any]:
    return load_fixture("allof_schema.json")
