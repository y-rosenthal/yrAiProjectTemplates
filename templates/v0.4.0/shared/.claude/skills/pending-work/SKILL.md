---
name: pending-work
description: Track "pending work" for this project - things to do later without forgetting them. Items are GitHub issues labeled pending-work in the project's repository, with a saved copy in _pending-work/pendingWork.md, but the user just talks to the agent. Covers the start-of-session count, listing items on request, adding items, showing details, working on items, and closing them.
when_to_use: Use at the start of every session (the SessionStart hook supplies the count), and whenever the user says things like "list pending", "add this to the pending list", "remind me later", "not now, save it for later", "what's pending?", "let's work on #12", "change the priority of...", or "#12 is done / no longer needed". Also use when you notice a problem you won't fix right now.
allowed-tools:
  - Bash(bash ${CLAUDE_SKILL_DIR}/scripts/pending.sh *)
  - Bash(gh issue list *)
  - Bash(gh issue view *)
  - Bash(gh issue create *)
  - Bash(gh issue edit *)
  - Bash(gh issue comment *)
  - Bash(gh issue close *)
  - Bash(gh issue reopen *)
---

# Pending work

## What it is for

- The user can add items now and work on them later, so that less important things are not forgotten.
- **At the beginning of every session**, the user sees how many pending items there are, and is asked whether to
  list them. The full list is not loaded at the start, to save context.
- GitHub issues are used "under the covers". The user may not want to use GitHub directly: call them **"pending
  items"**, and do the GitHub work for them.

## How it works

- Each item is a GitHub issue in the project's repository (`git remote get-url origin`) with the label
  `pending-work`, plus:
  - one category label: `fix`, `improvement`, `decision` or `recheck` (the list is `CATEGORIES` at the top of
    `scripts/pending.sh`; edit it for the project, then run `setup-labels`);
  - one priority label: `priority: high`, `priority: medium` or `priority: low`.
- `.claude/settings.json` runs `scripts/pending.sh session-start` when a session starts and after `/clear`. It shows
  the user the count (for example "12 pending items (3 high, 5 medium, 4 low)") and gives you the same count, not
  the list.
- `_pending-work/pendingWork.md` is a saved copy of the open items. Regenerate it after every change:
  `bash ${CLAUDE_SKILL_DIR}/scripts/pending.sh export`.
- `bash ${CLAUDE_SKILL_DIR}/scripts/pending.sh --help` shows every command.

## At the start of a session

In your **first reply**, add one short line with the count and ask whether to list the items, for example "You
have 12 pending items (3 high). Want me to list them?". Skip it if the user is already asking about pending work.
Answer their actual message as usual.

When they want the list ("list pending", "what's pending?", "yes"):

1. Run `bash ${CLAUDE_SKILL_DIR}/scripts/pending.sh list`.
2. Show it under the heading "Pending work", one line per item: `#12 [high] Short title`, highest priority first.
3. Ask whether they want to work on any of them now. They can pick numbers or say "not now".

## Adding an item

When the user asks you to remember something for later, or you find a problem you won't fix now:

1. Write a short, specific title (under about 70 characters). Name files or sections by name, not by number.
2. Write a body that someone (an agent in a fresh session) can act on without this conversation:

   ```
   **What:** the problem or task, 1-3 sentences.
   **Where:** files (and line numbers or section titles).
   **Why it matters:** the impact.
   **Suggested fix:** concrete steps, with sources/links if facts must be checked.
   **Done when:** how to verify (e.g. tests pass, command works, page renders).
   ```

3. Create the issue:

   ```bash
   gh issue create --title "..." --body "..." --label pending-work --label <category> --label "priority: <level>"
   ```

   Default to `priority: medium` unless the user says otherwise or the item breaks something (`high`). If `gh`
   says that a label is not found, run `bash ${CLAUDE_SKILL_DIR}/scripts/pending.sh setup-labels` once, then retry.
4. Run `bash ${CLAUDE_SKILL_DIR}/scripts/pending.sh export`, then confirm in one line: "Added pending item #N: title".

## Working on an item

1. Run `gh issue view <N>` and read the body and comments.
2. Do the work, following the project's other skills and rules. Verify the result.
3. Tell the user what changed and ask whether to close the item. Close it once they agree, or right away if they
   asked you to finish it:

   ```bash
   gh issue close <N> --comment "Done: <one-paragraph summary of what changed and how it was verified>"
   ```

4. If the item is only partly done, add a comment (`gh issue comment <N> --body "..."`) and leave it open.
5. Run `bash ${CLAUDE_SKILL_DIR}/scripts/pending.sh export` after every change.

## Changing or dropping an item

- **Priority or category:** `gh issue edit <N> --remove-label "priority: low" --add-label "priority: high"`.
- **No longer needed:** `gh issue close <N> --reason "not planned" --comment "<why>"`.
- **Reopen:** `gh issue reopen <N>`.
- Never delete issues.
- Don't commit or push unless the user asks. If they ask you to commit a fix, put `Fixes #N` in the commit message.

## When GitHub can't be reached, or there is no GitHub repository yet

If `gh` isn't installed or logged in, there's no network, or the project has no GitHub remote:

- `pending.sh` falls back to the saved copy in `_pending-work/pendingWork.md`, and to the queue.
- Record new items in `_pending-work/queue.md`, each as a `### [priority] Title` heading followed by the body.
- The next time `gh` works, create those issues, empty the queue file, and run `export`.
- If `gh` isn't logged in, ask the user to run `! gh auth login`. You can't log in for them.
- If there is no GitHub repository, offer to make a private one: `gh repo create --private --source . --push`, then
  `pending.sh setup-labels`. Don't make it without the user's approval.

Never put passwords, API keys or other secrets in an item.
