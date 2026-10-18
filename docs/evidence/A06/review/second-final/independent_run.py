"""F01-only two-entry final review, stopping at first failure, with no reruns."""
import ast
import copy
import io
import json
import os
from pathlib import Path
import sys
import zipfile

from review_tools import CODE, ROOT, dump, run, sha

FIRST = ROOT.parent / 'candidate1-761d9afe'

def unzip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) == len({n.casefold() for n in names})
        assert all(not n.startswith('/') and '..' not in n.split('/') and '\\' not in n for n in names)
        return {n: archive.read(n) for n in names}

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def ref(value):
    return {k: value[k] for k in ('artifact_id', 'revision', 'content_hash')}

def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)

def fixed_observations(original):
    files = unzip(original)
    manifest = json.loads(files['manifest.json'])
    assert sha(files['manifest.json']) == '3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f'
    rows = []
    report = json.loads(files['artifacts/pipeline-report.json'])
    for stage in report['payload']['stages']:
        wrapper = json.loads(files[stage['output']['path']])
        result = wrapper['payload']['result']
        rows.append(dict(stage_id=stage['stage_id'], kind=result['kind'], schema_version=result['schema_version'],
                         path=stage['output']['path'] + '#/payload/result'))
    source = (CODE / 'src/annotation/source/b_handoff/reader.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    stage_table = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_STAGE_RESULT_TYPES' for t in n.targets))
    expected_table = {r['stage_id']: (r['kind'], r['schema_version']) for r in rows}
    assert len(rows) == 14 and stage_table == expected_table
    test_tree = ast.parse((CODE / 'tests/test_a06_stage_results.py').read_text(encoding='utf-8'))
    test_rows = next(ast.literal_eval(n.value) for n in test_tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'OBSERVED' for t in n.targets))
    assert test_rows == [(r['stage_id'], r['kind'], r['schema_version']) for r in rows]
    first = json.loads((FIRST / 'original-inspection.json').read_bytes())['wrapper_result_versions']
    assert [(r['stage_id'], r['kind'], r['schema_version']) for r in rows] == [(r['stage_id'], r['result_kind'], r['result_version']) for r in first]
    dump(ROOT / 'observed-stage-results.json', dict(status='MATCHED_FIXED_INPUT_SOURCE_AND_FIRST_OBSERVATION', observations=rows,
                                                   production_table=stage_table, test_observed_rows=test_rows))
    return files, rows

