# yrAiProjectTemplates

Templates and tools to start a project for AI-assisted work, so that every project has the same base: rules for
every AI coding agent, a Quarto book of project documents (SPECs, guides, TODO lists, plans), and the skills and
checks that go with them.

## Quick start

```bash
yrNewAiProject.sh ~/Dropbox/_yrAiCoding/myProject                 # a work project
yrNewAiProject.sh --type book ~/Dropbox/_yrQuarto-master/myBook    # a book project
yrNewAiProject.sh --help                                           # what it does, and every option
```

`yrNewAiProject.sh` is in the Dropbox tools folder (`~/Dropbox/tools`, on `PATH`). It runs `bin/yrNewAiProject.py`.
On a new computer, run `bin/setup-computer.sh` once.

## The two types of project

| Type | Main purpose | Quarto books |
|---|---|---|
| `work` | Any work: programs, data, research, ... | The project docs in `docs/` (`quarto preview docs`) |
| `book` | A Quarto book to publish | The main book at the root (`quarto preview`), and the project docs in `docs/` (`quarto preview docs`) |

Every project gets `AGENTS.md` (the rules for every AI agent, with the shared rules), `CLAUDE.md` (it imports
`AGENTS.md`), `.gitignore`, the project-docs book with a first SPEC, and the `new-doc` skill.

## Layout

| Path | What it holds |
|---|---|
| `bin/yrNewAiProject.py` | Makes a project from a template, and checks a project against its template (`--verify`) |
| `bin/agents_init.py` | Copies the shared rules into a project's `AGENTS.md` (`agents-init.sh` in the tools folder) |
| `bin/setup-computer.sh` | Sets up a computer: makes Claude Code read the shared rules in every project |
| `rules/AGENTS.md` | The shared rules for every project and every AI agent |
| `templates/vX.Y.Z/` | One template version: `shared/` (for every project), `work/` and `book/` (for each type) |
| `docs/` | The documentation of this repository, a Quarto book: the user guide and the SPECs |
| `tests/selftest.py` | Tests the tools and the templates; run it after every change |

## Documentation

Read the book: `quarto preview docs`. It has the user guide (`docs/USER-GUIDE-v001.qmd`), the specification
(`docs/SPEC-v0.2.0.qmd`), and the writing and Quarto guides that every project gets.

The `yraiproject` tool of version 0.1.0 is retired; `yrNewAiProject` replaces it. The old tool is in the git tag
`yraiproject-final`.
