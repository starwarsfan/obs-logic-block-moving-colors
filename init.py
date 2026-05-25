#!/usr/bin/env python3
"""Personalise this template after forking.

Run once after cloning your fork:

    python init.py

The script asks for your block's name, then replaces all template
placeholders in plugin.py, pyproject.toml, tests/test_plugin.py, and
README.md in a single pass.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent

# ── Placeholder strings used throughout the template ──────────────────────────
# These exact strings are replaced in every target file.
T_CLASS = "LogicTemplate"        # Python class name
T_TYPE  = "logic_template"       # type_name + entry-point key
T_LABEL = "Logic Template"       # display label in the GUI palette
T_PKG   = "obs-plugin-template"  # pip package name

TARGET_FILES = [
    ROOT / "plugin.py",
    ROOT / "pyproject.toml",
    ROOT / "tests" / "test_plugin.py",
    ROOT / "README.md",
]


def _to_class(s: str) -> str:
    """'my block name' → 'MyBlockName'"""
    return "".join(w.capitalize() for w in re.split(r"[\s_\-]+", s) if w)


def _to_snake(s: str) -> str:
    """'My Block Name' → 'my_block_name'"""
    s = re.sub(r"[\s\-]+", "_", s.strip())
    return re.sub(r"[^a-z0-9_]", "", s.lower())


def _to_kebab(s: str) -> str:
    return s.replace("_", "-")


def _ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    return input(f"{prompt}{hint}: ").strip() or default


def _patch(path: Path, subs: list[tuple[str, str]]) -> bool:
    text = path.read_text("utf-8")
    result = text
    for old, new in subs:
        result = result.replace(old, new)
    if result != text:
        path.write_text(result, "utf-8")
        return True
    return False


def main() -> None:
    print("obs-logic-block — init\n")

    label = _ask("Block display name (shown in the GUI palette)", "My Block")
    type_name = _ask("Block type name (unique snake_case identifier)", _to_snake(label))

    if not re.match(r"^[a-z][a-z0-9_]*$", type_name):
        sys.exit(f"Error: type name must be lowercase snake_case (got {type_name!r})")

    class_name   = _to_class(type_name)
    package_name = "obs-plugin-" + _to_kebab(type_name)
    description  = _ask("Short description (leave blank to keep placeholder)", "")

    print(f"\n  Class name : {class_name}")
    print(f"  type_name  : {type_name}")
    print(f"  Label      : {label}")
    print(f"  Package    : {package_name}")
    if description:
        print(f"  Description: {description}")

    if input("\nProceed? [Y/n] ").strip().lower() in ("n", "no"):
        sys.exit("Aborted.")

    subs: list[tuple[str, str]] = [
        (T_CLASS, class_name),
        (T_TYPE,  type_name),
        (T_LABEL, label),
        (T_PKG,   package_name),
    ]
    if description:
        subs.append(("Replace this description with your block's purpose.", description))

    changed = [p.name for p in TARGET_FILES if p.exists() and _patch(p, subs)]

    print(f"\nDone — updated: {', '.join(changed) or 'nothing'}")
    print("\nNext steps:")
    print("  1. Edit plugin.py — implement your block logic")
    print("  2. Update tests/test_plugin.py to match your ports and evaluate() logic")
    print("  3. docker compose up")
    print("  4. Open http://localhost:8080 — your block is in the palette")


if __name__ == "__main__":
    main()
