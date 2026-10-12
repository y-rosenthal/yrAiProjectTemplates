<!-- Written by yrAiProject.sh. Do not edit: "yrAiProject.sh update" writes this file again. No "#" title:
docs/PROJECT-SETUP.qmd includes this file, and gives the title. -->

**Project setup by yrAiProject.sh.** `yrAiProject.sh`, the tool of yrAiProjectTemplates (https://github.com/y-rosenthal/yrAiProjectTemplates), set up this project. It installed the files below, and `yrAiProject.sh update` keeps them up to date. Read this page before you change one of them.

| | |
|---|---|
| Template version | v0.4.0 |
| Parts | rules, pending-work |
| Set up by | `yrAiProject.sh update` (an existing folder) |
| Last change | 2026-10-12 |

## The parts

- **rules**: the rules for every AI agent: `AGENTS.md`, with a copy of the shared rules (their source is `rules/AGENTS.md` in yrAiProjectTemplates), and `CLAUDE.md`, which imports it. A SessionStart hook shows a one-line notice about this setup at the start of each Claude Code session.
- **pending-work**: work to do later is GitHub issues with the label `pending-work`. The `pending-work` skill manages them, and a SessionStart hook shows how many are open.

## The files

| File | Part | Who changes it |
|---|---|---|
| `AGENTS.md` | rules | You: the project rules. The tool: only its two blocks, "yrAiProject setup" and "shared rules" |
| `CLAUDE.md` | rules | You. The tool only keeps the line `@AGENTS.md` |
| `.claude/settings.json` | rules, pending-work | You. The tool only adds its SessionStart hooks |
| `README.md` |  | You. The tool only writes its block "yrAiProject setup" at the end |
| `.claude/skills/pending-work/SKILL.md` | pending-work | The tool: `update` replaces it with each new version. If you change it, `update` leaves it alone |
| `.claude/skills/pending-work/scripts/pending.sh` | pending-work | The tool: `update` replaces it with each new version. If you change it, `update` leaves it alone |
| `.yrAiProject/` |  | The tool only: `manifest.json` (the record), `README.md` (this page), `session-start.json` (the notice). Do not edit |

## How to change things

- **Project rules:** edit `AGENTS.md`, outside the two blocks of the tool.
- **Shared rules:** edit `rules/AGENTS.md` in yrAiProjectTemplates and commit it. Then run `yrAiProject.sh update` in this project.
- **A file of the tool** (a skill, a guide): you can change it. Then `update` leaves it alone, and the file gets no newer versions. `yrAiProject.sh status` lists such files.
- **Without `yrAiProject.sh`** (for example, a collaborator): all these files are ordinary files. Change the files of the tool only if you must, and tell the project owner.

## Commands

```bash
yrAiProject.sh status             # is the project up to date? which files were changed by hand?
yrAiProject.sh update --dry-run   # what update would change (changes nothing)
yrAiProject.sh update             # update the project (shows the changes, then asks)
```

`yrAiProject.sh` is in the Dropbox tools folder of the project owner. `yrAiProject.sh --help` explains it.

## History

| Date | Command | Template | Parts |
|---|---|---|---|
| 2026-10-12 | set up (no history before v0.4.0) |  |  |
| 2026-10-12 | update | v0.4.0 | rules, pending-work |
