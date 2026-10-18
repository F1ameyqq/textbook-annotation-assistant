"""File/Git-only M failure seal. No product imports, SQLite opens or M replay."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'docs/evidence/A03/T3/execution/M'
CANDIDATE = 'c73070884476dc2edcb952d88e4f6ed356b74ae8'
K = '62a023a1c88c20d884a61f38d1ad995b0908b74c'
REPORT = 'docs/tasks/A03-T3-M-execution-report.md'
PRODUCTS = {
    'src/annotation/quality/synthetic_precheck.py',
    'src/annotation/runtime/storage/__init__.py',
    'src/annotation/runtime/storage/native.py',
    'src/annotation/runtime/storage/holds.py',
    'src/annotation/contracts/a03_native/__init__.py',
    'src/annotation/contracts/a03_native/_closure.py',
    'src/annotation/contracts/recovery.py',
    *('src/annotation/contracts/a03_native/data/' + name for name in (
        'oracle.json', 'api.json', 'profile.json', 'adoption.json',
        'schemas/prefix.json', 'schemas/basis.json', 'schemas/fact.json')),
}
GIT_CALLS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def load(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def git(*args, data=None):
    argv = ['git', '-c', 'core.longpaths=true', '-C', str(ROOT), *args]
    started = time.time_ns()
    process = subprocess.Popen(argv, cwd=str(ROOT), stdin=subprocess.PIPE if data is not None else None,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate(data, timeout=45)
    GIT_CALLS.append({'argv': argv, 'cwd': str(ROOT), 'pid': process.pid,
                      'started_at_ns': started, 'finished_at_ns': time.time_ns(),
                      'exit_code': process.returncode, 'alive': process.poll() is None,
                      'waited': True, 'stdout_sha256': sha(out), 'stderr': err.decode('utf-8', 'replace')})
    assert process.returncode == 0, (argv, err.decode('utf-8', 'replace'))
    return out


def blobs(specs):
    packed = git('cat-file', '--batch', data=''.join(s + '\n' for s in specs).encode('utf-8'))
    offset, result = 0, {}
    for spec in specs:
        end = packed.index(b'\n', offset)
        header = packed[offset:end].split()
        assert len(header) == 3 and header[1] == b'blob', (spec, header)
        size = int(header[2]); offset = end + 1
        result[spec] = packed[offset:offset + size]
        offset += size + 1
    assert offset == len(packed)
    return result


def allowed(path):
    return (path in PRODUCTS or path in (REPORT, 'docs/tasks/A03-T3-M-adoption.md',
            'tests/test_a03_t3_closure.py') or path.startswith(('examples/a03/T3-closure/',
            'docs/evidence/A03/T3/execution/M/')))


def verify_index():
    manifest = load(EVIDENCE / 'manifest.json')
    members = manifest['files']
    specs = [':' + item['path'] for item in members]
    indexed = blobs(specs)
    for item, spec in zip(members, specs):
        assert sha(indexed[spec]) == item['sha256'], item['path']
        assert sha((ROOT / item['path']).read_bytes()) == item['checkout_sha256'], item['path']
    actual = {relative(p) for p in EVIDENCE.rglob('*') if p.is_file()}
    expected = {item['path'] for item in members if item['path'].startswith(relative(EVIDENCE) + '/')}
    assert actual == expected | {relative(EVIDENCE / 'manifest.json')}, actual ^ expected
    print(json.dumps({'status': 'STAGED_RAW_MANIFEST_MATCH_ONLY', 'files': len(members),
                      'product_imports': 0, 'sqlite_connections': 0, 'business_runs': 0}))


def create():
    assert not (EVIDENCE / 'manifest.json').exists()
    assert not (EVIDENCE / 'closure-verification.json').exists()
    assert git('branch', '--show-current').decode().strip() == 'codex/a03-t3-closure'
    assert git('rev-parse', 'HEAD').decode().strip() == CANDIDATE
    candidate_paths = git('diff', '--name-only', K, CANDIDATE).decode().splitlines()
    changed = git('diff', '--cached', '--name-only', K).decode().splitlines()
    assert all(allowed(p) for p in changed), changed
    assert not git('diff', '--name-only'), 'Unstaged tracked changes'
    assert not git('diff', '--cached', '--name-only', CANDIDATE, '--', 'src',
                   'examples/a03/T1-capture/capture.py')
    assert not git('diff', '--cached', '--check')
    specs = [spec for p in candidate_paths for spec in (CANDIDATE + ':' + p, ':' + p)]
    pinned = blobs(specs)
    for p in candidate_paths:
        assert pinned[CANDIDATE + ':' + p] == pinned[':' + p], p

    batch = EVIDENCE / 'validation/author-01'
    identities = load(batch / 'runtime-identities.json')
    assert identities['candidate'] == CANDIDATE and identities['raw_equals_execution']
    view = batch / 'runtime-view'
    view_specs = [CANDIDATE + ':' + f['path'] for f in identities['files']]
    raw_view = blobs(view_specs)
    for f, spec in zip(identities['files'], view_specs):
        assert sha(raw_view[spec]) == f['raw_sha256'] == sha((view / f['path']).read_bytes())
    imports = load(batch / 'cases/M1/imports-execute-before.json')
    for mod in imports['modules']:
        file = Path(mod['file']).resolve()
        file.relative_to(view.resolve())
        assert sha(file.read_bytes()) == mod['sha256']
    assert imports['capture_sha256'] == sha(Path(imports['capture_file']).read_bytes())
    assert imports['capture_sha256'] == '3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b'
    private = view / 'src/annotation/contracts/a03_native'
    profile = load(private / 'data/profile.json')
    for p, expected in profile['implementation_pins']:
        file = view / ('src/' + p[1:]) if p.startswith('@') else private / p
        assert sha(file.read_bytes()) == expected, p
    for p, expected in profile['schema_pins']:
        assert sha((private / 'data' / p).read_bytes()) == expected, p
    for name in ('api', 'oracle'):
        assert profile[name + '_sha256'] == sha((private / ('data/' + name + '.json')).read_bytes())
    assert load(private / 'data/adoption.json')['profile_sha256'] == sha((private / 'data/profile.json').read_bytes())
    preflight = load(EVIDENCE / 'preflight/static-and-input-index.json')
    for f in preflight['files']:
        assert sha((ROOT / f['path']).read_bytes()) == f['checkout_sha256'], f['path']
    for f in preflight['fixtures']:
        assert sha((view / f['path']).read_bytes()) == f['sha256'], f['path']

    process_records = []
    for path in sorted(EVIDENCE.rglob('completed.json')):
        completed = load(path); started = load(path.parent / 'started.json')
        pre = load(path.parent / 'preregistered.json')
        assert completed['pid'] == started['pid'] and completed['alive'] is False
        assert isinstance(completed['exit_code'], int)
        assert (path.parent / 'stdout.txt').is_file() and (path.parent / 'stderr.txt').is_file()
        if 'waited' in completed:
            assert completed['waited'] is True
        process_records.append({'completion': relative(path), 'preregistration': relative(path.parent / 'preregistered.json'),
                                'argv': pre['argv'], 'actual': completed,
                                'wait_field': completed.get('waited', 'NOT_RECORDED_NATIVE_CHILD_EXIT_OBSERVED')})
    assert {x['actual']['pid'] for x in process_records} == {54532, 40560, 70408, 30264, 56488, 60108}
    for g in identities['git_processes']:
        assert g['exit_code'] == 0 and g['waited'] is True
    matrix = load(batch / 'matrix.json')
    assert len(matrix['actual']) == 1 and matrix['actual'][0]['case'] == 'M1'
    assert matrix['not_run'] == ['M2-sufficient', 'M2-insufficient', 'M3-new-plan', 'M3-final-drift']
    worker = load(batch / 'cases/M1/processes/execute/completed.json')
    assert worker['pid'] == 54532 and worker['timeout'] and worker['exit_code'] == 1
    assert not (batch / 'cases/M1/processes/finish').exists()

    crash = load(EVIDENCE / 'failure-closure/crash-byte-index.json')
    assert crash['sidecars_deleted'] is False and crash['original_sqlite_opened'] is False
    assert len(crash['files']) == 3
    for item in crash['files']:
        assert sha(Path(item['retained']).read_bytes()) == item['sha256']
    assert (EVIDENCE / 'failure-closure/pre-recovery-SQL-unavailable.json').is_file()
    failed_capture = load(batch / 'cases/M1/captures/before-cleanup-claim/capture.json')
    assert 'unexpected sidecar' in failed_capture['error']
    before = load(EVIDENCE / 'failure-closure-02/before-owner-release.json')
    after = load(EVIDENCE / 'failure-closure-02/after-owner-release.json')
    proof = load(EVIDENCE / 'failure-closure-02/owner-release-proof.json')
    final_capture = batch / 'cases/M1/captures/after-cleanup-release-02'
    sql = load(final_capture / 'SQL.json'); rt = sql['runtime']['tables']; target = sql['target']['tables']
    for name in ('books', 'plans', 'actions', 'intents', 'permits'):
        assert after['SQL'][name] == rt[name]
    assert before['status']['actions'] == rt['actions']
    assert after['SQL']['target_effects'] == target['effects']
    assert before['target_public_context']['effect_log'] == [json.loads(row['body']) for row in target['effects']]
    assert before['status']['event_head']['sequence'] == 15 and after['status']['event_head']['sequence'] == 18
    assert [x['state'] for x in sorted(rt['actions'], key=lambda x: x['position'])] == ['APPLIED', 'APPLIED', 'RESERVED']
    assert len(rt['intents']) == len(rt['permits']) == len(target['effects']) == 2
    assert len(target['observations']) == 6 and len(rt['native_report_reads']) == 0
    assert len([e for e in after['status']['events'] if e['event'] == 'DISPATCH_STARTED']) == 2
    assert all(b['owner'] is None and b['phase'] == 'RELEASED' and b['lease'] == 0 for b in rt['books'])
    assert proof['owner_released'] and proof['public_actions_and_effect_log_unchanged']
    assert proof['dispatch'] == proof['reconcile'] == proof['new_PRE_or_plan'] == 0
    for stage in ('initialized', 'before-execute', 'after-cleanup-release-02'):
        capture = load(batch / ('cases/M1/captures/' + stage + '/capture.json'))
        for rec in capture['records']:
            assert sha(Path(rec['retained']).read_bytes()) == rec['sha256']
    for file in after['imports'].values():
        Path(file).resolve().relative_to(view.resolve())

    report = (ROOT / REPORT).read_text(encoding='utf-8')
    for label, link in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', report):
        assert (ROOT / REPORT).parent.joinpath(link).exists(), (label, link)
    for p in (ROOT / 'examples/a03/T3-closure').glob('*.py'):
        ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
    summary = {'status': 'REWORK_FILE_SEAL_ONLY', 'candidate': CANDIDATE, 'K': K,
        'business_reruns': 0, 'business_corrections': 0, 'tests': 'NOT_RUN_AFTER_M1_FAILURE',
        'product_changes_after_failure': 0, 'source_and_runtime_view': 'EXACT_CANDIDATE_RAW_MATCH',
        'actual_imports': 'EXECUTE_BEFORE_ONLY_AND_CLEANUP_NATIVE_PATHS', 'processes': process_records,
        'runtime_view_git_processes': identities['git_processes'],
        'owner_release': proof, 'fresh_targets': 1, 'dispatch': 2, 'target_effects': 2,
        'target_observations': 6, 'pending_count_after_cleanup': after['status']['pending_count'],
        'plan_after_cleanup': [{'status': p['status'], 'cursor': p['cursor']} for p in rt['plans']],
        'raw_crash_sidecars_retained': True, 'original_crash_SQL': 'NOT_AVAILABLE_JOURNAL_RETAINED',
        'root_cause': 'NOT_PROVEN_WORKER_KILLED_WITHOUT_STACK',
        'missing_local_process_streams': 'Outer batch/tool and support wrapper parents; tool exits only',
        'not_run': matrix['not_run'], 'product_imports_in_sealer': 0, 'sqlite_connections_in_sealer': 0,
        'sealer_pid': os.getpid(), 'sealer_git_processes': GIT_CALLS}

    members = set(candidate_paths) | {REPORT, relative(Path(__file__))}
    members |= {relative(p) for p in EVIDENCE.rglob('*') if p.is_file()}
    members |= {relative(p) for p in (ROOT / 'examples/a03/T3-closure').rglob('*') if p.is_file()}
    assert not any('__pycache__' in p or p.endswith('.pyc') for p in members)
    member_specs = [':' + p for p in sorted(members)]
    staged = blobs(member_specs)  # All inputs/support/report were staged before sealing.
    summary['sealer_git_processes'] = GIT_CALLS
    write(EVIDENCE / 'closure-verification.json', summary)
    entries = [{'path': p, 'bytes': len(staged[':' + p]), 'sha256': sha(staged[':' + p]),
                'checkout_sha256': sha((ROOT / p).read_bytes()), 'source': 'STAGED_RAW_GIT_BLOB'} for p in sorted(members)]
    p = EVIDENCE / 'closure-verification.json'; raw = p.read_bytes()
    entries.append({'path': relative(p), 'bytes': len(raw), 'sha256': sha(raw),
                    'checkout_sha256': sha(raw), 'source': 'NEW_FILE_BYTES_PENDING_INDEX_VERIFICATION'})
    write(EVIDENCE / 'manifest.json', {'format': 'a03-M-file-seal-1', 'candidate': CANDIDATE, 'K': K,
        'status': 'REWORK', 'self_excluded_only': relative(EVIDENCE / 'manifest.json'),
        'scope': 'All M evidence plus candidate delta, current support/input/report files; older history referenced by fixed Git IDs',
        'files': sorted(entries, key=lambda x: x['path'])})
    print(json.dumps({'status': summary['status'], 'files': len(entries), 'registered_children': len(process_records),
                      'business_runs_in_sealer': 0, 'owner_released': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-index', action='store_true')
    args = parser.parse_args()
    if args.verify_index:
        verify_index()
    else:
        create()
