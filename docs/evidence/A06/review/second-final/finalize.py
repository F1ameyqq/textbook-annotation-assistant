"""Seal second/final independent delta evidence; no candidate execution."""
import datetime
import json
from pathlib import Path
import re
from review_tools import CODE, ROOT, dump, sha

WORKSPACE = Path('D:/1800')
REPORT = WORKSPACE / 'docs/tasks/A06-second-final-review-report.md'
FIRST = ROOT.parent / 'candidate1-761d9afe'

def main():
    summary = json.loads((ROOT / 'run-summary.json').read_bytes())
    assert summary['status'] == 'FINITE_DELTA_COMPLETE' and summary['all_expectations_met'] is True
    assert summary['public_entry_calls'] == 2
    release = json.loads((ROOT / 'release.json').read_bytes())
    probe = json.loads((ROOT / 'post-run-process-probe.json').read_bytes())
    assert release['status'] == 'RELEASED' and probe['all_absent'] is True
    assert all(p['process_reaped'] and not p['timed_out'] for p in release['synchronous_process_records'])
    raw = json.loads((ROOT / 'raw-export.json').read_bytes())
    for row in raw['files']:
        data = (CODE / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    assert not (CODE / '.git').exists() and not list(CODE.rglob('*.pyc'))
    inherited = json.loads((ROOT / 'inheritance-audit.json').read_bytes())
    for path, digest in inherited['previous_report_bindings'].items():
        assert sha((WORKSPACE / path).read_bytes()) == digest
    previous = json.loads((FIRST / 'review-manifest.json').read_bytes())
    for row in previous['files']:
        data = (WORKSPACE / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    original = WORKSPACE / '.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip'
    original_data = original.read_bytes()
    assert sha(original_data) == 'b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d'
    assert next((ROOT / 'inputs').glob('*.zip')).read_bytes() == original_data
    assert sha((ROOT / 'variant/unknown-stage-result.zip').read_bytes()) == '5911f8d572c97027f0ac12a5c1dbe3e190e59a6391904fdd91cef6501bf91af8'
    delta = json.loads((ROOT / 'receipt-delta-check.json').read_bytes())
    assert delta['after_removing_only_14_new_checks_equals_first_independent_receipt'] is True
    metadata = json.loads((ROOT / 'run/imports.stdout.txt').read_bytes())
    assert all(sha(Path(m['file']).read_bytes()) == m['sha256'] for m in metadata['modules'])
    checks = json.loads((ROOT / 'result-version-checks.json').read_bytes())
    assert len(checks) == 14 and all(c['validated'] and c['context'] == 'FIXED_STAGE_DIAGNOSTIC_ONLY' and c['grants_current_top_level_support'] is False and c['business_acceptance'] is False for c in checks)
    finding = dict(id='F01', status='CLOSED_FOR_FIXED_DIAGNOSTIC_SCOPE', source='src/annotation/source/b_handoff/reader.py',
                   source_sha256='a80acf8a15d7c822c82ef6720a6125e79cfcee0498ac60d3f1c7a80ca030cd61',
                   validator_lines=[116,129], public_wiring_line=340,
                   independent_observed_stage_kind_versions=14, narrow_field_scope='14 observed pairs plus original one unknown-version and one wrong-kind check',
                   full_public_entry_calls=2, unknown_nonfinal_stage_result_rejected_at='VERSION',
                   old_receipt_equal_after_removing_only_14_new_result_checks=True,
                   previous_failure_history_preserved=True, no_third_candidate=True,
                   no_C01_execution_or_joint_mapping_qualification=True)
    dump(ROOT / 'findings.json', [finding])
    text = REPORT.read_text(encoding='utf-8')
    assert not any(line.endswith((' ', '\t')) for line in text.splitlines())
    links = []
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' in target or target.startswith('#'):
            continue
        path = (REPORT.parent / target.split('#',1)[0]).resolve()
        future = path in ((ROOT / 'finalization.json').resolve(), (ROOT / 'review-manifest.json').resolve())
        assert path.exists() or future, str(path)
        links.append(dict(target=target, exists_or_created_at_sealing=True))
    final = dict(status='ACCEPTED', scope='A06 fixed-package read-only HOLD diagnostic and explicit refusal only',
                 candidate_number=2, final_candidate=True, delivery=raw['delivery'], candidate=raw['candidate'],
                 F01='CLOSED', raw_export_files_unchanged=len(raw['files']), raw_export_bytes=raw['total_bytes'],
                 first_review_files_unchanged=len(previous['files']), first_review_bytes_unchanged=sum(r['bytes'] for r in previous['files']),
                 report_sha256=sha(REPORT.read_bytes()), local_links=links, public_entry_calls=2, public_entry_reruns=0,
                 source_and_input_preserved=True, all_recorded_processes_released=True,
                 state_index_author_product_untouched=True,
                 unresolved_history_requiredness='UNCONFIRMED_REQUIREDNESS', joint_mapping='UNCONFIRMED',
                 business_acceptance=False, c01_execution_eligible=False,
                 finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    dump(ROOT / 'finalization.json', final)
    manifest_path = ROOT / 'review-manifest.json'
    assert not manifest_path.exists()
    files = []
    for path in sorted([p for p in ROOT.rglob('*') if p.is_file()] + [REPORT]):
        data = path.read_bytes()
        files.append(dict(path=str(path.relative_to(WORKSPACE)).replace('\\','/'), bytes=len(data), sha256=sha(data)))
    dump(manifest_path, dict(status='ACCEPTED', scope=final['scope'], delivery=raw['delivery'], candidate=raw['candidate'],
                            exclusions='Manifest itself. First-review evidence is referenced by its preserved fixed manifest, not duplicated or rewritten.',
                            files=files, file_count=len(files), total_bytes=sum(r['bytes'] for r in files)))
    assert all(sha((WORKSPACE / r['path']).read_bytes()) == r['sha256'] and (WORKSPACE / r['path']).stat().st_size == r['bytes'] for r in files)
    print(json.dumps(dict(status='ACCEPTED', F01='CLOSED', report=str(REPORT), report_sha256=final['report_sha256'],
                          manifest=str(manifest_path), manifest_sha256=sha(manifest_path.read_bytes()),
                          manifest_files=len(files), manifest_bytes=sum(r['bytes'] for r in files),
                          raw_files_unchanged=len(raw['files']), first_review_files_unchanged=len(previous['files']), public_entry_calls=2)))

if __name__ == '__main__':
    main()
