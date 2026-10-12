#!/usr/bin/env python3
"""yrAiProject: set up projects for AI-assisted work from the yrAiProjectTemplates templates, and keep them up to date.

Usage:
  yrAiProject.sh new PATH [--type work|book] [--title TEXT] [--description TEXT] [--version VER] [--github]
                          [--strict-empty] [--dry-run] [-y]
  yrAiProject.sh status [PATH]
  yrAiProject.sh update [PATH] [--with-docs] [--with-pending-work | --no-pending-work] [--version VER]
                          [--dry-run] [-y]
  yrAiProject.sh list
  yrAiProject.sh setup-computer [--check]
  yrAiProject.sh -h | --help

yrAiProject.sh is the command in the Dropbox tools folder; it runs this file, bin/yrAiProject.py of
yrAiProjectTemplates (python3 bin/yrAiProject.py works too). PATH is the project folder; for status and update the
default is the top of the current git repository, else the current folder.

Commands:
  new PATH        make a new project (a git repository) in PATH, which must not exist, or be empty, or hold only
                  .git. It gets every part (below) and the files of its type, with the project name, title,
                  description, type, date and version filled in; then git init (branch main) and a first commit.
                    --type TYPE         work (default) or book (also the main Quarto book at the root)
                    --title TEXT        the project title (default: the folder name)
                    --description TEXT  one sentence that says what the project is for (default: a TODO line)
                    --version VER       the template version, for example v0.3.0 (default: the newest)
                    --github            also make a private GitHub repository with the folder name (gh command),
                                        push the first commit, and make the labels of the pending-work skill
                    --strict-empty      refuse a folder that holds anything, even only .git
  status [PATH]   show the state of a project: never set up, partly set up (no record of a version), set up with
                  an older version, or up to date; and, for each part, what update would add or change, and the
                  files that were changed by hand (update leaves those alone). Changes nothing. Exit 0 if update
                  has nothing to do, else 1
  update [PATH]   set up an existing folder, or bring a project up to date with the newest template version. It
                  adds the parts that are missing, replaces the tool files that it installed and that nobody
                  changed, and never touches a file that was changed by hand. It makes no commit.
                    --with-docs          also add the docs part (default: only if the project has it)
                    --no-pending-work    don't add the pending-work part (remembered for later updates)
                    --with-pending-work  add the pending-work part after an earlier --no-pending-work
                    --version VER        the template version (default: the newest)
  list            list the template versions (newest first) and their project types
  setup-computer  set up this computer (once; safe to repeat): checks that the Dropbox tools folder is on PATH
                  (it only reports this), and makes ~/.claude/CLAUDE.md import the shared rules, so that Claude
                  Code follows them in every project. --check: change nothing; exit 1 if something is missing

Options of new and update:
  --dry-run       show what would be done, then stop; change nothing
  -y, --yes       don't ask for confirmation. Without -y, new and update show what they would do, with a diff of
                  each file that they would change, and ask "Apply these changes? [y/N]". With no terminal to
                  ask in (a script, an AI agent) and no -y, they change nothing and exit with status 6

The parts of a project:
  rules         AGENTS.md with a copy of the shared rules (rules/AGENTS.md, between <!-- begin shared rules -->
                and <!-- end shared rules -->; the project's own rules are kept), and CLAUDE.md that imports it
                (the line @AGENTS.md). Every project
  pending-work  the pending-work skill (.claude/skills/pending-work/): things to do later are GitHub issues, and
                a SessionStart hook in .claude/settings.json shows how many are open. Default: yes
  docs          the project-docs Quarto book in docs/ (SPECs, guides, plans) and the new-doc skill. New projects
                always; existing folders only with --with-docs
New projects also get README.md, .gitignore and, for a book, the main Quarto book.

The record: .yrAiProject/manifest.json holds the version, the parts, the filled-in values, a fingerprint
(SHA-256) of each file as it was installed, and the history of the runs. That is how update knows that a file was
not changed by hand.

How a project shows that yrAiProject set it up (new and update write all of these):
  .yrAiProject/README.md          for people and agents: the version, the parts, each installed file and who
                                  changes it, the commands, and the history
  .yrAiProject/session-start.json the one-line notice that a SessionStart hook in .claude/settings.json shows at
                                  the start of each Claude Code session
  AGENTS.md                       the block "yrAiProject setup" near the top (every AI agent reads it)
  README.md                       the block "yrAiProject setup" at the end, if the project has a README
  docs/PROJECT-SETUP.qmd          (docs part) a chapter of the docs book that shows .yrAiProject/README.md

Exit status: 0 OK (done, nothing to do, or --dry-run); 1 status found something to do, or the answer was no;
2 bad options, a missing template or a missing tool; 3 new: PATH is not empty; 5 git or gh failed;
6 confirmation needed, but there is no terminal (use -y or --dry-run).

Replaces yrNewAiProject.sh and agents-init.sh (they are now stubs that print the new command) and
bin/setup-computer.sh. No longer supported: template v0.0.1 (type generic), the manifests of the retired
yraiproject tool and of yrNewAiProject (.yrAiProjectTemplate/), --add-to-existing (use update), --verify (use
status) and --meta-repo. The full description: docs/USER-GUIDE-v001.qmd and docs/SPEC-v0.4.0.qmd in
yrAiProjectTemplates. Python 3.8 or later, standard library only; Linux, and Git Bash on Windows.
"""
import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

