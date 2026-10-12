# {{YRAI:PROJECT_TITLE}}

{{YRAI:PROJECT_DESCRIPTION}}

## Getting started

<!-- YRAI:BEGIN:GETTING_STARTED -->
TODO: say how to install, run and test the project.
<!-- YRAI:END:GETTING_STARTED -->

## Layout

| Path | What it holds |
|---|---|
| `docs/` | The project-docs Quarto book: the SPECs, the guides and the plans |
| `AGENTS.md` | The rules for AI coding agents; `CLAUDE.md` imports it |
| `.claude/skills/` | Step-by-step procedures for agents (`new-doc` adds a document to `docs/`) |
| `.yrAiProject/manifest.json` | The record of the template version and parts (`yrAiProject.sh status` reads it) |

## The Quarto book

| Book | Preview | Render | Output |
|---|---|---|---|
| Project docs | `quarto preview docs` | `quarto render docs` | `docs/_book/index.html` |

Run the commands from the project folder. `docs/QUARTO-GUIDE-v001.qmd` tells more.
