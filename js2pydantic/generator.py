"""Generate Pydantic model source code from parsed schemas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from js2pydantic.parser import ModelDef, SchemaParser, load_schema
from js2pydantic.types.mappings import EXTRA_IMPORTS
from js2pydantic.utils import format_code


def _build_jinja_env(custom_template: str | None = None) -> Environment:
    if custom_template:
        from jinja2 import FileSystemLoader

        loader = FileSystemLoader(str(Path(custom_template).parent))
        env = Environment(loader=loader, autoescape=select_autoescape())
        env.filters["repr"] = repr
        return env
    return Environment(
        loader=PackageLoader("js2pydantic", "templates"),
        autoescape=select_autoescape(),
    )


def _collect_imports(models: list[ModelDef]) -> dict[str, set[str]]:
    """Determine necessary imports from model definitions."""
    imports: dict[str, set[str]] = {
        "pydantic": {"BaseModel", "Field"},
        "typing": {"Literal"},
    }

    for model in models:
        for fld in model.fields:
            # Extra imports from type names
            for type_name, module in EXTRA_IMPORTS.items():
                if type_name in fld.python_type:
                    imports.setdefault(module, set()).add(type_name)
            if "Literal[" in fld.python_type:
                imports.setdefault("typing", set()).add("Literal")
            if "Any" in fld.python_type:
                imports.setdefault("typing", set()).add("Any")
            if " | " in fld.python_type:
                # Python 3.10+ union syntax; no typing.Union needed
                pass

    return imports


def render_models(models: list[ModelDef], custom_template: str | None = None) -> str:
    """Render model definitions to a Python source string."""
    env = _build_jinja_env(custom_template)
    template_name = Path(custom_template).name if custom_template else "model.py.j2"
    template = env.get_template(template_name)

    imports = _collect_imports(models)
    source = template.render(imports=imports, models=models)
    return source


def generate_from_schema(
    schema: dict[str, Any],
    *,
    root_name: str = "RootModel",
    openapi: bool = False,
    custom_template: str | None = None,
    format: bool = True,
) -> str:
    """Generate Python source from a raw schema dict."""
    parser = SchemaParser(schema, openapi=openapi)
    models = parser.parse(root_name=root_name)
    source = render_models(models, custom_template=custom_template)
    if format:
        source = format_code(source)
    return source


def generate(
    input_path: str | Path,
    *,
    output_path: str | Path | None = None,
    root_name: str = "RootModel",
    openapi: bool = False,
    custom_template: str | None = None,
    format: bool = True,
) -> str:
    """High-level API: load schema from disk and generate Python source.

    Returns the generated source string.  If *output_path* is given, also writes to disk.
    """
    schema = load_schema(input_path)
    source = generate_from_schema(
        schema,
        root_name=root_name,
        openapi=openapi,
        custom_template=custom_template,
        format=format,
    )
    if output_path:
        Path(output_path).write_text(source, encoding="utf-8")
    return source
