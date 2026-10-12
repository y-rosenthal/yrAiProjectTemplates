from __future__ import annotations

import re
import sys
from pathlib import Path

from yraiproject import fsutil


def _repo_root_from_manifest(manifest: dict, override: Path | None) -> Path | None:
    if override is not None:
        return override.resolve()
    root = manifest.get("paths", {}).get("metaRepoRoot")
    if root:
        return Path(root).resolve()
    return None


def _walk_target_files(target: Path, plan: dict[Path, Path]) -> list[Path]:
    """List files under target that are not in plan (ignoring .git and .yrAiProjectTemplate)."""
    extra: list[Path] = []
    skip_roots = {".git", ".yrAiProjectTemplate"}
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(target)
        if rel.parts and rel.parts[0] in skip_roots:
            continue
        if fsutil.is_skipped_rel(rel, skip_template_manifest=False):
            continue
        if rel not in plan:
            extra.append(rel)
    return sorted(extra, key=str)


def run_verify(
    target: Path,
    *,
    repo_root: Path | None,
    template_id: str | None,
    version_dir: str | None,
    check_content: bool,
) -> int:
    target = target.resolve()
    try:
        manifest = fsutil.load_manifest(target)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    tid = template_id or manifest.get("templateId")
    ver_raw = version_dir or manifest.get("templateVersion")
    if not tid or not ver_raw:
        print("error: manifest missing templateId/templateVersion; pass --template and --version.", file=sys.stderr)
        return 2

    vdir = str(ver_raw) if str(ver_raw).startswith("v") else f"v{ver_raw}"

    rr = _repo_root_from_manifest(manifest, repo_root)
    if rr is None or not rr.is_dir():
        print("error: need --repo-root (or manifest paths.metaRepoRoot) pointing at yrAiProjectTemplates.", file=sys.stderr)
        return 2

    try:
        plan, _ = fsutil.build_install_plan(rr, tid, vdir)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    missing: list[Path] = []
    content_issues: list[str] = []

    for rel, src in sorted(plan.items(), key=lambda x: str(x[0])):
        dest = target / rel
        if not dest.is_file():
            missing.append(rel)
            continue
        if not check_content:
            continue
        t_text = fsutil.read_text_maybe(src)
        u_text = fsutil.read_text_maybe(dest)
        if t_text is None or u_text is None:
            continue
        t_text = fsutil.normalize_text_for_compare(t_text)
        u_text = fsutil.normalize_text_for_compare(u_text)
        try:
            pat = fsutil.template_to_regex(t_text)
        except re.error as e:
            content_issues.append(f"{rel}: could not build placeholder regex: {e}")
            continue
        if not pat.match(u_text):
            content_issues.append(f"{rel}: content does not match template with YRAI placeholders")

    extra = _walk_target_files(target, plan)

    ok = not missing and not content_issues
    if missing:
        print("Missing expected files:", file=sys.stderr)
        for rel in missing:
            print(f"  - {rel}", file=sys.stderr)
    if content_issues:
        print("Content issues:", file=sys.stderr)
        for line in content_issues:
            print(f"  - {line}", file=sys.stderr)
    if extra:
        print("Note: extra files not in template+shared plan (informational):")
        for rel in extra:
            print(f"  + {rel}")

    if ok and not extra:
        print("verify: OK (paths match plan)")
    elif ok:
        print("verify: OK (paths match plan; see extra files above)")
    return 0 if ok else 1
