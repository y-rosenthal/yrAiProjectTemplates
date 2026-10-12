#!/usr/bin/env python3
"""agents-init: put the shared AI-agent rules into a project, so every collaborator's coding agent follows them.

Usage: agents-init.sh [DIR] [--check] [--pending-work]

agents-init.sh is the command in the Dropbox tools folder; it runs this file, bin/agents_init.py.

Copies the shared rules (everything from the first "## " heading of rules/AGENTS.md in yrAiProjectTemplates, the
repository that holds this script) into DIR/AGENTS.md,
between the lines <!-- begin shared rules --> and <!-- end shared rules -->:
  - no AGENTS.md: creates one with a title and the block;
  - an AGENTS.md without the block: adds the block at the end;
  - an AGENTS.md with the block: replaces the block (the project's own rules outside it are kept).
Then makes sure that Claude Code reads AGENTS.md: creates CLAUDE.md with the line "@AGENTS.md", or adds that line
at the top of an existing CLAUDE.md. Prints what it changed. Safe to run again: it changes only what is out of date.

  DIR             the project (default: the top of the current git repository, else the current directory)
  --check         change nothing; exit 1 if AGENTS.md or CLAUDE.md is out of date (or, with --pending-work, if the
                  pending-work skill or its hook is missing)
  --pending-work  also add the pending-work skill: things to do later are GitHub issues labeled pending-work, and a
                  SessionStart hook shows how many are open. Copies .claude/skills/pending-work/ from the newest
                  template version that has it, and adds the hook to .claude/settings.json (the file is created, or
                  the hook is added to the hooks that it has). A file that exists is never replaced: to get a newer
                  copy of a skill file, delete it and run again. Then, once, with a GitHub repository:
                  bash .claude/skills/pending-work/scripts/pending.sh setup-labels
  -h, --help      show this help and stop

Environment: AGENTS_SHARED_RULES=FILE uses FILE as the source instead of rules/AGENTS.md.
Stdlib only.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BEGIN = '<!-- begin shared rules: copied by agents-init from yrAiProjectTemplates/rules/AGENTS.md; edit there -->'
END = '<!-- end shared rules -->'
IMPORT = '@AGENTS.md'
RULES = Path(__file__).resolve().parents[1] / 'rules' / 'AGENTS.md'
TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'
PENDING = Path('.claude') / 'skills' / 'pending-work'
SETTINGS = Path('.claude') / 'settings.json'


def shared_block(source):
    text = source.read_text(encoding='utf-8')
    i = text.find('\n## ')
    if i < 0:
        sys.exit(f'agents-init: {source} has no "## " heading (nothing to share)')
    return f'{BEGIN}\n\n{text[i + 1:].strip()}\n\n{END}\n'


def project_dir(argv):
    args = [a for a in argv if not a.startswith('-')]
    if args:
        return Path(args[0]).resolve()
    r = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 else Path.cwd()


def new_agents_md(old, block, name):
    if old is None:
        return f'# Rules for AI coding agents ({name})\n\nProject rules go here. The shared rules below come from agents-init.\n\n{block}'
    m = re.search(r'^<!-- begin shared rules.*?^' + re.escape(END) + r'[ \t]*\n?', old, re.M | re.S)
    if m:
        return old[:m.start()] + block + old[m.end():]
    if re.search(r'^<!-- begin shared rules', old, re.M):
        sys.exit('agents-init: AGENTS.md has a begin marker but no end marker; fix it by hand')
    return old.rstrip('\n') + '\n\n' + block


def new_claude_md(old):
    if old is None:
        return f'{IMPORT}\n'
    if any(line.strip() == IMPORT for line in old.split('\n')):
        return old
    return f'{IMPORT}\n\n{old}'


def update(root, source=None, check=False, quiet=False):
    """Bring root/AGENTS.md and root/CLAUDE.md up to date (with check=True, change nothing).
    Returns the names of the files that were (or would be) changed. Used by yrNewAiProject."""
    block = shared_block(Path(source or os.environ.get('AGENTS_SHARED_RULES', RULES)))
    stale = []
    for name, make in (('AGENTS.md', lambda old: new_agents_md(old, block, root.name)), ('CLAUDE.md', new_claude_md)):
        path = root / name
        if path.is_symlink():
            print(f'  ! {path} is a symlink; replace it with a file that holds "{IMPORT}"' if name == 'CLAUDE.md'
                  else f'  ! {path} is a symlink; not changed')
            continue
        old = path.read_text(encoding='utf-8') if path.exists() else None
        new = make(old)
        if new == old:
            continue
        stale.append(name)
        if not check:
            path.write_text(new, encoding='utf-8')
            if not quiet:
                print(f'  {"created" if old is None else "updated"} {path}')
    return stale


def pending_source():
    """The shared/ folder of the newest template version that has the pending-work skill."""
    found = [v / 'shared' for v in TEMPLATES.glob('v*') if re.fullmatch(r'v\d+\.\d+\.\d+', v.name)
             and (v / 'shared' / PENDING).is_dir() and (v / 'shared' / SETTINGS).is_file()]
    if not found:
        sys.exit(f'agents-init: no template version in {TEMPLATES} has the pending-work skill')
    return max(found, key=lambda s: tuple(int(x) for x in s.parent.name[1:].split('.')))


def install_pending_work(root, check=False, quiet=False):
    """Add the pending-work skill and its SessionStart hook to root (with check=True, change nothing). Never
    replaces a file that exists. Returns the paths that were (or would be) added or changed."""
    shared = pending_source()
    changed = []
    for src in sorted((shared / PENDING).rglob('*')):
        rel = src.relative_to(shared)
        if not src.is_file() or '__pycache__' in rel.parts or (root / rel).exists():
            continue
        changed.append(str(rel))
        if not check:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, root / rel)
            shutil.copymode(src, root / rel)
    template = json.loads((shared / SETTINGS).read_text(encoding='utf-8'))
    path = root / SETTINGS
    existed = path.exists()
    if existed:
        try:
            settings = json.loads(path.read_text(encoding='utf-8'))
        except ValueError as e:
            sys.exit(f'agents-init: {path} is not valid JSON ({e}); fix it by hand, then run again')
    else:
        settings = {'$schema': template.get('$schema'), 'hooks': {}} if '$schema' in template else {'hooks': {}}
    hooks = settings.setdefault('hooks', {}) if isinstance(settings, dict) else None
    entries = hooks.setdefault('SessionStart', []) if isinstance(hooks, dict) else None
    if not isinstance(entries, list):
        sys.exit(f'agents-init: {path} has hooks in a form that agents-init does not know; add the hook by hand')
    if 'pending.sh' not in json.dumps(entries):
        changed.append(str(SETTINGS))
        if not check:
            entries.extend(template['hooks']['SessionStart'])
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')
    if not check and not quiet:
        for rel in changed:
            print(f'  {"updated" if rel == str(SETTINGS) and existed else "added"} {root / rel}')
    return changed


def main(argv):
    if '-h' in argv or '--help' in argv:
        print(__doc__)
        return 0
    check = '--check' in argv
    root = project_dir(argv)
    if not root.is_dir():
        sys.exit(f'agents-init: {root} is not a directory')
    stale = update(root, check=check)
    pending = install_pending_work(root, check=check) if '--pending-work' in argv else []
    if check:
        if pending:
            print(f'missing: {", ".join(pending)} (run agents-init.sh --pending-work)')
        print(f'out of date: {", ".join(stale)} (run agents-init.sh)' if stale else f'OK: {root} has the shared rules')
        return 1 if stale or pending else 0
    if not stale:
        print(f'OK: {root} already has the current shared rules')
    if '--pending-work' in argv:
        if pending:
            print('pending-work: added. Once, with a GitHub repository, make the labels:\n'
                  '  bash .claude/skills/pending-work/scripts/pending.sh setup-labels\n'
                  'Then commit the new files.')
        else:
            print('pending-work: already there (no file replaced)')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
