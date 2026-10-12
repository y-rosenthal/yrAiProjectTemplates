from __future__ import annotations

import sys
from pathlib import Path

from yraiproject import fsutil


def _version_dir_from_manifest(version: str) -> str:
    return version if version.startswith("v") else f"v{version}"


def run_install(
    target: Path,
    *,
    repo_root: Path | None,
    template_id: str,
    version_dir: str,
    allow_git_only: bool,
    allow_non_empty_safe: bool,
    dry_run: bool,
) -> int:
    rr = repo_root or fsutil.find_repo_root()
    if rr is None:
        print("error: could not find meta repository root (no genericTemplate/). Use --repo-root.", file=sys.stderr)
        return 2

    try:
        plan, shared_used = fsutil.build_install_plan(rr, template_id, version_dir)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    target = target.resolve()

    if not allow_non_empty_safe:
        if not fsutil.target_is_effectively_empty(target, allow_git_only=allow_git_only):
            print(
                "error: target directory is not empty. "
                "Use an empty directory, or only `.git` (default), or pass --allow-non-empty-safe "
                "to add files without overwriting. Use --strict-empty to forbid `.git`-only targets.",
                file=sys.stderr,
            )
            return 3

    if allow_non_empty_safe:
        for rel in plan:
            dest = target / rel
            if dest.exists():
                print(f"error: would overwrite existing path: {dest}", file=sys.stderr)
                return 4

    template_version = version_dir.removeprefix("v")

    if dry_run:
        print(f"Would write {len(plan)} files into {target}")
        for rel in sorted(plan, key=str):
            print(f"  + {rel}")
        print("Would write .yrAiProjectTemplate/manifest.json")
        return 0

    target.mkdir(parents=True, exist_ok=True)
    fsutil.copy_plan(plan, target, dry_run=False)
    fsutil.write_manifest(
        target,
        template_id=template_id,
        template_version=template_version,
        repo_root=rr,
        template_source_rel=f"{template_id}/{version_dir}",
        shared_applied=shared_used,
    )
    print(f"Installed {len(plan)} files into {target}")
    return 0
