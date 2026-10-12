#!/usr/bin/env bash
# setup-computer.sh: set up a computer to use yrAiProjectTemplates. Run it once on each computer (it is safe to
# run again: it changes only what is missing).
#
# Usage: setup-computer.sh [--check]
#
# It makes sure that:
#   1. the Dropbox tools folder (the folder next to _yrAiCoding that holds yrNewAiProject.sh and agents-init.sh)
#      is on PATH. It only reports this: add the line that it prints to ~/.bashrc yourself;
#   2. ~/.claude/CLAUDE.md imports the shared rules, rules/AGENTS.md of this repository, so Claude Code follows
#      them in every project on this computer. It adds the import line, or creates the file.
#
#   --check      change nothing; report what is missing; exit 1 if something is missing
#   -h, --help   show this help and stop
#
# Other AI tools read their own global file. For example, for Codex: ln -s RULES ~/.codex/AGENTS.md (RULES is the
# path that this script prints).
set -euo pipefail
case "${1:-}" in -h|--help) sed -n '2,/^[^#]/{/^#/s/^# \{0,1\}//p}' "$0"; exit 0 ;; esac

check=0
[ "${1:-}" = "--check" ] && check=1
here="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
meta="$(cd "$here/.." && pwd)"
rules="$meta/rules/AGENTS.md"
tools="$(cd "$meta/../../tools" 2>/dev/null && pwd || true)"
missing=0

echo "shared rules: $rules"
if [ -z "$tools" ] || [ ! -f "$tools/yrNewAiProject.sh" ]; then
  echo "  ! the tools folder with yrNewAiProject.sh was not found next to _yrAiCoding"; missing=1
elif [[ ":$PATH:" != *":$tools:"* ]]; then
  echo "  ! $tools is not on PATH. Add this line to ~/.bashrc, then open a new terminal:"
  echo "      export PATH=\"\$PATH:$tools\""
  missing=1
else
  echo "  ok: $tools is on PATH (yrNewAiProject.sh, agents-init.sh)"
fi

if [[ "$rules" == "$HOME"/* ]]; then import="@~${rules#"$HOME"}"; else import="@$rules"; fi
claude="$HOME/.claude/CLAUDE.md"
if [ -f "$claude" ] && grep -qxF "$import" "$claude"; then
  echo "  ok: $claude imports the shared rules"
elif [ "$check" = 1 ]; then
  echo "  ! $claude does not import the shared rules (line: $import)"; missing=1
else
  mkdir -p "$HOME/.claude"
  if [ -f "$claude" ]; then
    printf '\nThe shared rules for every project (yrAiProjectTemplates):\n\n%s\n' "$import" >> "$claude"
    echo "  added the import line to $claude"
  else
    printf '# My instructions for Claude Code (all projects)\n\nThe shared rules for every project (yrAiProjectTemplates):\n\n%s\n\n## Claude Code only\n\n(Add rules here that apply only to Claude Code.)\n' "$import" > "$claude"
    echo "  created $claude"
  fi
fi
[ "$check" = 1 ] && [ "$missing" = 1 ] && exit 1
exit 0
