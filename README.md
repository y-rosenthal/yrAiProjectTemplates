# yrAiProjectTemplates

Templates and tools to start a project for AI-assisted work, so that every project has the same base: rules for
every AI coding agent, a Quarto book of project documents (SPECs, guides, plans), pending work as GitHub issues, and the skills and
checks that go with them.

## Quick start

```bash
yrAiProject.sh new ~/Dropbox/_yrAiCoding/myProject                 # a new work project
yrAiProject.sh new --type book ~/Dropbox/_yrQuarto-master/myBook    # a new book project
yrAiProject.sh status                                               # the state of the project you are in
yrAiProject.sh update --dry-run                                     # what update would change (changes nothing)
yrAiProject.sh update                                               # set up or update it (shows the plan, asks)
yrAiProject.sh --help                                               # every command and option
```

`yrAiProject.sh` is in the Dropbox tools folder (`~/Dropbox/tools`, on `PATH`). It runs `bin/yrAiProject.py`.
On a new computer, run `yrAiProject.sh setup-computer` once. Before `new` or `update` changes anything, it shows
what it would change, with diffs, and asks (`-y` skips the question; `--dry-run` only shows).

## What a project gets

| Part | What it is | `new` | `update` of an existing project |
|---|---|---|---|
| rules | `AGENTS.md` (the rules for every AI agent, with the shared rules), `CLAUDE.md` (imports `AGENTS.md`), and the setup notice | yes | always |
| pending-work | Things to do later are GitHub issues; a SessionStart hook shows how many are open | yes | yes (`--no-pending-work` to skip) |
| docs | The project-docs Quarto book in `docs/` (SPECs, guides, plans) and the `new-doc` skill | yes | with `--with-docs` |

A new project also gets a README, `.gitignore` and, for the `book` type, the main Quarto book at the root
(`quarto preview`; the docs book: `quarto preview docs`). `.yrAiProject/manifest.json` records the version and
the parts.

**The setup notice:** each project shows clearly, to people and to AI agents, that `yrAiProject.sh` set it up.
`.yrAiProject/README.md` lists the files that the tool installed and who changes each one. A message at the start
of each Claude Code session, a block in `AGENTS.md`, a line at the end of `README.md`, and a page of the docs book
point to it.

## Layout

| Path | What it holds |
|---|---|
| `bin/yrAiProject.py` | The tool: `new`, `status`, `update`, `list`, `setup-computer` |
| `rules/AGENTS.md` | The shared rules for every project and every AI agent |
| `templates/vX.Y.Z/` | One template version: `shared/` (for every project), `work/` and `book/` (for each new type) |
| `docs/` | The documentation of this repository, a Quarto book: the user guide and the SPECs |
| `tests/selftest.py` | Tests the tool and the templates; run it after every change |

## Documentation

Read the book: `quarto preview docs`. It has the user guide (`docs/USER-GUIDE-v001.qmd`), the specification
(`docs/SPEC-v0.4.0.qmd`), and the writing and Quarto guides that every project gets.

`yrAiProject.sh` replaces `yrNewAiProject.sh` and `agents-init.sh` (the old names only print the new command).
Template v0.0.1 and the records of older tools are no longer supported; they are in the git tags
`yraiproject-final` and `templates-v0.2.0`.

<!-- begin yrAiProject setup: written by yrAiProject.sh; "yrAiProject.sh update" replaces this block -->
*Set up by `yrAiProject.sh` (yrAiProjectTemplates v0.4.0; parts: rules, pending-work). It installed the rules
for AI agents, the skills and the settings, and it updates them. Before you change them, read
`.yrAiProject/README.md`.*
<!-- end yrAiProject setup -->
