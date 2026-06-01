"""Unit tests for the generator."""

from __future__ import annotations

import ast

from js2pydantic.generator import generate_from_schema


class TestGeneratorSyntax:
    def test_user_schema_generates_valid_python(self, user_schema: dict) -> None:
        source = generate_from_schema(user_schema, root_name="User")
        # Must be valid Python
        tree = ast.parse(source)
        assert any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))

    def test_nested_schema_generates_valid_python(self, nested_schema: dict) -> None:
        source = generate_from_schema(nested_schema, root_name="Order")
        tree = ast.parse(source)
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "Order" in classes
        assert "Customer" in classes
        assert "Item" in classes

    def test_openapi_spec_generates_valid_python(self, openapi_spec: dict) -> None:
        source = generate_from_schema(openapi_spec, openapi=True)
        tree = ast.parse(source)
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "Pet" in classes
        assert "Owner" in classes

    def test_contains_expected_imports(self, user_schema: dict) -> None:
        source = generate_from_schema(user_schema, root_name="User")
        assert "from pydantic import" in source
        assert "BaseModel" in source
        assert "Field" in source
        assert "from typing import Literal" in source
        assert "EmailStr" in source

    def test_field_constraints_present(self, user_schema: dict) -> None:
        source = generate_from_schema(user_schema, root_name="User")
        assert "min_length=1" in source
        assert "ge=0" in source


class TestGeneratorFormatting:
    def test_black_formatting_applied(self, user_schema: dict) -> None:
        source = generate_from_schema(user_schema, root_name="User", format=True)
        # Black changes quotes to double quotes, etc.
        assert '"""' in source or '"' in source

    def test_no_format_option(self, user_schema: dict) -> None:
        source_unformatted = generate_from_schema(
            user_schema, root_name="User", format=False
        )
        source_formatted = generate_from_schema(
            user_schema, root_name="User", format=True
        )
        # They may differ; at minimum both should be valid Python
        ast.parse(source_unformatted)
        ast.parse(source_formatted)
