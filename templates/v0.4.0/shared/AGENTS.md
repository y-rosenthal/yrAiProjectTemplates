# Rules for AI coding agents ({{YRAI:PROJECT_TITLE}})

These rules are for every collaborator and every coding agent (Claude Code, Codex, Cursor, Copilot and others).
`CLAUDE.md` imports this file. Put project rules here, not in the private memory of one agent.

<!-- begin yrAiProject setup -->
<!-- end yrAiProject setup -->

## The project

- {{YRAI:PROJECT_DESCRIPTION}}
- `README.md` gives the layout and the commands that build each Quarto book.

## Documentation

- `docs/` is the project-docs Quarto book: SPECs, guides and plans. Read the newest SPEC first. It says
  what the project must do.
- Add a document with the `new-doc` skill (`.claude/skills/new-doc/SKILL.md`). The rules for documents are in
  `docs/DOC-GUIDE-v001.qmd`.
- Update the SPEC and the other documents in the same change as the work that they describe.
- After you change `docs/`, run `quarto render docs`. It must finish without errors.

## Pending work

- Things to do later are "pending items": GitHub issues labeled `pending-work` in the project's repository. A
  SessionStart hook (`.claude/settings.json`) shows the user how many are open. List them only when the user asks.
- Add, list, work on and close items with the `pending-work` skill (`.claude/skills/pending-work/SKILL.md`).

## Skills

- `.claude/skills/NAME/SKILL.md` files are step-by-step procedures. Claude Code loads them as skills. With another
  agent, read the `SKILL.md` for the task and follow it.

<!-- begin shared rules -->
<!-- end shared rules -->
