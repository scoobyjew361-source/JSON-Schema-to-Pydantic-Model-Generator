"""End-to-end tests: generate code and validate real data with Pydantic."""

from __future__ import annotations

import ast

import pytest

from js2pydantic.generator import generate_from_schema


def exec_generated(source: str):
    """Execute generated source and return the module namespace."""
    tree = ast.parse(source)
    ns: dict = {}
    exec(compile(tree, filename="<generated>", mode="exec"), ns)
    return ns


class TestEndToEndUser:
    def test_user_valid_data(self, user_schema: dict) -> None:
        source = generate_from_schema(user_schema, root_name="User")
        ns = exec_generated(source)
        User = ns["User"]
        user = User(name="Alice", age=30, email="alice@example.com", role="admin")
        assert user.name == "Alice"
        assert user.age == 30

    def test_user_optional_defaults(self, user_schema: dict) -> None:
        source = generate_from_schema(user_schema, root_name="User")
        ns = exec_generated(source)
        User = ns["User"]
        user = User(name="Bob", age=25)
        assert user.email is None
        assert user.role is None

    def test_user_constraint_violation(self, user_schema: dict) -> None:
        source = generate_from_schema(user_schema, root_name="User")
        ns = exec_generated(source)
        User = ns["User"]
        with pytest.raises(Exception):  # pydantic.ValidationError
            User(name="", age=25)


class TestEndToEndNested:
    def test_nested_valid_data(self, nested_schema: dict) -> None:
        source = generate_from_schema(nested_schema, root_name="Order")
        ns = exec_generated(source)
        Order = ns["Order"]
        order = Order(
            id=1,
            customer={"name": "Alice", "email": "alice@example.com"},
            items=[{"sku": "A123", "price": 9.99}],
        )
        assert order.id == 1


class TestEndToEndOpenAPI:
    def test_pet_valid_data(self, openapi_spec: dict) -> None:
        source = generate_from_schema(openapi_spec, openapi=True)
        ns = exec_generated(source)
        Pet = ns["Pet"]
        pet = Pet(name="Whiskers", age=3, kind="cat")
        assert pet.name == "Whiskers"
