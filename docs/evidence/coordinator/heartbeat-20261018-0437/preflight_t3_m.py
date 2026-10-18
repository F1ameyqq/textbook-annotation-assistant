"""Admit a frozen failed M delivery for static independent review only."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WT = Path('D:/1800-worktrees/a03-t3')
OUT = Path(__file__).with_name('T3-M-delivery-preflight.json')
assert not OUT.exists()
target = '3f39a117b1b98e85c5a449a07f13b3490ef77e18'
candidate = 'c73070884476dc2edcb952d88e4f6ed356b74ae8'
base = '62a023a1c88c20d884a61f38d1ad995b0908b74c'
result = {'target': target, 'candidate': candidate, 'base': base, 'commands': [], 'business_calls': 0, 'product_imports': 0, 'SQL_calls': 0}
def save():
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
def git(*args):
    row = {'argv': ['git', '-c', 'core.longpaths=true', *args], 'cwd': str(WT), 'timeout_seconds': 60, 'retries': 0, 'preregistered_at_ns': time.time_ns()}
    result['commands'].append(row)
    save()
    p = subprocess.Popen(row['argv'], cwd=WT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    row.update(pid=p.pid, started_at_ns=time.time_ns())
    save()
    out, err = p.communicate(timeout=60)
    row.update(exit_code=p.returncode, waited=True, ended_at_ns=time.time_ns(), stdout=out.decode('utf8', 'replace'), stderr=err.decode('utf8', 'replace'))
    save()
    assert p.returncode == 0
    return out.decode('utf8').strip()
assert git('rev-parse', 'HEAD') == target
assert git('status', '--porcelain') == ''
assert git('diff', '--name-only', candidate, target, '--', 'src', 'tests', 'examples/a03/T3-closure/run.py', 'examples/a03/T3-closure/prepare.py', 'examples/a03/T3-closure/static_check.py', 'examples/a03/T3-closure/inputs') == ''
changed = git('diff', '--name-only', base, target).splitlines()
allowed = {
    'src/annotation/quality/synthetic_precheck.py', 'src/annotation/runtime/storage/__init__.py',
    'src/annotation/runtime/storage/native.py', 'src/annotation/runtime/storage/holds.py',
    'src/annotation/contracts/a03_native/__init__.py', 'src/annotation/contracts/a03_native/_closure.py',
    'src/annotation/contracts/recovery.py', 'tests/test_a03_t3_closure.py',
    'docs/tasks/A03-T3-M-adoption.md', 'docs/tasks/A03-T3-M-execution-report.md',
}
allowed.update('src/annotation/contracts/a03_native/data/' + p for p in ['oracle.json', 'api.json', 'profile.json', 'adoption.json', 'schemas/prefix.json', 'schemas/basis.json', 'schemas/fact.json'])
assert all(p in allowed or p.startswith(('examples/a03/T3-closure/', 'docs/evidence/A03/T3/execution/M/')) for p in changed)

row = {'argv': ['git', '-c', 'core.longpaths=true', 'cat-file', '--batch'], 'cwd': str(WT), 'preregistered_at_ns': time.time_ns(), 'scope': 'Fixed manifest and raw blobs; deterministic object reads only'}
result['commands'].append(row)
save()
p = subprocess.Popen(row['argv'], cwd=WT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
row.update(pid=p.pid, started_at_ns=time.time_ns())
save()
stream = hashlib.sha256()
cache = {}
def blob(path):
    if path in cache:
        return cache[path]
    p.stdin.write((target + ':' + path + '\n').encode())
    p.stdin.flush()
    header = p.stdout.readline()
    parts = header.split()
    assert len(parts) == 3 and parts[1] == b'blob', (path, header)
    data = p.stdout.read(int(parts[2]))
    tail = p.stdout.read(1)
    assert tail == b'\n' and len(data) == int(parts[2])
    stream.update(header + data + tail)
    cache[path] = data
    return data
try:
    manifest_path = 'docs/evidence/A03/T3/execution/M/manifest.json'
    manifest_bytes = blob(manifest_path)
    manifest = json.loads(manifest_bytes)
    assert manifest['candidate'] == candidate and manifest['K'] == base and manifest['status'] == 'REWORK'
    assert len(manifest['files']) == 263
    for item in manifest['files']:
        data = blob(item['path'])
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
    report = 'docs/tasks/A03-T3-M-execution-report.md'
    report_sha = hashlib.sha256(blob(report)).hexdigest()
    closure = json.loads(blob('docs/evidence/A03/T3/execution/M/closure-verification.json'))
    assert closure['dispatch'] == closure['target_effects'] == 2
    assert closure['fresh_targets'] == 1 and len(closure['not_run']) == 4
    assert closure['owner_release']['owner_released']
    assert closure['business_reruns'] == 0
    assert closure['product_changes_after_failure'] == 0
    for item in closure['processes']:
        actual = json.loads(blob(item['completion']))
        assert actual == item['actual'] and actual['alive'] is False
        assert actual['exit_code'] in (0, 1)
    for sidecar, expected in [
        ('runtime.sqlite3', '089b73b935751ae33cce3fabbdf22585496925f104352e61ab2cf4ff3e7d351e'),
        ('runtime.sqlite3-journal', 'da0c72a2ad0c543b1c7351b7737812a6749e7350a3bc716fe921f02b265552e1'),
        ('target.sqlite3', 'a1901643fd8b1543142eab53342495b256b24aae878e4e082fdf554a7fefcf8c'),
    ]:
        matches = [v for v in manifest['files'] if v['sha256'] == expected and 'crash-bytes/' in v['path']]
        assert len(matches) == 1, sidecar
finally:
    p.stdin.close()
    exit_code = p.wait(timeout=60)
    stderr = p.stderr.read()
    row.update(exit_code=exit_code, waited=True, ended_at_ns=time.time_ns(), object_count=len(cache), stdout_sha256=stream.hexdigest(), stderr=stderr.decode('utf8', 'replace'))
    assert exit_code == 0
    save()
result.update(status='FROZEN_REWORK_DELIVERY_ADMITTED_FOR_STATIC_REVIEW', manifest=manifest_path,
    manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(), raw_members_verified=263,
    report=report, report_sha256=report_sha, changed_path_count=len(changed), allowed_scope_only=True,
    candidate_product_inputs_driver_unchanged=True, working_tree_clean=True, recorded_processes_exited=True,
    owner_release_recorded=True, root_cause='NOT_PROVEN', failed_case='M1_TIMEOUT_45_SECONDS',
    dispatch=2, target_effects=2, other_cases='NOT_RUN', functional_acceptance=False,
    historical_missing_wrapper_streams_preserved=True, new_business_or_timeout_extension_authorized=False)
save()
print(json.dumps({k:result[k] for k in ['status','manifest_sha256','report_sha256','raw_members_verified']}))
