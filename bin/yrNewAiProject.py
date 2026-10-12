#!/usr/bin/env python3
"""yrNewAiProject: make a new project (a git repository) for AI-assisted work, from the yrAiProjectTemplates templates.

Usage:
  yrNewAiProject.sh [--type work|book] [OPTIONS] PATH    make a project in the folder PATH
  yrNewAiProject.sh --verify [--check-content] PATH       check a project against the template that it was made from
  yrNewAiProject.sh --list                                list the template versions and their project types

yrNewAiProject.sh is the command in the Dropbox tools folder; it runs this file, bin/yrNewAiProject.py
(python3 bin/yrNewAiProject.py works too).

What a new project gets:
  every type   AGENTS.md (the rules for every AI agent, with the owner's shared rules), CLAUDE.md (imports
               AGENTS.md), .gitignore, the project-docs Quarto book in docs/ (a first SPEC, a TODO list, a
               writing guide and a Quarto guide) and the new-doc skill (.claude/skills/new-doc/)
  work         a README for any kind of work. Preview the docs book: quarto preview docs
  book         also the main Quarto book (the book to publish) at the project root, and a PLANNING document in
               docs/. Preview the main book: quarto preview; the docs book: quarto preview docs
The tool fills in the project name, title, description, type, date and template version, records them in
.yrAiProjectTemplate/manifest.json, makes a git repository (branch main) and commits the files.

Options to make a project:
  PATH                  the project folder; its name is the project name. It must not exist, or be empty, or hold
                        only .git (see --add-to-existing and --strict-empty)
  --type TYPE           work (default) or book. --list shows the types of each template version
  --title TEXT          the project title (default: the folder name)
  --description TEXT    one sentence that says what the project is for (default: a TODO line to replace)
  --version VER         the template version, for example v0.2.0 (default: the newest)
  --github              also make a private GitHub repository with the folder name (with the gh command), and
                        push the first commit to it
  --add-to-existing     add the template to a folder that already has files. A file that exists already is never
                        changed: the tool stops before it writes anything if a template file exists. There is no
                        first commit: look at the new files, then commit them yourself
  --strict-empty        refuse a folder that holds anything, even only .git
  --dry-run             show what would be done; change nothing
  --meta-repo DIR       the yrAiProjectTemplates folder to take the templates from (default: the one that holds this
                        script)

Options to check a project:
  --verify PATH         check the project in PATH against its template (from its manifest). A missing template
                        file is a problem. Extra files, and shared rules that are out of date, are notes
  --check-content       with --verify: also compare the text of each template file. The filled-in values, the text
                        between <!-- YRAI:BEGIN:NAME --> and <!-- YRAI:END:NAME -->, and the shared-rules block may
                        differ; any other change is reported. Files that you edit (README, docs) are expected to
                        differ: use this to see what changed since the project was made
  --type, --version     with --verify: check against this type or version, not the ones in the manifest

Other options:
  --list                list the template versions (newest first) and their project types
  -h, --help            show this help and stop

Exit status: 0 OK; 1 --verify found a problem; 2 bad options, a missing template or a missing tool; 3 PATH is not
empty; 4 --add-to-existing would change a file that exists; 5 git or gh failed.
Python 3.8 or later, standard library only. The full description: docs/USER-GUIDE-v001.qmd and
docs/SPEC-v0.2.0.qmd in yrAiProjectTemplates. Replaces the retired yraiproject tool (git tag yraiproject-final).
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agents_init  # noqa: E402

TOOL_VERSION = '0.2.0'
SKIP_NAMES = {'.git', '__pycache__', '.quarto', '_book', '.DS_Store', 'yraiproject.template.yml'}
MANIFEST = Path('.yrAiProjectTemplate') / 'manifest.json'
SCALAR = re.compile(r'\{\{YRAI:([A-Z][A-Z0-9_]*)\}\}')
TOKEN = re.compile(r'\{\{YRAI:(BEGIN:|END:)?([A-Z][A-Z0-9_]*)\}\}|<!-- YRAI:(BEGIN|END):([A-Z][A-Z0-9_]*) -->')
SHARED_BLOCK = re.compile(r'^<!-- begin shared rules.*?^<!-- end shared rules -->[ \t]*$', re.M | re.S)


class Fail(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


# ---- templates -------------------------------------------------------------------------------------------------

def version_key(name):
    return tuple(int(x) for x in name[1:].split('.'))


def template_versions(meta):
    root = meta / 'templates'
    found = [p.name for p in root.iterdir() if p.is_dir() and re.fullmatch(r'v\d+\.\d+\.\d+', p.name)] \
        if root.is_dir() else []
    return sorted(found, key=version_key, reverse=True)


def project_types(meta, version):
    return sorted(p.name for p in (meta / 'templates' / version).iterdir() if p.is_dir() and p.name != 'shared')


def plan(meta, version, ptype):
    """{relative path: source file}: the shared files first, then the type's files (which win on the same path)."""
    vdir = meta / 'templates' / version
    if not vdir.is_dir():
        raise Fail(2, f'no template version {version} in {meta / "templates"} (see --list)')
    if not (vdir / ptype).is_dir():
        raise Fail(2, f'no project type {ptype!r} in {version}; types: {", ".join(project_types(meta, version))}')
    files = {}
    for part in ('shared', ptype):
        base = vdir / part
        if not base.is_dir():
            continue
        for src in sorted(base.rglob('*')):
            rel = src.relative_to(base)
            if src.is_file() and not SKIP_NAMES.intersection(rel.parts):
                files[rel] = src
    return files


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


