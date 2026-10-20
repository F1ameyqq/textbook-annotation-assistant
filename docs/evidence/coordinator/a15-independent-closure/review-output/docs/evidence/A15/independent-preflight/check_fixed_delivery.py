"""Independent fixed-input checks only; candidate and suite are never imported."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path('D:/1800-worktrees/a15-independent-fixed')
OUT = ROOT / 'docs/evidence/A15/independent-preflight'
EVIDENCE = ROOT / 'docs/evidence/A15/certificate-exception'
FINAL = '7432122b9fd5602785ebfb2b3f24e407fdf76eda'
PRIOR = '25f9083b2c8183196a7b2d7671efd40d2ef78713'
CANDIDATE_SHA = '78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652'
MANIFEST_SHA = 'ef39744d3f0b22a54a24341e70d0e15d445383086000d8253d7454c5d41e7267'
commands = []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')

def save(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write(encode(value))

def git(*args):
    command = ['git', '-c', 'core.longpaths=true', '-C', 'D:/1800', *args]
    result = subprocess.run(command, env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'}, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    commands.append({'argv': command, 'GIT_NO_LAZY_FETCH': '1', 'exit_code': result.returncode,
                     'stdout_bytes': len(result.stdout), 'stderr_bytes': len(result.stderr)})
    assert result.returncode == 0
    return result.stdout

def tree(raw):
    entries = {}
    for item in raw.split(b'\0'):
        if item:
            identity, path = item.split(b'\t', 1)
            entries[path.decode('utf-8')] = identity.decode('ascii')
    return entries

def check_result(result, spec):
    assert result['task'] == 'A15' and result['mode'] == 'PURE_OFFLINE_ONLY'
    assert result['candidate_sha256'] == CANDIDATE_SHA
    assert result['case_spec_sha256'] == '4101642aedd493e8e50964fad7c0ea3c49128638b0b863bee22115b0b5d1fbc6'
    assert result['first_failure'] is None and result['live_activated'] is False
    assert result['claim_is_synthetic_only'] is True and result['live_output_or_profile_read'] is False
    assert result['old_suites_run'] is False
    assert set(result['resource_calls']) == {'subprocess', 'socket', 'thread', 'native_api', 'profile', 'occupancy', 'browser', 'live_entry'}
    assert all(type(value) is int and value == 0 for value in result['resource_calls'].values())
    cases = result['cases']
    assert [case['case'] for case in cases] == ['E1', 'E2', 'E3', 'E4']
    assert all(case['status'] == 'PASS' for case in cases)
    for index, group in enumerate(('E1', 'E2')):
        assert [(item['id'], item['rejection']) for item in cases[index]['checks']] == [(item['id'], item['expected']) for item in spec[group]]
    assert len(cases[0]['checks']) == 10 and len(cases[1]['checks']) == 29
    assert cases[2]['checks'][0]['exception_only_in_approval'] is True
    assert cases[3]['checks'][0]['rejection'] == 'ACTIVATION_ALREADY_CLAIMED'
    assert cases[3]['checks'][0]['marker_bytes_unchanged'] is True
    assert cases[2]['checks'][0]['marker_sha256'] == cases[3]['checks'][0]['marker_sha256']

manifest_path = EVIDENCE / 'packaging-disposition-delivery/delivery-raw-manifest.json'
raw_manifest = manifest_path.read_bytes()
assert sha(raw_manifest) == MANIFEST_SHA
manifest = json.loads(raw_manifest)
prior = tree(git('ls-tree', '-r', '-z', PRIOR))
final = tree(git('ls-tree', '-r', '-z', FINAL))
assert len(prior) == 31243
assert not [path for path, identity in prior.items() if final.get(path) != identity]
added = sorted(set(final) - set(prior))
assert len(added) == 16
assert all(path.startswith('docs/evidence/A15/certificate-exception/first-author-delta/') or
           path.startswith('docs/evidence/A15/certificate-exception/packaging-disposition-delivery/') for path in added)
members = []
for item in manifest['members']:
    relative = Path(item['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    raw = (ROOT / relative).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    assert (len(raw), sha(raw), blob) == (item['size'], item['sha256'], item['git_blob_expected'])
    assert final[item['path']] == '100644 blob ' + blob
    members.append({'path': item['path'], 'size': len(raw), 'sha256': sha(raw), 'git_blob': blob})
assert git('cat-file', 'blob', FINAL + ':' + manifest_path.relative_to(ROOT).as_posix()) == raw_manifest
assert len(members) + 1 == 47
assert sha((EVIDENCE / 'candidate-manifest.json').read_bytes()) == CANDIDATE_SHA
static = ROOT / 'docs/evidence/A15/independent-preflight-static'
static_manifest = json.loads((static / 'manifest.json').read_bytes())
assert sha((static / 'manifest.json').read_bytes()) == '63ef0c36d0663f89f5a5afa636ce1a160f01949050d652c453a3f0c834470bc2'
for item in static_manifest['members']:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
old_audit = json.loads((static / 'raw-and-source-audit.json').read_bytes())
for item in old_audit['raw_members']:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
assert 'STATIC_SCOPE_CHECKS_COMPLETE_NO_BLOCKING_FINDING' in (static / 'report.md').read_text(encoding='utf-8')
spec = json.loads((EVIDENCE / 'finite-cases.json').read_bytes())
author_result = json.loads((EVIDENCE / 'first-author-delta/suite-result.json').read_bytes())
check_result(author_result, spec)
command_result = json.loads((EVIDENCE / 'packaging-disposition-delivery/command-result.json').read_bytes())
assert command_result['exit_code'] == 0 and command_result['invocations'] == 1
author_release = json.loads((EVIDENCE / 'packaging-disposition-delivery/author-release.json').read_bytes())
assert author_release['state'] == 'RELEASED' and author_release['product_subprocesses'] == 0
assert author_release['profile_metadata_reads'] == 0 and author_release['real_occupancy_checks'] == 0
assert author_release['browser_contexts'] == 0 and author_release['network_attempts'] == 0
assert all(value == 0 for value in author_release['resource_calls'].values())
assert (EVIDENCE / 'packaging-disposition-delivery/first-delta-stderr.txt').read_bytes() == b''
assert len((EVIDENCE / 'packaging-disposition-delivery/first-delta-stdout.txt').read_bytes()) == 111
delta_output = EVIDENCE / 'first-independent-delta'
assert not delta_output.exists()
coordinator = Path('D:/1800/docs/evidence/coordinator/a15-offline-author-delivery')
intent = (coordinator / 'independent-run-intent.json').read_bytes()
assert sha(intent) == '091efd86a4b38487a8bc8439be14d9648a9037a23c20e4005fe53e7b62427bd9'
with (OUT / 'coordinator-independent-run-intent.json').open('xb') as stream:
    stream.write(intent)
raw_preflight = (coordinator / 'raw-preflight.json').read_bytes()
assert sha(raw_preflight) == 'f48b65846bfedabaceb0d0f913212957bcc032bbaf9fe4aa8a23b778beee05ae'
with (OUT / 'coordinator-author-raw-preflight.json').open('xb') as stream:
    stream.write(raw_preflight)
save('fixed-input-preflight.json', {'task': 'A15', 'at': datetime.now(timezone.utc).isoformat(),
 'status': 'READY_FOR_SINGLE_INDEPENDENT_E1_E4', 'author_final': FINAL, 'prior_failure_final': PRIOR,
 'author_manifest_sha256': MANIFEST_SHA, 'candidate_sha256': CANDIDATE_SHA,
 'raw_members_including_manifest': 47, 'members': members,
 'original_31_raw_and_static_seal_unchanged': True, 'prior_final_old_members_preserved': len(prior),
 'new_paths': added, 'new_paths_count': len(added),
 'static_report_sha256': sha((static / 'report.md').read_bytes()),
 'static_manifest_sha256': sha((static / 'manifest.json').read_bytes()),
 'author_delta_result': {'cases': 'E1-E4 PASS 4/4', 'duration_ms': author_result['duration_ms'],
                         'exit_code': 0, 'author_scope_only': True},
 'author_release_static_consistency_verified': True,
 'independent_delta_output': delta_output.relative_to(ROOT).as_posix(),
 'independent_delta_output_absent': True, 'independent_delta_executions_before': 0,
 'static_git_commands': commands, 'product_imports_or_runs': 0, 'live_activated': False})
print(json.dumps({'raw_members': 47, 'old_members_preserved': len(prior), 'new_raw': len(added),
 'author_delta_static_receipt_consistent': True, 'independent_delta_executions': 0, 'ready': True}))
