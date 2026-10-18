"""Independent raw-object export and delivery identity checks; no candidate calls."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = Path('D:/1800-worktrees/a06')
DELIVERY = '761d9afed8b9d3d33851ad3d79b0bee7c294089d'
CANDIDATE = '9076d35e81678cdba8ad8651e95a44265fdc345c'
BASE = 'a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8'
ZIP = Path('D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip')
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1')
GIT = ['git', '-c', 'core.longpaths=true', '-C', str(REPO)]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def dump(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def git(*args):
    result = subprocess.run(GIT + list(args), cwd=str(ROOT), env=ENV, capture_output=True, check=True)
    return result.stdout

def selected(path):
    return (path.startswith(('src/', 'examples/', 'tests/fixtures/contracts/', 'tests/fixtures/a06/', 'docs/evidence/A06/'))
            or path.startswith('tests/test_a06')
            or path in ('pyproject.toml', 'README.md', 'docs/tasks/A06-execution-report.md'))

def main():
    code = ROOT / 'code'
    code.mkdir(exist_ok=False)
    for commit in (BASE, CANDIDATE, DELIVERY):
        assert git('cat-file', '-t', commit).strip() == b'commit'
    diff = git('diff', '--name-status', BASE, DELIVERY).decode('utf-8')
    (ROOT / 'delivery-diff.txt').write_text(diff, encoding='utf-8')
    changes = [row.split('\t') for row in diff.splitlines()]
    def allowed(path):
        return (path.startswith(('src/annotation/source/b_handoff/', 'examples/a06/', 'tests/fixtures/a06/', 'docs/evidence/A06/'))
                or path.startswith('tests/test_a06') or path == 'docs/tasks/A06-execution-report.md')
    assert all(row[0] == 'A' and len(row) == 2 and allowed(row[1]) for row in changes)
    frozen_paths = ['src/annotation/source/b_handoff', 'examples/a06/consume.py', 'examples/a06/make_variants.py',
                    'examples/a06/verify.py', 'tests/test_a06_versions.py', 'tests/fixtures/a06']
    frozen_delta = git('diff', '--name-status', CANDIDATE, DELIVERY, '--', *frozen_paths)
    assert not frozen_delta, frozen_delta
    entries = []
    for raw in git('ls-tree', '-r', '-z', '--full-tree', DELIVERY).split(b'\0'):
        if not raw:
            continue
        header, raw_path = raw.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split()
        path = raw_path.decode('utf-8')
        if selected(path):
            assert mode in ('100644', '100755') and kind == 'blob'
            entries.append((oid, path, mode))
    batch = subprocess.Popen(GIT + ['cat-file', '--batch'], cwd=str(ROOT), env=ENV, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    records = []
    for oid, path, mode in entries:
        batch.stdin.write((oid + '\n').encode('ascii'))
        batch.stdin.flush()
        response = batch.stdout.readline().decode('ascii').strip().split()
        assert len(response) == 3 and response[:2] == [oid, 'blob'], response
        size = int(response[2])
        data = batch.stdout.read(size)
        assert len(data) == size and batch.stdout.read(1) == b'\n'
        assert hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\0' + data).hexdigest() == oid
        target = code / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records.append(dict(path=path, git_blob=oid, mode=mode, bytes=size, sha256=sha(data)))
    batch.stdin.close()
    assert batch.wait(timeout=30) == 0
    assert not batch.stderr.read()
    expected = {
        'docs/tasks/A06-execution-report.md': 'deba7a12f2b74b9261a8404ce19885fcea3c574d68f8e1bbd9761a8c2e7df0bb',
        'docs/evidence/A06/manifest.json': 'e37efb2ba44b6005cb4c15e095ab22e00d804c4884ce988d6b613cb8b5189d33',
        'docs/evidence/A06/author/release.json': '2f7eb5d6203ae7e7c441170c03ef17d012e7139df64423635c38ada30120283c',
    }
    assert all(sha((code / path).read_bytes()) == value for path, value in expected.items())
    original = ZIP.read_bytes()
    assert len(original) == 11681712 and sha(original) == 'b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d'
    inputs = ROOT / 'inputs'
    inputs.mkdir(exist_ok=False)
    copied = inputs / ZIP.name
    shutil.copyfile(ZIP, copied)
    assert copied.read_bytes() == original
    dump('raw-export.json', dict(delivery=DELIVERY, candidate=CANDIDATE, base=BASE, git_argv_prefix=GIT,
                                 environment_overrides={'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0'},
                                 files=records, total_bytes=sum(row['bytes'] for row in records)))
    dump('preparation.json', dict(status='STATIC_READY', changes=len(changes), all_new_allowed=True,
                                 frozen_product_recipe_tests_unchanged=True, raw_export_files=len(records),
                                 input=dict(original=str(ZIP), copy=str(copied), bytes=len(original), sha256=sha(original)),
                                 git_batch_pid=batch.pid, git_batch_returncode=batch.returncode, git_batch_reaped=True,
                                 python=sys.version, executable=sys.executable))
    print(json.dumps(dict(status='STATIC_READY', files=len(records), bytes=sum(row['bytes'] for row in records), changes=len(changes))))

if __name__ == '__main__':
    main()
