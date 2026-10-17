"""Freeze new native package pins and statically inspect actual bridge syntax."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / 'src/annotation/contracts/a03_native'
EVIDENCE = ROOT / 'docs/evidence/A03/execution/P2-R8-native-bridge'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def main():
    ast.parse((ROOT / 'tests/test_a03_r8_native_bridge.py').read_text(encoding='utf-8'), filename='test_a03_r8_native_bridge.py')
    for folder in ('src/annotation/contracts/a03_native', 'examples/a03/P2-R8-native-bridge'):
        for path in (ROOT / folder).rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    exchange_path = PACKAGE / 'data/schemas/exchange.json'
    exchange = json.loads(exchange_path.read_bytes())
    post = exchange['$defs']['AmendedCheckReport']['properties']['payload']['oneOf'][2]
    post['properties']['report_observation'] = exchange['$defs']['AmendedCheckReport']['properties']['payload']['oneOf'][0]['properties']['synthetic_run_ref']
    if 'report_observation' not in post['required']:
        post['required'].append('report_observation')
    write(exchange_path, exchange)
    implementations = [p for p in sorted(PACKAGE.glob('*.py'))]
    for relative in ('contracts/__init__.py', 'contracts/validation.py', 'contracts/recovery.py',
                     'quality/targetcheck/__init__.py', 'quality/synthetic_precheck.py',
                     'delivery/planner/__init__.py', 'delivery/mock/persistent.py', 'delivery/reconciler/__init__.py'):
        implementations.append(ROOT / 'src/annotation' / relative)
    for folder in ('runtime/storage', 'runtime/recovery'):
        implementations.extend(sorted((ROOT / 'src/annotation' / folder).glob('*.py')))
    for path in implementations:
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    implementation_pins = [[p.name if p.parent == PACKAGE else '@annotation/' + p.relative_to(ROOT / 'src/annotation').as_posix(), sha(p)] for p in implementations]
    selection = {'profile_id': 'a03-native-synthetic-1-PROPOSAL',
        'artifact_version': '1.4.0-a03-native-proposal', 'exchange_version': 'a03-exchange-4-proposal',
        'adoption_scope': 'A_INTERNAL_FIXED_SYNTHETIC_ONLY', 'role': 'CURRENT',
        'schema_pins': [['schemas/' + p.name, sha(p)] for p in sorted((PACKAGE / 'data/schemas').glob('*.json'))],
        'api_sha256': sha(PACKAGE / 'data/api.json'),
        'interface_sha256': sha(PACKAGE / 'data/interface-source.json'),
        'oracle_sha256': sha(PACKAGE / 'data/oracle.json'),
        'verifier_sha256': '6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d',
        'implementation_pins': implementation_pins,
        'oracle_adoption': 'Fixed five comparisons migrated to product; historical CANDIDATE/false files unchanged; not B, OCR or real quality',
        'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    write(PACKAGE / 'data/profile.json', selection)
    write(PACKAGE / 'data/adoption.json', {'profile_sha256': sha(PACKAGE / 'data/profile.json'),
        'scope': 'A_INTERNAL_FIXED_SYNTHETIC_ONLY', 'runtime_authority': 'PRIVATE_DURABLE_REGISTRY_REQUIRED',
        'status': 'REVIEW', 'B_contract': 'UNCONFIRMED', 'I01': 'NOT_RELEASED'})
    actual = []
    files = {
        'src/annotation/contracts/__init__.py': {'validate_bundle', 'assert_plan_ready', 'seal_artifact'},
        'src/annotation/contracts/validation.py': {'validate_bundle'},
        'src/annotation/contracts/recovery.py': {'validate_recovery_bundle', 'assert_recovery_plan_ready'},
        'src/annotation/quality/targetcheck/__init__.py': {'make_artifact', 'analyze_target', 'check_target'},
        'src/annotation/delivery/planner/__init__.py': {'create_plan', 'verify_generated_plan', 'bind_plan_observation', 'snapshot_state_equivalent'},
        'src/annotation/delivery/mock/persistent.py': {'create', 'open', '_verify_observation', 'snapshot_from_observation', 'prepare_action', 'verify_prepared_action'}}
    for path, names in files.items():
        source = (ROOT / path).read_text(encoding='utf-8')
        tree = ast.parse(source, filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in names:
                if 'bridge_context' not in [arg.arg for arg in node.args.kwonlyargs]:
                    raise RuntimeError('not keyword-only: ' + path + ':' + node.name)
                actual.append({'path': path, 'name': node.name, 'signature': ast.get_source_segment(source, node).split('):', 1)[0] + '):'})
    if len(actual) != 19:
        raise RuntimeError('expected nineteen signatures')
    write(EVIDENCE / 'contract-signatures.json', actual)
    print(json.dumps({'actual_signatures': len(actual), 'profile_sha256': sha(PACKAGE / 'data/profile.json')}))


if __name__ == '__main__':
    main()