def audit_variant(original_files, recipe):
    data = Path(recipe['path']).read_bytes()
    assert sha(data) == recipe['sha256'] == '5911f8d572c97027f0ac12a5c1dbe3e190e59a6391904fdd91cef6501bf91af8'
    files = unzip(data)
    manifest = json.loads(files['manifest.json'])
    assert sha(files['manifest.json']) == recipe['manifest_sha256']
    assert len(manifest['files']) == len({r['path'] for r in manifest['files']})
    assert set(files) == {r['path'] for r in manifest['files']} | {'manifest.json'}
    assert all(len(files[r['path']]) == r['bytes'] and sha(files[r['path']]) == r['sha256'] for r in manifest['files'])
    documents = {n: json.loads(v) for n, v in files.items() if n.endswith('.json') and n != 'manifest.json'}
    hashes = 0
    for document in documents.values():
        for node in walk(document):
            if 'payload' in node and 'content_hash' in node:
                assert sha(canonical(node['payload'])) == node['content_hash']
                hashes += 1
    report = documents['artifacts/pipeline-report.json']
    previous_report = json.loads(original_files['artifacts/pipeline-report.json'])
    assert manifest['report_ref'] == ref(report)
    assert report['payload']['final_outputs'] == previous_report['payload']['final_outputs']
    current = {key: documents['artifacts/' + name + '.json'] for key, name in [('evidence_ref', 'evidence'), ('graph_ref', 'graph'), ('quality_ref', 'check')]}
    for key, obj in current.items():
        assert report['payload']['final_outputs'][key] == manifest['final_outputs'][key] == ref(obj)
    target_path = None
    checked_wrappers = []
    for stage, old_stage in zip(report['payload']['stages'], previous_report['payload']['stages']):
        assert stage['stage_id'] == old_stage['stage_id']
        path = stage['output']['path']
        wrapper = documents[path]
        result = wrapper['payload']['result']
        before = json.loads(original_files[old_stage['output']['path']])['payload']['result']
        assert sha(files[path]) == stage['output']['sha256']
        assert ref(wrapper) == stage['output']['artifact_ref'] and ref(result) == stage['result_ref']
        if stage['stage_id'] == 'inline_apply':
            restored = copy.deepcopy(result)
            assert restored['schema_version'] == 'b-inline-apply-stage-trial/9.9'
            restored['schema_version'] = before['schema_version']
            assert restored == before and ref(result) == ref(before) and result['payload'] == before['payload']
            target_path = path + '#/payload/result/schema_version'
        else:
            assert result == before
        for sid, key, route in [('continuation_prepare', 'evidence_ref', ('payload', 'evidence')), ('content_apply', 'graph_ref', ('payload', 'graph')), ('content_quality', 'quality_ref', ())]:
            if stage['stage_id'] == sid:
                final = result
                for field in route:
                    final = final[field]
                assert final == current[key]
        checked_wrappers.append(dict(stage_id=stage['stage_id'], path=path, wrapper_ref=ref(wrapper), result_ref=ref(result)))
    assert target_path == recipe['expected_error_path']
    for name in ('artifacts/evidence.json', 'artifacts/graph.json', 'artifacts/check.json', 'inputs/inline-observed.zip'):
        assert files[name] == original_files[name]
    changes = {}
    for name in sorted(set(files) | set(original_files)):
        before, after = original_files.get(name), files.get(name)
        if before != after:
            changes[name] = {'before': None if before is None else dict(bytes=len(before), sha256=sha(before)),
                             'after': None if after is None else dict(bytes=len(after), sha256=sha(after))}
    assert changes == recipe['changed_members']
    dump(ROOT / 'variant-static-audit.json', dict(status='READY_FOR_TWO_PUBLIC_ENTRIES', zip_sha256=sha(data), bytes=len(data),
        manifest_sha256=sha(files['manifest.json']), manifest_members=len(manifest['files']), outer_members=len(files),
        payload_occurrences_verified=hashes, non_destructive_member_and_payload_hashes_valid=True,
        current_E_G_Check_and_inner_zip_bytes_unchanged=True, other_13_stage_results_unchanged=True,
        target_result_only_schema_version_changed=True, all_wrapper_result_and_final_refs_valid=True,
        expected_error_path=target_path, wrapper_bindings=checked_wrappers, changed_members=changes))

