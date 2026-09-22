#!/usr/bin/env python3
"""Verify the README claim: the engine runs entirely on the Python standard library.

Deterministic, stdlib-only, no network. Two checks:

1. pyproject.toml declares `dependencies = []` (the package ships no required
   third-party dependency).
2. Every import in src/ resolves to a stdlib module, the package itself, or a
   guarded optional-SDK import (inside try/except ImportError — the documented
   "optional Airbyte SDK" pattern).

Exits nonzero on any violation.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
PACKAGE = "market_sentiment_fedgpt"

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def handles_import_error(handler: ast.ExceptHandler) -> bool:
    t = handler.type
    if t is None:
        return False
    if isinstance(t, ast.Name):
        return t.id in ("ImportError", "ModuleNotFoundError")
    if isinstance(t, ast.Tuple):
        return any(
            isinstance(e, ast.Name) and e.id in ("ImportError", "ModuleNotFoundError")
            for e in t.elts
        )
    return False


def collect_roots(node: ast.AST, guarded: bool, out: list[tuple[str, bool]]) -> None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            out.append((alias.name.split(".")[0], guarded))
        return
    if isinstance(node, ast.ImportFrom):
        if node.level == 0 and node.module:
            out.append((node.module.split(".")[0], guarded))
        return  # relative imports are intra-package by construction
    if isinstance(node, ast.Try):
        body_guarded = guarded or any(handles_import_error(h) for h in node.handlers)
        for child in node.body:
            collect_roots(child, body_guarded, out)
        for child in node.handlers + node.orelse + node.finalbody:
            collect_roots(child, guarded, out)
        return
    for child in ast.iter_child_nodes(node):
        collect_roots(child, guarded, out)


def main() -> int:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if re.search(r"^dependencies\s*=\s*\[\s*\]", pyproject, re.MULTILINE):
        print("PASS  pyproject.toml declares dependencies = []")
    else:
        fail("pyproject.toml no longer declares dependencies = []")

    allowed_roots = set(sys.stdlib_module_names) | {PACKAGE}
    py_files = sorted(SRC_ROOT.rglob("*.py"))
    if not py_files:
        fail("no Python files found under src/")
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        roots: list[tuple[str, bool]] = []
        collect_roots(tree, False, roots)
        for root, guarded in roots:
            if root in allowed_roots:
                continue
            rel = py_file.relative_to(REPO_ROOT)
            if guarded:
                print(f"PASS  guarded optional import in {rel}: {root}")
            else:
                fail(f"non-stdlib, unguarded import {root!r} in {rel}")

    if failures:
        print(f"\nzero-dependency posture: FAILED ({len(failures)} violation(s))")
        raise SystemExit(1)
    print("\nzero-dependency posture: VERIFIED (stdlib-only runtime confirmed)")
    raise SystemExit(0)


if __name__ == "__main__":
    raise SystemExit(main())
