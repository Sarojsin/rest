"""Structural discipline assertions (plan 18 §3, 21 §10) — cheap, decisive.

1. The cross-module import inventory may only shrink against
   tests/structure/couplings_baseline.txt (equality assertion).
2. No module (outside its router composition files) may import app.api —
   api is the composition layer over modules, never the reverse.
3. No naive datetimes anywhere in app/: every datetime.now must pass
   tz=UTC (plan 21 §4 money & time rule).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
MODULES = APP / "modules"
BASELINE = Path(__file__).resolve().parent / "couplings_baseline.txt"

COMPOSITION_FILE_RE = re.compile(r"^(router.*|.*router)\.py$")


def _own_module(path: Path) -> str | None:
    rel = path.relative_to(MODULES).parts
    return rel[0] if len(rel) > 1 else None


def _source_files() -> list[Path]:
    files = [p for p in MODULES.rglob("*.py") if "__pycache__" not in p.parts]
    return files


def _couplings(files: list[Path]) -> set[tuple[str, str, str]]:
    """Compute {(source_module, target_module, imported_part)}."""
    out: set[tuple[str, str, str]] = set()
    for p in files:
        own = _own_module(p)
        if own is None:
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                targets.append(node.module)
            elif isinstance(node, ast.Import):
                targets.extend(a.name for a in node.names)
            for target in targets:
                if not target.startswith("app.modules."):
                    continue
                tgt = target.split(".")[2]
                if tgt == own:
                    continue
                parts = target.split(".")
                # semantic part: what layer is being imported (models, services,
                # schemas, ...) — deeper suffixes record the exact submodule
                part = ".".join(parts[3:]) if len(parts) > 3 else "base"
                out.add((own, tgt, part))
    return out


def _baseline() -> set[tuple[str, str, str]]:
    out = set()
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        src, rest = line.split(" -> ")
        tgt, part = rest.split(" : ")
        out.add((src.strip(), tgt.strip(), part.strip()))
    return out


def test_cross_module_couplings_only_shrink() -> None:
    current = _couplings(_source_files())
    frozen = _baseline()
    new = current - frozen
    removed = frozen - current
    assert not new, (
        "New cross-module import(s) detected — they are forbidden (02 §2.1). "
        f"Drain them or, only after a plan-level ADR, move them into the baseline.\n"
        f"    New: {sorted(new)}"
    )
    # Removals are celebrated, not errors — but the baseline file must be
    # updated in the same PR so the inventory stays the single source of truth.
    assert not removed, (
        "Coupling(s) resolved! Delete them from tests/structure/couplings_baseline.txt "
        f"in this PR so the inventory reflects reality: {sorted(removed)}"
    )


def test_modules_do_not_import_api_except_router_composition() -> None:
    offenders: list[str] = []
    for p in _source_files():
        if COMPOSITION_FILE_RE.match(p.name):
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            elif isinstance(node, ast.Import):
                names.extend(a.name for a in node.names)
            for name in names:
                if name.startswith("app.api"):
                    offenders.append(f"{p.relative_to(APP)}: {name}")
    assert not offenders, (
        "Non-composition module files may not import app.api (21 §2 layering): " f"{offenders}"
    )


def test_no_naive_datetimes_in_app() -> None:
    """
    Every datetime usage must be timezone-aware: `datetime.now(UTC)`.
    Naive `datetime.now()` / `utcnow()` silently corrupt money windows and
    day locks (21 §4). Allowed: `now(UTC)` / `datetime.now(tz)` etc.
    """
    bad: list[str] = []
    pattern_naive_call_tail = re.compile(r"datetime\.now\(\s*\)")
    for p in [APP / _p for _p in ["main.py", "seed.py"]] + list(APP.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        text = p.read_text(encoding="utf-8")
        if "datetime" not in text:
            continue
        rel = str(p.relative_to(APP))
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.split("#")[0]
            if "utcnow(" in stripped:
                bad.append(f"{rel}:{i}")
            elif pattern_naive_call_tail.search(stripped):
                bad.append(f"{rel}:{i}")
    assert not bad, (
        "Naive datetime usage found (21 §4 — plan 11 §2 'time always UTC'): " f"{bad}"
    )
