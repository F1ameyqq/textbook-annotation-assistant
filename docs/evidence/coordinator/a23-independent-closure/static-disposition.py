"""Static-only disposition; parses source as data, imports no product/test code."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/1800-worktrees/a23-independent-fixed')
OUT = ROOT / 'docs/evidence/A23/independent-session-completion-review'
EVIDENCE = ROOT / 'docs/evidence/A23/session-completion'


def load(path):
    return json.loads(path.read_bytes())


def save(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


gate_source = (ROOT / 'src/annotation/source/usense/current_readonly/gate.py').read_bytes().decode('utf-8')
gate_ast = ast.parse(gate_source)
values = {}
functions = {node.name: node for node in gate_ast.body if isinstance(node, ast.FunctionDef)}


def literal(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, ast.List):
        return [literal(item) for item in node.elts]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return literal(node.left) + literal(node.right)
    if isinstance(node, ast.Dict):
        result = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                result.update(literal(value))
            else:
                result[literal(key)] = literal(value)
        return result
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('auth_scope', 'static_image_scope'):
        assert not node.args and not node.keywords
        return literal(next(item.value for item in functions[node.func.id].body if isinstance(item, ast.Return)))
    raise ValueError('Unsupported static expression: ' + type(node).__name__)


for node in gate_ast.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        values[node.targets[0].id] = literal(node.value)

candidate_raw = (EVIDENCE / 'candidate-manifest.json').read_bytes()
candidate_sha = hashlib.sha256(candidate_raw).hexdigest()
assert candidate_sha == '18921b3335809c0c0722dc1bf8bf1495d8628bab780ce95045079c82c1f615ad'
values['candidate'] = candidate_sha
scope_node = next(node.value for node in functions['scope_binding'].body if isinstance(node, ast.Return))
expected = literal(scope_node)
assert len(expected) == 53


def same_typed(actual, wanted):
    if type(actual) is not type(wanted):
        return False
    if type(wanted) is list:
        return len(actual) == len(wanted) and all(same_typed(a, b) for a, b in zip(actual, wanted))
    return actual == wanted


template_checks = []
for name in ('activation-template-NONEXECUTABLE.json', 'decision-template-NONEXECUTABLE.json',
             'independent-report-template-NONEXECUTABLE.json'):
    document = load(EVIDENCE / name)
    mismatches = [key for key, value in expected.items() if not same_typed(document.get(key), value)]
    assert not mismatches, (name, mismatches)
    template_checks.append({'path': name, 'typed_scope_fields_equal': 53})

candidate = json.loads(candidate_raw)
assert 'candidate_manifest_sha256' not in candidate
assert all(same_typed(candidate.get(key), value) for key, value in expected.items()
           if key != 'candidate_manifest_sha256')
decision = load(EVIDENCE / 'decision-template-NONEXECUTABLE.json')
assert all(decision[key] is False for key in ('live_authorized', 'certificate_exception_authorized',
           'login_submission_authorized', 'credential_transmission_authorized',
           'credential_tls_exception_authorized', 'local_credential_config_read_authorized'))
activation = load(EVIDENCE / 'activation-template-NONEXECUTABLE.json')
assert activation['not_before'] is None and activation['expires_at'] is None
assert load(EVIDENCE / 'independent-report-template-NONEXECUTABLE.json')['result'] == 'NOT_REVIEWED'
standing_sha = hashlib.sha256((EVIDENCE / 'authority/standing-permission.json').read_bytes()).hexdigest()
assert standing_sha == expected['standing_tls_permission_sha256']

probe_source = (ROOT / 'tools/a16_current_state_probe.py').read_bytes().decode('utf-8')
probe_ast = ast.parse(probe_source)
regions = {node.name: ast.get_source_segment(probe_source, node).encode('utf-8')
           for node in probe_ast.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))}
region_checks = []
for entry in load(EVIDENCE / 'unchanged-regions.json')['probe_exact_regions']:
    current = hashlib.sha256(regions[entry['name']]).hexdigest()
    assert current == entry['sha256']
    region_checks.append({'name': entry['name'], 'sha256': current})

save('static-scope-and-disposition.json', {
    'status': 'STATIC_CONFORMITY_CONFIRMED', 'product_imports': 0, 'product_or_test_runs': 0,
    'method': 'Restricted AST data evaluation of constant dictionaries; no exec/eval or product imports',
    'candidate_sha256': candidate_sha, 'scope_member_count': 53, 'templates': template_checks,
    'scope_binding': expected, 'candidate_non_self_scope_fields_equal': 52,
    'external_candidate_binding': 'Exact raw SHA256 matches dispatch/input manifest and all three templates',
    'helper_failure_disposition': {
        'original_result': '1 FAIL, 3 NOT_RUN; original helper and output preserved without rerun',
        'failed_expectation': 'Candidate manifest required to contain its own candidate_manifest_sha256',
        'cause': 'Reviewer helper incorrectly imposed circular self-digest membership',
        'product_basis': 'candidate() explicitly excludes candidate_manifest_sha256 from internal field comparison; external raw digest is independently checked',
        'product_semantic_counterexample': False,
        'report_mutation_loop_in_failed_control': 'NOT_RUN',
        'decision_mutation_basis': 'Independent 18-test suite exercised all decision scope removals; common gate loop checks decision and report',
        'later_control_methods': 'NOT_RUN; no control replay or product fix'},
    'templates_remain_nonexecutable': True, 'standing_permission_sha256': standing_sha,
    'unchanged_region_hashes': region_checks,
    'unchanged_prior_evidence_basis': 'Frozen raw preservation evidence and coordinator base/final mechanical preflight; no old suite rerun',
    'no_live_authorization_from_report': True})

not_run = [{'case': name, 'status': 'NOT_RUN', 'reason': 'Failfast stopped control run01 after reviewer self-digest expectation failure'}
           for name in ('cross_barrier_interleaving', 'failed_body_and_finite_projection', 'one_20_second_deadline')]
save('controls-not-run.json', {'control_run01': {'tests_run': 1, 'failures': 1, 'duration_ms': 93},
                             'successors': not_run, 'original_results_relabelled': False})
print(json.dumps({'static_status': 'CONFORMITY_CONFIRMED', 'scope_fields': 53, 'templates': 3,
                  'candidate_non_self_fields': 52, 'unchanged_regions': len(region_checks),
                  'original_control_failures_preserved': 1, 'control_successors_not_run': 3}))
