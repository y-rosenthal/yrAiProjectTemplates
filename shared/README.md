# `shared/` — content merged into every template install

Files in this directory are **optional** shared assets for the **yrAiProjectTemplates** meta repository.

When you run **`yraiproject install`** (see `docs/META-SPEC-v0.1.0.qmd` and `tools/yraiproject/`), the CLI copies **`shared/`** into the target project **first**, then copies the selected **versioned template** on top. If the same relative path exists in both places, the **template wins**.

**Use `shared/` for:** editor configs, optional root-level project playbooks (Markdown your team names and links from `README`), or other files that every instantiated project should receive identically.

**Do not use `shared/` for:** template-specific documentation or anything that should vary by template family—put those under `genericTemplate/<version>/` instead.

This directory may be empty except for this README.
