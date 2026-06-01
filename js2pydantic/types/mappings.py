"""JSON Schema type → Python type mappings."""

from __future__ import annotations

from typing import Any

JSON_SCHEMA_TO_PYTHON: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
    "null": "None",
}

FORMAT_MAPPING: dict[str, str] = {
    "email": "EmailStr",
    "uuid": "UUID",
    "date": "date",
    "date-time": "datetime",
    "uri": "HttpUrl",
    "hostname": "str",
    "ipv4": "str",
    "ipv6": "str",
}

EXTRA_IMPORTS: dict[str, str] = {
    "EmailStr": "pydantic",
    "HttpUrl": "pydantic",
    "UUID": "uuid",
    "date": "datetime",
    "datetime": "datetime",
}


def get_python_type(schema: dict[str, Any]) -> str:
    """Return a Python type annotation string for a JSON Schema fragment."""
    # Handle enum -> Literal
    enum_vals = schema.get("enum")
    if enum_vals is not None:
        return _literal_for(enum_vals)

    # Handle anyOf / oneOf
    for key in ("anyOf", "oneOf"):
        if key in schema:
            variants = [get_python_type(sub) for sub in schema[key]]
            return " | ".join(dict.fromkeys(variants))  # dedupe, keep order

    # Handle allOf (merge / intersection)
    if "allOf" in schema:
        parts = [get_python_type(sub) for sub in schema["allOf"]]
        return " | ".join(dict.fromkeys(parts))

    # Handle $ref
    ref = schema.get("$ref")
    if ref is not None:
        return ref_to_classname(ref)

    js_type = schema.get("type")
    if js_type is None:
        return "Any"

    if isinstance(js_type, list):
        # e.g. ["string", "null"] -> str | None
        parts = []
        for t in js_type:
            if t == "null":
                parts.append("None")
            else:
                parts.append(JSON_SCHEMA_TO_PYTHON.get(t, "Any"))
        return " | ".join(dict.fromkeys(parts))

    if js_type == "string":
        fmt = schema.get("format")
        if fmt in FORMAT_MAPPING:
            return FORMAT_MAPPING[fmt]
        return "str"

    if js_type == "array":
        items = schema.get("items")
        if items is not None:
            inner = get_python_type(items)
            return f"list[{inner}]"
        return "list[Any]"

    if js_type == "object":
        # Plain untyped object
        return "dict[str, Any]"

    return JSON_SCHEMA_TO_PYTHON.get(js_type, "Any")


def _literal_for(values: list[Any]) -> str:
    parts = []
    for v in values:
        if isinstance(v, str):
            parts.append(repr(v))
        elif isinstance(v, bool):
            parts.append(str(v))
        elif v is None:
            parts.append("None")
        else:
            parts.append(repr(v))
    return f"Literal[{', '.join(parts)}]"


def ref_to_classname(ref: str) -> str:
    """Convert a JSON Schema $ref to a Python class name."""
    # Supported patterns:
    # #/definitions/Foo
    # #/$defs/Foo
    # #/components/schemas/Foo
    # ./foo.json#/definitions/Foo  -> Foo (simplified)
    if "#" in ref:
        _, fragment = ref.split("#", 1)
    else:
        fragment = ref

    fragment = fragment.lstrip("/")
    parts = fragment.split("/")
    if len(parts) >= 2:
        return _to_classname(parts[-1])
    return _to_classname(ref)


def _to_classname(name: str) -> str:
    """Sanitize a schema name into a valid Python class name."""
    # Remove non-alphanumeric, capitalize words
    import re

    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # snake_case / kebab-case -> PascalCase
    words = name.split("_")
    return "".join(w.capitalize() for w in words if w)
