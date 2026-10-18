"""Audited raw Git exports and static delivery sealing. No business execution."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from support import ROOT, HERE, OUT, BASE, TEST, GROUPS, index, sha, write, check_frozen

WORKFLOW = '05ba526cbd8575edc778016cf25cee13661a65c6'
MODIFIED = ('src/annotation/runtime/storage/__init__.py', 'src/annotation/runtime/storage/native.py',
    'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json')
REPORT = 'docs/tasks/A03-P2-R12-R1-unknown-projection-report.md'


def git(root, name, args, stdin=None):
    folder = root / 'git-processes' / name
    folder.mkdir(parents=True, exist_ok=False)
    argv = ['git', '-c', 'core.longpaths=true', *args]
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 30,
        'script_sha256': sha(Path(__file__).read_bytes()), 'source_index_sha256': sha((HERE / 'inputs.json').read_bytes()),
        'input_sha256': sha(stdin) if stdin is not None else None, 'retries': 0})
    if stdin is not None:
        write(folder / 'stdin.bin', stdin)
    with (folder / 'stdout.bin').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': child.pid, 'parent_pid': os.getpid(), 'started_at_ns': time.time_ns()})
        timed_out = False
        try:
            child.communicate(input=stdin, timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            child.communicate(timeout=5)
    write(folder / 'completed.json', {'pid': child.pid, 'exit_code': child.returncode, 'timeout': timed_out,
        'alive': child.poll() is None, 'ended_at_ns': time.time_ns(),
        'stdout_sha256': sha((folder / 'stdout.bin').read_bytes()), 'stderr_sha256': sha((folder / 'stderr.txt').read_bytes())})
    assert child.returncode == 0 and not timed_out, str(folder)
    return (folder / 'stdout.bin').read_bytes()


def raw_export(root, name, revision, path):
    raw = git(root, name, ['show', revision + ':' + path])
    write(root / 'raw-git' / revision / path, raw)
    return raw


def tree(raw):
    result = {}
    for item in raw.split(b'\0'):
        if item:
            head, path = item.split(b'\t', 1)
            result[path.decode('utf-8')] = head.decode('ascii')
    return result


def stage(root):
    check_frozen()
    baseline = tree(git(root, 'base-tree', ['ls-tree', '-r', '-z', BASE]))
    staged = tree(git(root, 'index-tree', ['ls-files', '--stage', '-z']).replace(b' 0\t', b'\t'))
    # ls-files has no object type; compare mode/blob explicitly.
    protected = {p: value for p, value in baseline.items() if p not in MODIFIED}
    for path, original in protected.items():
        mode, kind, blob = original.split(' ')
        assert staged[path] == mode + ' ' + blob, 'protected staged file changed: ' + path
    profile_before = json.loads(raw_export(root, 'baseline-profile', BASE, MODIFIED[2]))
    profile_after = json.loads((ROOT / MODIFIED[2]).read_bytes())
    permitted = {'@annotation/runtime/storage/__init__.py', '@annotation/runtime/storage/native.py'}
    for old, new in zip(profile_before['implementation_pins'], profile_after['implementation_pins']):
        assert old[0] == new[0]
        if old[0] in permitted:
            assert new[1] == sha((ROOT / 'src' / new[0][1:]).read_bytes())
        else:
            assert old == new
    x, y = dict(profile_before), dict(profile_after)
    x.pop('implementation_pins'); y.pop('implementation_pins')
    assert x == y
    adoption_before = json.loads(raw_export(root, 'baseline-adoption', BASE, MODIFIED[3]))
    adoption_after = json.loads((ROOT / MODIFIED[3]).read_bytes())
    assert adoption_after.pop('profile_sha256') == sha((ROOT / MODIFIED[2]).read_bytes())
    adoption_before.pop('profile_sha256')
    assert adoption_before == adoption_after
    for i, path in enumerate(MODIFIED[:2]):
        raw_export(root, 'baseline-product-' + str(i), BASE, path)
    for name, digest in (
        ('A03-P2-R12-R1-unknown-projection-repair.md', 'ec269e977ed67276e5b4d1901c32c28acd75ba44870094fa0eb5fecf0cdc0076'),
        ('A03-P2-R12-prerequisite-review-report.md', '33c224427aa86bce6d4966aa8eafd7fae51e5bf2823c09a56745d1fc6cdaff95'),
        ('A03-P2-R12-inconclusive-readback-validation.md', '15c4f65a698a86ffeb0bbde8a6c97465905bcb0fb5f9bfc1856aec522161f1df')):
        assert sha(raw_export(root, name + '-export', WORKFLOW, 'docs/tasks/' + name)) == digest
    # One raw batch export verifies Git-normalized candidate bytes against the pins and source index.
    names = sorted(p for p in staged if p in MODIFIED or p.startswith(HERE.relative_to(ROOT).as_posix() + '/') or p == TEST.relative_to(ROOT).as_posix())
    request = b''.join((':' + p + '\n').encode('utf-8') for p in names)
    response = git(root, 'staged-raw-bytes', ['cat-file', '--batch'], request)
    offset = 0
    for path in names:
        end = response.index(b'\n', offset)
        size = int(response[offset:end].split()[-1]); offset = end + 1
        raw = response[offset:offset+size]; offset += size + 1
        assert raw == (ROOT / path).read_bytes(), 'staged/raw checkout mismatch: ' + path
    assert offset == len(response)
    write(root / 'static-stage-proof.json', {'base': BASE, 'workflow': WORKFLOW, 'protected_tree_entries': len(protected),
        'protected_mode_type_blob_unchanged': True, 'staged_raw_files': len(names), 'pins_only_allowed_fields': True,
        'functional_scenes_run': 0, 'source_index_sha256': check_frozen()})


def seal(root, candidate):
    check_frozen()
    current = git(root, 'final-HEAD', ['rev-parse', 'HEAD']).decode().strip()
    assert current == candidate
    before = tree(git(root, 'final-base-tree', ['ls-tree', '-r', '-z', BASE]))
    now = tree(git(root, 'final-candidate-tree', ['ls-tree', '-r', '-z', candidate]))
    assert all(now.get(p) == value for p, value in before.items() if p not in MODIFIED)
    untracked = git(root, 'final-status', ['status', '--porcelain=v1', '-uall']).decode('utf-8')
    for line in untracked.splitlines():
        path = line[3:].strip('"')
        assert path.startswith(OUT.relative_to(ROOT).as_posix() + '/') or path == REPORT, 'post-freeze edit: ' + line
    processes = []
    for start in sorted(OUT.rglob('started.json')):
        complete = start.with_name('completed.json')
        assert complete.is_file(), 'missing completion: ' + str(start)
        data = json.loads(complete.read_bytes())
        assert data['alive'] is False
        processes.append({'start': start.relative_to(ROOT).as_posix(), 'completion': complete.relative_to(ROOT).as_posix(), **data})
    write(root / 'process-release-proof.json', {'all_own_Popen_reaped': True, 'count': len(processes), 'processes': processes})
    report = ROOT / REPORT
    for target in re.findall(r'\]\(([^)]+)\)', report.read_text(encoding='utf-8')):
        if '://' not in target and not target.startswith('#'):
            assert (report.parent / target.split('#')[0]).resolve().exists(), target
    paths = [*(ROOT / p for p in MODIFIED), *HERE.rglob('*'), TEST, *OUT.rglob('*'), report]
    files = index(p for p in paths if p.name != 'manifest.json' and '__pycache__' not in p.parts and p.suffix != '.pyc')
    write(root / 'final-file-audit.json', {'candidate_code_commit': candidate, 'base': BASE, 'workflow': WORKFLOW,
        'protected_mode_type_blob_unchanged': True, 'old_tree_entries': len(before),
        'source_frozen': True, 'report_links_exist': True, 'tracked_existing_changes': list(MODIFIED),
        'files_before_final_audit_and_manifest': len(files), 'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
    paths = [*(ROOT / p for p in MODIFIED), *HERE.rglob('*'), TEST, *OUT.rglob('*'), report]
    files = index(p for p in paths if p.name != 'manifest.json' and '__pycache__' not in p.parts and p.suffix != '.pyc')
    write(OUT / 'manifest.json', {'algorithm': 'SHA256', 'base': BASE, 'candidate_code_commit': candidate,
        'excluded': [str((OUT / 'manifest.json').relative_to(ROOT).as_posix())], 'files': files})
    print(json.dumps({'manifest_files': len(files), 'own_processes_reaped': len(processes), 'status': 'REVIEW'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('stage', 'seal'))
    parser.add_argument('--candidate')
    args = parser.parse_args()
    root = OUT / ('preflight' if args.mode == 'stage' else 'sealing')
    root.mkdir(parents=True, exist_ok=False)
    stage(root) if args.mode == 'stage' else seal(root, args.candidate)
