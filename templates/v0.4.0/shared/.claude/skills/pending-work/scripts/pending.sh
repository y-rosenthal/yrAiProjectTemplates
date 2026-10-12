#!/usr/bin/env bash
# pending.sh - helper for the "pending work" system of this project.
#
# Pending work items are GitHub issues labeled "pending-work" in this project's
# GitHub repository (the "origin" remote). The user never has to use GitHub
# directly: Claude adds, lists and closes items with the `gh` command (see SKILL.md).
#
# Usage: bash pending.sh COMMAND
#   session-start   JSON for the SessionStart hook: shows the user how many items are open
#                   (by priority) and tells Claude to offer to list them. The list itself is
#                   not loaded, to save context
#   list            open items, one per line, highest priority first (the default command)
#   export          rewrite the saved copy of the open items (MIRROR, below)
#   setup-labels    create or update the labels this system uses (safe to repeat)
#   -h, --help      show this help and stop
#
# Only bash and gh are needed (gh has jq built in), so this also works in Git Bash on Windows.
# If gh is missing, not logged in, or GitHub can't be reached, session-start and list fall
# back to the saved copy (MIRROR) and to items queued offline (QUEUE).
# Settings for this project are at the top of the script: MIRROR, QUEUE and CATEGORIES.

set -uo pipefail
case "${1:-}" in -h|--help) sed -n '2,/^[^#]/{/^#/s/^# \{0,1\}//p}' "$0"; exit 0 ;; esac

# ---- settings for this project ----------------------------------------------------------------
MIRROR="_pending-work/pendingWork.md"   # saved copy of the open items (relative to the project folder)
QUEUE="_pending-work/queue.md"          # items written while GitHub could not be reached
# Category labels: "name|color|description". Each item gets one category and one priority.
CATEGORIES=(
  "fix|D93F0B|Something is wrong and needs fixing"
  "improvement|0E8A16|New or better content or features"
  "decision|5319E7|Needs the owner's decision"
  "recheck|1D76DB|Time-sensitive fact to re-verify"
)
# ------------------------------------------------------------------------------------------------

here="$(cd "$(dirname "$0")" && pwd)"
root="${CLAUDE_PROJECT_DIR:-}"
[ -n "$root" ] && [ -d "$root" ] || root="$(git -C "$here" rev-parse --show-toplevel 2>/dev/null || pwd)"
mirror="$root/$MIRROR"
queue="$root/$QUEUE"

# owner/repo from the git remote (no network needed)
remote_url="$(git -C "$root" remote get-url origin 2>/dev/null || true)"
repo="$(printf '%s' "$remote_url" | sed -E 's#(\.git)?/*$##; s#^.*github\.com[:/]##')"
case "$remote_url" in *github.com*) ;; *) repo="" ;; esac

gh_bin="$(command -v gh || true)"
[ -z "$gh_bin" ] && [ -x /snap/bin/gh ] && gh_bin=/snap/bin/gh

run_gh() {
  if [ -z "$gh_bin" ] || [ -z "$repo" ]; then return 127; fi
  if command -v timeout >/dev/null 2>&1; then
    timeout 20 "$gh_bin" "$@"
  else
    "$gh_bin" "$@"
  fi
}

# jq helpers shared by the commands below (gh's built-in jq)
JQ_DEFS='
def prio: ([.labels[].name | select(startswith("priority: ")) | ltrimstr("priority: ")] | first) // "-";
def rank: ({"high": 0, "medium": 1, "low": 2}[prio]) // 3;
def cats: [.labels[].name | select(. != "pending-work" and (startswith("priority: ") | not))] | join(", ");
def ordered: sort_by([rank, .number]);
'

