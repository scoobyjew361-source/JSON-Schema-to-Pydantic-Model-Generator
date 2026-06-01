"""Unit tests for SchemaParser."""

from __future__ import annotations

from js2pydantic.parser import SchemaParser


class TestParserBasics:
    def test_user_schema(self, user_schema: dict) -> None:
        parser = SchemaParser(user_schema)
        models = parser.parse()
        assert len(models) == 1
        model = models[0]
        assert model.name == "User"
        field_names = {f.name for f in model.fields}
        assert field_names == {"name", "age", "email", "role", "tags"}

        name_field = next(f for f in model.fields if f.name == "name")
        assert name_field.python_type == "str"
        assert name_field.field_kwargs == {"min_length": 1}
        assert not name_field.has_default

        age_field = next(f for f in model.fields if f.name == "age")
        assert age_field.python_type == "int"
        assert age_field.field_kwargs == {"ge": 0}

        email_field = next(f for f in model.fields if f.name == "email")
        assert email_field.python_type == "EmailStr | None"
        assert email_field.has_default
        assert email_field.default is None

        role_field = next(f for f in model.fields if f.name == "role")
        assert "Literal" in role_field.python_type
        assert role_field.has_default

    def test_nested_schema(self, nested_schema: dict) -> None:
        parser = SchemaParser(nested_schema)
        models = parser.parse()
        names = [m.name for m in models]
        assert "Order" in names
        assert "Customer" in names
        assert "Item" in names

        order = next(m for m in models if m.name == "Order")
        customer_field = next(f for f in order.fields if f.name == "customer")
        assert customer_field.python_type == "Customer"

    def test_openapi_spec(self, openapi_spec: dict) -> None:
        parser = SchemaParser(openapi_spec, openapi=True)
        models = parser.parse()
        names = {m.name for m in models}
        assert names == {"Pet", "Owner"}

        pet = next(m for m in models if m.name == "Pet")
        kind_field = next(f for f in pet.fields if f.name == "kind")
        assert "Literal" in kind_field.python_type

        owner = next(m for m in models if m.name == "Owner")
        phone_field = next(f for f in owner.fields if f.name == "phone")
        assert phone_field.field_kwargs == {"pattern": "^\\+?[0-9\\- ]+$"}

    def test_anyof_schema(self, anyof_schema: dict) -> None:
        parser = SchemaParser(anyof_schema)
        models = parser.parse()
        model = models[0]
        value_field = next(f for f in model.fields if f.name == "value")
        assert value_field.python_type == "str | int"
        assert not value_field.has_default

        mode_field = next(f for f in model.fields if f.name == "mode")
        assert mode_field.python_type == "str | None"
        assert mode_field.has_default

    def test_allof_schema(self, allof_schema: dict) -> None:
        parser = SchemaParser(allof_schema)
        models = parser.parse()
        names = {m.name for m in models}
        assert "Employee" in names
        # allOf is merged into Employee; Person properties are included
        emp = next(m for m in models if m.name == "Employee")
        field_names = {f.name for f in emp.fields}
        assert "firstName" in field_names
        assert "department" in field_names


class TestRefToClassname:
    def test_definitions(self) -> None:
        from js2pydantic.types.mappings import ref_to_classname

        assert ref_to_classname("#/definitions/FooBar") == "Foobar"
        assert ref_to_classname("#/$defs/FooBar") == "Foobar"
        assert ref_to_classname("#/components/schemas/Pet") == "Pet"
