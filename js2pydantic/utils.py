"""Utility helpers."""

from __future__ import annotations

import black


def format_code(source: str) -> str:
    """Format Python source using Black."""
    try:
        return black.format_str(
            source,
            mode=black.Mode(target_versions={black.TargetVersion.PY310}),  # type: ignore[attr-defined]
        )
    except Exception:
        # If formatting fails, return unformatted so the user can debug
        return source