META = Path(__file__).resolve().parents[1]
TOOL_VERSION = '0.4.0'
REPO_URL = 'https://github.com/y-rosenthal/yrAiProjectTemplates'
SKIP_NAMES = {'.git', '__pycache__', '.quarto', '_book', '.DS_Store'}
MANIFEST = Path('.yrAiProject') / 'manifest.json'
ABOUT = Path('.yrAiProject') / 'README.md'
NOTICE = Path('.yrAiProject') / 'session-start.json'
SETUP_BEGIN = '<!-- begin yrAiProject setup: written by yrAiProject.sh; "yrAiProject.sh update" replaces this block -->'
SETUP_END = '<!-- end yrAiProject setup -->'
SETUP_BLOCK = re.compile(r'^<!-- begin yrAiProject setup.*?^' + re.escape(SETUP_END) + r'[ \t]*\n?', re.M | re.S)
DOCS_TOC = 'docs/_quarto.yml'
SETUP_PAGE = 'PROJECT-SETUP.qmd'
OLD_MANIFEST = Path('.yrAiProjectTemplate') / 'manifest.json'
RULES = META / 'rules' / 'AGENTS.md'
BEGIN = '<!-- begin shared rules: copied by yrAiProject from yrAiProjectTemplates/rules/AGENTS.md; edit there -->'
END = '<!-- end shared rules -->'
BLOCK = re.compile(r'^<!-- begin shared rules.*?^' + re.escape(END) + r'[ \t]*\n?', re.M | re.S)
IMPORT = '@AGENTS.md'
SETTINGS = '.claude/settings.json'
SPECIAL = {'AGENTS.md', 'CLAUDE.md', SETTINGS}      # merged into the project's file, not copied
PENDING_SCRIPT = '.claude/skills/pending-work/scripts/pending.sh'
SCALAR = re.compile(r'\{\{YRAI:([A-Z][A-Z0-9_]*)\}\}')
PARTS = ('rules', 'pending-work', 'docs')


