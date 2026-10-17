"""Bounded coordinator audit and one unchanged offline reproduction."""
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
REVIEW = ROOT / 'docs/evidence/A04/review/coordinate-R3'
TARGET = '6c8137a4fadddc01a47906d564ab3460277c8958'
STAGE = ROOT / '.local/stages/A04-coordinator/coordinate-R3/raw git with spaces'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def git_blobs(paths):
    proc = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT,
                          input=('\n'.join(TARGET + ':' + p for p in paths) + '\n').encode(),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    stream = io.BytesIO(proc.stdout)
    result = {}
    for name in paths:
        header = stream.readline().split()
        assert len(header) == 3 and header[1] == b'blob', (name, header)
        result[name] = stream.read(int(header[2]))
        assert stream.read(1) == b'\n'
    assert not stream.read()
    return result


manifest_bytes = (REVIEW / 'sha256-manifest.json').read_bytes()
manifest = json.loads(manifest_bytes)
assert manifest['target_commit'] == TARGET
assert manifest['OFFLINE_R3'] == 'ACCEPTED' and manifest['A04_OVERALL'] == 'BLOCKED'
assert len({x['path'] for x in manifest['files']}) == len(manifest['files'])
for item in manifest['files']:
    path = (ROOT / item['path']).resolve()
    assert ROOT in path.parents
    data = path.read_bytes()
    assert sha(data) == item['sha256'] and len(data) == item['bytes'], item['path']

release = json.loads((REVIEW / 'self-release.json').read_bytes())
assert release['all_original_workers_exited']
assert all(x['original_process_exited'] for x in release['observations'])
assert all(x['data']['all_reaped'] for x in release['groups'])
assert release['browser_network_platform_login_profile_credentials_model_book_actions'] == 0

fm = json.loads((REVIEW / 'inputs/frozen-tree-manifest.json').read_bytes())
archive_bytes = (REVIEW / 'inputs/frozen-inputs.tar.gz').read_bytes()
assert sha(archive_bytes) == fm['archive_sha256']
files = {x['path']: x for x in fm['files']}
blobs = git_blobs(list(files))
with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode='r:gz') as archive:
    regular = [m for m in archive.getmembers() if m.isfile()]
    assert {m.name for m in regular} == set(files)
    assert all(m.isfile() or m.isdir() for m in archive.getmembers())
    for member in regular:
        path = PurePosixPath(member.name)
        assert not path.is_absolute() and '..' not in path.parts
        data = archive.extractfile(member).read()
        expected = files[member.name]
        assert data == blobs[member.name]
        assert sha(data) == expected['sha256'] and len(data) == expected['bytes']

STAGE.mkdir(parents=True, exist_ok=False)
for name, data in blobs.items():
    path = STAGE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

args = [sys.executable, '-B', str(REVIEW / 'inputs/unchanged-R2-repro/repro_incomplete_rows.py'),
        '--root', str(STAGE), '--output', str(OUT / 'exact-reproduction')]
completed = subprocess.run(args, cwd=STAGE.parent, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=45)
(OUT / 'stdout.txt').write_bytes(completed.stdout)
(OUT / 'stderr.txt').write_bytes(completed.stderr)
write_json(OUT / 'process.json', {'argv': args, 'cwd': str(STAGE.parent),
           'returncode': completed.returncode, 'reaped': True,
           'stdout_sha256': sha(completed.stdout), 'stderr_sha256': sha(completed.stderr)})
result = json.loads((OUT / 'exact-reproduction/result.json').read_bytes())
assert completed.returncode == 0
assert result['sha256'] == '205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd'
assert result['public_cli_returncode'] == 2 and not result['final_bundle_created']
assert not result['public_loader_accepted'] and not result['defect_reproduced']
assert not (OUT / 'exact-reproduction/output').exists()
checks = {'at': datetime.now(timezone.utc).isoformat(), 'target_commit': TARGET,
          'review_manifest_sha256': sha(manifest_bytes), 'review_entries_verified': len(manifest['files']),
          'report_sha256': sha((ROOT / 'docs/tasks/A04-coordinate-R3-review-report.md').read_bytes()),
          'raw_git_archive_files_verified': len(files), 'review_release_recorded_identities': len(release['observations']),
          'scope': 'Review byte audit and one exact offline public-CLI rejection; no full-suite rerun.',
          'reproduction': result, 'product_changes': False, 'platform_actions': 0,
          'paid_model_calls': 0, 'OFFLINE_R3': 'ACCEPTED', 'A04_OVERALL': 'BLOCKED'}
write_json(OUT / 'checks.json', checks)
print(json.dumps({k: checks[k] for k in ['review_entries_verified', 'raw_git_archive_files_verified', 'OFFLINE_R3', 'A04_OVERALL']}))
