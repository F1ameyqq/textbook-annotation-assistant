"""Once-only finite public-entry review; no candidate patching or extra scenarios."""
import datetime
import io
import json
import os
from pathlib import Path
import sys
import zipfile

from review_tools import CODE, ROOT, dump, run, sha

def documents_from_fixed_zip(path):
    # Databases and scripts remain opaque bytes; no imports, sqlite or extraction.
    with zipfile.ZipFile(path) as archive:
        files = {n: archive.read(n) for n in archive.namelist()}
    documents = {n: json.loads(v) for n, v in files.items() if n.endswith('.json') and n != 'manifest.json'}
    with zipfile.ZipFile(io.BytesIO(files['inputs/inline-observed.zip'])) as archive:
        for n in archive.namelist():
            if n.endswith('.json'):
                documents['inputs/inline-observed.zip!/' + n] = json.loads(archive.read(n))
    return files, documents

def pointer(documents, location):
    name, fragment = location.split('#', 1)
    value = documents[name]
    if fragment:
        for key in fragment.lstrip('/').split('/'):
            key = key.replace('~1', '/').replace('~0', '~')
            value = value[int(key)] if isinstance(value, list) else value[key]
    return value

def inspect_original(output, source):
    receipt, received_documents = output['receipt'], output['documents']
    files, fixed_documents = documents_from_fixed_zip(source)
    checks = {}
    checks['every_native_document_and_unknown_value_preserved'] = received_documents == fixed_documents
    checks['hold_and_no_execution_or_content_qualification'] = (receipt['decision'] == 'HOLD' and all(receipt[k] is False for k in (
        'business_acceptance', 'c01_execution_eligible', 'transcription_verified', 'joint_mapping_confirmed')))
    checks['counts_are_fixed_candidates_and_issues'] = receipt['counts'] == dict(question_candidates=34, answer_candidates=66, current_check_issues=127)
    checks['input_exact'] = (receipt['input']['sha256'] == sha(Path(source).read_bytes())
                             and receipt['input']['manifest_sha256'] == sha(files['manifest.json']) and receipt['input']['bytes'] == 11681712)
    gap = receipt['history_gap']
    checks['history_gap_and_requiredness_preserved'] = (gap['reference'] == {
        'artifact_id': 'b-evidence-18e2d1ee2a22288f585513f0', 'revision': 1,
        'content_hash': 'a2e53e1fc5ddee5ed0eaa57102af074a9b20b7815aa065116464446b9be7a8da'}
        and gap['statuses'] == ['UNRESOLVED_HISTORY_REFERENCE', 'UNCONFIRMED_REQUIREDNESS']
        and gap['optional'] is None and gap['requiredness'] == 'UNCONFIRMED'
        and all(pointer(fixed_documents, p) == gap['reference'] for p in gap['locations']))
    checks['current_entities_complete_native_values'] = len(receipt['content']['entities']) == 100 and all(
        row['native'] == pointer(fixed_documents, row['path']) for row in receipt['content']['entities'])
    checks['region_drafts_retained_without_old_source_fragment_requirement'] = all(
        row['source_region'] == pointer(fixed_documents, row['path'])['source_region'] and row['preserved']
        for row in receipt['content']['region_drafts']) and len(receipt['content']['region_drafts']) == 3
    checks['unicode_codepoint_spans_actual_text'] = (receipt['content']['span_convention'] == 'UNICODE_CODE_POINTS_LEFT_CLOSED_RIGHT_OPEN' and all(
        row['text'] == pointer(fixed_documents, row['path'].rsplit('/pieces/', 1)[0])['text'][row['output_span'][0]:row['output_span'][1]]
        for row in receipt['content']['character_spans']))
    checks['no_platform_box_inference'] = receipt['content']['platform_box_count'] is None
    archive_versions = sorted({r['schema_version'] for r in receipt['archives']})
    checks['four_archive_versions_bound_and_preserved'] = archive_versions == ['b-check-trial/0.4', 'b-check-trial/0.5', 'b-graph-trial/0.4', 'b-graph-trial/0.5'] and all(
        r['disposition'] == 'ARCHIVE_ONLY' and r['business_acceptance'] is False and
        r['reference'] == {k: pointer(fixed_documents, r['path'])[k] for k in ('artifact_id', 'revision', 'content_hash')}
        for r in receipt['archives'])
    checks['viewer173_resource173_distinct'] = receipt['assets']['viewer-173']['sha256'] != receipt['assets']['resource-173']['sha256']
    checks['scope_and_run_not_overwritten'] = all(receipt['scopes'][name] == {
        'scope_id': fixed_documents[name].get('scope_id'), 'run_id': fixed_documents[name].get('run_id')}
        for name in ('artifacts/evidence.json', 'artifacts/graph.json', 'artifacts/check.json', 'artifacts/pipeline-report.json')) and receipt['scopes']['package'] != receipt['scopes']['artifacts/graph.json']['scope_id']
    layers = []
    for row in receipt['content']['entities']:
        entity = row['native']
        layers.append(dict(id=row['id'], group=row['group'], source_fragments=len(entity.get('fragments', [])),
                           active_content_fragments=len(entity.get('content_fragments', [])),
                           typed_regions=len(entity.get('regions', [])), render_regions=len(entity.get('render_regions', [])),
                           content_fragment_ids=[v.get('content_fragment_id') for v in entity.get('content_fragments', [])]))
    stage_versions = []
    for stage in receipt['pipeline']['stages']:
        wrapper = fixed_documents[stage['wrapper_path']]
        result = wrapper['payload']['result']
        stage_versions.append(dict(stage_id=stage['stage_id'], wrapper_kind=wrapper.get('kind'),
                                   wrapper_version=wrapper.get('schema_version'), result_kind=result.get('kind'),
                                   result_version=result.get('schema_version'), wrapper_ref=stage['wrapper_ref'], result_ref=stage['result_ref']))
    return dict(checks=checks, all_expected=all(checks.values()), integrity=receipt['integrity'],
                counts=receipt['counts'], versions=receipt['versions'], scopes=receipt['scopes'],
                history_gap=gap, archive_versions=archive_versions, archive_occurrences=len(receipt['archives']),
                region_drafts=receipt['content']['region_drafts'], character_span_count=len(receipt['content']['character_spans']),
                layers=layers, wrapper_result_versions=stage_versions)