class Fail(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


# ---- templates -------------------------------------------------------------------------------------------------

def version_key(name):
    return tuple(int(x) for x in name[1:].split('.'))


def template_versions():
    root = META / 'templates'
    found = [p.name for p in root.iterdir() if p.is_dir() and re.fullmatch(r'v\d+\.\d+\.\d+', p.name)] \
        if root.is_dir() else []
    return sorted(found, key=version_key, reverse=True)


def pick_version(requested):
    versions = template_versions()
    if not versions:
        raise Fail(2, f'no templates in {META / "templates"}')
    version = requested or versions[0]
    version = version if version.startswith('v') else 'v' + version
    if version not in versions:
        raise Fail(2, f'no template version {version}; versions: {", ".join(versions)}')
    return version


def project_types(version):
    return sorted(p.name for p in (META / 'templates' / version).iterdir() if p.is_dir() and p.name != 'shared')


def template_files(version, ptype=None):
    """{relative path (posix): source file}: the shared files, then the type's files (they win on the same path).
    Without a type, only the shared files (what update installs)."""
    vdir = META / 'templates' / version
    if ptype and not (vdir / ptype).is_dir():
        raise Fail(2, f'no project type {ptype!r} in {version}; types: {", ".join(project_types(version))}')
    files = {}
    for part in ['shared'] + ([ptype] if ptype else []):
        base = vdir / part
        for src in sorted(base.rglob('*')) if base.is_dir() else []:
            rel = src.relative_to(base)
            if src.is_file() and not SKIP_NAMES.intersection(rel.parts):
                files[rel.as_posix()] = src
    return files


def part_of(rel):
    if rel in ('AGENTS.md', 'CLAUDE.md'):
        return 'rules'
    if rel == SETTINGS or rel.startswith('.claude/skills/pending-work/'):
        return 'pending-work'
    if rel.startswith('docs/') or rel.startswith('.claude/skills/new-doc/'):
        return 'docs'
    return 'base'


def is_tool_file(rel):
    """A file that update keeps up to date (unless it was changed by hand). The other files (README, the SPEC, the
    _quarto.yml, ...) are starting points that the project owns: update adds them once, then leaves them."""
    return rel.startswith('.claude/skills/') or rel == 'docs/' + SETUP_PAGE or \
        bool(re.fullmatch(r'docs/[A-Z][A-Z-]*-GUIDE-v\d+\.qmd', rel))


def fill(text, values, yaml=False):
    def value(m):
        v = values.get(m.group(1))
        if v is None:
            return m.group(0)
        return v.replace('\\', '\\\\').replace('"', '\\"') if yaml else v
    return SCALAR.sub(value, text)


def fill_file(text, values, suffix):
    """The text of a template file with its values filled in. In YAML (.yml files, and the front matter of .qmd and
    .md files) a value is escaped for a double-quoted string: the templates put every value in double quotes there."""
    if suffix in ('.yml', '.yaml'):
        return fill(text, values, yaml=True)
    if suffix in ('.qmd', '.md', '.Rmd') and text.startswith('---\n'):
        end = text.find('\n---', 4)
        if end > 0:
            return fill(text[:end], values, yaml=True) + fill(text[end:], values)
    return fill(text, values)


def template_text(src, values):
    return fill_file(src.read_bytes().decode('utf-8').replace('\r\n', '\n'), values, src.suffix)


def read(path):
    """The text of a file (line ends \\n), or None if it does not exist."""
    if not path.is_file():
        return None
    return path.read_bytes().decode('utf-8', errors='replace').replace('\r\n', '\n')


def digest(text):
    return hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()


# ---- the special files: AGENTS.md, CLAUDE.md, .claude/settings.json -------------------------------------------

def shared_block():
    source = Path(os.environ.get('AGENTS_SHARED_RULES', RULES))
    text = source.read_text(encoding='utf-8')
    i = text.find('\n## ')
    if i < 0:
        raise Fail(2, f'{source} has no "## " heading (nothing to share)')
    return f'{BEGIN}\n\n{text[i + 1:].strip()}\n\n{END}\n'


def parts_text(parts):
    return ', '.join(p for p in PARTS if p in parts)


def setup_block_agents(version, parts):
    """The block "yrAiProject setup" of AGENTS.md: every AI agent reads it."""
    return f'''{SETUP_BEGIN}
## Set up by yrAiProject.sh

`yrAiProject.sh` (yrAiProjectTemplates {version}; parts: {parts_text(parts)}) set up this project. It installed
files here, and `yrAiProject.sh update` keeps them up to date.

- Before you change a file that it installed, read `.yrAiProject/README.md`. It lists the files, and tells who
  changes each one.
- Do not edit this block, the shared-rules block, or the files in `.yrAiProject/`. `yrAiProject.sh update`
  writes them again.
- At the start of a session, tell the user in one line that `yrAiProject.sh` set up this project, unless a
  SessionStart message already told them.
{SETUP_END}
'''


def setup_block_readme(version, parts):
    """The block "yrAiProject setup" at the end of README.md: for people."""
    return f'''{SETUP_BEGIN}
*Set up by `yrAiProject.sh` (yrAiProjectTemplates {version}; parts: {parts_text(parts)}). It installed the rules
for AI agents, the skills and the settings, and it updates them. Before you change them, read
`.yrAiProject/README.md`.*
{SETUP_END}
'''


def put_setup_block(old, block, where):
    """old with block replaced, or put in: 'top' (after the # title line) or 'end'."""
    m = SETUP_BLOCK.search(old)
    if m:
        return old[:m.start()] + block + old[m.end():]
    if re.search(r'^<!-- begin yrAiProject setup', old, re.M):
        raise Fail(2, 'a file has a "begin yrAiProject setup" line but no "end yrAiProject setup" line; fix it by hand')
    if where == 'end':
        return old.rstrip('\n') + '\n\n' + block
    lines = old.split('\n')
    if lines and lines[0].startswith('# '):
        return lines[0] + '\n\n' + block + '\n' + '\n'.join(lines[1:]).lstrip('\n')
    return block + '\n' + old


def new_agents_md(old, name, version, parts):
    block = shared_block()
    setup = setup_block_agents(version, parts)
    if old is None:
        return (f'# Rules for AI coding agents ({name})\n\n{setup}\nProject rules go here. The shared rules below come '
                f'from yrAiProject.\n\n{block}')
    m = BLOCK.search(old)
    if m:
        old = old[:m.start()] + block + old[m.end():]
    elif re.search(r'^<!-- begin shared rules', old, re.M):
        raise Fail(2, 'AGENTS.md has a "begin shared rules" line but no "end shared rules" line; fix it by hand')
    else:
        old = old.rstrip('\n') + '\n\n' + block
    return put_setup_block(old, setup, 'top')


def new_readme(old, version, parts):
    return None if old is None else put_setup_block(old, setup_block_readme(version, parts), 'end')


def new_docs_toc(old):
    """docs/_quarto.yml with the setup page after index.qmd; old if it lists the page; None if there is no place."""
    if SETUP_PAGE in old:
        return old
    m = re.search(r'^([ \t]*)- index\.qmd[ \t]*\n', old, re.M)
    if not m:
        return None
    return old[:m.end()] + f'{m.group(1)}- {SETUP_PAGE}\n' + old[m.end():]


def new_claude_md(old):
    if old is None:
        return f'{IMPORT}\n'
    if any(line.strip() == IMPORT for line in old.split('\n')):
        return old
    return f'{IMPORT}\n\n{old}'


def hook_part(entry):
    """The part of a SessionStart entry of the template: the setup notice (rules) or the pending count."""
    text = json.dumps(entry)
    return 'pending-work' if 'pending.sh' in text else 'rules' if NOTICE.name in text else None


def new_settings(old, template, parts):
    """(settings.json with the template's SessionStart hooks of these parts added, the parts whose hooks were added).
    A hook that the project has already (its script name is in an entry) is not added again. (None, set()) if old is
    not JSON that this tool understands."""
    tmpl = json.loads(template)
    if old is None:
        settings = {'$schema': tmpl['$schema']} if '$schema' in tmpl else {}
    else:
        try:
            settings = json.loads(old)
        except ValueError:
            return None, set()
    hooks = settings.setdefault('hooks', {}) if isinstance(settings, dict) else None
    entries = hooks.setdefault('SessionStart', []) if isinstance(hooks, dict) else None
    if not isinstance(entries, list):
        return None, set()
    added = set()
    for entry in tmpl['hooks']['SessionStart']:
        part = hook_part(entry)
        key = 'pending.sh' if part == 'pending-work' else NOTICE.name
        if part in parts and key not in json.dumps(entries):
            if part == 'rules':
                entries.insert(0, entry)
            else:
                entries.append(entry)
            added.add(part)
    if not added:
        return old, added
    return json.dumps(settings, indent=2) + '\n', added


# ---- the files about the setup: .yrAiProject/README.md and session-start.json ------------------------------------

def about_text(target, m):
    """.yrAiProject/README.md: what yrAiProject installed in the project, and who changes each file."""
    version, parts, files = m.get('version'), m.get('parts', []), m.get('files', {})
    made = f'`yrAiProject.sh new` (a new {m["projectType"]} project)' if m.get('projectType') else \
        '`yrAiProject.sh update` (an existing folder)'
    rows = [('AGENTS.md', 'rules', 'You: the project rules. The tool: only its two blocks, "yrAiProject setup" and '
             '"shared rules"'),
            ('CLAUDE.md', 'rules', 'You. The tool only keeps the line `@AGENTS.md`')]
    if (target / SETTINGS).is_file():
        rows.append((SETTINGS, 'rules' + (', pending-work' if 'pending-work' in parts else ''),
                     'You. The tool only adds its SessionStart hooks'))
    if (target / 'README.md').is_file():
        rows.append(('README.md', '', 'You. The tool only writes its block "yrAiProject setup" at the end'))
    for rel in sorted(files):
        if rel in SPECIAL or rel == 'README.md':
            continue
        if is_tool_file(rel):
            who = 'The tool: `update` replaces it with each new version. If you change it, `update` leaves it alone'
        elif rel == DOCS_TOC:
            who = f'You. The tool only adds the line `{SETUP_PAGE}` if it is missing'
        else:
            who = 'You. The tool added it once, and does not change it'
        rows.append((rel, part_of(rel).replace('base', ''), who))
    rows.append(('.yrAiProject/', '', 'The tool only: `manifest.json` (the record), `README.md` (this page), '
                 '`session-start.json` (the notice). Do not edit'))
    about_parts = {
        'rules': 'the rules for every AI agent: `AGENTS.md`, with a copy of the shared rules (their source is '
                 '`rules/AGENTS.md` in yrAiProjectTemplates), and `CLAUDE.md`, which imports it. A SessionStart hook '
                 'shows a one-line notice about this setup at the start of each Claude Code session.',
        'pending-work': 'work to do later is GitHub issues with the label `pending-work`. The `pending-work` skill '
                        'manages them, and a SessionStart hook shows how many are open.',
        'docs': 'the project-docs Quarto book in `docs/` (SPECs, guides, plans), and the `new-doc` skill, which adds '
                'a document.',
    }
    history = m.get('history') or []
    out = [
        '<!-- Written by yrAiProject.sh. Do not edit: "yrAiProject.sh update" writes this file again. No "#" title:',
        f'docs/{SETUP_PAGE} includes this file, and gives the title. -->', '',
        f'**Project setup by yrAiProject.sh.** `yrAiProject.sh`, the tool of yrAiProjectTemplates ({REPO_URL}), set up '
        'this project. It installed the '
        'files below, and `yrAiProject.sh update` keeps them up to date. Read this page before you change one of them.',
        '',
        '| | |', '|---|---|',
        f'| Template version | {version} |',
        f'| Parts | {parts_text(parts)} |',
        f'| Set up by | {made} |',
        f'| Last change | {(m.get("updatedAt") or m.get("createdAt") or "")[:10]} |', '',
        '## The parts', '',
    ]
    out += [f'- **{p}**: {about_parts[p]}' for p in PARTS if p in parts]
    out += ['', '## The files', '', '| File | Part | Who changes it |', '|---|---|---|']
    out += [f'| `{rel}` | {part} | {who} |' for rel, part, who in rows]
    out += [
        '', '## How to change things', '',
        '- **Project rules:** edit `AGENTS.md`, outside the two blocks of the tool.',
        '- **Shared rules:** edit `rules/AGENTS.md` in yrAiProjectTemplates and commit it. Then run '
        '`yrAiProject.sh update` in this project.',
        '- **A file of the tool** (a skill, a guide): you can change it. Then `update` leaves it alone, and the file '
        'gets no newer versions. `yrAiProject.sh status` lists such files.',
        '- **Without `yrAiProject.sh`** (for example, a collaborator): all these files are ordinary files. Change the '
        'files of the tool only if you must, and tell the project owner.',
        '', '## Commands', '',
        '```bash',
        'yrAiProject.sh status             # is the project up to date? which files were changed by hand?',
        'yrAiProject.sh update --dry-run   # what update would change (changes nothing)',
        'yrAiProject.sh update             # update the project (shows the changes, then asks)',
        '```', '',
        '`yrAiProject.sh` is in the Dropbox tools folder of the project owner. `yrAiProject.sh --help` explains it.',
        '', '## History', '',
        '| Date | Command | Template | Parts |', '|---|---|---|---|',
    ]
    out += [f'| {h.get("date", "")} | {h.get("command", "")} | {h.get("version") or ""} | '
            f'{parts_text(h.get("parts") or [])} |' for h in history]
    return '\n'.join(out) + '\n'


def notice_text(m):
    """.yrAiProject/session-start.json: the output of the SessionStart hook of the rules part."""
    what = f'yrAiProjectTemplates {m.get("version")}; parts: {parts_text(m.get("parts", []))}'
    user = f'Set up by yrAiProject.sh ({what}). Before you change its files, read .yrAiProject/README.md.'
    context = (f'This project was set up by yrAiProject.sh ({what}); the user saw a one-line notice about it. '
               '.yrAiProject/README.md lists the files that the tool installed, and tells who changes each one. Read '
               'it before you change AGENTS.md, CLAUDE.md, .claude/settings.json, a file in .claude/skills/, or the '
               'docs guides. Do not edit the tool\'s blocks in AGENTS.md and README.md, or the files in .yrAiProject/: '
               '"yrAiProject.sh update" writes them again. "yrAiProject.sh status" shows whether the project is up to '
               'date.')
    return json.dumps({'systemMessage': user, 'hookSpecificOutput': {'hookEventName': 'SessionStart',
                                                                      'additionalContext': context}}, indent=2) + '\n'


def with_history(m, command):
    """The record m with one more history entry (and, for a record from before v0.4.0, an entry for its setup)."""
    history = list(m.get('history') or [])
    if 'history' not in m and m.get('createdAt'):
        history.append({'date': m['createdAt'][:10], 'command': 'set up (no history before v0.4.0)',
                        'version': None, 'parts': []})
    history.append({'date': datetime.date.today().isoformat(), 'command': command, 'version': m.get('version'),
                    'parts': list(m.get('parts', []))})
    return dict(m, history=history)


def write_record(target, m):
    """Write the record and the two files about the setup that come from it."""
    save_manifest(target, m)
    write(target, ABOUT.as_posix(), about_text(target, m))
    write(target, NOTICE.as_posix(), notice_text(m))


# ---- the state of a project ------------------------------------------------------------------------------------

class Action:
    """One file: add, change, keep (left alone, with a reason) or ok (up to date)."""
    def __init__(self, kind, rel, part, new=None, old=None, src=None, note=''):
        self.kind, self.rel, self.part, self.new, self.old, self.src, self.note = kind, rel, part, new, old, src, note


def load_manifest(target):
    path = target / MANIFEST
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except ValueError:
        raise Fail(2, f'{path} is not valid JSON; fix it by hand, or delete it (then update treats the project as '
                      'never recorded)')


def detect_parts(target):
    """The parts that a project without a record has (for example from the old agents-init tool, or by hand)."""
    found = set()
    agents = read(target / 'AGENTS.md')
    if agents and BLOCK.search(agents):
        found.add('rules')
    settings = read(target / SETTINGS) or ''
    if (target / '.claude/skills/pending-work/SKILL.md').is_file() or 'pending.sh' in settings:
        found.add('pending-work')
    if (target / 'docs/_quarto.yml').is_file() and (target / '.claude/skills/new-doc/SKILL.md').is_file():
        found.add('docs')
    return found


def project_values(target, manifest, args=None):
    old = (manifest or {}).get('values', {})
    title = getattr(args, 'title', None)
    description = getattr(args, 'description', None)
    return {
        'PROJECT_NAME': target.name,
        'PROJECT_TITLE': title or old.get('PROJECT_TITLE') or target.name,
        'PROJECT_DESCRIPTION': description or old.get('PROJECT_DESCRIPTION') or
        'TODO: one sentence that says what this project is for.',
        'PROJECT_TYPE': (manifest or {}).get('projectType') or getattr(args, 'type', None) or 'work',
        'CREATED_DATE': old.get('CREATED_DATE') or datetime.date.today().isoformat(),
        'TEMPLATE_VERSION': '',          # filled in by the caller
    }


class State:
    """What update would do in target (and what status reports)."""

    def __init__(self, target, args):
        self.target = target
        self.manifest = load_manifest(target)
        self.has_old_manifest = (target / OLD_MANIFEST).is_file()
        self.installed = set(self.manifest.get('parts', [])) if self.manifest else detect_parts(target)
        self.skipped = set(self.manifest.get('skippedParts', [])) if self.manifest else set()
        self.newest = pick_version(None)
        self.version = pick_version(getattr(args, 'version', None))
        self.parts = set(self.installed) | {'rules'}
        if getattr(args, 'no_pending_work', False):
            self.parts.discard('pending-work')
            if 'pending-work' not in self.installed:
                self.skipped.add('pending-work')
        elif getattr(args, 'with_pending_work', False) or 'pending-work' not in self.skipped:
            self.parts.add('pending-work')
            self.skipped.discard('pending-work')
        if getattr(args, 'with_docs', False):
            self.parts.add('docs')
        self.values = project_values(target, self.manifest, args)
        self.values['TEMPLATE_VERSION'] = self.version
        self.notes = []
        self.actions = self.plan()

    def plan(self):
        target, recorded = self.target, (self.manifest or {}).get('files', {})
        files = template_files(self.version)
        if 'docs' in self.parts and 'docs' not in self.installed and (target / 'docs/_quarto.yml').exists() \
                and 'docs/_quarto.yml' not in recorded:
            self.parts.discard('docs')
            self.notes.append('docs: docs/_quarto.yml exists already and is not from yrAiProject, so the docs part '
                              'is not added')
        for part in sorted(self.parts):
            if part != 'rules' and not any(part_of(rel) == part for rel in files):
                self.parts.discard(part)
                self.notes.append(f'{part}: template {self.version} does not have this part')
        actions = []
        for rel, src in files.items():
            part = part_of(rel)
            if part not in self.parts or rel in SPECIAL:
                continue
            new = template_text(src, self.values)
            cur = read(target / rel)
            if is_tool_file(rel):
                if cur is None:
                    actions.append(Action('add', rel, part, new, src=src,
                                          note='it was missing' if rel in recorded else ''))
                elif cur == new:
                    actions.append(Action('ok', rel, part, new))
                elif recorded.get(rel) == digest(cur):
                    actions.append(Action('change', rel, part, new, cur, src=src, note='a newer version'))
                else:
                    actions.append(Action('keep', rel, part, note='differs from the template, and was changed here '
                                          'or not installed by yrAiProject: left alone'))
            elif cur is None and rel not in recorded:
                if '{{< include ../README.md >}}' in new and not (target / 'README.md').is_file():
                    new = new.replace("The text below is the\nproject's `README.md`.", 'The project has no '
                                      '`README.md`.').replace('{{< include ../README.md >}}', '').rstrip('\n') + '\n'
                    note = 'without the README, which the project does not have'
                else:
                    note = ''
                actions.append(Action('add', rel, part, new, src=src, note=note))
        parts = self.installed | self.parts
        merged = (('AGENTS.md', lambda old: new_agents_md(old, target.name, self.version, parts),
                   'the setup notice and the shared rules'),
                  ('CLAUDE.md', new_claude_md, 'imports AGENTS.md'),
                  ('README.md', lambda old: new_readme(old, self.version, parts), 'the setup notice at the end'))
        for rel, make, note in merged:
            if (target / rel).is_symlink():
                actions.append(Action('keep', rel, 'rules', note='a symlink: replace it with a file'))
                continue
            old = read(target / rel)
            new = make(old)
            if new is not None:
                actions.append(Action('ok' if new == old else ('add' if old is None else 'change'), rel, 'rules',
                                      new, old, note=note))
        if SETTINGS in files:
            old = read(target / SETTINGS)
            new, added = new_settings(old, template_text(files[SETTINGS], self.values), self.parts)
            part = 'pending-work' if 'pending-work' in added else 'rules'
            if new is None:
                actions.append(Action('keep', SETTINGS, part, note='not JSON that yrAiProject understands: add the '
                                      'SessionStart hooks by hand (see the template)'))
            else:
                actions.append(Action('ok' if new == old else ('add' if old is None else 'change'), SETTINGS, part,
                                      new, old, note='the SessionStart hook' + ('s' if len(added) > 1 else '')))
        cur = read(target / DOCS_TOC)
        if 'docs' in self.parts and 'docs/' + SETUP_PAGE in files and cur is not None:
            new = new_docs_toc(cur)
            if new is None:
                self.notes.append(f'docs: add the line "- {SETUP_PAGE}" to the chapters in {DOCS_TOC} by hand')
            elif new != cur:
                actions.append(Action('change', DOCS_TOC, 'docs', new, cur, note=f'lists {SETUP_PAGE}'))
        return actions

    def about_current(self):
        """Whether .yrAiProject/README.md and session-start.json are what the current record makes."""
        m = self.manifest
        return m is not None and read(self.target / ABOUT) == about_text(self.target, m) \
            and read(self.target / NOTICE) == notice_text(m)

    def changes(self):
        return [a for a in self.actions if a.kind in ('add', 'change')]

    def record_changes(self):
        """Whether the record (.yrAiProject/manifest.json) must be written."""
        m = self.manifest
        return bool(self.changes()) or m is None or not self.about_current() or m.get('version') != self.version \
            or set(m.get('parts', [])) != self.installed | self.parts or set(m.get('skippedParts', [])) != self.skipped

    def describe(self):
        m, t = self.manifest, self.target
        print(f'{t}')
        if m:
            when = (m.get('updatedAt') or m.get('createdAt') or '')[:10]
            print(f'  set up with yrAiProject, template {m.get("version")} ({when})' +
                  ('' if m.get('version') == self.newest else f'; the newest version is {self.newest}'))
        elif self.installed:
            print('  partly set up: it has ' + ', '.join(sorted(self.installed)) + ', but no record of a version '
                  '(set up by hand, or with the old agents-init tool)')
        else:
            print('  not set up with yrAiProject')
        if self.has_old_manifest:
            print(f'  note: {OLD_MANIFEST} is a record of the retired yrNewAiProject tool; it is no longer read')
        for part in PARTS:
            acts = [a for a in self.actions if a.part == part]
            add = sum(a.kind == 'add' for a in acts)
            change = sum(a.kind == 'change' for a in acts)
            keep = [a for a in acts if a.kind == 'keep']
            if part not in self.parts:
                text = 'installed; not updated this time' if part in self.installed else \
                    'not installed (you chose --no-pending-work; update --with-pending-work adds it)' \
                    if part in self.skipped else 'not installed (optional: update --with-docs)' if part == 'docs' \
                    else 'not installed'
            elif part not in self.installed:
                text = f'not installed: update adds it ({add + change} file(s))'
            elif add or change:
                text = 'out of date: update would ' + ' and '.join(
                    x for x in (f'add {add}' if add else '', f'change {change}' if change else '') if x) + ' file(s)'
            else:
                text = 'up to date'
            if keep:
                text += f'; {len(keep)} file(s) changed by hand (left alone)'
            print(f'  {part:<13} {text}')
        if m and not self.about_current():
            print(f'  setup notice  out of date or missing: update writes {ABOUT.as_posix()} and {NOTICE.name}')
        elif m:
            print(f'  about this setup: {ABOUT.as_posix()}')
        for n in self.notes:
            print(f'  note: {n}')


def show_diff(a):
    old = a.old or ''
    lines = difflib.unified_diff(old.splitlines(keepends=True), a.new.splitlines(keepends=True),
                                 '/dev/null' if a.old is None else 'a/' + a.rel, 'b/' + a.rel)
    for line in lines:
        print('    ' + line.rstrip('\n'))


def ask(args, question='Apply these changes?'):
    if args.yes:
        return True
    sys.stdout.flush()
    if not sys.stdin.isatty():
        raise Fail(6, 'this needs your confirmation, but there is no terminal to ask in. Nothing was changed. '
                      'Run again with -y to apply the changes, or with --dry-run to only see them')
    try:
        answer = input(f'{question} [y/N] ')
    except EOFError:
        answer = ''
    return answer.strip().lower() in ('y', 'yes')


def git(target, *cmd):
    r = subprocess.run(['git', '-C', str(target), *cmd], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def write(target, rel, text, src=None):
    dest = target / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(text.encode('utf-8'))
    if src is not None:
        shutil.copymode(src, dest)


def save_manifest(target, manifest):
    write(target, MANIFEST.as_posix(), json.dumps(manifest, indent=2) + '\n')


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def templates_commit():
    code, out = git(META, 'rev-parse', '--short', 'HEAD')
    return out if code == 0 else None


# ---- the commands ----------------------------------------------------------------------------------------------

def project_dir(path):
    if path:
        return Path(path).expanduser().resolve()
    code, out = git(Path.cwd(), 'rev-parse', '--show-toplevel')
    return Path(out) if code == 0 else Path.cwd()


def cmd_status(args):
    target = project_dir(args.path)
    if not target.is_dir():
        raise Fail(2, f'{target} is not a folder')
    state = State(target, args)
    state.describe()
    if state.changes() or state.record_changes():
        print('Run "yrAiProject.sh update" to see the changes (with diffs) and apply them.')
        return 1
    return 0


def cmd_update(args):
    target = project_dir(args.path)
    if not target.is_dir():
        raise Fail(2, f'{target} is not a folder; to make a new project: yrAiProject.sh new PATH')
    if args.no_pending_work and args.with_pending_work:
        raise Fail(2, 'use --with-pending-work or --no-pending-work, not both')
    state = State(target, args)
    state.describe()
    print()
    changes = state.changes()
    keeps = [a for a in state.actions if a.kind == 'keep']
    if not state.record_changes():
        print('Nothing to do: the project is up to date.')
        for a in keeps:
            print(f'  = {a.rel}: {a.note}')
        return 0
    print(f'What "update" would do (template {state.version}):')
    for a in changes:
        print(f'  {"+ add   " if a.kind == "add" else "~ change"} {a.rel}' + (f'  ({a.note})' if a.note else ''))
    for rel, what in ((MANIFEST, 'the record of this setup'), (ABOUT, 'about this setup, for people and agents'),
                      (NOTICE, 'the notice at the start of a Claude Code session')):
        print(f'  {"~ change" if (target / rel).is_file() else "+ add   "} {rel.as_posix()}  ({what})')
    for a in keeps:
        print(f'  = keep   {a.rel}: {a.note}')
    shown = [a for a in changes if a.rel in SPECIAL or a.kind == 'change']
    if shown:
        print('\nThe changes, line by line (+ added, - removed):')
        for a in shown:
            print(f'  {a.rel}:')
            show_diff(a)
    print()
    code, _ = git(target, 'rev-parse', '--is-inside-work-tree')
    if code:
        print('! This folder is not a git repository: git cannot undo these changes.')
    else:
        code, out = git(target, 'status', '--porcelain', '--', *[a.rel for a in changes if a.kind == 'change'])
        if out and changes:
            print('! These files have uncommitted changes (commit them first, so that you can undo the update):')
            print('    ' + out.replace('\n', '\n    '))
    if args.dry_run:
        print('--dry-run: nothing was changed.')
        return 0
    if not ask(args):
        print('Nothing was changed.')
        return 1
    for a in changes:
        write(target, a.rel, a.new, a.src)
    m = state.manifest or {'schemaVersion': 3, 'createdAt': now(), 'projectType': None, 'history': []}
    files = dict(m.get('files', {}))
    for a in state.actions:
        if a.kind in ('add', 'change', 'ok') and a.rel not in SPECIAL:
            files[a.rel] = digest(a.new)
    m.update({
        'schemaVersion': 3,
        'version': state.version,
        'parts': sorted(state.installed | state.parts),
        'skippedParts': sorted(state.skipped),
        'values': state.values,
        'files': dict(sorted(files.items())),
        'updatedAt': now(),
        'tool': {'name': 'yrAiProject', 'version': TOOL_VERSION, 'templatesCommit': templates_commit()},
    })
    write_record(target, with_history(m, 'update'))
    print(f'Done: {len(changes)} file(s) added or changed, and the record written. Nothing was committed:')
    print('look at the changes (git status, git diff), then commit them.')
    print(f'What yrAiProject installed, and who changes each file: {ABOUT.as_posix()}')
    if 'pending-work' in state.parts and 'pending-work' not in state.installed:
        print(f'For pending work, once, with a GitHub repository: bash {PENDING_SCRIPT} setup-labels')
    return 0


def cmd_new(args):
    if not args.path:
        raise Fail(2, 'give the folder of the new project: yrAiProject.sh new PATH')
    target = Path(args.path).expanduser().resolve()
    name = target.name
    version = pick_version(args.version)
    ptype = args.type or 'work'
    files = template_files(version, ptype)
    entries = [e.name for e in target.iterdir()] if target.is_dir() else []
    if target.exists() and not target.is_dir() or entries and not (entries == ['.git'] and not args.strict_empty):
        raise Fail(3, f'{target} is not empty. To set up an existing folder: yrAiProject.sh update {target}\n'
                      f'(yrAiProject.sh status {target} shows its state)')
    if args.github:
        if not shutil.which('gh'):
            raise Fail(2, '--github needs the gh command (https://cli.github.com/)')
        code = subprocess.run(['gh', 'auth', 'status'], capture_output=True).returncode
        if code:
            raise Fail(2, '--github: gh is not logged in (run: gh auth login)')
    values = project_values(target, None, args)
    values.update(PROJECT_TYPE=ptype, TEMPLATE_VERSION=version)
    texts = {rel: template_text(src, values) for rel, src in files.items()}
    parts = sorted({part_of(rel) for rel in texts} & set(PARTS))
    texts['AGENTS.md'] = new_agents_md(texts.get('AGENTS.md'), name, version, parts)
    if 'README.md' in texts:
        texts['README.md'] = new_readme(texts['README.md'], version, parts)
    has_git = (target / '.git').exists()

    print(f'"new" would make a {ptype} project {name!r} in {target}, from template {version}:')
    for rel in sorted(texts):
        print(f'  + {rel}')
    print(f'  + {MANIFEST.as_posix()}  (the record of this setup)')
    print(f'  + {ABOUT.as_posix()}  (about this setup, for people and agents)')
    print(f'  + {NOTICE.as_posix()}  (the notice at the start of a Claude Code session)')
    print('  then: ' + ('' if has_git else 'git init (branch main), ') + 'commit the files' +
          (f', make the private GitHub repository {name} and push to it, make the pending-work labels'
           if args.github else ''))
    if args.dry_run:
        print('--dry-run: nothing was changed.')
        return 0
    if not ask(args):
        print('Nothing was changed.')
        return 1

    for rel, text in texts.items():
        write(target, rel, text, files.get(rel))
    write_record(target, with_history({
        'schemaVersion': 3,
        'version': version,
        'projectType': ptype,
        'parts': parts,
        'skippedParts': [],
        'values': values,
        'history': [],
        'files': {rel: digest(text) for rel, text in sorted(texts.items()) if rel not in SPECIAL},
        'createdAt': now(),
        'updatedAt': now(),
        'tool': {'name': 'yrAiProject', 'version': TOOL_VERSION, 'templatesCommit': templates_commit()},
    }, 'new'))
    print(f'made the files ({len(texts) + 3})')
    if not has_git:
        code, out = git(target, 'init', '-q', '-b', 'main')
        if code:
            raise Fail(5, f'git init failed:\n{out}')
    code, out = git(target, 'add', '-A')
    if not code:
        code, out = git(target, 'commit', '-q', '-m', f'Make {name} from yrAiProjectTemplates {version} ({ptype} project)',
                        '-m', f'yrAiProject.sh made this project, with the parts {parts_text(parts)}. '
                        f'{ABOUT.as_posix()} lists the files that it installed, and tells who changes each one.')
    if code:
        raise Fail(5, f'git commit failed (the files are written):\n{out}')
    print('made the git repository and the first commit')
    if args.github:
        r = subprocess.run(['gh', 'repo', 'create', name, '--private', '--source', str(target), '--remote', 'origin',
                            '--push'], cwd=target, capture_output=True, text=True)
        if r.returncode:
            raise Fail(5, f'gh repo create failed (the project is made; only GitHub failed):\n{r.stdout}{r.stderr}')
        print('made the private GitHub repository and pushed')
        if (target / PENDING_SCRIPT).is_file():
            r = subprocess.run(['bash', PENDING_SCRIPT, 'setup-labels'], cwd=target, capture_output=True, text=True)
            print('made the pending-work labels' if r.returncode == 0 else
                  f'! could not make the pending-work labels (later: bash {PENDING_SCRIPT} setup-labels)')
    print('next:')
    print(f'  cd {target}')
    if ptype == 'book':
        print('  quarto preview          # the main book')
    print('  quarto preview docs     # the project docs (SPECs, guides, plans)')
    print(f'What yrAiProject installed, and who changes each file: {ABOUT.as_posix()}')
    return 0


def cmd_list(args):
    for i, v in enumerate(template_versions()):
        print(f'{v}{" (newest, the default)" if i == 0 else ""}: {", ".join(project_types(v))}')
    return 0


def cmd_setup_computer(args):
    tools = (META / '..' / '..' / 'tools').resolve()
    home = Path.home()
    missing = False
    print(f'shared rules: {RULES}')
    if not (tools / 'yrAiProject.sh').is_file():
        print(f'  ! the tools folder with yrAiProject.sh was not found ({tools})')
        missing = True
    elif str(tools) not in os.environ.get('PATH', '').split(os.pathsep):
        print(f'  ! {tools} is not on PATH. Add this line to ~/.bashrc, then open a new terminal:')
        print(f'      export PATH="$PATH:{tools}"')
        missing = True
    else:
        print(f'  ok: {tools} is on PATH (yrAiProject.sh)')
    try:
        line = '@~/' + RULES.relative_to(home).as_posix()
    except ValueError:
        line = '@' + RULES.as_posix()
    claude = home / '.claude' / 'CLAUDE.md'
    text = read(claude)
    if text is not None and line in text.split('\n'):
        print(f'  ok: {claude} imports the shared rules')
    elif args.check:
        print(f'  ! {claude} does not import the shared rules (line: {line})')
        missing = True
    else:
        claude.parent.mkdir(exist_ok=True)
        if text is not None:
            claude.write_text(text.rstrip('\n') + f'\n\nThe shared rules for every project (yrAiProjectTemplates):\n\n{line}\n',
                              encoding='utf-8')
            print(f'  added the import line to {claude}')
        else:
            claude.write_text('# My instructions for Claude Code (all projects)\n\nThe shared rules for every project '
                              f'(yrAiProjectTemplates):\n\n{line}\n\n## Claude Code only\n\n(Add rules here that apply '
                              'only to Claude Code.)\n', encoding='utf-8')
            print(f'  created {claude}')
    print('Other AI tools read their own global file. For example, for Codex: ln -s RULES ~/.codex/AGENTS.md '
          '(RULES is the path above).')
    return 1 if args.check and missing else 0


def main(argv):
    if not argv or argv[0] in ('-h', '--help', 'help') or '-h' in argv or '--help' in argv:
        print(__doc__)
        return 0
    p = argparse.ArgumentParser(prog='yrAiProject.sh', add_help=False)
    sub = p.add_subparsers(dest='command')
    n = sub.add_parser('new', add_help=False)
    n.add_argument('path', nargs='?')
    for opt in ('--type', '--title', '--description', '--version'):
        n.add_argument(opt)
    for opt in ('--github', '--strict-empty', '--dry-run'):
        n.add_argument(opt, action='store_true')
    n.add_argument('-y', '--yes', action='store_true')
    s = sub.add_parser('status', add_help=False)
    s.add_argument('path', nargs='?')
    u = sub.add_parser('update', add_help=False)
    u.add_argument('path', nargs='?')
    u.add_argument('--version')
    for opt in ('--with-docs', '--with-pending-work', '--no-pending-work', '--dry-run'):
        u.add_argument(opt, action='store_true')
    u.add_argument('-y', '--yes', action='store_true')
    sub.add_parser('list', add_help=False)
    c = sub.add_parser('setup-computer', add_help=False)
    c.add_argument('--check', action='store_true')
    try:
        args = p.parse_args(argv)
    except SystemExit:
        print('see: yrAiProject.sh --help', file=sys.stderr)
        return 2
    if not args.command:
        print('give a command (new, status, update, list, setup-computer); see: yrAiProject.sh --help', file=sys.stderr)
        return 2
    commands = {'new': cmd_new, 'status': cmd_status, 'update': cmd_update, 'list': cmd_list,
                'setup-computer': cmd_setup_computer}
    try:
        return commands[args.command](args)
    except Fail as e:
        print(f'yrAiProject: {e}', file=sys.stderr)
        return e.status
    except KeyboardInterrupt:
        print('\nStopped.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
