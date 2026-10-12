from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SKIP_DIR_NAMES = frozenset({".git", "__pycache__", ".quarto", "_book"})
TEMPLATE_MANIFEST_NAME = "yraiproject.template.yml"
META_SPEC_VERSION = "0.1.0"
PLACEHOLDER_TOKEN = re.compile(r"(\{\{YRAI:[^}]+\}\})")


def find_repo_root(start: Path | None = None) -> Path | None:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "genericTemplate").is_dir():
            return p
    return None


def is_skipped_rel(rel: Path, *, skip_template_manifest: bool) -> bool:
    if any(part in SKIP_DIR_NAMES for part in rel.parts):
        return True
    if skip_template_manifest and rel == Path(TEMPLATE_MANIFEST_NAME):
        return True
    return False


def iter_shared_files(shared_root: Path) -> Iterator[tuple[Path, Path]]:
    """Yield (absolute source path, relative path under install target)."""
    if not shared_root.is_dir():
        return
    for path in shared_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(shared_root)
        if is_skipped_rel(rel, skip_template_manifest=False):
            continue
        if rel == Path("README.md"):
            continue
        yield path, rel


def iter_template_files(template_root: Path) -> Iterator[tuple[Path, Path]]:
    for path in template_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(template_root)
        if is_skipped_rel(rel, skip_template_manifest=True):
            continue
        yield path, rel


def build_install_plan(repo_root: Path, template_id: str, version_dir: str) -> tuple[dict[Path, Path], bool]:
    """
    Merge shared/ then template; template wins on same rel path.
    Returns (rel -> absolute source path, shared_was_used).
    """
    shared_root = repo_root / "shared"
    template_root = repo_root / template_id / version_dir
    if not template_root.is_dir():
        raise FileNotFoundError(f"Template not found: {template_root}")

    plan: dict[Path, Path] = {}
    shared_used = False
    for src, rel in iter_shared_files(shared_root):
        plan[rel] = src
        shared_used = True
    for src, rel in iter_template_files(template_root):
        plan[rel] = src
    return plan, shared_used


def target_is_effectively_empty(target: Path, *, allow_git_only: bool) -> bool:
    if not target.exists():
        return True
    if not target.is_dir():
        return False
    entries = list(target.iterdir())
    if not entries:
        return True
    if allow_git_only and len(entries) == 1 and entries[0].name == ".git":
        return True
    return False


def template_to_regex(text: str) -> re.Pattern[str]:
    parts = PLACEHOLDER_TOKEN.split(text)
    out: list[str] = []
    for i, part in enumerate(parts):
        if PLACEHOLDER_TOKEN.fullmatch(part):
            out.append(".*?")
        else:
            out.append(re.escape(part))
    return re.compile("^" + "".join(out) + "$", re.DOTALL)


def read_text_maybe(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def normalize_text_for_compare(s: str) -> str:
    return s.replace("\r\n", "\n")


def write_manifest(
    target_root: Path,
    *,
    template_id: str,
    template_version: str,
    repo_root: Path | None,
    template_source_rel: str,
    shared_applied: bool,
) -> None:
    meta_dir = target_root / ".yrAiProjectTemplate"
    meta_dir.mkdir(parents=True, exist_ok=True)
    from yraiproject import __version__ as installer_version

    installed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {
        "schemaVersion": 1,
        "templateId": template_id,
        "templateVersion": template_version,
        "metaSpecVersion": META_SPEC_VERSION,
        "installedAt": installed_at,
        "installer": {"name": "yraiproject", "version": installer_version},
        "paths": {
            "templateSource": template_source_rel,
            "sharedApplied": shared_applied,
            "metaRepoRoot": str(repo_root) if repo_root else None,
        },
    }
    (meta_dir / "manifest.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_manifest(target_root: Path) -> dict:
    p = target_root / ".yrAiProjectTemplate" / "manifest.json"
    if not p.is_file():
        raise FileNotFoundError(f"Missing manifest: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def copy_plan(plan: dict[Path, Path], target_root: Path, *, dry_run: bool) -> None:
    for rel, src in sorted(plan.items(), key=lambda x: str(x[0])):
        dest = target_root / rel
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
