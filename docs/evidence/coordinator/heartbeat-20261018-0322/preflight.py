"""Read-only fixed-delivery hashes and scope checks; no product imports or SQL."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('D:/1800')
OUT = ROOT / 'docs/evidence/coordinator/heartbeat-20261018-0322/checks.json'
PRODUCT = '1330047dd29890dea0e433ff01b991f615bf78f4'

def git(*args, cwd=ROOT, data=None):
    return subprocess.run(['git', '-c', 'core.longpaths=true', *args], cwd=cwd,
                          input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True).stdout

def blobs(commit, paths):
    requests = b''.join((commit + ':' + p + '\n').encode() for p in paths)
    raw = git('cat-file', '--batch', data=requests)
    result, offset = {}, 0
    for path in paths:
        end = raw.index(b'\n', offset)
        header = raw[offset:end].split()
        assert header[1] == b'blob', (path, header)
        size = int(header[2])
        start = end + 1
        result[path] = raw[start:start + size]
        assert raw[start + size:start + size + 1] == b'\n'
        offset = start + size + 1
    assert offset == len(raw)
    return result

def sha(data):
    return hashlib.sha256(data).hexdigest()

result = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'scope': 'Delivery admission only; not independent acceptance or integration',
          'business_calls': 0, 'SQL_calls': 0, 'tasks': {}}
for task, target, base, manifest, report in [
    ('A03-T2', '699f748a124162b3118e3996c03757725daac363',
     'f111eb609d065a2506da52007c3b283928d537aa',
     'docs/evidence/A03/T2/execution/manifest.json', 'docs/tasks/A03-T2-execution-report.md'),
    ('A03-T3', '765aef597a93fe36060fce65e17b22fe1c3408b8',
     '3fcdb73416142a0a85dfb951a7f839849871c549',
     'docs/evidence/A03/T3/execution/plan-R1/manifest.json', 'docs/tasks/A03-T3-integration-plan.md'),
]:
    wt = Path('D:/1800-worktrees/' + task.lower())
    head = git('rev-parse', 'HEAD', cwd=wt).decode().strip()
    status = git('status', '--porcelain', cwd=wt).decode()
    assert head == target and not status, (task, head, status)
    manifest_raw = blobs(target, [manifest])[manifest]
    m = json.loads(manifest_raw)
    members = m.get('files', m.get('members'))
    paths = [x['path'] for x in members]
    assert len(set(paths)) == len(paths)
    data = blobs(target, paths)
    errors = [x['path'] for x in members
              if sha(data[x['path']]) != x['sha256'] or len(data[x['path']]) != x['bytes']]
    assert not errors, errors
    delta = git('diff', '--name-only', base, target).decode().splitlines()
    product_delta = git('diff', '--name-only', PRODUCT, target, '--', 'src', 'pyproject.toml').decode().splitlines()
    assert not product_delta, product_delta
    if task == 'A03-T2':
        assert all(p.startswith('docs/evidence/A03/T2/execution/') or p == report for p in delta), delta
        release_path = 'docs/evidence/A03/T2/execution/sealing/final-release-proof.json'
        release = json.loads(data[release_path])
        assert release['registered_process_count'] == 15
        assert all(p['exit_code'] == 0 and not p['alive'] and not p['timeout'] for p in release['registered_processes'])
        assert all(not p['alive'] for p in release['boundary_keepers']['all_keeper_threads'])
        book = release['final_book']
        assert book['owner'] is None and book['pid'] is None and book['lease'] == 0 and book['phase'] == 'RELEASED'
        matrix = json.loads(data['docs/evidence/A03/T2/execution/validation/author-01/matrix.json'])
        assert matrix == {'C': 'PASS_AUTHOR_ONLY', 'H1': 'PASS_AUTHOR_ONLY', 'status': 'REVIEW'}
        detail = {'registered_processes_exited': 15, 'owner_released': True,
                  'static_process_recording_gap': '3 synchronous Git calls, retained disclosure; not repaired or hidden',
                  'release_proof': release_path, 'release_sha256': sha(data[release_path]),
                  'candidate_execution_paths_unchanged': True}
    else:
        assert len(delta) == 9 and all(p.startswith('docs/evidence/A03/T3/execution/plan-R1/') or
             p in [report, 'docs/tasks/A03-T3-remaining-matrix.md'] for p in delta), delta
        old_paths = git('ls-tree', '-r', '--name-only', base, '--', 'docs/evidence/A03/T3/execution').decode().splitlines()
        old = blobs(base, old_paths)
        new = blobs(target, old_paths)
        assert old == new
        detail = {'old_execution_files_unchanged': len(old_paths), 'release_basis': 'Completed author turn; documentation only, no business/SQL processes',
                  'new_plan_evidence_files': 7, 'functional_review': 'NOT_RUN_DOCUMENT_ONLY'}
    result['tasks'][task] = dict(target_commit=target, base_commit=base, manifest=manifest,
        manifest_sha256=sha(manifest_raw), report=report, report_sha256=sha(data[report]),
        members_raw_hash_verified=len(members), hash_mismatches=errors,
        changed_paths=delta, product_delta=product_delta, working_tree_clean=True, **detail)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: {'members': v['members_raw_hash_verified'], 'changes': len(v['changed_paths']),
                     'manifest_sha256': v['manifest_sha256']} for k, v in result['tasks'].items()}))
