"""Independent, offline P1-R2 mapping/API/profile byte inspection."""
import hashlib
import json
import sys
from pathlib import Path

STAGE = Path(sys.argv[1]).resolve()
OUT = Path(__file__).resolve().parent
R1 = STAGE / 'examples/a03/P1-R1'
R2 = STAGE / 'examples/a03/P1-R2'


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def diffs(a, b, at=''):
    if type(a) is not type(b):
        return [{'path': at, 'old': a, 'new': b}]
    if isinstance(a, dict):
        result = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                result.append({'path': at + '/' + k, 'old': a.get(k), 'new': b.get(k)})
            else:
                result.extend(diffs(a[k], b[k], at + '/' + k))
        return result
    if isinstance(a, list):
        if len(a) != len(b):
            return [{'path': at, 'old': a, 'new': b}]
        result = []
        for i, (left, right) in enumerate(zip(a, b)):
            result.extend(diffs(left, right, at + '/' + str(i)))
        return result
    return [] if a == b else [{'path': at, 'old': a, 'new': b}]


def signatures(o, at=''):
    result = {}
    if isinstance(o, dict):
        for k, v in o.items():
            if 'signature' in k:
                result[at + '/' + k] = v
            result.update(signatures(v, at + '/' + k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            result.update(signatures(v, at + '/' + str(i)))
    return result


old_manifest, new_manifest = load(R1/'data/case-manifest.json'), load(R2/'data/case-manifest.json')
old_cases = {o['case_id']: o for o in old_manifest['cases']}
new_cases = {o['case_id']: o for o in new_manifest['cases']}
mapping = load(R2/'data/r1-case-mapping.json')['mappings']
rows, failures, changes = [], [], {}
for row in mapping:
    case_id = row['r1_case_id']
    old = R1/'data'/old_cases[case_id]['path']
    new = R2/'data'/new_cases[case_id]['path']
    actual_old, actual_new = sha(old), sha(new)
    ok = (actual_old == row['r1_sha256'] and actual_new == row['r2_sha256']
          and row['r2_case_id'] == case_id and row['r1_path'] == old_cases[case_id]['path']
          and row['r2_path'] == new_cases[case_id]['path'])
    unchanged = old.read_bytes() == new.read_bytes()
    if not ok or unchanged != row['bytes_unchanged']:
        failures.append(case_id)
    rows.append({'case_id': case_id, 'mapping_matches_bytes': ok, 'bytes_equal': unchanged,
                 'r1_sha256': actual_old, 'r2_sha256': actual_new})
    if not unchanged:
        changes[case_id] = diffs(load(old), load(new))

old_api, new_api = load(R1/'api-proposal.json'), load(R2/'api-proposal.json')
sig_old, sig_new = signatures(old_api), signatures(new_api)
profile = new_api['candidate_profile']
schemas = []
for name, spec in profile['schema_files'].items():
    p = R2/spec['path']
    actual = sha(p)
    schemas.append({'name': name, 'path': spec['path'], 'actual_sha256': actual,
                    'declared': spec, 'matches': actual == spec['sha256']})

summary = {
    'source': str(STAGE), 'final_commit': '940a5de33a24b1a3a9ded6e69ade1dd0609ed83a',
    'design_commit': 'a250a76dc0b3f13b9dee3bcd2c3d7414032b9768',
    'method': 'Actual R1/R2 case bytes and recursive scalar diff; no expected codes used as oracle.',
    'old_manifest_case_count': len(old_cases), 'new_manifest_case_count': len(new_cases),
    'mapping_unique_and_exact': len(mapping) == len({r['r1_case_id'] for r in mapping}) == len(old_cases)
        and {r['r1_case_id'] for r in mapping} == set(old_cases),
    'added_case_ids': sorted(set(new_cases)-set(old_cases)),
    'mapping_failures': failures, 'byte_equal_count': sum(r['bytes_equal'] for r in rows),
    'byte_changed_count': sum(not r['bytes_equal'] for r in rows), 'rows': rows,
    'api_signature_count': len(sig_old), 'api_signatures_unchanged': sig_old == sig_new,
    'api_signature_differences': diffs(sig_old, sig_new), 'profile': profile, 'schema_checks': schemas,
    'limitations': ['Static serialized design review only. No future runtime/API or restore execution.',
                    'Subset/profile checks are not full JSON Schema standards validation.'],
}
for name, obj in [('mapping-summary.json', summary), ('changed-case-diffs.json', changes)]:
    (OUT/name).write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('rows','profile','schema_checks')}, indent=2))
print(json.dumps({'schema_checks': schemas}, indent=2))