def read_text(path):
    try:
        return path.read_bytes().decode('utf-8')
    except (UnicodeDecodeError, OSError):
        return None


# ---- helpers ---------------------------------------------------------------------------------------------------

def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def is_effectively_empty(target, allow_git_only):
    if not target.exists():
        return True
    if not target.is_dir():
        return False
    entries = [e.name for e in target.iterdir()]
    return not entries or (allow_git_only and entries == ['.git'])


def meta_commit(meta):
    code, out = run(['git', '-C', str(meta), 'rev-parse', '--short', 'HEAD'])
    return out if code == 0 else None


# ---- make a project --------------------------------------------------------------------------------------------

def create(args, meta):
    target = Path(args.path).expanduser().resolve()
    name = target.name
    versions = template_versions(meta)
    if not versions:
        raise Fail(2, f'no templates in {meta / "templates"}')
    version = args.version or versions[0]
    version = version if version.startswith('v') else 'v' + version
    ptype = args.type or 'work'
    files = plan(meta, version, ptype)
    if args.github and args.add_to_existing:
        raise Fail(2, '--github needs the first commit, which --add-to-existing does not make; '
                      'commit the new files, then run: gh repo create NAME --private --source . --push')
    if args.add_to_existing:
        clash = [rel for rel in files if (target / rel).exists()] + \
                ([MANIFEST] if (target / MANIFEST).exists() else [])
        if clash:
            raise Fail(4, 'these files exist already, so nothing was written:\n' +
                       '\n'.join(f'  - {target / rel}' for rel in clash))
    elif not is_effectively_empty(target, allow_git_only=not args.strict_empty):
        raise Fail(3, f'{target} is not empty. Use an empty folder (or one that holds only .git), '
                      'or add --add-to-existing to add the template without changing any file')
    if args.github:
        if not shutil.which('gh'):
            raise Fail(2, '--github needs the gh command (https://cli.github.com/)')
        code, out = run(['gh', 'auth', 'status'])
        if code:
            raise Fail(2, f'--github: gh is not logged in (run: gh auth login)\n{out}')
    values = {
        'PROJECT_NAME': name,
        'PROJECT_TITLE': args.title or name,
        'PROJECT_DESCRIPTION': args.description or 'TODO: one sentence that says what this project is for.',
        'PROJECT_TYPE': ptype,
        'CREATED_DATE': datetime.date.today().isoformat(),
        'TEMPLATE_VERSION': version,
    }
    has_git = (target / '.git').exists()
    commit = not args.add_to_existing

    if args.dry_run:
        print(f'would make a {ptype} project {name!r} in {target} from template {version}:')
        for rel in sorted(files, key=str):
            print(f'  + {rel}')
        print(f'  + {MANIFEST}')
        print('would fill the shared rules into AGENTS.md (agents-init)')
        print(('would use the existing git repository' if has_git else 'would run: git init -b main') +
              ('; would commit the files' if commit else '; would not commit'))
        if args.github:
            print(f'would run: gh repo create {name} --private --source {target} --remote origin --push')
        return 0

    target.mkdir(parents=True, exist_ok=True)
    for rel, src in files.items():
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = read_text(src)
        if text is None:
            shutil.copyfile(src, dest)
        else:
            dest.write_bytes(fill_file(text, values, src.suffix).encode('utf-8'))
        shutil.copymode(src, dest)
    agents_init.update(target, quiet=True)
    manifest = {
        'schemaVersion': 2,
        'templateVersion': version,
        'projectType': ptype,
        'values': values,
        'createdAt': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'addedToExisting': bool(args.add_to_existing),
        'installer': {'name': 'yrNewAiProject', 'version': TOOL_VERSION},
        'metaRepo': {'path': str(meta), 'commit': meta_commit(meta)},
    }
    (target / MANIFEST).parent.mkdir(exist_ok=True)
    (target / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'made a {ptype} project {name!r} in {target} from template {version}: {len(files) + 1} files')

    if not has_git:
        code, out = run(['git', 'init', '-q', '-b', 'main'], cwd=target)
        if code:
            raise Fail(5, f'git init failed:\n{out}')
        print('  git init (branch main)')
    if commit:
        code, out = run(['git', 'add', '-A'], cwd=target)
        if not code:
            code, out = run(['git', 'commit', '-q', '-m',
                             f'Make {name} from yrAiProjectTemplates {version} ({ptype} project)'], cwd=target)
        if code:
            raise Fail(5, f'git commit failed (the files are written):\n{out}')
        print('  committed the files')
    else:
        print('  not committed: look at the new files (git status), then commit them')
    if args.github:
        code, out = run(['gh', 'repo', 'create', name, '--private', '--source', str(target),
                         '--remote', 'origin', '--push'], cwd=target)
        if code:
            raise Fail(5, f'gh repo create failed (the project is made; only GitHub failed):\n{out}')
        print(f'  made the private GitHub repository and pushed: {out.splitlines()[-1] if out else name}')
    print('next:')
    print(f'  cd {target}')
    if ptype == 'book':
        print('  quarto preview          # the main book')
    print('  quarto preview docs     # the project docs (SPECs, guides, TODO)')
    return 0


