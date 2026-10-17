# -*- coding: utf-8 -*-
"""Final byte preservation and evidence reconciliation; no functional reruns."""
import hashlib
import json
from archive_common import ROOT, OUT, REPORT, load, sha, write, report_links, process_records

initial = load(OUT / 'input-index.json')
supplement = load(OUT / 'compatibility-input-supplement.json')
assert len(initial['files']) == 442 and len(supplement['files']) == 1
rows = initial['files'] + supplement['files']
assert len({row['file'] for row in rows}) == 443
for row in rows:
    path = OUT / row['file']
    raw = path.read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['raw_git_sha1']
assert {p.relative_to(OUT).as_posix() for p in (OUT / 'input').rglob('*') if p.is_file()} == {r['file'] for r in rows}
protected = load(OUT / 'protected-old-files.json')['files']
assert len(protected) == 3267
for row in protected:
    path = ROOT / row['path']
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']

source = load(OUT / 'source-data-wheel-audit.json')
assert len(source['product_modules']) == 7 and len(source['packaged_data']) == 9
assert len(source['seven_cases']) == 7 and len(source['wheel_codec_files']) == 16
assert source['wheel_RECORD_verified'] and not source['wheel_rebuilt_or_installed']
assert len(load(OUT / 'raw-source-index.json')['entries']) == 171
product = load(OUT / 'product-api-results.json')
assert product['status'] == 'BOUNDED_PRODUCT_READONLY_CHECKS_PASSED'
assert len(product['seven_fixed_cases']) == 7 and len(product['selection_checks']) == 27
assert all(row['complete_API_calls'] == 1 and row['none_book_consumers'] == 0 for row in product['seven_fixed_cases'])
assert product['snapshot_complete_input_preserved'] and product['snapshot_resources_match_actual_bytes']
assert product['temporary_path_root_removed'] and product['path_boundary']['winerror'] == 1314
assert product['path_boundary']['junction'] == 'CREATED_AND_TARGET_VERIFIED'
assert product['field_reset'] == 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
wheel = load(OUT / 'wheel-outside-results.json')
assert wheel['status'] == 'OUTSIDE_FROZEN_WHEEL_CHECKS_PASSED'
assert wheel['PYTHONPATH_absent'] and not wheel['repository_source_fallback_or_old_static_imports']
assert len(wheel['observations']) == 2 and all(row['complete_API_calls'] == 1 for row in wheel['observations'])
assert load(OUT / 'wheel-cleanup.json')['removed']
first = load(OUT / 'c01-compatibility-results.json')
assert (first['tests_run'], first['failures'], first['errors'], first['rounds']) == (70, 2, 1, 1)
completed = load(OUT / 'c01-affected-completion-results.json')
assert (completed['tests_run'], completed['failures'], completed['errors']) == (2, 0, 0)
assert not completed['full_C01_matrix_rerun'] and not completed['passed_methods_rerun']
author = load(OUT / 'author-evidence-audit.json')
assert author['parent_count'] == 13 and author['nested_count'] == 10
parents, children = process_records(skip=('final-verification-01',))
assert len(parents) == 9
pending = tuple(OUT / name for name in ('process-release.json', 'final-verification.json', 'sha256-manifest.json'))
links = report_links(allowed_pending=pending)
assert sum(not row['exists'] for row in links) == 3
assert not list(OUT.rglob('__pycache__'))
text = REPORT.read_text(encoding='utf8')
assert 'ACCEPTED' in text and '70 项首轮全部通过' in text
assert initial['delivery'] in text and initial['workflow'] in text
assert 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION' in text
value = {
    'status': 'FINAL_BYTE_AND_EVIDENCE_RECONCILIATION_PASSED',
    'functional_tests_rerun': 0, 'product_imports': 0,
    'initial_exports': 442, 'review_only_compatibility_supplement': 1,
    'verified_current_input_files': len(rows), 'raw_author_input_pins': 171,
    'protected_old_files_verified': len(protected),
    'pre_seal_recorded_checks': len(parents), 'nested_children': len(children),
    'original_C01_full_round': {'tests': 70, 'subtest_failures': 2, 'errors': 1},
    'affected_C01_method_completion': {'tests': 2, 'failures': 0, 'errors': 0},
    'report_sha256': sha(REPORT), 'report_links': links,
    'pending_links_completed_by_seal_wrapper': [p.name for p in pending],
    'all_failed_records_retained': True,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
}
write(OUT / 'final-checks.json', value)
print(json.dumps({'status': value['status'], 'inputs': len(rows), 'protected': len(protected),
                  'parents_before_seal': len(parents), 'nested': len(children), 'links': len(links)}))
