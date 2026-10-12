# Shared rules for AI coding agents (all projects)

The source of the rules that Prof. Rosenthal wants in every project, for every AI coding tool and every
collaborator. Everything from the first `## ` heading on is the shared block:

- `agents-init.sh` (in the Dropbox tools folder; it runs `bin/agents_init.py`) copies it into a project's
  `AGENTS.md`, between `<!-- begin shared rules -->` and `<!-- end shared rules -->`;
- `yrNewAiProject.sh` does the same for each new project;
- Claude Code reads this file directly on each of the owner's computers: `~/.claude/CLAUDE.md` imports it
  (`bin/setup-computer.sh` adds the import line).

Edit the rules here and commit them. Then run `agents-init.sh` in each project to update its copy.

## Scripts have --help

Every script you write or change (for a skill, a tool, or a one-off script that stays in the project) has `-h`
and `--help`. The help states the general purpose of the script, its usage line, and every option with its
default. With `-h` or `--help`, the script prints the help, exits with status 0, and does no work: it changes no
files and installs nothing.

- Python: the docstring at the top holds the help. At the start of `main`, before any work:
  `if '-h' in argv or '--help' in argv: print(__doc__); return 0` (or use `argparse` with a description).
- Bash: the header comment holds the help. Right after `set -euo pipefail`, before any setup:
  `case "${1:-}" in -h|--help) sed -n '2,/^[^#]/{/^#/s/^# \{0,1\}//p}' "$0"; exit 0 ;; esac`
- Other languages: the same behavior, in the usual way for that language.
- When you add, remove or change an option, update the help in the same change.
- Do not add `--help` to files that are only imported or sourced, or to third-party files that the project
  keeps unchanged (for example files from an upstream repository).

## Rules for every AI tool are in AGENTS.md

- Put a project's rules in its `AGENTS.md`, so that every collaborator's coding agent reads them. Most agents read
  `AGENTS.md` (Codex, Cursor, GitHub Copilot, Claude Code). Keep `CLAUDE.md` as one import line, `@AGENTS.md`, plus
  rules that apply only to Claude Code. Do not use a symlink for `CLAUDE.md` (Windows clones and Dropbox can break it).
- If a project's `AGENTS.md` does not have the block `<!-- begin shared rules -->`, tell the user and offer to run
  `agents-init.sh` in the project. `agents-init.sh --help` explains it.