# ---- check a project -------------------------------------------------------------------------------------------

def template_pattern(text):
    """A regular expression for a template file whose known values are filled in: the YRAI regions, the values that
    are still unknown and the shared-rules block may hold any text."""
    text = SHARED_BLOCK.sub('<!-- begin shared rules -->\n<!-- end shared rules -->', text)
    out, pos, region = [], 0, None
    for m in TOKEN.finditer(text):
        if region is None:
            out.append(re.escape(text[pos:m.start()]))
        kind = (m.group(1) or '').rstrip(':') or m.group(3) or ''
        key = m.group(2) or m.group(4)
        if kind == 'BEGIN' and region is None:
            out.append(re.escape(m.group(0)) + '.*?')
            region = key
        elif kind == 'END' and region == key:
            out.append(re.escape(m.group(0)))
            region = None
        elif region is None:
            out.append('.*?')
        pos = m.end()
    if region is None:
        out.append(re.escape(text[pos:]))
    else:
        out.append('.*')
    return re.compile('^' + ''.join(out) + '$', re.S)


def verify(args, meta):
    target = Path(args.path).expanduser().resolve()
    mpath = target / MANIFEST
    if not mpath.is_file():
        raise Fail(2, f'{mpath} not found: is {target} a project made by yrNewAiProject (or yraiproject)?')
    manifest = json.loads(mpath.read_text(encoding='utf-8'))
    if manifest.get('schemaVersion') == 1:          # made by the retired yraiproject tool
        version = 'v' + str(manifest.get('templateVersion', '')).lstrip('v')
        ptype = 'generic'
        values = {}
    else:
        version, ptype = manifest.get('templateVersion'), manifest.get('projectType')
        values = manifest.get('values', {})
    version = args.version or version
    version = version if version.startswith('v') else 'v' + version
    ptype = args.type or ptype
    files = plan(meta, version, ptype)
    problems, notes = [], []
    for rel, src in sorted(files.items(), key=lambda x: str(x[0])):
        dest = target / rel
        if not dest.is_file():
            problems.append(f'missing: {rel}')
            continue
        if args.check_content:
            t, u = read_text(src), read_text(dest)
            if t is None or u is None:
                if t is None and u is None and src.read_bytes() != dest.read_bytes():
                    problems.append(f'changed: {rel} (a binary file)')
                continue
            u = SHARED_BLOCK.sub('<!-- begin shared rules -->\n<!-- end shared rules -->', u.replace('\r\n', '\n'))
            if not template_pattern(fill_file(t.replace('\r\n', '\n'), values, src.suffix)).match(u):
                problems.append(f'changed: {rel} (text outside the filled-in values and YRAI regions)')
    for path in sorted(target.rglob('*')):
        rel = path.relative_to(target)
        if path.is_file() and rel not in files and rel != MANIFEST and not SKIP_NAMES.intersection(rel.parts):
            notes.append(f'extra: {rel}')
    if (target / 'AGENTS.md').is_file() and agents_init.update(target, check=True):
        notes.append('the shared rules in AGENTS.md (or the import in CLAUDE.md) are out of date: run agents-init')
    print(f'{target}: a {ptype} project from template {version}')
    for n in notes:
        print('  note:', n)
    for p in problems:
        print('  -', p)
    print(f'{len(problems)} problem(s)' if problems else 'OK: every template file is here' +
          (' and unchanged' if args.check_content else ''))
    return 1 if problems else 0


