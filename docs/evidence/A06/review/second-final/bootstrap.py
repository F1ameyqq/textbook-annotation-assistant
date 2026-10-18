"""Independent second/final fixed raw-Git export and retained-evidence audit."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
WORKSPACE = Path('D:/1800')
REPO = 'D:/1800-worktrees/a06'
OLD = '761d9afed8b9d3d33851ad3d79b0bee7c294089d'
CANDIDATE = '43ebdd21f2dc6803ae322b95776806e167884749'
DELIVERY = 'd78737815279965f660057bea0a572b426098aaa'
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1')
GIT = ['git', '-c', 'core.longpaths=true', '-C', REPO]
READER = 'src/annotation/source/b_handoff/reader.py'

def sha(value):
    return hashlib.sha256(value).hexdigest()

def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def git(*args):
    return subprocess.run(GIT + list(args), cwd=ROOT, env=ENV, capture_output=True, check=True).stdout

def tree(commit):
    rows = {}
    for raw in git('ls-tree', '-r', '-z', '--full-tree', commit).split(b'\0'):
        if raw:
            header, path = raw.split(b'\t', 1)
            mode, kind, oid = header.decode('ascii').split()
            rows[path.decode('utf-8')] = (mode, kind, oid)
    return rows

def selected(path):
    return (path.startswith(('src/', 'examples/a06/', 'tests/fixtures/a06/', 'docs/evidence/A06/second-final/'))
            or path.startswith('tests/test_a06') or path == 'docs/tasks/A06-second-final-execution-report.md')

def main():
    code = ROOT / 'code'
    code.mkdir(exist_ok=False)
    for commit in (OLD, CANDIDATE, DELIVERY):
        assert git('cat-file', '-t', commit).strip() == b'commit'
    old_tree, new_tree = tree(OLD), tree(DELIVERY)
    old_mutations = [p for p, v in old_tree.items() if new_tree.get(p) != v]
    assert old_mutations == [READER], old_mutations
    new_paths = sorted(set(new_tree) - set(old_tree))
    def allowed(path):
        return (path.startswith(('examples/a06/', 'docs/evidence/A06/second-final/'))
                or path.startswith('tests/test_a06') or path == 'docs/tasks/A06-second-final-execution-report.md')
    assert all(allowed(p) for p in new_paths)
    frozen_delta = git('diff', '--name-status', CANDIDATE, DELIVERY, '--', 'src/', 'examples/', 'tests/')
    assert not frozen_delta
    delta = git('diff', OLD, DELIVERY, '--', READER)
    (ROOT / 'fixed-reader.diff').write_bytes(delta)
    (ROOT / 'fixed-delivery-name-status.txt').write_bytes(git('diff', '--name-status', OLD, DELIVERY))
    batch = subprocess.Popen(GIT + ['cat-file', '--batch'], cwd=ROOT, env=ENV, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    records = []
    for path, (mode, kind, oid) in sorted(new_tree.items()):
        if not selected(path):
            continue
        assert kind == 'blob' and mode in ('100644', '100755')
        batch.stdin.write((oid + '\n').encode('ascii'))
        batch.stdin.flush()
        header = batch.stdout.readline().decode('ascii').strip().split()
        assert header[:2] == [oid, 'blob'] and len(header) == 3
        size = int(header[2])
        data = batch.stdout.read(size)
        assert len(data) == size and batch.stdout.read(1) == b'\n'
        assert hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\0' + data).hexdigest() == oid
        target = code / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records.append(dict(path=path, git_blob=oid, bytes=size, sha256=sha(data)))
    batch.stdin.close()
    assert batch.wait(timeout=30) == 0 and not batch.stderr.read()
    identities = {
        'docs/tasks/A06-second-final-execution-report.md': (9325, '11fd37526062a92a034a29c5ad591449db5e33388cc16812f49c1757796ff66d'),
        'docs/evidence/A06/second-final/manifest.json': (7426, '5e09e958ed0d97ea51b855918a777182278cd9f52c9af98b630a001205e533db'),
        'docs/evidence/A06/second-final/release.json': (4188, '5cc99900a4195965cfe516f377bb30ed19fcd9e5e9b66ae227c4390209be301b'),
        READER: (None, 'a80acf8a15d7c822c82ef6720a6125e79cfcee0498ac60d3f1c7a80ca030cd61')}
    for path, (length, digest) in identities.items():
        data = (code / path).read_bytes()
        assert (length is None or len(data) == length) and sha(data) == digest
    manifest = json.loads((code / 'docs/evidence/A06/second-final/manifest.json').read_bytes())
    for row in manifest['files']:
        data = (code / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    first_root = WORKSPACE / 'docs/evidence/A06/review/candidate1-761d9afe'
    old_bindings = {'docs/tasks/A06-review-report.md': 'fdefde2e92095b9e922ae264a6b9595af5d93ee4c6dd5f5f980e941a031c0ae4',
                    'docs/evidence/A06/review/candidate1-761d9afe/review-manifest.json': 'b3842a023b39c1f26ba42db6eab93329adfae4ad084e756b09cb67a780af5624',
                    'docs/evidence/A06/review/candidate1-761d9afe/release.json': '3917bf27b1d013dad625b2bfdb9b779fcc877dabe15380b147f8405399f64ea9'}
    assert all(sha((WORKSPACE / p).read_bytes()) == h for p, h in old_bindings.items())
    old_manifest = json.loads((first_root / 'review-manifest.json').read_bytes())
    for row in old_manifest['files']:
        data = (WORKSPACE / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    old_source = (first_root / 'code' / READER).read_text(encoding='utf-8')
    new_source = (code / READER).read_text(encoding='utf-8')
    old_functions = {n.name: ast.get_source_segment(old_source, n) for n in ast.parse(old_source).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    new_functions = {n.name: ast.get_source_segment(new_source, n) for n in ast.parse(new_source).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    unchanged_functions = [name for name in old_functions if old_functions[name] == new_functions[name]]
    changed_functions = [name for name in old_functions if old_functions[name] != new_functions[name]]
    assert changed_functions == ['_receive_package']
    reconstructed = new_functions['_receive_package'].replace(
        '        result_version_check = _validate_stage_result(stage["stage_id"], result, name + "#/payload/result")\n', '').replace(
        '"final_route": final_route,\n                               "result_version_check": result_version_check})', '"final_route": final_route})')
    assert reconstructed == old_functions['_receive_package']
    inputs = ROOT / 'inputs'
    inputs.mkdir(exist_ok=False)
    original = WORKSPACE / '.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip'
    data = original.read_bytes()
    assert len(data) == 11681712 and sha(data) == 'b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d'
    shutil.copyfile(original, inputs / original.name)
    dump('raw-export.json', dict(delivery=DELIVERY, candidate=CANDIDATE, previous_delivery=OLD, git_argv_prefix=GIT,
                                 files=records, total_bytes=sum(r['bytes'] for r in records),
                                 git_batch_pid=batch.pid, git_batch_reaped=True, environment_overrides={'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0'}))
    dump('inheritance-audit.json', dict(status='STATIC_READY', previous_report_bindings=old_bindings,
                                       old_manifest_files_verified=len(old_manifest['files']),
                                       old_manifest_bytes_verified=sum(r['bytes'] for r in old_manifest['files']),
                                       all_previous_git_paths_unchanged_except_reader=True,
                                       unchanged_reader_functions=unchanged_functions, changed_reader_functions=changed_functions,
                                       receive_function_exactly_reconstructed_after_removing_F01_wiring=True,
                                       new_stage_validator_only=True, new_paths=new_paths,
                                       frozen_product_recipes_tests_unchanged=True,
                                       author_manifest_members_verified=len(manifest['files']),
                                       author_manifest_bytes_verified=sum(r['bytes'] for r in manifest['files']),
                                       inherited_without_rerun=['bad-resource', 'stale-check', 'top-level-archive-version-matrix', 'c01-normal', 'c01-exception', 'c01-unknown']))
    print(json.dumps(dict(status='STATIC_READY', exported_files=len(records), author_manifest_members=len(manifest['files']),
                          first_review_members_preserved=len(old_manifest['files']), old_mutations=old_mutations)))

if __name__ == '__main__':
    main()
