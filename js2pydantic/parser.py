"""Parse JSON Schema / OpenAPI and build an internal representation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from js2pydantic.types.mappings import get_python_type, ref_to_classname


@dataclass
class FieldDef:
    name: str
    python_type: str
    default: Any = None
    has_default: bool = False
    field_kwargs: dict[str, Any] = field(default_factory=dict)
    description: str | None = None


@dataclass
class ModelDef:
    name: str
    fields: list[FieldDef] = field(default_factory=list)
    description: str | None = None
    base_class: str = "BaseModel"


class SchemaParser:
    """Parse a JSON Schema into a list of ModelDefs."""

    def __init__(self, raw_schema: dict[str, Any], openapi: bool = False) -> None:
        self.raw = raw_schema
        self.openapi = openapi
        self.models: list[ModelDef] = []
        self._visited_refs: set[str] = set()
        self._definitions: dict[str, dict[str, Any]] = {}

        # Extract definitions / $defs / components.schemas
        self._definitions.update(self.raw.get("definitions", {}))
        self._definitions.update(self.raw.get("$defs", {}))
        if openapi:
            self._definitions.update(
                self.raw.get("components", {}).get("schemas", {})
            )

    def parse(self, root_name: str = "RootModel") -> list[ModelDef]:
        if self.openapi:
            schemas = self.raw.get("components", {}).get("schemas", {})
            for name, subschema in schemas.items():
                if name not in self._visited_refs:
                    self._parse_schema(subschema, name)
            return self.models

        root_schema = self.raw
        # Prefer title from schema as root name
        effective_name = root_schema.get("title") or root_name
        # If top-level has no type but has properties, treat as object
        if root_schema.get("type") == "object" or "properties" in root_schema:
            self._parse_schema(root_schema, effective_name)
        elif "allOf" in root_schema:
            self._parse_schema(root_schema, effective_name)
        elif "$ref" in root_schema:
            self._parse_schema(root_schema, effective_name)
        else:
            # Primitive root - not common for model generation
            self._parse_schema(root_schema, effective_name)
        return self.models

    def _parse_schema(self, schema: dict[str, Any], suggested_name: str) -> str:
        """Parse a schema fragment, return a Python type string for it."""
        ref = schema.get("$ref")
        if ref:
            return self._resolve_ref(ref)

        schema_type = schema.get("type")
        if "allOf" in schema:
            return self._parse_allof_object(schema["allOf"], suggested_name)

        if schema_type == "object" or "properties" in schema:
            return self._parse_object(schema, suggested_name)

        if schema_type == "array":
            items = schema.get("items", {})
            inner = self._parse_schema(items, f"{suggested_name}Item")
            return f"list[{inner}]"

        # Primitive / anyOf / oneOf / allOf / enum
        return get_python_type(schema)

    def _resolve_ref(self, ref: str) -> str:
        """Resolve a $ref and parse the target schema if needed."""
        classname = ref_to_classname(ref)
        if ref in self._visited_refs:
            return classname
        self._visited_refs.add(ref)

        # Local fragment
        if ref.startswith("#/"):
            parts = ref[2:].split("/")
            target = self.raw
            for p in parts:
                target = target.get(p, {})
            if target:
                self._parse_schema(target, classname)
            return classname

        # External ref (simplified: assume basename)
        return classname

    def _parse_allof_object(self, subschemas: list[dict[str, Any]], name: str) -> str:
        """Merge allOf subschemas into a single object model."""
        name = ref_to_classname(name)
        if any(m.name == name for m in self.models):
            return name

        merged_properties: dict[str, Any] = {}
        merged_required: set[str] = set()
        description = None

        for sub in subschemas:
            resolved = sub
            if "$ref" in sub:
                resolved = self._resolve_ref_schema(sub["$ref"])
            if resolved.get("description") or resolved.get("title"):
                description = resolved.get("description") or resolved.get("title")
            merged_properties.update(resolved.get("properties", {}))
            merged_required.update(resolved.get("required", []))

        fields: list[FieldDef] = []
        for prop_name, prop_schema in merged_properties.items():
            fld = self._parse_property(prop_name, prop_schema, prop_name in merged_required)
            fields.append(fld)

        model = ModelDef(name=name, fields=fields, description=description)
        self.models.append(model)
        return name

    def _resolve_ref_schema(self, ref: str) -> dict[str, Any]:
        """Resolve a $ref to the actual schema dict."""
        result: dict[str, Any] = {}
        if ref.startswith("#/"):
            parts = ref[2:].split("/")
            target: Any = self.raw
            for p in parts:
                target = target.get(p, {})
            result = target if isinstance(target, dict) else {}
        return result

    def _parse_object(self, schema: dict[str, Any], name: str) -> str:
        """Parse an object schema into a ModelDef."""
        name = ref_to_classname(name)
        # Avoid duplicates
        if any(m.name == name for m in self.models):
            return name

        required = set(schema.get("required", []))
        properties = schema.get("properties", {})
        description = schema.get("description") or schema.get("title")

        fields: list[FieldDef] = []
        for prop_name, prop_schema in properties.items():
            fld = self._parse_property(prop_name, prop_schema, prop_name in required)
            fields.append(fld)

        # Handle additionalProperties -> **kwargs not supported in basic Pydantic,
        # so we skip for now.
        model = ModelDef(name=name, fields=fields, description=description)
        self.models.append(model)
        return name

    def _parse_property(self, name: str, schema: dict[str, Any], is_required: bool) -> FieldDef:
        """Parse a single property into a FieldDef."""
        py_type = self._parse_schema(schema, name)
        description = schema.get("description")
        default = schema.get("default")
        has_default = "default" in schema

        field_kwargs: dict[str, Any] = {}

        # Constraints mapping
        if "minLength" in schema:
            field_kwargs["min_length"] = schema["minLength"]
        if "maxLength" in schema:
            field_kwargs["max_length"] = schema["maxLength"]
        if "minimum" in schema:
            field_kwargs["ge"] = schema["minimum"]
        if "maximum" in schema:
            field_kwargs["le"] = schema["maximum"]
        if "exclusiveMinimum" in schema:
            field_kwargs["gt"] = schema["exclusiveMinimum"]
        if "exclusiveMaximum" in schema:
            field_kwargs["lt"] = schema["exclusiveMaximum"]
        if "pattern" in schema:
            field_kwargs["pattern"] = schema["pattern"]
        if "minItems" in schema:
            field_kwargs["min_length"] = schema["minItems"]
        if "maxItems" in schema:
            field_kwargs["max_length"] = schema["maxItems"]
        if "multipleOf" in schema:
            field_kwargs["multiple_of"] = schema["multipleOf"]

        # Optional handling
        if not is_required and not has_default:
            if "None" not in py_type.split(" | "):
                py_type = f"{py_type} | None"
            has_default = True
            default = None

        return FieldDef(
            name=name,
            python_type=py_type,
            default=default,
            has_default=has_default,
            field_kwargs=field_kwargs,
            description=description,
        )


def load_schema(path: str | Path) -> dict[str, Any]:
    """Load a JSON or YAML schema from disk."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data: dict[str, Any]
    if p.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return data
