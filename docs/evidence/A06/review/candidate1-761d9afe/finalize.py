"""Seal retained evidence and report; no receiver or business calls."""
import datetime
import hashlib
import json
from pathlib import Path
import re

from review_tools import CODE, ROOT, dump, sha

WORKSPACE = Path('D:/1800')
REPORT = WORKSPACE / 'docs/tasks/A06-review-report.md'

def main():
    raw = json.loads((ROOT / 'raw-export.json').read_bytes())
    verified = []
    for row in raw['files']:
        value = (CODE / row['path']).read_bytes()
        assert len(value) == row['bytes'] and sha(value) == row['sha256']
        verified.append(row['path'])
    assert not (CODE / '.git').exists()
    assert not list(CODE.rglob('*.pyc'))
    summary = json.loads((ROOT / 'run-summary.json').read_bytes())
    assert summary['public_full_entry_calls'] == 4 and summary['public_full_entry_calls_per_case'] == 1
    assert summary['all_expectations_met'] is True
    release = json.loads((ROOT / 'release.json').read_bytes())
    probe = json.loads((ROOT / 'post-run-process-probe.json').read_bytes())
    assert release['status'] == 'RELEASED' and probe['all_absent'] is True
    reader_path = CODE / 'src/annotation/source/b_handoff/reader.py'
    lines = reader_path.read_text(encoding='utf-8').splitlines()
    excerpts = {str(start) + '-' + str(end): '\n'.join(f'{i+1}: {lines[i]}' for i in range(start-1,end))
                for start, end in [(43,49), (238,242), (260,268), (296,328)]}
    inspection = json.loads((ROOT / 'original-inspection.json').read_bytes())
    finding = dict(id='F01', priority='P2', status='OPEN_REWORK', basis='Original A06 receiver task: wrapper and payload.result each have version and identity independently checked',
                   source='src/annotation/source/b_handoff/reader.py', source_sha256=sha(reader_path.read_bytes()),
                   decisive_lines=[303,304,306,307], excerpts=excerpts,
                   finding='Wrapper schema_version/kind is gated. Non-final stage payload.result has only artifact_id/revision/content_hash ref binding, with no independent result schema_version/kind policy; raw native values retained is not version checking.',
                   final_current_versions_gated=True,
                   actual_four_full_entry_expectations_met=True,
                   observed_wrapper_result_versions=inspection['wrapper_result_versions'],
                   evidence_type='STATIC_FIXED_SOURCE_PLUS_ORIGINAL_INPUT_OBSERVATION',
                   extra_variant_generated=False, extra_public_receiver_call=False,
                   no_claim_of_executed_unknown_intermediate_version_acceptance=True,
                   second_candidate_not_activated=True)
    dump(ROOT / 'static-findings.json', [finding])
    text = REPORT.read_text(encoding='utf-8')
    assert not any(line.endswith((' ', '\t')) for line in text.splitlines())
    links = []
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' in target or target.startswith('#'):
            continue
        path = (REPORT.parent / target.split('#',1)[0]).resolve()
        # finalization and manifest will be written directly below.
        future = path in ((ROOT / 'finalization.json').resolve(), (ROOT / 'review-manifest.json').resolve())
        assert path.exists() or future, str(path)
        links.append(dict(target=target, exists_or_created_by_sealing=True))
    final = dict(status='REWORK', reason='F01_MISSING_INDEPENDENT_STAGE_RESULT_VERSION_CHECK',
                 dynamic_expectations_met=True, no_additional_scenarios_or_business_reruns=True,
                 raw_export_files_unchanged=len(verified), raw_export_bytes=sum(r['bytes'] for r in raw['files']),
                 report_relative_path=str(REPORT.relative_to(WORKSPACE)).replace('\\','/'), report_sha256=sha(REPORT.read_bytes()),
                 report_local_links=links, no_trailing_whitespace=True,
                 original_zip_preserved=True, execution_sessions_released=True,
                 no_state_index_product_author_mutations=True,
                 finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    dump(ROOT / 'finalization.json', final)
    manifest_path = ROOT / 'review-manifest.json'
    assert not manifest_path.exists()
    paths = [p for p in ROOT.rglob('*') if p.is_file()] + [REPORT]
    files = []
    for path in sorted(paths):
        value = path.read_bytes()
        files.append(dict(path=str(path.relative_to(WORKSPACE)).replace('\\','/'), bytes=len(value), sha256=sha(value)))
    manifest = dict(status='REWORK', delivery=raw['delivery'], candidate=raw['candidate'], base=raw['base'],
                    exclusion='This manifest excludes itself to avoid a circular hash. It covers this report, all review scripts, raw-code copies, fixed input copy, variants, recipes, raw streams, process records and review findings.',
                    files=files, file_count=len(files), total_bytes=sum(r['bytes'] for r in files))
    dump(manifest_path, manifest)
    assert all((WORKSPACE / r['path']).stat().st_size == r['bytes'] and sha((WORKSPACE / r['path']).read_bytes()) == r['sha256'] for r in files)
    print(json.dumps(dict(status='REWORK', finding='F01', report=str(REPORT), report_sha256=final['report_sha256'],
                          manifest=str(manifest_path), manifest_sha256=sha(manifest_path.read_bytes()),
                          manifest_files=len(files), manifest_bytes=manifest['total_bytes'], raw_files_unchanged=len(verified),
                          public_receiver_calls=4, background_or_platform_sessions=0)))

if __name__ == '__main__':
    main()
