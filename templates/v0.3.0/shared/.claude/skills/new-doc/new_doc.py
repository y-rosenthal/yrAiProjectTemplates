#!/usr/bin/env python3
"""new_doc.py: add a document (a SPEC by default) to the project-docs Quarto book, and list it in docs/_quarto.yml.

Usage: new_doc.py [TYPE] [--title TEXT] [--version X.Y.Z] [--part NAME] [--blank] [--docs DIR] [--dry-run]

  TYPE            the document type: SPEC (default), USER-GUIDE, DESIGN-GUIDE, TODO, PLANNING, or any other name
                  in capital letters, digits and hyphens (small letters are changed to capitals)
  --title TEXT    the subtitle: a short description of the document (default: one for the type)
  --version X.Y.Z SPEC only: the version of the new SPEC (default: the newest SPEC's version with the last number
                  plus 1, or 0.1.0 if there is no SPEC)
  --part NAME     the part of the book to put a new type in (default: "Specification" for SPEC, "Guides" for
                  a name that ends in GUIDE, else "Work"); the part is made if it does not exist
  --blank         start from the empty outline of the type (default: a copy of the newest version, if there is one)
  --docs DIR      the project-docs book folder (default: docs/ in the top folder of the git repository)
  --dry-run       show what would be done; change nothing
  -h, --help      show this help and stop

File names (docs/DOC-GUIDE-v001.qmd): a SPEC has the version of its development step (SPEC-v0.2.0.qmd); other
documents have a copy number (USER-GUIDE-v001.qmd, then -v002 when the old copy must stay next to the new one).
The new file goes into docs/_quarto.yml above the previous version of the same type (newest first), or at the end
of its part. Stdlib only.
"""
import re
import subprocess
import sys
from pathlib import Path

OUTLINES = {
    'SPEC': ('what this version must do',
             ['Purpose {#sec-purpose}', 'Scope {#sec-scope}', 'Requirements {#sec-requirements}',
              'Design {#sec-design}', 'Open questions {#sec-open-questions}']),
    'USER-GUIDE': ('how to use the project', ['Who this guide is for', 'Start', 'Tasks', 'Troubleshooting']),
    'DESIGN-GUIDE': ('how the project is made, and why', ['Goals', 'Structure', 'Decisions', 'Rejected alternatives']),
    'TODO': ('the work still to do', ['Open', 'Done']),
    'PLANNING': ('plans', ['Goals', 'Steps', 'Risks']),
}
DEFAULT_OUTLINE = ('TODO: a short description', ['Purpose', 'Content'])


def opt(argv, name):
    if name not in argv:
        return None
    i = argv.index(name)
    if i + 1 >= len(argv):
        sys.exit(f'new_doc.py: {name} needs a value (see --help)')
    return argv[i + 1]


def docs_dir(argv):
    given = opt(argv, '--docs')
    if given:
        return Path(given).resolve()
    r = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    return (Path(r.stdout.strip()) if r.returncode == 0 else Path.cwd()) / 'docs'


def versions(docs, kind):
    """The existing files of this type, newest first, as (version tuple, path)."""
    pat = re.compile(rf'^{re.escape(kind)}-v(\d+)\.(\d+)\.(\d+)\.qmd$' if kind == 'SPEC'
                     else rf'^{re.escape(kind)}-v(\d+)\.qmd$')
    found = [(tuple(int(g) for g in m.groups()), p) for p in docs.glob(f'{kind}-v*.qmd') if (m := pat.match(p.name))]
    return sorted(found, reverse=True)


def outline(kind, title):
    sub, sections = OUTLINES.get(kind, DEFAULT_OUTLINE)
    body = ''.join(f'## {s}\n\nTODO.\n\n' for s in sections)
    return f'---\ntitle: "{{name}}"\nsubtitle: "{title or sub}"\n---\n\n{body}'.rstrip() + '\n'


def from_previous(prev, title):
    text = prev.read_text(encoding='utf-8')
    text = re.sub(r'^title:.*$', 'title: "{name}"', text, count=1, flags=re.M)
    if title:
        text = re.sub(r'^subtitle:.*$', f'subtitle: "{title}"', text, count=1, flags=re.M)
    return text


