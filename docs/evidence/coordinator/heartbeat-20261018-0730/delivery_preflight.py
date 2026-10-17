"""R11 frozen delivery checks only; no product imports or functional execution."""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path('D:/1800')
SOURCE = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
OUT = ROOT / 'docs/evidence/coordinator/heartbeat-20261018-0730'
BASE = '1c26b4a8eb378af33e57668472d2071e9ea6afff'
TARGET = 'cc5966dc58c62017a27266c40ca0cedc5c68485c'
PREFIX = 'docs/evidence/A03/execution/P2-R11-crash-cuts/'
REPORT = 'docs/tasks/A03-P2-R11-crash-cuts-report.md'

def git(*args, data=None):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=SOURCE, input=data)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def tree(commit):
    rows = {}
    for raw in git('ls-tree', '-rz', commit).split(b'\0'):
        if raw:
            meta, path = raw.split(b'\t', 1)
            rows[path.decode()] = meta.decode().split()
    return rows

assert git('rev-parse', 'HEAD').decode().strip() == TARGET
assert not git('status', '--porcelain=v1', '--untracked-files=all').strip()
assert git('rev-parse', TARGET + '^').decode().strip() == BASE
before, after = tree(BASE), tree(TARGET)
assert all(after.get(p) == v for p, v in before.items())
added = set(after) - set(before)
assert all(p == REPORT or p == 'tests/test_a03_p2_r11_crash_cuts.py' or
           p.startswith(PREFIX) or p.startswith('examples/a03/P2-R11-crash-cuts/') for p in added)
manifest_raw = (SOURCE / (PREFIX + 'manifest.json')).read_bytes()
manifest = json.loads(manifest_raw)
entries = manifest['entries']
assert len(entries) == len({r['path'] for r in entries})
assert {r['path'] for r in entries} | {PREFIX + 'manifest.json'} == added
batch = git('cat-file', '--batch', data=('\n'.join(after[p][2] for p in sorted(added)) + '\n').encode())
offset = 0
git_raw = {}
for p in sorted(added):
    end = batch.index(b'\n', offset)
    size = int(batch[offset:end].split()[2])
    raw = batch[end + 1:end + 1 + size]
    assert raw == (SOURCE / p).read_bytes(), p
    git_raw[p] = raw
    offset = end + size + 2
assert offset == len(batch)
for r in entries:
    raw = git_raw[r['path']]
    assert len(raw) == r['bytes'] and sha(raw) == r['sha256'], r['path']

release_raw = git_raw[PREFIX + 'process-release.json']
release = json.loads(release_raw)
processes = []
for r in release['records']:
    start = json.loads(git_raw[PREFIX + r['path']])
    end = json.loads(git_raw[PREFIX + str(Path(r['path']).with_name('completed.json')).replace('\\', '/')])
    assert r['pid'] == start['pid']
    expected_exit = 90 if '-crash/' in r['path'] else 0
    assert r['exit_code'] == end['exit_code'] == expected_exit
    assert end['pid'] == start['pid'] == r['pid']
    assert r['alive'] is False and end['alive'] is False
    assert not r['timed_out'] and not end.get('timed_out', end.get('timeout', False))
    processes.append({'pid': r['pid'], 'record': r['path'], 'exit_code': expected_exit, 'alive': False})
assert len(processes) == 19 and len({r['pid'] for r in processes}) == 19
assert sum(r['exit_code'] == 90 for r in processes) == 4
os_receipt = json.loads(git_raw[PREFIX + 'process-os-readback.json'])
assert os_receipt['all_recorded_ids_absent']
assert {r['pid'] for r in processes} <= {r['pid'] for r in os_receipt['records'] if not r['present']}
ids = ','.join(str(r['pid']) for r in os_receipt['records'])
ps = "$ErrorActionPreference='Stop'; $rows = @(" + ids + ") | ForEach-Object { $p = Get-Process -Id $_ -ErrorAction SilentlyContinue; [pscustomobject]@{pid=$_;present=($null -ne $p)} }; ConvertTo-Json -InputObject @($rows) -Compress"
live = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', ps]).decode('utf-8-sig'))
assert all(not r['present'] for r in live), 'registered PID currently present; inspect identity before dispatch'

task = 'docs/tasks/A03-P2-R11-crash-cut-validation.md'
task_raw = git('cat-file', 'blob', 'bc0074bc8b852ef14012ee338bf3153ccb1f932b:' + task)
assert task_raw == git_raw[PREFIX + 'inputs/A03-P2-R11-crash-cut-validation.md']
assert sha(task_raw) == 'ef09227381b7b8f2f0e9c9f590b67fb63dd898ca9758cab490e3044c2cc3f500'
result = {
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'source_worktree': SOURCE.as_posix(), 'base_commit': BASE, 'target_commit': TARGET,
    'root_head_before_action': subprocess.check_output(['git', '-c', 'core.longpaths=true', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
    'decision': 'READY_FOR_INDEPENDENT_REVIEW_NOT_ACCEPTED',
    'working_tree_clean': True, 'base_entries_unchanged': len(before),
    'added_raw_blobs_verified': len(added), 'manifest_entries_verified': len(entries),
    'report': REPORT, 'report_sha256': sha(git_raw[REPORT]),
    'manifest': PREFIX + 'manifest.json', 'manifest_sha256': sha(manifest_raw),
    'process_release': PREFIX + 'process-release.json', 'process_release_sha256': sha(release_raw),
    'process_records_checked': processes, 'current_recorded_pid_check': live,
    'author_outcome': json.loads(git_raw[PREFIX + 'bounded-outcome.json']),
    'author_preservation_limit': json.loads(git_raw[PREFIX + 'stage-binary-preservation.json']),
    'task_document': task, 'task_sha256': sha(task_raw),
    'checks': ['exact clean HEAD and parent', 'all old raw Git mode/type/blob entries unchanged',
               'added paths restricted and complete manifest coverage', 'manifest and raw target blob bytes',
               'recorded start/completion/release crosschecks and current OS PID absence', 'raw dispatched task identity'],
    'product_imports': 0, 'functional_runs': 0, 'product_changes': 0, 'platform_actions': 0,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION', 'I01': 'NOT_RELEASED',
}
with (OUT / 'delivery-preflight.json').open('xb') as f:
    f.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps({k: result[k] for k in ('decision', 'base_entries_unchanged', 'added_raw_blobs_verified', 'manifest_entries_verified', 'report_sha256', 'manifest_sha256', 'process_release_sha256')}, ensure_ascii=False))