def main():
    assert json.loads((ROOT / 'inheritance-audit.json').read_bytes())['status'] == 'STATIC_READY'
    logs = ROOT / 'run'
    logs.mkdir(exist_ok=False)
    cwd = ROOT / 'foreign-cwd'
    cwd.mkdir(exist_ok=False)
    source = next((ROOT / 'inputs').glob('*.zip'))
    processes, outcomes = [], []
    full_calls = 0
    def finish(status):
        summary = dict(status=status, driver_pid=os.getpid(), candidate_number=2, final_candidate=True,
                       delivery='d78737815279965f660057bea0a572b426098aaa', candidate='43ebdd21f2dc6803ae322b95776806e167884749',
                       outcomes=outcomes, all_expectations_met=all(r['expected_matched'] for r in outcomes),
                       public_entry_calls=full_calls, processes=processes, children_reaped=len(processes),
                       original_unchanged=sha(source.read_bytes()) == 'b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d',
                       no_full_first_matrix_rerun=True, background_processes_started=0)
        dump(ROOT / 'run-summary.json', summary)
        print(json.dumps({k: summary[k] for k in ('status', 'driver_pid', 'all_expectations_met', 'public_entry_calls', 'children_reaped')}))
        return 0 if status == 'FINITE_DELTA_COMPLETE' else 1
    try:
        original_files, observations = fixed_observations(source.read_bytes())
        metadata_code = """import sys,json,pathlib,hashlib,PIL,pydantic
import annotation.source.b_handoff as b
import annotation.source.b_handoff.reader as r
import annotation.source.b_handoff.__main__ as cli
print(json.dumps({'python':sys.version,'executable':sys.executable,'Pillow':PIL.__version__,'pydantic':pydantic.__version__,'modules':[{'name':m.__name__,'file':m.__file__,'sha256':hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest()} for m in [b,r,cli]]}))
"""
        rc, stdout, stderr, record = run('imports', [sys.executable, '-B', '-c', metadata_code], cwd, logs)
        processes.append(record)
        metadata = json.loads(stdout) if rc == 0 else {}
        matched = rc == 0 and not stderr and all(Path(m['file']).resolve().is_relative_to(CODE.resolve()) for m in metadata.get('modules', [])) and len(metadata.get('modules', [])) == 3
        outcomes.append(dict(case='imports', exit_code=rc, expected_matched=matched))
        if not matched:
            return finish('BLOCKED_IMPORTS')
        rc, stdout, stderr, record = run('narrow-stage-fields', [sys.executable, '-B', CODE / 'tests/test_a06_stage_results.py', '-v'], cwd, logs)
        processes.append(record)
        matched = rc == 0 and b'Ran 3 tests' in stderr and b'OK' in stderr
        outcomes.append(dict(case='narrow-stage-fields', exit_code=rc, expected_matched=matched, scope='14 observed pairs plus one unknown version and one wrong kind'))
        if not matched:
            return finish('REWORK_NARROW_FIELDS')
        rc, stdout, stderr, record = run('make-stage-result-variant', [sys.executable, '-B', CODE / 'examples/a06/make_stage_result_variant.py', source, ROOT / 'variant'], cwd, logs)
        processes.append(record)
        outcomes.append(dict(case='make-stage-result-variant', exit_code=rc, expected_matched=rc == 0 and not stderr))
        if rc != 0 or stderr:
            return finish('BLOCKED_VARIANT_GENERATION')
        recipe = json.loads(stdout)
        audit_variant(original_files, recipe)
        cases = [('original', source, 'b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d', '3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f'),
                 ('unknown-stage-result', recipe['path'], recipe['sha256'], recipe['manifest_sha256'])]
        for name, path, digest, manifest_digest in cases:
            rc, stdout, stderr, record = run(name, [sys.executable, '-B', CODE / 'examples/a06/consume.py', path, '--sha256', digest, '--manifest-sha256', manifest_digest], cwd, logs)
            full_calls += 1
            processes.append(record)
            receipt = json.loads(stdout)
            if name == 'original':
                observed = []
                pruned = copy.deepcopy(receipt)
                checks_valid = True
                for stage, expected, old_stage in zip(receipt['pipeline']['stages'], observations, pruned['pipeline']['stages']):
                    check = stage['result_version_check']
                    checks_valid = checks_valid and stage['stage_id'] == expected['stage_id'] and check == {
                        'path': expected['path'], 'kind': expected['kind'], 'schema_version': expected['schema_version'],
                        'validated': True, 'context': 'FIXED_STAGE_DIAGNOSTIC_ONLY', 'grants_current_top_level_support': False, 'business_acceptance': False}
                    observed.append(dict(stage_id=stage['stage_id'], **check))
                    del old_stage['result_version_check']
                previous_receipt = json.loads((FIRST / 'run/original.stdout.txt').read_bytes())['receipt']
                unchanged = pruned == previous_receipt
                matched = rc == 0 and not stderr and receipt['decision'] == 'HOLD' and len(receipt['pipeline']['stages']) == 14 and checks_valid and unchanged
                dump(ROOT / 'result-version-checks.json', observed)
                dump(ROOT / 'receipt-delta-check.json', dict(after_removing_only_14_new_checks_equals_first_independent_receipt=unchanged,
                    reference_stdout_sha256=sha((FIRST / 'run/original.stdout.txt').read_bytes()), counts=receipt['counts'], history_gap=receipt['history_gap'],
                    business_acceptance=receipt['business_acceptance'], c01_execution_eligible=receipt['c01_execution_eligible'], scopes=receipt['scopes']))
                outcomes.append(dict(case=name, exit_code=rc, expected_matched=matched, decision=receipt['decision'], version_checks=14,
                                     previous_receipt_exact_after_removing_checks=unchanged))
            else:
                error = receipt.get('error', {})
                matched = rc == 2 and not stderr and receipt['decision'] == 'REJECTED' and receipt['business_acceptance'] is False and receipt['c01_execution_eligible'] is False and (
                    error.get('code'), error.get('layer'), error.get('path')) == ('UNSUPPORTED_VERSION', 'VERSION', recipe['expected_error_path'])
                outcomes.append(dict(case=name, exit_code=rc, expected_matched=matched, decision=receipt.get('decision'), error=error))
            if not matched:
                return finish('REWORK_PUBLIC_ENTRY')
        return finish('FINITE_DELTA_COMPLETE')
    except Exception as exc:
        outcomes.append(dict(case='review-driver-failure', expected_matched=False, error=repr(exc)))
        return finish('BLOCKED_REVIEW_DRIVER')

if __name__ == '__main__':
    raise SystemExit(main())
