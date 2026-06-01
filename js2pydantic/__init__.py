"""JSON Schema to Pydantic Model Generator."""

__version__ = "0.1.0"

from js2pydantic.generator import generate, generate_from_schema

__all__ = ["generate", "generate_from_schema", "__version__"]
