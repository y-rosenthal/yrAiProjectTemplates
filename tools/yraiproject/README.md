# `yraiproject` CLI

Reference implementation for **[META-SPEC v0.1.0](../../docs/META-SPEC-v0.1.0.qmd)** (`docs/META-SPEC-v0.1.0.qmd` in the meta repo).

## Install (editable)

From the **yrAiProjectTemplates** repository root:

```bash
pip install -e ./tools/yraiproject
```

## Commands

```bash
# Install default template into a new directory (fails if target is non-empty)
yraiproject install /path/to/new-project

# Require a completely empty target (reject .git-only trees)
yraiproject install /path/to/repo --strict-empty

# Add template files into existing tree without overwriting
yraiproject install /path/to/repo --allow-non-empty-safe

# Verify paths (and optional content) against template + shared overlay
yraiproject verify /path/to/project --check-content
```

Pass **`--repo-root`** if the CLI cannot auto-detect the meta repository (it searches parent directories for `genericTemplate/`).
