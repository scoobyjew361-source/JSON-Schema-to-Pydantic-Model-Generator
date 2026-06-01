"""Typer CLI for js2pydantic."""

from __future__ import annotations

from pathlib import Path

import typer

from js2pydantic.generator import generate

app = typer.Typer(
    name="js2pydantic",
    help="Generate typed Pydantic models from JSON Schema or OpenAPI specs.",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    if value:
        from js2pydantic import __version__

        typer.echo(f"js2pydantic {__version__}")
        raise typer.Exit()


@app.command()
def main(
    input_path: Path = typer.Argument(..., help="Path to JSON Schema or OpenAPI file."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output Python file path."
    ),
    openapi: bool = typer.Option(
        False, "--openapi", help="Treat input as an OpenAPI 3.x spec."
    ),
    template: Path | None = typer.Option(
        None, "--template", "-t", help="Custom Jinja2 template file."
    ),
    no_format: bool = typer.Option(
        False, "--no-format", help="Skip Black formatting of the output."
    ),
    root_name: str = typer.Option(
        "RootModel", "--root-name", help="Class name for the root model."
    ),
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True
    ),
) -> None:
    """Generate Pydantic models from INPUT_PATH."""
    if not input_path.exists():
        typer.secho(f"Error: file not found: {input_path}", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        source = generate(
            input_path,
            output_path=output,
            root_name=root_name,
            openapi=openapi,
            custom_template=str(template) if template else None,
            format=not no_format,
        )
    except Exception as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if output:
        typer.secho(f"Generated: {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(source)


if __name__ == "__main__":
    app()
