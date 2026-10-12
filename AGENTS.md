# Rules for AI coding agents (yrAiProjectTemplates)

These rules are for every collaborator and every coding agent. `CLAUDE.md` imports this file.

## The repository

- Templates and a tool for AI-assisted projects: `bin/yrAiProject.py` (`yrAiProject.sh` in the tools folder) makes
  new projects from `templates/VERSION/{shared,TYPE}` (`new`), reports the state of a project (`status`), and sets
  up or updates existing projects (`update`), with the shared rules (`rules/AGENTS.md`). `README.md` gives the
  layout.
- `docs/` is the documentation book: `docs/USER-GUIDE-v001.qmd` (how to use it) and `docs/SPEC-v0.4.0.qmd` (what
  it must do). Read the newest SPEC before you change anything.
- The command `yrAiProject.sh` is a wrapper in the Dropbox tools folder (`~/Dropbox/tools`, a separate git
  repository); `yrNewAiProject.sh` and `agents-init.sh` there are stubs that print the new command. Keep them in
  step with `bin/`.

## How to work

- A released template version (git tag `templates-vX.Y.Z`) does not change. Put a change in a new version folder
  (a copy of the newest one), and write a SPEC for that version in `docs/`.
- `rules/AGENTS.md` holds the shared rules for all projects. After you change it, run
  `python3 bin/yrAiProject.py update --no-pending-work --dry-run` in this repository, show the owner the plan, and
  apply it (`-y`) when the owner agrees. Tell the owner to run `yrAiProject.sh update` in the other projects.
- Update `README.md`, `docs/USER-GUIDE-v001.qmd` and the SPEC in the same change as the tools or the templates.
- Before you commit: `python3 tests/selftest.py` must print `OK`, and `quarto render docs` must finish without
  errors.
- The tools use the Python standard library only, and run on Linux and in Git Bash on Windows.
- Do not push, tag or make GitHub repositories without the owner's approval.

<!-- begin shared rules: copied by yrAiProject from yrAiProjectTemplates/rules/AGENTS.md; edit there -->

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
- If a project's `AGENTS.md` does not have the block `<!-- begin shared rules -->`, tell the user and offer to set
  the project up with `yrAiProject.sh update`. `yrAiProject.sh status` shows the project's state, and
  `yrAiProject.sh --help` explains both. An agent has no terminal to answer `update`'s question in: run
  `yrAiProject.sh update --dry-run`, show the user the plan, and run `yrAiProject.sh update -y` only after the user
  approves it.

## Work to do later is GitHub issues

- Record work to do later as GitHub issues in the project's own repository, not in a to-do file, a task board or a
  TODO document. If the project has the `pending-work` skill (`.claude/skills/pending-work/`), use it: the issues
  have the label `pending-work`, and a SessionStart hook shows the user how many are open.
- If a project keeps such a list in a file, tell the user and offer to move it into issues.

<!-- end shared rules -->
