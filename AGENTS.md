# Rules for AI coding agents (yrAiProjectTemplates)

These rules are for every collaborator and every coding agent. `CLAUDE.md` imports this file.

## The repository

- Templates and tools to start AI-assisted projects: `bin/yrNewAiProject.py` makes a project from
  `templates/VERSION/{shared,TYPE}`, and `bin/agents_init.py` copies the shared rules (`rules/AGENTS.md`) into a
  project. `README.md` gives the layout.
- `docs/` is the documentation book: `docs/USER-GUIDE-v001.qmd` (how to use it) and `docs/SPEC-v0.2.0.qmd` (what
  it must do). Read the newest SPEC before you change anything.
- The commands `yrNewAiProject.sh` and `agents-init.sh` are wrappers in the Dropbox tools folder (`~/Dropbox/tools`,
  a separate git repository). Keep their names and behavior in step with `bin/`.

## How to work

- A released template version (git tag `templates-vX.Y.Z`) does not change. Put a change in a new version folder
  (a copy of the newest one), and write a SPEC for that version in `docs/`.
- `rules/AGENTS.md` holds the shared rules for all projects. After you change it, run
  `python3 bin/agents_init.py` in this repository, and tell the owner to run `agents-init.sh` in the other projects.
- Update `README.md`, `docs/USER-GUIDE-v001.qmd` and the SPEC in the same change as the tools or the templates.
- Before you commit: `python3 tests/selftest.py` must print `OK`, and `quarto render docs` must finish without
  errors.
- The tools use the Python standard library only, and run on Linux and in Git Bash on Windows.
- Do not push, tag or make GitHub repositories without the owner's approval.

<!-- begin shared rules: copied by agents-init from yrAiProjectTemplates/rules/AGENTS.md; edit there -->

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

<!-- end shared rules -->
