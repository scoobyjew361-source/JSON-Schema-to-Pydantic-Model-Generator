"""Integration tests for the CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "js2pydantic.cli"]


class TestCLI:
    def test_cli_version(self) -> None:
        result = subprocess.run(
            [*CLI, "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "js2pydantic" in result.stdout

    def test_cli_missing_file(self) -> None:
        result = subprocess.run(
            [*CLI, "nonexistent.json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "not found" in result.stdout

    def test_cli_generate_stdout(self, fixtures_dir: Path) -> None:
        inp = fixtures_dir / "user_schema.json"
        result = subprocess.run(
            [*CLI, str(inp)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "class User" in result.stdout

    def test_cli_generate_output(self, fixtures_dir: Path, tmp_path: Path) -> None:
        inp = fixtures_dir / "user_schema.json"
        out = tmp_path / "user_models.py"
        result = subprocess.run(
            [*CLI, str(inp), "--output", str(out)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text()
        assert "class User" in content

    def test_cli_openapi(self, fixtures_dir: Path) -> None:
        inp = fixtures_dir / "openapi_spec.yaml"
        result = subprocess.run(
            [*CLI, str(inp), "--openapi"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "class Pet" in result.stdout
        assert "class Owner" in result.stdout