# A jq string literal for a shell string (gh's --jq has no --arg option).
jq_lit() { printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"; }

# What Claude is told at the start of a session. COUNT is replaced by the count line.
INSTRUCTIONS='Instructions for Claude: The user has already seen this count; the list itself was not loaded, to save context. In your FIRST reply, add one short line, for example "You have COUNT. Want me to list them?" (skip it if the user is already asking about pending work). Do not list the items unless the user asks; then run `bash .claude/skills/pending-work/scripts/pending.sh list` and show one line per item (number, priority, title). Call them "pending items"; the user does not want to deal with GitHub directly. To see details, add, change or close items, follow the pending-work skill (.claude/skills/pending-work/SKILL.md).'

fallback_list() {
  # Print the open items from the saved copy (and any items queued offline).
  local found=0
  if [ -f "$mirror" ]; then
    grep -E '^### #[0-9]+' "$mirror" | sed -E 's/^### //' && found=1
  fi
  if [ -f "$queue" ]; then
    grep -E '^### ' "$queue" | sed -E 's/^### /(not yet on GitHub) /' && found=1
  fi
  [ "$found" -eq 1 ]
}

# "N pending items (H high, M medium, L low)" from lines like "#12 [high] Title"
count_line() {
  awk '
    { n++; if (match($0, /\[[a-z-]+\]/)) p[substr($0, RSTART + 1, RLENGTH - 2)]++ }
    END {
      if (n == 0) { print "no pending items"; exit }
      s = n " pending item" (n == 1 ? "" : "s"); d = ""
      split("high medium low", order, " ")
      for (i = 1; i <= 3; i++) if (p[order[i]]) d = d (d ? ", " : "") p[order[i]] " " order[i]
      print s (d ? " (" d ")" : "")
    }'
}

cmd="${1:-list}"
case "$cmd" in

  session-start)
    lines="$(run_gh issue list --repo "$repo" --label pending-work --state open --limit 200 \
      --json number,title,labels --jq "$JQ_DEFS"' ordered | .[] | "#\(.number) [\(prio)] \(.title)"' 2>/dev/null)"
    status=$?
    source_note=""
    if [ $status -ne 0 ]; then
      lines="$(fallback_list 2>/dev/null || true)"
      if [ -n "$repo" ]; then
        source_note=" GitHub could not be reached, so the count comes from the saved copy ($MIRROR) and may be out of date."
      else
        source_note=" This project has no GitHub repository yet, so the count comes from $QUEUE."
      fi
    fi
    count="$(printf '%s\n' "$lines" | grep . | count_line)"
    if [ "$count" = "no pending items" ]; then
      user_msg="Pending work: nothing pending."
      context="Pending work for this project: no open items.$source_note If the user mentions something to do later, offer to add it as a pending item (pending-work skill)."
    else
      user_msg="Pending work: $count. Want to see them? Say \"list pending\"."
      context="PENDING WORK: this project has $count (GitHub issues labeled pending-work${repo:+ in $repo}).$source_note ${INSTRUCTIONS//COUNT/$count}"
    fi
    printf '{"systemMessage": %s, "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": %s}}\n' \
      "$(jq_lit "$user_msg")" "$(jq_lit "$context")"
    ;;

  list)
    out="$(run_gh issue list --repo "$repo" --label pending-work --state open --limit 200 \
      --json number,title,labels \
      --jq "$JQ_DEFS"' ordered | .[] | "#\(.number) [\(prio)] \(.title)  (\(cats))"' 2>/dev/null)"
    status=$?
    if [ $status -eq 0 ] && [ -n "$out" ]; then
      printf '%s\n' "$out"
    elif [ $status -eq 0 ]; then
      echo "No open pending-work items."
      [ -f "$queue" ] && grep -E '^### ' "$queue" | sed -E 's/^### /(not yet on GitHub) /'
    else
      if [ -n "$repo" ]; then echo "(GitHub unreachable - showing the saved copy in $MIRROR)"
      else echo "(no GitHub repository - showing the items queued in $QUEUE)"; fi
      fallback_list || echo "(no saved list found)"
    fi
    ;;

  export)
    body="$(run_gh issue list --repo "$repo" --label pending-work --state open --limit 200 \
      --json number,title,labels,body,createdAt,url \
      --jq "$JQ_DEFS"'
        "## Open items (\(length))\n\n" +
        (ordered | map("### #\(.number) [\(prio)] \(.title)\n\nCategory: \(cats) · Opened: \(.createdAt[0:10]) · \(.url)\n\n\(.body)\n\n---\n") | join("\n"))' 2>/dev/null)"
    if [ -z "$body" ]; then
      echo "export: could not read the issues from GitHub; $mirror was not changed." >&2
      exit 1
    fi
    mkdir -p "$(dirname "$mirror")"
    {
      echo "# Pending work"
      echo
      echo "<!-- Generated by .claude/skills/pending-work/scripts/pending.sh export on $(date '+%Y-%m-%d %H:%M')."
      echo "     Don't edit by hand. -->"
      echo
      echo "This is a copy of the open \"pending work\" items for this project. They are stored as"
      echo "GitHub issues labeled \`pending-work\` in the repository \`$repo\`, but you"
      echo "never need to use GitHub: just tell Claude Code, for example \"add a pending item: ...\","
      echo "\"list pending\", \"let's work on #12\", or \"#12 is no longer needed\"."
      echo "Claude Code shows how many items are open at the start of every session."
      echo
      printf '%s\n' "$body"
    } > "$mirror"
    echo "wrote $mirror"
    ;;

  setup-labels)
    if [ -z "$repo" ]; then echo "setup-labels: no GitHub repository (git remote origin)" >&2; exit 1; fi
    run_gh label create "pending-work" --repo "$repo" --color "FBCA04" --description "Work to do later (counted at the start of each Claude Code session)" --force
    for c in "${CATEGORIES[@]}"; do
      IFS='|' read -r name color desc <<< "$c"
      run_gh label create "$name" --repo "$repo" --color "$color" --description "$desc" --force
    done
    run_gh label create "priority: high"   --repo "$repo" --color "B60205" --description "Do soon" --force
    run_gh label create "priority: medium" --repo "$repo" --color "FBCA04" --description "Normal priority" --force
    run_gh label create "priority: low"    --repo "$repo" --color "C2E0C6" --description "When there's time" --force
    ;;

  *)
    echo "usage: bash pending.sh {session-start|list|export|setup-labels|--help}" >&2
    exit 2
    ;;
esac
