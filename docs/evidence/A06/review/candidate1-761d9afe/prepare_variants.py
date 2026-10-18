"""Audit the fixed recipe's outputs as bytes/JSON before public receiver calls."""
import io
import json
import os
from pathlib import Path
import sys
import zipfile

from review_tools import CODE, ROOT, dump, run, sha

def read_zip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) == len({p.casefold() for p in names})
        assert all(not n.startswith('/') and '..' not in n.split('/') and '\\' not in n for n in names)
        return {n: archive.read(n) for n in names}

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)

def ref(value):
    return {k: value[k] for k in ('artifact_id', 'revision', 'content_hash') if k in value}

def audit(data, case):
    files = read_zip(data)
    manifest = json.loads(files['manifest.json'])
    listed = manifest['files']
    assert set(files) == {r['path'] for r in listed} | {'manifest.json'}
    assert len(listed) == len({r['path'] for r in listed})
    assert all(len(files[r['path']]) == r['bytes'] and sha(files[r['path']]) == r['sha256'] for r in listed)
    documents = {n: json.loads(v) for n, v in files.items() if n.endswith('.json') and n != 'manifest.json'}
    inner = read_zip(files['inputs/inline-observed.zip'])
    inline = documents['inputs/inline-package.json']
    assert all(len(inner[n]) == r['bytes'] and sha(inner[n]) == r['sha256'] for n, r in inline['members'].items())
    all_documents = list(documents.values()) + [json.loads(v) for n, v in inner.items() if n.endswith('.json')]
    payload_count = 0
    for document in all_documents:
        for node in walk(document):
            if 'payload' in node and 'content_hash' in node:
                assert sha(canonical(node['payload'])) == node['content_hash']
                payload_count += 1
    e, g, c, p = [documents['artifacts/' + n + '.json'] for n in ('evidence', 'graph', 'check', 'pipeline-report')]
    assert manifest['report_ref'] == ref(p)
    finals = {'evidence_ref': e, 'graph_ref': g, 'quality_ref': c}
    for key, value in finals.items():
        assert manifest['final_outputs'][key] == ref(value) == p['payload']['final_outputs'][key]
    wrappers = []
    for stage in p['payload']['stages']:
        output = stage['output']
        name = output['path']
        wrapper = documents[name]
        assert sha(files[name]) == output['sha256']
        assert ref(wrapper) == output['artifact_ref']
        result = wrapper['payload']['result']
        assert ref(result) == stage['result_ref']
        for stage_id, final, route in [('continuation_prepare', e, ('payload', 'evidence')),
                                       ('content_apply', g, ('payload', 'graph')), ('content_quality', c, ())]:
            if stage['stage_id'] == stage_id:
                observed = result
                for field in route:
                    observed = observed[field]
                assert observed == final
        wrappers.append(dict(stage=stage['stage_id'], wrapper=name, wrapper_sha256=sha(files[name]), result_ref=ref(result)))
    assert c['payload']['evidence_ref'] == ref(e)
    assert ref(e) in c['input_refs'] and ref(e) in g['input_refs'] and ref(g) in c['input_refs']
    stale = c['payload']['graph_ref'] != ref(g)
    assert stale == (case == 'stale-check')
    if stale:
        assert c['payload']['graph_ref'] == c['payload']['base_check_archive']['payload']['graph_ref']
    assert (g['schema_version'] == 'b-graph-trial/9.9') == (case == 'unknown-version')
    return dict(case=case, zip_sha256=sha(data), zip_bytes=len(data), manifest_sha256=sha(files['manifest.json']),
                manifest_files=len(listed), outer_members=len(files), inner_members=len(inner),
                payload_occurrences_verified=payload_count, manifest_and_all_member_hashes_valid=True,
                payload_self_hashes_valid=True, wrappers_and_finals_valid=True, wrappers=wrappers,
                graph_version=g['schema_version'], check_graph_ref=c['payload']['graph_ref'], current_graph_ref=ref(g),
                deliberate_stale_relation=stale), files

def main():
    logs = ROOT / 'static'
    logs.mkdir(exist_ok=False)
    source = next((ROOT / 'inputs').glob('*.zip'))
    variants = ROOT / 'variants'
    code, stdout, stderr, process = run('make-variants', [sys.executable, '-B', CODE / 'examples/a06/make_variants.py', source, variants], ROOT, logs)
    assert code == 0 and not stderr
    recipes = json.loads(stdout)
    original = source.read_bytes()
    original_audit, original_files = audit(original, 'original')
    assert original_audit['manifest_sha256'] == '3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f'
    author_manifest = json.loads((CODE / 'docs/evidence/A06/manifest.json').read_bytes())
    author_files = author_manifest['files']
    assert all(len((CODE / r['path']).read_bytes()) == r['bytes'] and sha((CODE / r['path']).read_bytes()) == r['sha256'] for r in author_files)
    checks = [original_audit]
    for recipe in recipes:
        data = Path(recipe['path']).read_bytes()
        observed, files = audit(data, recipe['case'])
        assert recipe['sha256'] == observed['zip_sha256'] and recipe['manifest_sha256'] == observed['manifest_sha256']
        actual_changes = {}
        for name in sorted(set(original_files) | set(files)):
            before, after = original_files.get(name), files.get(name)
            if before != after:
                actual_changes[name] = {'before': None if before is None else {'bytes': len(before), 'sha256': sha(before)},
                                        'after': None if after is None else {'bytes': len(after), 'sha256': sha(after)}}
        assert actual_changes == recipe['changed_members']
        author = json.loads((CODE / ('docs/evidence/A06/author/frozen-01/' + recipe['case'] + '-recipe.json')).read_bytes())
        assert author['sha256'] == sha(data)
        if recipe['case'] == 'bad-resource':
            assert files['supporting-fixtures/q4-stem.jpg'] == b'A06 TEST_VARIANT: intentionally undecodable image\n'
            assert set(actual_changes) == {'manifest.json', 'supporting-fixtures/q4-stem.jpg'}
        observed.update(changed_members=actual_changes, recipe_changes_match=True, deterministic_author_hash_match=True,
                        expected_code=recipe['expected_code'], expected_layer=recipe['expected_layer'])
        checks.append(observed)
    dump(ROOT / 'static-audit.json', dict(status='READY_FOR_FOUR_PUBLIC_CALLS', parent_pid=os.getpid(),
                                         author_manifest_members_verified=len(author_files),
                                         author_manifest_bytes_verified=sum(r['bytes'] for r in author_files),
                                         checks=checks, generator_process=process,
                                         no_database_open_or_B_code_execution=True))
    print(json.dumps(dict(status='READY_FOR_FOUR_PUBLIC_CALLS', inputs=len(checks), generator_pid=process['pid'], generator_reaped=True)))

if __name__ == '__main__':
    main()
