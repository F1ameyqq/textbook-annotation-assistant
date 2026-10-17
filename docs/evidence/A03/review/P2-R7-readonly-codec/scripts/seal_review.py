# -*- coding: utf-8 -*-
"""Record one byte-only final check, seal after its wait, then verify the full archive."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from archive_common import ROOT, OUT, REPORT, load, sha, write, report_links, process_records

assert not (OUT / 'sha256-manifest.json').exists()
argv = [sys.executable, '-X', 'utf8', '-B', str(OUT / 'scripts/run_recorded.py'),
        'final-verification-01', '30', str(OUT / 'scripts/final_checks.py')]
env = dict(os.environ)
env.pop('PYTHONPATH', None)
env['PYTHONDONTWRITEBYTECODE'] = '1'
with (OUT / 'seal-recorder.stdout.log').open('xb') as stdout, (OUT / 'seal-recorder.stderr.log').open('xb') as stderr:
    code = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=40).returncode
assert code == 0, 'final verification failed; preserved records must be inspected before any follow-up'
parents, children = process_records()
assert len(parents) == 10
write(OUT / 'process-release.json', {
    'status': 'OWNED_REVIEW_CHECKS_WAITED_AND_EXITED',
    'parents': parents, 'children': children, 'parent_count': len(parents), 'nested_count': len(children),
    'failed_checks_retained': ['c01-compatibility-01', 'author-evidence-audit-01'],
    'basis': 'Recorded wait/communicate completion only; no system/profile/process scan',
    'functional_cases_after_bounded_completion': 0,
    'native_product_sessions': 0, 'background_jobs': 0,
})
checks = load(OUT / 'final-checks.json')
write(OUT / 'final-verification.json', {
    'status': 'ACCEPTED_R7_INTERNAL_READONLY_ARCHIVE_READY',
    'created_at': datetime.now(timezone.utc).isoformat(),
    'workflow': '5cb696378f8c53a7720a5b775b3188012bf5626b',
    'base': '81d3ec7e42e0a1a76ad744bf59536fc5f68adee4',
    'target': '8ad45dd07214ae406a3fab28d76a4b5abd6eef03',
    'role': 'STATIC_INSPECTION', 'adoption_scope': 'A_INTERNAL_READONLY',
    'final_check_exit_code': 0, 'final_checks_sha256': sha(OUT / 'final-checks.json'),
    'input_files_verified': checks['verified_current_input_files'],
    'old_files_preserved': checks['protected_old_files_verified'],
    'process_release_sha256': sha(OUT / 'process-release.json'),
    'parent_count': len(parents), 'nested_count': len(children),
    'report_sha256': sha(REPORT),
    'C01_first_full_round_was_not_green': True,
    'C01_reviewer_setup_corrected_only_for_two_affected_methods': True,
    'functional_reruns_in_finalization': 0,
    'manifest_excludes_only_itself': True,
    'post_write_manifest_body_and_inventory_recheck': 'seal_review.py asserts before successful exit',
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
    'INTEGRATED_state_written': False, 'I01_released': False,
})
paths = sorted([p for p in OUT.rglob('*') if p.is_file()] + [REPORT])
manifest_path = OUT / 'sha256-manifest.json'
assert manifest_path not in paths and len(paths) == len(set(paths))
write(manifest_path, {
    'status': 'R7_READONLY_REVIEW_FROZEN',
    'scope': 'R7 codec STATIC_INSPECTION / A_INTERNAL_READONLY only',
    'root': str(ROOT), 'excluded_only': manifest_path.relative_to(ROOT).as_posix(),
    'files': [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in paths],
})
# This second pass independently re-reads the completed manifest and file bodies.
manifest = load(manifest_path)
actual_paths = {p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p != manifest_path}
actual_paths.add(REPORT.relative_to(ROOT).as_posix())
assert actual_paths == {row['path'] for row in manifest['files']}
for row in manifest['files']:
    p = ROOT / row['path']
    assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], row['path']
assert all(row['exists'] for row in report_links())
assert sha(REPORT) == load(OUT / 'final-verification.json')['report_sha256']
print(json.dumps({'status': 'SEALED_AND_INDEPENDENTLY_REHASHED',
                  'manifest_files': len(manifest['files']), 'report_sha256': sha(REPORT),
                  'manifest_sha256': sha(manifest_path), 'parents': len(parents), 'nested': len(children)}, ensure_ascii=False))