def list_templates(meta):
    versions = template_versions(meta)
    if not versions:
        raise Fail(2, f'no templates in {meta / "templates"}')
    for i, v in enumerate(versions):
        print(f'{v}{" (newest, the default)" if i == 0 else ""}: {", ".join(project_types(meta, v))}')
    return 0


def main(argv):
    if '-h' in argv or '--help' in argv:
        print(__doc__)
        return 0
    p = argparse.ArgumentParser(prog='yrNewAiProject', add_help=False)
    p.add_argument('path', nargs='?')
    p.add_argument('--type')
    p.add_argument('--title')
    p.add_argument('--description')
    p.add_argument('--version')
    p.add_argument('--github', action='store_true')
    p.add_argument('--add-to-existing', action='store_true')
    p.add_argument('--strict-empty', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--meta-repo')
    p.add_argument('--verify', action='store_true')
    p.add_argument('--check-content', action='store_true')
    p.add_argument('--list', action='store_true')
    try:
        args = p.parse_args(argv)
    except SystemExit:
        print('see: yrNewAiProject.sh --help', file=sys.stderr)
        return 2
    meta = Path(args.meta_repo).expanduser().resolve() if args.meta_repo else HERE.parent
    try:
        if args.list:
            return list_templates(meta)
        if not args.path:
            raise Fail(2, 'give the project folder (PATH); see: yrNewAiProject.sh --help')
        if args.check_content and not args.verify:
            raise Fail(2, '--check-content is used with --verify')
        return verify(args, meta) if args.verify else create(args, meta)
    except Fail as e:
        print(f'yrNewAiProject: {e}', file=sys.stderr)
        return e.status


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