def add_to_toc(toc_text, new_file, prev_file, part):
    """Return the new _quarto.yml text, or None if the file could not be placed."""
    lines = toc_text.split('\n')
    if prev_file:                                         # above the previous version (newest first)
        for i, line in enumerate(lines):
            m = re.match(r'^(\s*)- ' + re.escape(prev_file) + r'\s*$', line)
            if m:
                lines.insert(i, f'{m.group(1)}- {new_file}')
                return '\n'.join(lines)
    for i, line in enumerate(lines):                      # at the end of the part
        m = re.match(r'^(\s*)- part:\s*["\']?' + re.escape(part) + r'["\']?\s*$', line)
        if not m:
            continue
        indent = len(m.group(1))
        j, item = i + 2, ' ' * (indent + 4)
        while j < len(lines) and lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) > indent:
            item = lines[j][:len(lines[j]) - len(lines[j].lstrip())] if lines[j].lstrip().startswith('- ') else item
            j += 1
        lines.insert(j, f'{item}- {new_file}')
        return '\n'.join(lines)
    for i, line in enumerate(lines):                      # a new part at the end of book: chapters:
        if re.match(r'^  chapters:\s*$', line):
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].startswith('    ')):
                j += 1
            while lines[j - 1].strip() == '':
                j -= 1
            lines[j:j] = [f'    - part: "{part}"', '      chapters:', f'        - {new_file}']
            return '\n'.join(lines)
    return None


def main(argv):
    if '-h' in argv or '--help' in argv:
        print(__doc__)
        return 0
    values = {opt(argv, o) for o in ('--title', '--version', '--part', '--docs')}
    words = [a for a in argv if not a.startswith('--') and a not in values]
    kind = (words[0] if words else 'SPEC').upper()
    if not re.fullmatch(r'[A-Z][A-Z0-9-]*', kind):
        sys.exit(f'new_doc.py: bad type {kind!r}: use capital letters, digits and hyphens (see --help)')
    title, dry = opt(argv, '--title'), '--dry-run' in argv
    docs = docs_dir(argv)
    toc = docs / '_quarto.yml'
    if not toc.exists():
        sys.exit(f'new_doc.py: {toc} not found (use --docs DIR)')
    found = versions(docs, kind)
    newest = found[0][1] if found else None
    if kind == 'SPEC':
        v = opt(argv, '--version')
        if v and not re.fullmatch(r'\d+\.\d+\.\d+', v.lstrip('v')):
            sys.exit(f'new_doc.py: bad version {v!r}: use X.Y.Z')
        ver = v.lstrip('v') if v else ('.'.join(map(str, (*found[0][0][:2], found[0][0][2] + 1))) if found else '0.1.0')
        name = f'SPEC-v{ver}'
    else:
        if opt(argv, '--version'):
            sys.exit('new_doc.py: --version is only for a SPEC; other documents get the next copy number')
        name = f'{kind}-v{(found[0][0][0] + 1 if found else 1):03d}'
    path = docs / f'{name}.qmd'
    if path.exists():
        sys.exit(f'new_doc.py: {path} exists already')
    part = opt(argv, '--part') or ('Specification' if kind == 'SPEC' else 'Guides' if kind.endswith('GUIDE') else 'Work')
    text = (outline(kind, title) if '--blank' in argv or not newest else from_previous(newest, title)).replace('{name}', name)
    new_toc = add_to_toc(toc.read_text(encoding='utf-8'), path.name, newest.name if newest else None, part)
    print(f'{"would make" if dry else "made"} {path}' + (f' (a copy of {newest.name})' if newest and '--blank' not in argv else ''))
    if new_toc is None:
        print(f'  ! could not find where to list it in {toc}: add "- {path.name}" to book: chapters: by hand')
    else:
        print(f'{"would list" if dry else "listed"} it in {toc}' + (f', above {newest.name}' if newest else f', part "{part}"'))
    if not dry:
        path.write_text(text, encoding='utf-8')
        if new_toc is not None:
            toc.write_text(new_toc, encoding='utf-8')
        print('next: write the content, then run: quarto render docs')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
