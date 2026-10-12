#!/usr/bin/env python3
"""selftest.py: prove that yrAiProject (new, status, update, list, setup-computer), the new-doc skill and the
pending-work skill work. Run it after every change.

Usage: python3 tests/selftest.py [--keep] [--no-quarto]

  --keep        keep the scratch folder with the test projects (its path is printed)
  --no-quarto   skip the Quarto renders (default: render the books if the quarto command exists)
  -h, --help    show this help and stop

In a scratch folder, it makes work and book projects with "new" and checks the files, the filled-in values, the
record (.yrAiProject/manifest.json), the shared rules, the first commit and "status" (also after a Quarto render);
the new-doc script; the output of the pending-work hook; "update" on existing folders (the plan and its diffs,
--dry-run, the refusal without a terminal, the parts, --with-docs, --no-pending-work, a newer tool file, a file
changed by hand, a deleted file); setup-computer (with a scratch HOME); and the error cases. Every command runs with
no terminal (stdin is /dev/null), so nothing waits for an answer. It never uses --github without --dry-run, so it
makes nothing on GitHub. Prints OK at the end; exit status 1 if a check fails. Stdlib only.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

META = Path(__file__).resolve().parents[1]
TOOL = META / 'bin' / 'yrAiProject.py'
NEWEST = 'v0.3.0'
PENDING = Path('.claude') / 'skills' / 'pending-work' / 'scripts' / 'pending.sh'
SKILL = Path('.claude') / 'skills' / 'pending-work' / 'SKILL.md'
MANIFEST = Path('.yrAiProject') / 'manifest.json'
ENV = dict(os.environ, GIT_AUTHOR_NAME='selftest', GIT_AUTHOR_EMAIL='selftest@example.com',
           GIT_COMMITTER_NAME='selftest', GIT_COMMITTER_EMAIL='selftest@example.com')
failures = []


def run(cmd, cwd=None, env=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, env=env or ENV,
                       stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout + r.stderr


def tool(*args, cwd=None, env=None):
    return run([sys.executable, TOOL, *args], cwd=cwd, env=env)


def check(ok, what, detail=''):
    print(f'  {"ok  " if ok else "FAIL"} {what}')
    if not ok:
        failures.append(what)
        if detail:
            print('       ' + detail.strip().replace('\n', '\n       ')[:2000])


def scalars_left(root):
    return [str(p.relative_to(root)) for p in root.rglob('*')
            if p.is_file() and '.git' not in p.parts and '{{YRAI:' in p.read_text(errors='replace')]


def snapshot(root):
    return {p: p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}


def manifest(root):
    return json.loads((root / MANIFEST).read_text())


def hook_json(out):
    try:
        return json.loads(out)
    except ValueError:
        return {}


def main(argv):
    if '-h' in argv or '--help' in argv:
        print(__doc__)
        return 0
    quarto = shutil.which('quarto') and '--no-quarto' not in argv
    tmp = Path(tempfile.mkdtemp(prefix='yrAiProject-selftest-'))
    print(f'scratch folder: {tmp}')

    print('help and list')
    for script in (TOOL, META / 'templates' / NEWEST / 'shared' / '.claude' / 'skills' / 'new-doc' / 'new_doc.py',
                   META / 'templates' / NEWEST / 'shared' / PENDING):
        code, out = run(['bash', script, '--help'] if script.suffix == '.sh' else [sys.executable, script, '--help'])
        check(code == 0 and 'Usage' in out, f'{script.name} --help')
    code, out = tool()
    check(code == 0 and 'Usage' in out, 'no command: the help')
    code, out = tool('list')
    check(code == 0 and f'{NEWEST} (newest' in out and 'v0.2.0' in out and 'book' in out and 'v0.0.1' not in out,
          'list', out)
    code, out = tool('nosuch')
    check(code == 2, 'an unknown command: exit 2', out)

    print('new')
    for ptype in ('work', 'book'):
        p = tmp / f'my-{ptype}'
        code, out = tool('new', p, '--type', ptype, '--title', f'My "{ptype}" project', '--description',
                         'A test project.', '-y')
        check(code == 0, f'new a {ptype} project', out)
        m = manifest(p)
        check(m['schemaVersion'] == 3 and m['version'] == NEWEST and m['projectType'] == ptype
              and m['parts'] == ['docs', 'pending-work', 'rules'] and str(SKILL.as_posix()) in m['files'],
              f'{ptype}: the record', json.dumps(m)[:600])
        check(not scalars_left(p), f'{ptype}: every {{{{YRAI:...}}}} value is filled in', str(scalars_left(p)))
        agents = (p / 'AGENTS.md').read_text()
        check('Scripts have --help' in agents and 'A test project.' in agents and '## Pending work' in agents,
              f'{ptype}: AGENTS.md has the shared rules')
        check((p / 'CLAUDE.md').read_text().startswith('@AGENTS.md'), f'{ptype}: CLAUDE.md imports AGENTS.md')
        code, out = run(['git', 'log', '--oneline'], cwd=p)
        check(code == 0 and len(out.strip().splitlines()) == 1, f'{ptype}: one first commit', out)
        code, out = run(['git', 'status', '--short'], cwd=p)
        check(out.strip() == '', f'{ptype}: nothing left uncommitted', out)
        check(((p / '_quarto.yml').exists()) == (ptype == 'book'), f'{ptype}: main book only in a book project')
        code, out = tool('status', p)
        check(code == 0 and out.count('up to date') == 3, f'{ptype}: status says up to date', out)
        if quarto:
            for book in (['docs'] + ([] if ptype == 'work' else ['.'])):
                code, out = run(['quarto', 'render', book], cwd=p)
                check(code == 0, f'{ptype}: quarto render {book}', out[-800:])
            code, out = run(['git', 'status', '--short'], cwd=p)
            check(out.strip() == '', f'{ptype}: the renders change no tracked file and leave no new file', out)
            code, out = tool('status', p)
            check(code == 0, f'{ptype}: status after the renders', out)
    book = tmp / 'my-book'
    yml = (book / '_quarto.yml').read_text()
    check('title: "My \\"book\\" project"' in yml, 'a quote in --title is escaped in YAML', yml[:400])

    code, out = tool('new', tmp / 'asks')
    check(code == 6 and not (tmp / 'asks').exists(), 'new with no terminal and no -y: exit 6, nothing made', out)
    code, out = tool('new', tmp / 'dry', '--type', 'book', '--github', '--dry-run')
    check(code in (0, 2) and not (tmp / 'dry').exists(), 'new --dry-run (with --github) makes nothing', out)
    code, out = tool('new', tmp / 'my-work', '-y')
    check(code == 3 and 'yrAiProject.sh update' in out, 'new in a folder that is not empty: exit 3, points to update',
          out)
    gitonly = tmp / 'git-only'
    run(['git', 'init', '-q', gitonly])
    code, out = tool('new', gitonly, '--strict-empty', '-y')
    check(code == 3, 'new --strict-empty refuses a folder with only .git', out)
    code, out = tool('new', gitonly, '-y')
    check(code == 0, 'new accepts a folder with only .git', out)
    code, out = tool('new', tmp / 'bad', '--type', 'nosuch', '-y')
    check(code == 2 and not (tmp / 'bad').exists(), 'new --type nosuch: exit 2', out)
    code, out = tool('new', tmp / 'bad', '--version', 'v9.9.9', '-y')
    check(code == 2 and not (tmp / 'bad').exists(), 'new --version v9.9.9: exit 2', out)
    old = tmp / 'from-v020'
    code, out = tool('new', old, '--version', 'v0.2.0', '-y')
    check(code == 0 and manifest(old)['parts'] == ['docs', 'rules'] and not (old / SKILL).exists(),
          'new --version v0.2.0: an older version (no pending-work)', out)
    code, out = tool('status', old)
    check(code == 1 and 'the newest version is ' + NEWEST in out and 'pending-work  not installed: update adds it'
          in out, 'status of a project of an older version', out)

    print('new-doc')
    nd = [sys.executable, book / '.claude' / 'skills' / 'new-doc' / 'new_doc.py']
    for args, made in (([], 'SPEC-v0.1.1.qmd'), (['user-guide', '--title', 'How to use it'], 'USER-GUIDE-v001.qmd'),
                       (['USER-GUIDE'], 'USER-GUIDE-v002.qmd'), (['RESEARCH-NOTES', '--blank'], 'RESEARCH-NOTES-v001.qmd'),
                       (['--version', '1.0.0'], 'SPEC-v1.0.0.qmd')):
        code, out = run(nd + args, cwd=book)
        check(code == 0 and (book / 'docs' / made).exists() and made in (book / 'docs' / '_quarto.yml').read_text(),
              f'new_doc.py {" ".join(args) or "(no options)"} -> {made}', out)
    toc = (book / 'docs' / '_quarto.yml').read_text()
    check(toc.index('SPEC-v1.0.0') < toc.index('SPEC-v0.1.1') < toc.index('SPEC-v0.1.0')
          and toc.index('USER-GUIDE-v002') < toc.index('USER-GUIDE-v001'), 'new_doc.py lists the newest version first')
    code, out = run(nd + ['--version', '2.0.0', '--dry-run'], cwd=book)
    check(code == 0 and not (book / 'docs' / 'SPEC-v2.0.0.qmd').exists(), 'new_doc.py --dry-run writes nothing')
    code, out = run(nd + ['PLANNING', '--version', '1.0.0'], cwd=book)
    check(code != 0, 'new_doc.py refuses --version for a type that is not SPEC')
    if quarto:
        code, out = run(['quarto', 'render', 'docs'], cwd=book)
        check(code == 0, 'quarto render docs after new_doc.py', out[-800:])
    code, out = tool('status', book)
    check(code == 0, 'status: new documents are not changes to the tool files', out)

    print('pending-work hook')
    work = tmp / 'my-work'
    settings = json.loads((work / '.claude' / 'settings.json').read_text())
    check('pending.sh' in json.dumps(settings['hooks']['SessionStart']), 'a new project has the SessionStart hook')
    code, out = run(['bash', PENDING, 'session-start'], cwd=work)
    hook = hook_json(out)
    check(code == 0 and hook.get('systemMessage') == 'Pending work: nothing pending.'
          and hook.get('hookSpecificOutput', {}).get('hookEventName') == 'SessionStart',
          'session-start with no GitHub repository: valid hook JSON, nothing pending', out)
    queue = work / '_pending-work' / 'queue.md'
    queue.parent.mkdir()
    queue.write_text('### [high] First thing\nbody\n\n### [low] Second thing\nbody\n')
    code, out = run(['bash', PENDING, 'session-start'], cwd=work)
    hook = hook_json(out)
    context = hook.get('hookSpecificOutput', {}).get('additionalContext', '')
    check(code == 0 and '2 pending items (1 high, 1 low)' in hook.get('systemMessage', '')
          and 'First thing' not in context, 'session-start gives the count by priority, not the list', out)
    code, out = run(['bash', PENDING, 'list'], cwd=work)
    check(code == 0 and 'First thing' in out and 'Second thing' in out, 'list shows the queued items', out)
    shutil.rmtree(queue.parent)

    print('update an existing folder')
    ex = tmp / 'existing'
    (ex / '.claude').mkdir(parents=True)
    run(['git', 'init', '-q', ex])
    (ex / 'README.md').write_text('# Mine\n')
    (ex / 'CLAUDE.md').write_text('# My rules\n')
    (ex / '.claude' / 'settings.json').write_text('{"permissions": {"allow": ["Bash(ls)"]}}\n')
    run(['git', 'add', '-A'], cwd=ex)
    run(['git', 'commit', '-q', '-m', 'mine'], cwd=ex)
    code, out = tool('status', ex)
    check(code == 1 and 'not set up with yrAiProject' in out and 'docs          not installed (optional' in out,
          'status of a folder that was never set up', out)
    before = snapshot(ex)
    code, out = tool('update', ex)
    check(code == 6 and snapshot(ex) == before and '+@AGENTS.md' in out,
          'update with no terminal and no -y: shows the plan, exit 6, changes nothing', out)
    code, out = tool('update', ex, '--dry-run')
    check(code == 0 and snapshot(ex) == before and '+ add    .claude/skills/pending-work/SKILL.md' in out
          and '~ change .claude/settings.json' in out and '"matcher": "startup|clear"' in out
          and '+ add    AGENTS.md' in out and 'README.md' not in out.split('What "update"')[1],
          'update --dry-run: the plan with diffs, changes nothing, no template README', out)
    code, out = tool('update', ex, '-y')
    s = json.loads((ex / '.claude' / 'settings.json').read_text())
    claude = (ex / 'CLAUDE.md').read_text()
    check(code == 0 and 'Scripts have --help' in (ex / 'AGENTS.md').read_text() and claude.startswith('@AGENTS.md')
          and '# My rules' in claude and s['permissions'] == {'allow': ['Bash(ls)']}
          and 'pending.sh' in json.dumps(s['hooks']) and (ex / PENDING).is_file()
          and os.access(ex / PENDING, os.X_OK) and (ex / 'README.md').read_text() == '# Mine\n'
          and not (ex / 'docs').exists() and manifest(ex)['parts'] == ['pending-work', 'rules'],
          'update -y: the shared rules and pending-work, keeps what is there, no docs', out)
    code, out = tool('status', ex)
    check(code == 0 and 'set up with yrAiProject, template ' + NEWEST in out, 'status after update: up to date', out)
    code, out = tool('update', ex, '-y')
    check(code == 0 and 'Nothing to do' in out, 'update again: nothing to do', out)

    m = manifest(ex)
    older = '---\nname: pending-work\n---\nAn older version.\n'
    (ex / SKILL).write_text(older)
    m['files'][SKILL.as_posix()] = hashlib.sha256(older.encode()).hexdigest()
    (ex / MANIFEST).write_text(json.dumps(m))
    code, out = tool('status', ex)
    check(code == 1 and 'out of date: update would change 1 file(s)' in out, 'status sees an older tool file', out)
    code, out = tool('update', ex, '-y')
    check(code == 0 and (ex / SKILL).read_text() != older and '-An older version.' in out,
          'update replaces a tool file that nobody changed, and shows the diff', out)
    (ex / SKILL).write_text((ex / SKILL).read_text() + 'My own line.\n')
    code, out = tool('update', ex, '-y')
    check(code == 0 and 'My own line.' in (ex / SKILL).read_text() and 'changed here' in out,
          'update leaves a file that was changed by hand', out)
    (ex / PENDING).unlink()
    code, out = tool('update', ex, '-y')
    check(code == 0 and (ex / PENDING).is_file() and 'it was missing' in out, 'update adds a deleted tool file again',
          out)
    agents = (ex / 'AGENTS.md').read_text()
    (ex / 'AGENTS.md').write_text('# Rules\n\nMine.\n\n' + agents.split('\n\n', 2)[2].replace('Scripts have --help',
                                                                                               'Scripts have help'))
    code, out = tool('status', ex)
    check(code == 1 and 'rules         out of date' in out, 'status sees shared rules that are out of date', out)
    code, out = tool('update', ex, '-y')
    text = (ex / 'AGENTS.md').read_text()
    check(code == 0 and 'Scripts have --help' in text and 'Mine.' in text,
          'update brings the shared rules up to date, and keeps the project rules', out)

    print('update: the optional parts')
    np = tmp / 'no-pending'
    np.mkdir()
    code, out = tool('update', np, '--no-pending-work', '-y')
    check(code == 0 and not (np / '.claude').exists() and manifest(np)['skippedParts'] == ['pending-work'],
          'update --no-pending-work: only the rules', out)
    code, out = tool('status', np)
    check(code == 0 and 'you chose --no-pending-work' in out, 'status remembers --no-pending-work', out)
    code, out = tool('update', np, '--with-pending-work', '--with-docs', '-y')
    check(code == 0 and (np / SKILL).is_file() and (np / 'docs' / '_quarto.yml').is_file()
          and (np / '.claude' / 'skills' / 'new-doc' / 'new_doc.py').is_file()
          and manifest(np)['parts'] == ['docs', 'pending-work', 'rules'] and manifest(np)['skippedParts'] == [],
          'update --with-pending-work --with-docs adds both parts', out)
    if quarto:
        code, out = run(['quarto', 'render', 'docs'], cwd=np)
        check(code == 0, 'quarto render docs after update --with-docs', out[-800:])
    od = tmp / 'own-docs'
    (od / 'docs').mkdir(parents=True)
    (od / 'docs' / '_quarto.yml').write_text('project:\n  type: website\n')
    code, out = tool('update', od, '--with-docs', '-y')
    check(code == 0 and 'not from yrAiProject' in out and (od / 'docs' / '_quarto.yml').read_text()
          == 'project:\n  type: website\n' and not (od / 'docs' / 'index.qmd').exists(),
          'update --with-docs does not add the docs part over another docs/_quarto.yml', out)
    bad = tmp / 'bad-settings'
    (bad / '.claude').mkdir(parents=True)
    (bad / '.claude' / 'settings.json').write_text('{not json')
    code, out = tool('update', bad, '-y')
    check(code == 0 and (bad / '.claude' / 'settings.json').read_text() == '{not json' and 'by hand' in out
          and (bad / 'AGENTS.md').is_file(), 'update leaves a settings.json that is not JSON, and does the rest', out)
    code, out = tool('update', tmp / 'no-such-folder', '-y')
    check(code == 2, 'update of a folder that does not exist: exit 2', out)
    code, out = tool('update', ex, '--no-pending-work', '--with-pending-work', '-y')
    check(code == 2, 'update --no-pending-work --with-pending-work: exit 2', out)

    print('setup-computer')
    home = tmp / 'home'
    home.mkdir()
    env = dict(ENV, HOME=str(home))
    code, out = tool('setup-computer', '--check', env=env)
    check(code == 1 and not (home / '.claude').exists(), 'setup-computer --check: reports, changes nothing', out)
    tool('setup-computer', env=env)
    code, out = tool('setup-computer', env=env)
    text = (home / '.claude' / 'CLAUDE.md').read_text()
    check(text.count('rules/AGENTS.md') == 1 and 'imports the shared rules' in out,
          'setup-computer adds the import line once', text + out)

    if '--keep' in argv:
        print(f'kept: {tmp}')
    else:
        shutil.rmtree(tmp)
    if failures:
        print(f'{len(failures)} check(s) failed')
        return 1
    print('OK: every check passed' + ('' if quarto else ' (Quarto renders skipped)'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
