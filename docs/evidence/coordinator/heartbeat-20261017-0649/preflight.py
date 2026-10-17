"""Coordinator byte/scope/release preflight; no product imports or DB access."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('D:/1800')
OUT = ROOT / 'docs/evidence/coordinator/heartbeat-20261017-0649'
WT = Path('C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800')
COMMIT = '6c8137a4fadddc01a47906d564ab3460277c8958'
BASE = '76898657e76ac2db071327e90c6ca5031d17571f'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def write(name, value):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def git(root, *args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(root), *args])

def check_manifest(root, relative, report, expected_manifest, expected_report):
    b = (root / relative).read_bytes()
    assert sha(b) == expected_manifest
    assert sha((root / report).read_bytes()) == expected_report
    m = json.loads(b)
    paths = set()
    for e in m['files']:
        p = (root / e['path']).resolve()
        assert p.is_relative_to(root) and e['path'] not in paths
        paths.add(e['path'])
        v = p.read_bytes()
        assert len(v) == e['bytes'] and sha(v) == e['sha256'], e['path']
    return m

def raw_git_matches(root, revision, entries):
    p = subprocess.Popen(['git', '-C', str(root), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for e in entries:
            p.stdin.write((revision + ':' + e['path'] + '\n').encode())
            p.stdin.flush()
            header = p.stdout.readline().split()
            assert len(header) == 3 and header[1] == b'blob', e['path']
            b = p.stdout.read(int(header[2]))
            assert p.stdout.read(1) == b'\n'
            assert len(b) == e['bytes'] and sha(b) == e['sha256'], e['path']
        p.stdin.close()
        assert p.wait(timeout=10) == 0
    finally:
        if p.poll() is None:
            p.terminate()
            p.wait(timeout=10)

a03_manifest = 'docs/evidence/A03/review/P2-R1-proposal/sha256-manifest.json'
a03_report = 'docs/tasks/A03-P2-R1-proposal-review-report.md'
m03 = check_manifest(ROOT, a03_manifest, a03_report,
    '68b7c8f16f0a5973fa20e962525b8dab12b095b85b2343e95e6373ae38d152ac',
    '265d5b8a67548b4e6322c105859475a852ca6d82bc8c0c04ec10bf2eedb411f0')
assert all(e['path'].startswith('docs/evidence/A03/review/P2-R1-proposal/') or e['path'] == a03_report for e in m03['files'])
argv = [sys.executable, '-B', str(ROOT / 'docs/evidence/A03/review/P2-R1-proposal/scripts/verify_archive.py')]
p = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
(OUT / 'A03-archive-stdout.log').write_bytes(p.stdout)
(OUT / 'A03-archive-stderr.log').write_bytes(p.stderr)
write('A03-archive-command.json', {'argv': argv, 'exit_code': p.returncode, 'scope': 'read-only archive verifier; no finalize/product/DB'})
assert p.returncode == 0
r03 = {'at': datetime.now(timezone.utc).isoformat(), 'decision': 'REWORK_ARCHIVE_VERIFIED', 'reviewed_proposal': m03['proposal_commit'], 'manifest_entries': len(m03['files']), 'report_sha256': sha((ROOT / a03_report).read_bytes()), 'manifest_sha256': sha((ROOT / a03_manifest).read_bytes()), 'read_only_archive_command_exit': p.returncode, 'session_release_basis': 'Completed independent turn and frozen synchronous static-run exit record; no OS scan.', 'product_tests_run': False, 'functional_acceptance': False, 'i01_released': False}
write('A03-review-preflight.json', r03)

a04_manifest = 'docs/evidence/A04/execution/coordinate-R3/sha256-manifest.json'
a04_report = 'docs/tasks/A04-coordinate-R3-execution-report.md'
assert git(WT, 'rev-parse', 'HEAD').decode().strip() == COMMIT
assert git(WT, 'status', '--porcelain') == b''
m04 = check_manifest(WT, a04_manifest, a04_report,
    '634c254021f91ec2f6ed2b0737a3b234f4fb382c4e8878490abedf3b428d1b92',
    '9e80fb8e715da518b1e999c951b9798ad5cb0b7dbfc12c09d325ea0f5f850334')
entries = m04['files'] + [{'path': a04_manifest, 'bytes': (WT / a04_manifest).stat().st_size, 'sha256': sha((WT / a04_manifest).read_bytes())}]
raw_git_matches(WT, COMMIT, entries)
changes = git(WT, 'diff', '--name-only', BASE, COMMIT).decode().splitlines()
allowed_files = {'src/annotation/source/usense/parser.py', 'src/annotation/source/usense/png_pixels.py', 'tests/test_a04_png_r3.py', a04_report}
assert all(p in allowed_files or p.startswith('docs/evidence/A04/execution/coordinate-R3/') for p in changes)
release = json.loads((WT / 'docs/evidence/A04/execution/coordinate-R3/process-release.json').read_bytes())
assert release['all_recorded_workers_ended'] and release['network_browser_platform_OCR_model_actions'] == 0
assert release['profile_acquired'] is False and release['profile_current_state'] == 'NOT_INSPECTED'
r04 = {'at': datetime.now(timezone.utc).isoformat(), 'decision': 'FROZEN_DELIVERY_INTEGRITY_VERIFIED', 'base_commit': BASE, 'commit': COMMIT, 'implementation_commit': m04['implementation_commit'], 'manifest_entries_verified_disk_and_raw_git': len(m04['files']), 'manifest_self_verified': True, 'manifest_sha256': sha((WT / a04_manifest).read_bytes()), 'report_sha256': sha((WT / a04_report).read_bytes()), 'changed_path_count': len(changes), 'out_of_scope_paths': [], 'clean_worktree': True, 'release_recorded_workers': release['recorded_owned_pid_count'], 'session_release_basis': 'Completed execution turn and byte-verified author release/exit records; no current OS/profile inspection.', 'product_tests_run': False, 'independent_acceptance': False, 'live_R01_R06': 'BLOCKED'}
write('A04-delivery-preflight.json', r04)
print(json.dumps({'A03': r03, 'A04': r04}, ensure_ascii=False))
