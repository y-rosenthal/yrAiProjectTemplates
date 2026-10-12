# yrAiProjectTemplates

This **meta repository** holds **versioned project templates** for projects that may be developed with help from **language models or other automated assistants**. Conventions here emphasize **plain-text, version-controlled** files that any tool (or human) can read—without tying you to a specific vendor (see **`docs/`**).

## What lives here

| Path | Role |
|------|------|
| **`README.md` (this file)** | Overview of the **template library** repository itself. |
| **`docs/`** | Quarto source for the **meta-project documentation book** (SPEC, authoring guides, AI-tool notes—not a downstream app’s doc set). |
| **`shared/`** | Optional files merged into **every** template install before the versioned template overlay (see the SPEC). |
| **`genericTemplate/<version>/`** | A **frozen** template tree (e.g. `v0.0.1`) you can copy into a new project. |

Each **downstream** project created from a template has its **own** root `README.md` and **`docs/`** folder as defined by that template version.

## Templates and versions

Each subfolder under the repo root is a **template family** (today: **`genericTemplate`**). Inside it, **version directories** (e.g. **`v0.0.1`**) hold immutable snapshots so you can compare versions without relying only on git history.

## Files, folders, and assisted development

Templates and this book encourage **predictable layout** (root `README`, `docs/`, documented commands) and optional **project playbooks** so context stays in git. That works with **any** assistant that can read repository files. See **`docs/META-PROJECT-CONVENTIONS.qmd`** or the **“Project files and assisted development”** chapter in the rendered book—not product-specific setup guides.

## Specification and CLI

- **Normative behavior** (placeholders, `.yrAiProjectTemplate/manifest.json`, shared overlay, CI rationale): **`docs/META-SPEC-v0.1.0.qmd`** (also the **“META-SPEC v0.1.0”** chapter in the rendered book).
- **Command-line tools:** Python package **`tools/yraiproject/`**. On many Linux systems Python is **PEP 668–managed**, so use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ./tools/yraiproject
yraiproject install /path/to/new-project --repo-root "$(pwd)"
yraiproject verify /path/to/new-project --repo-root "$(pwd)" --check-content
```

See **`tools/yraiproject/README.md`** for flag details; **`--repo-root`** can be omitted when you run the command from (or inside) a clone of this repository.

## Building the meta documentation book

From the repository root:

```bash
quarto render docs
```

Open **`docs/_book/index.html`**. For a deeper walkthrough, see **`docs/QUARTO-DOC-GUIDE.qmd`**.
