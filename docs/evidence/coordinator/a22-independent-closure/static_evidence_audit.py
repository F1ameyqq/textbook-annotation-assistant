"""Report metadata repair only: no product import, test or prior control rerun."""
import ast
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
FOLDER = ROOT / 'docs/evidence/A22/session-reuse'
source = (ROOT / 'tools/a16_current_state_probe.py').read_bytes().decode('utf-8')
tree = ast.parse(source)
segments = {node.name: ast.get_source_segment(source, node) for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
unchanged = json.loads((FOLDER / 'unchanged-regions.json').read_bytes())
checked = []
for item in unchanged['probe_exact_regions']:
    segment = segments[item['name']]
    actual = hashlib.sha256(segment.encode('utf-8')).hexdigest()
    assert actual == item['sha256'], item['name']
    checked.append({'name': item['name'], 'sha256': actual, 'current_segment_matches_frozen_evidence': True})
first_node = next(node for node in tree.body if getattr(node, 'name', None) == 'NavigationEvidence')
wrong_region = ''.join(source.splitlines(keepends=True)[first_node.lineno-1:first_node.end_lineno])
assert wrong_region == segments['NavigationEvidence'] + '\n'

candidate_raw = (FOLDER / 'candidate-manifest.json').read_bytes()
delivery_raw = (FOLDER / 'delivery-manifest.json').read_bytes()
candidate, delivery = json.loads(candidate_raw), json.loads(delivery_raw)
assert hashlib.sha256(candidate_raw).hexdigest() == '264e7fd8120efc8dd8f95f6c66b28693104d82f47e3d68e3a91fd0c422b38141'
assert hashlib.sha256(delivery_raw).hexdigest() == 'dd8ff91275f46b35f0551cf1dfb17971cce0352c1606bbca8d6e3af8c6dfaeb0'
for manifest in (candidate, delivery):
    seen = set()
    for member in manifest['members']:
        path = Path(member['path'])
        assert not path.is_absolute() and '..' not in path.parts and ':' not in str(path)
        assert member['path'] not in seen
        seen.add(member['path'])
        raw = (ROOT / path).read_bytes()
        assert len(raw) == member['size']
        assert hashlib.sha256(raw).hexdigest() == member['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == member['blob']

inputs = json.loads((OUT / 'input-audit.json').read_bytes())
bound_paths = {m['path'] for m in candidate['members']} | {m['path'] for m in delivery['members']}
bound_paths.add('docs/evidence/A22/session-reuse/delivery-manifest.json')
assert bound_paths == {m['path'] for m in inputs['members']}

# This duplicates no semantic control: compare frozen document values to the
# frozen report template and inspect declared source literals without importing.
report = json.loads((FOLDER / 'independent-report-template-NONEXECUTABLE.json').read_bytes())
scope_keys = [key for key in report if key != 'result']
assert len(scope_keys) == 50 and report['result'] == 'NOT_REVIEWED'
for name in ('decision', 'activation'):
    document = json.loads((FOLDER / (name + '-template-NONEXECUTABLE.json')).read_bytes())
    for key in scope_keys:
        assert type(document[key]) is type(report[key]) and document[key] == report[key]
    for key in scope_keys:
        if key != 'candidate_manifest_sha256':
            assert type(candidate[key]) is type(report[key]) and candidate[key] == report[key]

result = {'task': 'A22', 'kind': 'STATIC_METADATA_AUDIT_ONLY', 'success': True,
    'candidate_members_verified': len(candidate['members']), 'delivery_members_verified': len(delivery['members']),
    'unique_bound_input_members': len(bound_paths), 'template_scope_members': len(scope_keys),
    'scope_consistent_templates': 3, 'current_region_digests': checked,
    'failed_control_diagnosis': {'case': 'NavigationEvidence extraction',
        'failed_extractor': 'splitlines(keepends=True)[lineno-1:end_lineno]',
        'frozen_extractor': 'ast.get_source_segment(source,node)',
        'difference_proven': 'Failed extractor includes exactly one trailing LF beyond the AST source segment',
        'product_changed': False, 'failed_test_original_preserved': True,
        'suite_or_control_rerun': False,
        'successor_control': 'test_02_missing_scope_members_and_wrong_same_value_types_cannot_bind NOT_RUN'},
    'baseline_region_identity_basis': 'Frozen author AST comparison and root preservation facts; this helper only checks current segments against supplied frozen digests',
    'product_imports': 0, 'product_entry_points': 0, 'suites_run': 0,
    'real_browser_network_profile_credentials_native_or_live': 0}
with (OUT / 'static-evidence-audit.json').open('xb') as stream:
    stream.write((json.dumps(result, ensure_ascii=True, indent=2) + '\n').encode('utf-8'))
print(json.dumps({k: v for k, v in result.items() if k not in ('current_region_digests', 'failed_control_diagnosis')}))
