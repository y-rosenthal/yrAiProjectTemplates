from __future__ import annotations

import argparse
import sys
from pathlib import Path

from yraiproject.install_cmd import run_install
from yraiproject.verify_cmd import run_verify


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(
        prog="yraiproject",
        description="Install and verify projects from yrAiProjectTemplates (see docs/META-SPEC-v0.1.0.qmd).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    repo_help = "Path to yrAiProjectTemplates clone (auto-detected if genericTemplate/ exists in parents)"

    pi = sub.add_parser("install", help="Copy shared/ + template into TARGET; write .yrAiProjectTemplate/manifest.json")
    pi.add_argument("--repo-root", type=Path, default=None, help=repo_help)
    pi.add_argument("target", type=Path, help="Destination project directory")
    pi.add_argument("--template", default="genericTemplate", help="Template id directory under repo root (default: genericTemplate)")
    pi.add_argument("--version", default="v0.0.1", dest="version_dir", metavar="VER", help="Template version folder (default: v0.0.1)")
    pi.add_argument(
        "--strict-empty",
        action="store_true",
        help="Require a completely empty target (by default, a lone .git directory is treated as empty)",
    )
    pi.add_argument(
        "--allow-non-empty-safe",
        action="store_true",
        help="Allow non-empty target if no install path would overwrite an existing file",
    )
    pi.add_argument("--dry-run", action="store_true", help="Print planned actions without writing files")

    pv = sub.add_parser("verify", help="Check TARGET against template + shared overlay (uses manifest.json)")
    pv.add_argument("--repo-root", type=Path, default=None, help=repo_help)
    pv.add_argument("target", type=Path, help="Project root containing .yrAiProjectTemplate/manifest.json")
    pv.add_argument("--template", default=None, help="Override template id from manifest")
    pv.add_argument("--version", default=None, dest="version_dir", metavar="VER", help="Override template version from manifest")
    pv.add_argument(
        "--check-content",
        action="store_true",
        help="Match text files with YRAI placeholder-aware regex (UTF-8 only)",
    )

    args = p.parse_args(argv)

    if args.command == "install":
        return run_install(
            args.target,
            repo_root=args.repo_root,
            template_id=args.template,
            version_dir=args.version_dir,
            allow_git_only=not args.strict_empty,
            allow_non_empty_safe=args.allow_non_empty_safe,
            dry_run=args.dry_run,
        )
    if args.command == "verify":
        return run_verify(
            args.target,
            repo_root=args.repo_root,
            template_id=args.template,
            version_dir=args.version_dir,
            check_content=args.check_content,
        )
    return 2