def main():
    assert json.loads((ROOT / 'static-audit.json').read_bytes())['status'] == 'READY_FOR_FOUR_PUBLIC_CALLS'
    logs = ROOT / 'run'
    logs.mkdir(exist_ok=False)
    cwd1, cwd2 = ROOT / 'foreign-cwd-one', ROOT / 'foreign-cwd-two'
    cwd1.mkdir(exist_ok=False)
    cwd2.mkdir(exist_ok=False)
    source = next((ROOT / 'inputs').glob('*.zip'))
    processes, outcomes = [], []
    metadata_code = """import sys,json,pathlib,hashlib,inspect,PIL,pydantic
import annotation.source.b_handoff as b
import annotation.source.b_handoff.reader as r
import annotation.source.b_handoff.views as v
import annotation.source.b_handoff.__main__ as cli
import annotation.contracts as c
mods=[b,r,v,cli,c]
print(json.dumps({'python':sys.version,'executable':sys.executable,'Pillow':PIL.__version__,'pydantic':pydantic.__version__,'schema_version':c.SCHEMA_VERSION,'schema_title':c.schema().get('title'),'contract_entries':{n:callable(getattr(c,n,None)) for n in ['load_bundle','validate_bundle','schema','ContractError']},'receive_signature':str(inspect.signature(b.receive_package)),'modules':[{'name':m.__name__,'file':m.__file__,'sha256':hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest()} for m in mods]}))
"""
    rc, stdout, stderr, process = run('imports', [sys.executable, '-B', '-c', metadata_code], cwd1, logs)
    processes.append(process)
    metadata = json.loads(stdout) if rc == 0 else {}
    import_ok = rc == 0 and not stderr and metadata['schema_version'] == '1.0.0-a-proposal' and all(metadata['contract_entries'].values()) and all(
        Path(m['file']).resolve().is_relative_to(CODE.resolve()) for m in metadata['modules'])
    outcomes.append(dict(case='imports', expected_matched=import_ok, exit_code=rc))
    if not import_ok:
        dump(ROOT / 'run-summary.json', dict(status='BLOCKED', outcomes=outcomes, processes=processes))
        return 1
    variants = json.loads((ROOT / 'variants/variants.json').read_bytes())
    cases = [dict(case='original', path=str(source), sha256='b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d',
                  manifest_sha256='3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f')] + variants
    for case in cases:
        argv = [sys.executable, '-B', CODE / 'examples/a06/consume.py', case['path'], '--sha256', case['sha256'], '--manifest-sha256', case['manifest_sha256']]
        if case['case'] == 'original':
            argv.append('--documents')
        rc, stdout, stderr, process = run(case['case'], argv, cwd2, logs)
        processes.append(process)
        outcome = dict(case=case['case'], exit_code=rc, stderr_empty=not stderr, input_sha256=case['sha256'])
        try:
            output = json.loads(stdout)
            if case['case'] == 'original':
                inspection = inspect_original(output, source)
                dump(ROOT / 'original-inspection.json', inspection)
                outcome.update(decision=output['receipt']['decision'], expected_matched=rc == 0 and not stderr and inspection['all_expected'])
            else:
                error = output.get('error', {})
                expected_path = {'bad-resource': 'supporting-fixtures/q4-stem.jpg', 'stale-check': 'artifacts/check.json#/payload/graph_ref',
                                 'unknown-version': 'artifacts/graph.json#/schema_version'}[case['case']]
                outcome.update(decision=output.get('decision'), error=error, expected_matched=(rc == 2 and not stderr and output.get('decision') == 'REJECTED' and
                    error.get('code') == case['expected_code'] and error.get('layer') == case['expected_layer'] and error.get('path') == expected_path))
        except Exception as exc:
            outcome.update(expected_matched=False, inspection_error=repr(exc))
        outcomes.append(outcome)
    version_code = """import json
from annotation.source.b_handoff import version_policy,HandoffError
rows=[]
for kind,prefix in [('QuestionGraphTrial','b-graph-trial/'),('CheckReportTrial','b-check-trial/')]:
 for v,location,bound in [('0.4','CURRENT',False),('0.4','ARCHIVE',True),('0.5','CURRENT',False),('0.5','ARCHIVE',True),('0.6','CURRENT',False),('0.7','CURRENT',False),('9.9','CURRENT',False)]:
  try: observed=version_policy(prefix+v,kind=kind,location=location,bound_archive=bound)
  except HandoffError as e: observed=e.code
  rows.append(dict(kind=kind,version=v,location=location,observed=observed))
print(json.dumps(rows))
"""
    rc, stdout, stderr, process = run('versions', [sys.executable, '-B', '-c', version_code], cwd1, logs)
    processes.append(process)
    rows = json.loads(stdout) if rc == 0 else []
    for row in rows:
        row['expected'] = ('ARCHIVE_ONLY' if row['location'] == 'ARCHIVE' else 'ARCHIVE_ONLY_NOT_CURRENT') if row['version'] in ('0.4', '0.5') else ('READ_ONLY_HOLD' if row['version'] == '0.7' else 'UNSUPPORTED_VERSION')
        row['expected_matched'] = row['observed'] == row['expected']
    dump(ROOT / 'version-matrix.json', rows)
    outcomes.append(dict(case='versions', exit_code=rc, expected_matched=rc == 0 and not stderr and len(rows) == 14 and all(r['expected_matched'] for r in rows)))
    for fixture, state in [('normal', 'READY_FOR_SUBMISSION'), ('exception', 'NEEDS_REVIEW'), ('unknown', 'NEEDS_RECONCILIATION')]:
        rc, stdout, stderr, process = run('c01-' + fixture, [sys.executable, '-B', CODE / 'examples/contracts/consume.py', CODE / 'tests/fixtures/contracts' / fixture], cwd1, logs)
        processes.append(process)
        observed = json.loads(stdout) if rc == 0 else {}
        outcomes.append(dict(case='c01-' + fixture, exit_code=rc, expected_matched=rc == 0 and not stderr and observed.get('comparison') == 'EXACT_MATCH' and observed.get('batch_state') == state, observed=observed))
    original_unchanged = sha(source.read_bytes()) == 'b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d'
    original_external = Path('D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip')
    assert sha(original_external.read_bytes()) == sha(source.read_bytes())
    summary = dict(status='FINITE_RUN_COMPLETE', driver_pid=os.getpid(), parent_pid=os.getppid(),
                   outcomes=outcomes, all_expectations_met=all(r['expected_matched'] for r in outcomes),
                   public_full_entry_calls=4, public_full_entry_calls_per_case=1,
                   original_unchanged=original_unchanged, processes=processes, children_reaped=len(processes),
                   background_processes_started=0, no_candidate_or_guard_changes=True,
                   complete_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    dump(ROOT / 'run-summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('status', 'driver_pid', 'all_expectations_met', 'public_full_entry_calls', 'children_reaped')}))
    return 0 if summary['all_expectations_met'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
