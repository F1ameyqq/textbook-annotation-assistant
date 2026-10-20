"""Seal static evidence; no product imports or delta execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path('D:/1800-worktrees/a15-independent-fixed')
OUT = ROOT / 'docs/evidence/A15/independent-preflight-static'
EVIDENCE = ROOT / 'docs/evidence/A15/certificate-exception'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write_new(path, data):
    with path.open('xb') as stream:
        stream.write(data)

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')

audit = json.loads((OUT / 'raw-and-source-audit.json').read_bytes())
members = list(audit['raw_members'])
manifest = EVIDENCE / 'delivery-raw-manifest.json'
members.append({'path': manifest.relative_to(ROOT).as_posix(), 'sha256': audit['delivery_manifest_sha256']})
members.append({'path': 'r1-reference.py', 'sha256': audit['r1_reference_sha256']})
for item in members:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
command = ['git', '-c', 'core.longpaths=true', '-C', 'D:/1800', 'cat-file', 'blob',
 '077e6a6eda23d617d18bac835870d69aa3a75ee4:docs/tasks/A15-packaging-disposition-first-delta.md']
result = subprocess.run(command, env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'}, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
assert result.returncode == 0
assert sha(result.stdout) == '1513fa552dd25e1f51dc3ada1d28be936b67c22d96c3fa1165230e30399ab8a7'
write_new(OUT / 'packaging-disposition-authority.md', result.stdout)
coordinator_raw = Path('D:/1800/docs/evidence/coordinator/a15-packaging-disposition/raw-preflight.json').read_bytes()
assert sha(coordinator_raw) == 'd0676cbbc3d90ec62679c5befccdc1e2ea57e980bfe64381d4574515ad6ae07f'
write_new(OUT / 'coordinator-raw-preflight-snapshot.json', coordinator_raw)
release = {'task': 'A15', 'phase': 'STATIC_ONLY', 'at': datetime.now(timezone.utc).isoformat(),
 'fixed_original_31_raw_and_r1_unchanged': True, 'verified_input_hashes': members,
 'static_audit_invocation': {'argv': ['python', '-B', 'docs/evidence/A15/independent-preflight-static/static_audit.py'],
  'exit_code': 0, 'stdout': '{"raw_members": 31, "candidate_members": 22, "old_members_preserved": 31212, "new_product": 23, "new_final": 31, "invariant_bodies": 21, "raw_diff_bytes": 23514, "static_git_reads": 14, "E1_E4_executions": 0}\n',
  'stderr': ''},
 'additional_fixed_authority_git_read': {'argv': command, 'GIT_NO_LAZY_FETCH': '1', 'exit_code': result.returncode,
  'stdout_sha256': sha(result.stdout), 'stderr_bytes': len(result.stderr)},
 'independent_delta_executions': 0, 'candidate_imports': 0, 'product_subprocesses': 0,
 'browser_network_profile_native_api_real_occupancy_actions': 0, 'messages_sent': 0,
 'state': 'RELEASED_NO_PRODUCT_RESOURCES_CREATED', 'static_script_and_git_processes': 'SYNCHRONOUS_COMPLETED',
 'profile_locks_or_a13_markers': 'NOT_TOUCHED', 'process_scan_performed': False,
 'analysis_or_shell_own_os_exit_identity': 'NOT_MEASURED_NOT_CLAIMED',
 'next_phase_requires_separate_fixed_dispatch': True}
write_new(OUT / 'input-preservation-and-release.json', encode(release))
files = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != 'manifest.json':
        data = path.read_bytes()
        files.append({'path': path.relative_to(ROOT).as_posix(), 'size': len(data), 'sha256': sha(data)})
write_new(OUT / 'manifest.json', encode({'task': 'A15', 'phase': 'INDEPENDENT_STATIC_ONLY',
 'self_excluded': True, 'members': files, 'independent_E1_E4_executions': 0}))
print(json.dumps({'sealed_static_members': len(files), 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()),
                  'original_inputs_unchanged': True, 'E1_E4_executions': 0}))
