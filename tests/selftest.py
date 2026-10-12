#!/usr/bin/env python3
"""selftest.py: prove that yrNewAiProject, agents-init and the new-doc skill work. Run it after every change.

Usage: python3 tests/selftest.py [--keep] [--no-quarto]

  --keep        keep the scratch folder with the test projects (its path is printed)
  --no-quarto   skip the Quarto renders (default: render the books if the quarto command exists)
  -h, --help    show this help and stop

In a scratch folder, it makes work and book projects and checks: the files, the filled-in values, the manifest,
the shared rules in AGENTS.md, the first commit, --verify and --check-content (also after a Quarto render), the
new-doc script, the pending-work skill (its hook output, and agents-init --pending-work), the template v0.0.1, and
every error case (exit statuses 2, 3 and 4). It never uses --github
without --dry-run, so it makes nothing on GitHub. Prints OK at the end; exit status 1 if a check fails.
Stdlib only.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

META = Path(__file__).resolve().parents[1]
TOOL = META / 'bin' / 'yrNewAiProject.py'
AGENTS_INIT = META / 'bin' / 'agents_init.py'
NEWEST = 'v0.3.0'
PENDING = Path('.claude') / 'skills' / 'pending-work' / 'scripts' / 'pending.sh'
ENV = dict(os.environ, GIT_AUTHOR_NAME='selftest', GIT_AUTHOR_EMAIL='selftest@example.com',
           GIT_COMMITTER_NAME='selftest', GIT_COMMITTER_EMAIL='selftest@example.com')
failures = []


def run(cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout + r.stderr


def tool(*args, cwd=None):
    return run([sys.executable, TOOL, *args], cwd=cwd)


def check(ok, what, detail=''):
    print(f'  {"ok  " if ok else "FAIL"} {what}')
    if not ok:
        failures.append(what)
        if detail:
            print('       ' + detail.strip().replace('\n', '\n       ')[:1500])


def scalars_left(root):
    return [str(p.relative_to(root)) for p in root.rglob('*')
            if p.is_file() and '.git' not in p.parts and '{{YRAI:' in p.read_text(errors='replace')
            and '{{YRAI:BEGIN' not in p.read_text(errors='replace')]


def main(argv):
    if '-h' in argv or '--help' in argv:
        print(__doc__)
        return 0
    quarto = shutil.which('quarto') and '--no-quarto' not in argv
    tmp = Path(tempfile.mkdtemp(prefix='yrNewAiProject-selftest-'))
    print(f'scratch folder: {tmp}')

    print('help and list')
    for script in (TOOL, AGENTS_INIT, META / 'bin' / 'setup-computer.sh',
                   META / 'templates' / NEWEST / 'shared' / '.claude' / 'skills' / 'new-doc' / 'new_doc.py',
                   META / 'templates' / NEWEST / 'shared' / PENDING):
        code, out = run(['bash', script, '--help'] if script.suffix == '.sh' else [sys.executable, script, '--help'])
        check(code == 0 and 'Usage' in out, f'{script.name} --help')
    code, out = tool('--list')
    check(code == 0 and NEWEST in out and 'v0.2.0' in out and 'book' in out and 'work' in out and 'v0.0.1' in out, '--list', out)

    print('make projects')
    for ptype in ('work', 'book'):
        p = tmp / f'my-{ptype}'
        code, out = tool('--type', ptype, '--title', f'My "{ptype}" project', '--description', 'A test project.', p)
        check(code == 0, f'make a {ptype} project', out)
        man = json.loads((p / '.yrAiProjectTemplate' / 'manifest.json').read_text())
        check(man['projectType'] == ptype and man['templateVersion'] == NEWEST and man['schemaVersion'] == 2,
              f'{ptype}: manifest')
        check(not scalars_left(p), f'{ptype}: every {{{{YRAI:...}}}} value is filled in', str(scalars_left(p)))
        agents = (p / 'AGENTS.md').read_text()
        check('Scripts have --help' in agents and 'A test project.' in agents, f'{ptype}: AGENTS.md has the shared rules')
        check((p / 'CLAUDE.md').read_text().startswith('@AGENTS.md'), f'{ptype}: CLAUDE.md imports AGENTS.md')
        code, out = run(['git', 'log', '--oneline'], cwd=p)
        check(code == 0 and len(out.strip().splitlines()) == 1, f'{ptype}: one first commit', out)
        code, out = run(['git', 'status', '--short'], cwd=p)
        check(out.strip() == '', f'{ptype}: nothing left uncommitted', out)
        check(((p / '_quarto.yml').exists()) == (ptype == 'book'), f'{ptype}: main book only in a book project')
        code, out = tool('--verify', '--check-content', p)
        check(code == 0, f'{ptype}: --verify --check-content', out)
        if quarto:
            for book in (['docs'] + ([] if ptype == 'work' else ['.'])):
                code, out = run(['quarto', 'render', book], cwd=p)
                check(code == 0, f'{ptype}: quarto render {book}', out[-800:])
            code, out = run(['git', 'status', '--short'], cwd=p)
            check(out.strip() == '', f'{ptype}: the renders change no tracked file and leave no new file', out)
            code, out = tool('--verify', '--check-content', p)
            check(code == 0 and 'extra' not in out, f'{ptype}: --verify --check-content after the renders', out)
    book = tmp / 'my-book'
    yml = (book / '_quarto.yml').read_text()
    check('title: "My \\"book\\" project"' in yml, 'a quote in --title is escaped in YAML', yml[:400])

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
    code, out = run(nd + ['TODO', '--version', '1.0.0'], cwd=book)
    check(code != 0, 'new_doc.py refuses --version for a type that is not SPEC')
    if quarto:
        code, out = run(['quarto', 'render', 'docs'], cwd=book)
        check(code == 0, 'quarto render docs after new_doc.py', out[-800:])

    print('pending-work')
    work = tmp / 'my-work'
    settings = json.loads((work / '.claude' / 'settings.json').read_text())
    check('pending.sh' in json.dumps(settings['hooks']['SessionStart']), 'a new project has the SessionStart hook')
    code, out = run(['bash', PENDING, 'session-start'], cwd=work)
    try:
        hook = json.loads(out)
    except ValueError:
        hook = {}
    check(code == 0 and hook.get('systemMessage') == 'Pending work: nothing pending.'
          and hook.get('hookSpecificOutput', {}).get('hookEventName') == 'SessionStart',
          'session-start with no GitHub repository: valid hook JSON, nothing pending', out)
    queue = work / '_pending-work' / 'queue.md'
    queue.parent.mkdir()
    queue.write_text('### [high] First thing\nbody\n\n### [low] Second thing\nbody\n')
    code, out = run(['bash', PENDING, 'session-start'], cwd=work)
    try:
        hook = json.loads(out)
    except ValueError:
        hook = {}
    context = hook.get('hookSpecificOutput', {}).get('additionalContext', '')
    check(code == 0 and '2 pending items (1 high, 1 low)' in hook.get('systemMessage', '')
          and 'First thing' not in context, 'session-start gives the count by priority, not the list', out)
    code, out = run(['bash', PENDING, 'list'], cwd=work)
    check(code == 0 and 'First thing' in out and 'Second thing' in out, 'list shows the queued items', out)
    shutil.rmtree(queue.parent)
    old = tmp / 'old-project'
    (old / '.claude').mkdir(parents=True)
    (old / '.claude' / 'settings.json').write_text(json.dumps({'permissions': {'allow': ['Bash(ls)']}}))
    code, out = run([sys.executable, AGENTS_INIT, old, '--check', '--pending-work'])
    check(code == 1 and 'missing' in out, 'agents-init --check --pending-work reports a missing skill', out)
    code, out = run([sys.executable, AGENTS_INIT, old, '--pending-work'])
    s = json.loads((old / '.claude' / 'settings.json').read_text())
    check(code == 0 and (old / PENDING).is_file() and s['permissions'] == {'allow': ['Bash(ls)']}
          and 'pending.sh' in json.dumps(s['hooks']['SessionStart']),
          'agents-init --pending-work adds the skill and the hook, and keeps the other settings', out)
    (old / PENDING).write_text('# changed by the project\n')
    before = (old / '.claude' / 'settings.json').read_text()
    code, out = run([sys.executable, AGENTS_INIT, old, '--pending-work'])
    code2, out2 = run([sys.executable, AGENTS_INIT, old, '--check', '--pending-work'])
    check(code == 0 and code2 == 0 and (old / PENDING).read_text() == '# changed by the project\n'
          and (old / '.claude' / 'settings.json').read_text() == before,
          'agents-init --pending-work again: replaces no file, adds no second hook', out + out2)

    print('verify finds problems')
    work = tmp / 'my-work'
    readme = (work / 'README.md').read_text()
    (work / 'README.md').write_text(readme.replace('TODO: say how to install, run and test the project.',
                                                   'Run make.'))
    code, out = tool('--verify', '--check-content', work)
    check(code == 0, 'an edit inside a YRAI region is allowed', out)
    (work / 'CLAUDE.md').write_text((work / 'CLAUDE.md').read_text() + 'Extra line.\n')
    code, out = tool('--verify', '--check-content', work)
    check(code == 1 and 'changed: CLAUDE.md' in out, '--check-content reports an edit outside the regions', out)
    (work / 'docs' / 'TODO-v001.qmd').unlink()
    code, out = tool('--verify', work)
    check(code == 1 and 'missing: docs/TODO-v001.qmd' in out, '--verify reports a missing file', out)
    agents = (work / 'AGENTS.md').read_text()
    (work / 'AGENTS.md').write_text(agents.replace('Scripts have --help', 'Scripts have help'))
    code, out = tool('--verify', work)
    check('out of date' in out, '--verify notes shared rules that are out of date', out)

    print('error cases')
    code, out = tool(work)
    check(code == 3, 'a folder that is not empty: exit 3', out)
    gitonly = tmp / 'git-only'
    run(['git', 'init', '-q', gitonly])
    code, out = tool('--strict-empty', gitonly)
    check(code == 3, '--strict-empty refuses a folder with only .git', out)
    code, out = tool(gitonly)
    check(code == 0, 'a folder with only .git is accepted', out)
    existing = tmp / 'existing'
    existing.mkdir()
    (existing / 'README.md').write_text('# Mine\n')
    code, out = tool('--add-to-existing', existing)
    check(code == 4 and sorted(p.name for p in existing.iterdir()) == ['README.md'],
          '--add-to-existing stops, and writes nothing, if a template file exists', out)
    (existing / 'README.md').rename(existing / 'NOTES.md')
    code, out = tool('--add-to-existing', existing)
    code2, log = run(['git', 'log'], cwd=existing)
    check(code == 0 and (existing / 'AGENTS.md').exists() and (existing / 'NOTES.md').exists() and code2 != 0,
          '--add-to-existing adds the files and makes no commit', out + log)
    code, out = tool('--add-to-existing', '--github', tmp / 'x')
    check(code == 2, '--github with --add-to-existing: exit 2', out)
    code, out = tool('--dry-run', '--github', '--type', 'book', tmp / 'dry')
    check(code in (0, 2) and not (tmp / 'dry').exists(), '--dry-run (with --github) makes nothing', out)
    code, out = tool('--type', 'nosuch', tmp / 'bad')
    check(code == 2 and not (tmp / 'bad').exists(), 'an unknown type: exit 2', out)
    code, out = tool('--version', 'v9.9.9', tmp / 'bad')
    check(code == 2, 'an unknown version: exit 2', out)
    code, out = tool('--check-content', tmp / 'bad')
    check(code == 2, '--check-content without --verify: exit 2', out)

    print('template v0.0.1 and old manifests')
    old = tmp / 'old-generic'
    code, out = tool('--version', 'v0.0.1', '--type', 'generic', old)
    check(code == 0 and (old / 'docs' / '_quarto.yml').exists(), 'make a project from v0.0.1 (generic)', out)
    code, out = tool('--verify', '--check-content', old)
    check(code == 0, 'verify the v0.0.1 project', out)
    (old / '.yrAiProjectTemplate' / 'manifest.json').write_text(json.dumps(
        {'schemaVersion': 1, 'templateId': 'genericTemplate', 'templateVersion': '0.0.1'}))
    code, out = tool('--verify', old)
    check(code == 0, 'verify reads a manifest of the retired yraiproject tool', out)

    print('agents-init')
    code, out = run([sys.executable, AGENTS_INIT, work])
    code2, out2 = run([sys.executable, AGENTS_INIT, work, '--check'])
    check(code == 0 and code2 == 0 and 'Scripts have --help' in (work / 'AGENTS.md').read_text(),
          'agents-init brings the shared rules up to date', out + out2)

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
