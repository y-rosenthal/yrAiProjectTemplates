# {{YRAI:PROJECT_TITLE}}

{{YRAI:PROJECT_DESCRIPTION}}

## Getting started

<!-- YRAI:BEGIN:GETTING_STARTED -->
TODO: say who the book is for, and how and where it is published.
<!-- YRAI:END:GETTING_STARTED -->

## Layout

| Path | What it holds |
|---|---|
| `_quarto.yml`, `index.qmd`, the chapter files | The main book, which is published |
| `docs/` | The project-docs Quarto book: the SPECs, the TODO list, the plans for the main book, and the guides |
| `AGENTS.md` | The rules for AI coding agents; `CLAUDE.md` imports it |
| `.claude/skills/` | Step-by-step procedures for agents (`new-doc` adds a document to `docs/`) |
| `.yrAiProjectTemplate/manifest.json` | The template that this project was made from |

## The Quarto books

| Book | Preview | Render | Output |
|---|---|---|---|
| Main book | `quarto preview` | `quarto render` | `_book/index.html` |
| Project docs | `quarto preview docs` | `quarto render docs` | `docs/_book/index.html` |

Run the commands from the project folder. `docs/QUARTO-GUIDE-v001.qmd` tells more.
