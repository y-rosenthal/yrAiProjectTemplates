---
name: new-doc
description: Add a document to the project-docs Quarto book (docs/) - a SPEC by default, or a USER-GUIDE, DESIGN-GUIDE, TODO, PLANNING or other type that the user names - with the right file name and version, listed in docs/_quarto.yml. Use when asked for a new spec, guide, plan or other project document, or for the next version of one.
argument-hint: "[TYPE] [--title TEXT] [--version X.Y.Z]"
---

# Add a project document (new-doc)

The rules for documents are in `docs/DOC-GUIDE-v001.qmd`. In short: a SPEC has the version of its development step
(`SPEC-v0.2.0.qmd`); other documents have a copy number (`USER-GUIDE-v001.qmd`). The newest version is listed first
in `docs/_quarto.yml`.

## Steps

1. Find the type. If the user does not name one, use `SPEC`. For a SPEC, ask for the version only if the user
   gives a reason to skip the default (the newest version with the last number plus 1).
2. Make the file and list it in the book (from the project folder):

   ```bash
   python3 .claude/skills/new-doc/new_doc.py TYPE [--title "short description"] [--version X.Y.Z] [--blank]
   ```

   Without `--blank`, the new file starts as a copy of the newest version of that type. Use `--dry-run` first if
   you are not sure; `--help` shows all the options.
3. Write the content that the user asked for. Follow the writing rules in `docs/DOC-GUIDE-v001.qmd`. For a new SPEC,
   change only what is different in this development step, and keep the older SPEC files unchanged.
4. Run `quarto render docs`. It must finish without errors.
5. Tell the user the file name, and how to see it: `quarto preview docs`.
