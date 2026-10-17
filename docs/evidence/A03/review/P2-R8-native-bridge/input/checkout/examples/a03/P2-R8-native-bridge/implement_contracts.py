"""One-time R8 source/data preparation; never executed by the product."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'src/annotation/contracts/a03_native'
OLD = ROOT / 'src/annotation/contracts/a03_bridge'


def raw(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def replace_file(name, before, after):
    path = ROOT / name
    value = path.read_text(encoding='utf-8')
    if before not in value:
        raise RuntimeError('source anchor missing: ' + name + ': ' + before[:60])
    raw(path, value.replace(before, after).encode('utf-8'))


def prepare():
    DEST.mkdir(parents=True, exist_ok=False)
    raw(DEST / '.gitattributes', b'* -text whitespace=trailing-space,space-before-tab,cr-at-eol\n')
    names = {'exchange': 'exchange-v3.schema.json', 'fact': 'fact-v3.schema.json',
        'prefix': 'prefix-v2.schema.json', 'basis': 'basis-v3.schema.json',
        'conversion': 'conversion-v3.schema.json', 'pre_run': 'pre-run-v2.schema.json'}
    docs = {}
    for key, name in names.items():
        original = (OLD / 'data/schemas' / name).read_bytes().decode('utf-8')
        original = original.replace('1.3.0-a03-static-proposal', '1.4.0-a03-native-proposal')
        original = original.replace('a03-exchange-3-proposal', 'a03-exchange-4-proposal')
        docs[key] = json.loads(original)
    exchange = docs['exchange']
    exchange['properties']['artifacts']['items']['oneOf'] = [row for row in exchange['properties']['artifacts']['items']['oneOf'] if '/Amended' in row['$ref']]
    exchange['title'] = 'A03 native synthetic proposal: structure is not runtime authority'
    exchange['$id'] = 'urn:a03:native:exchange-4'
    run = docs['pre_run']
    run['properties']['format_version']['const'] = 'a03-native-pre-run-1'
    run['properties']['runtime_status']['const'] = 'ACTUAL_CHECKS_COMPUTED'
    run['properties']['admission']['const'] = 'RUNTIME_RECHECK_REQUIRED'
    for check in run['properties']['checks']['properties'].values():
        check.clear()
        check['enum'] = ['PASS', 'FAIL']
    ref = run['properties']['source_ref']
    resource = run['properties']['actual_observation']
    run['properties'].update({'evidence_ref': ref, 'policy_ref': exchange['$defs']['PolicyRef'],
        'run_id': {'type': 'string', 'minLength': 1},
        'input_manifest': {'type': 'array', 'items': resource},
        'native_binding': {'type': 'object', 'properties': {
            key: {'type': 'integer', 'minimum': 0} if key == 'generation' else {'type': 'string', 'minLength': 1}
            for key in ('registry_id', 'registration_id', 'owner_id', 'generation', 'target_store_id', 'target_session_id')},
            'required': ['registry_id', 'registration_id', 'owner_id', 'generation', 'target_store_id', 'target_session_id'], 'additionalProperties': False}})
    run['required'] += ['evidence_ref', 'policy_ref', 'run_id', 'input_manifest', 'native_binding']
    for key, doc in docs.items():
        raw(DEST / 'data/schemas' / (key + '.json'), encoded(doc))
    oracle = (ROOT / 'examples/a03/P2-R2-proposal/oracle.json').read_bytes()
    raw(DEST / 'data/oracle.json', oracle)
    interfaces = json.loads((ROOT / 'examples/a03/P2-R4-bridge-registration/bridge-interface-proposal.json').read_bytes())
    raw(DEST / 'data/interface-source.json', encoded(interfaces))
    raw(DEST / 'data/api.json', encoded({'profile_id': 'a03-native-synthetic-1-PROPOSAL',
        'version': '1.4.0-a03-native-proposal', 'exchange_version': 'a03-exchange-4-proposal',
        'registry': json.loads((OLD / 'data/api.json').read_bytes())['registry'],
        'roles': ['CURRENT'], 'adoption_scope': 'A_INTERNAL_FIXED_SYNTHETIC_ONLY',
        'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}))
    rules = (OLD / '_rules.py').read_text(encoding='utf-8')
    rules = rules.replace('Normal product implementation of the frozen R2/R3/R5 static rules.', 'R8 native closure derived from frozen R7 R2/R3/R5 rules; old bytes stay frozen.')
    rules = rules.replace('from ._errors', 'from ..a03_bridge._errors').replace('from ._json', 'from ..a03_bridge._json').replace('from ._schema', 'from ..a03_bridge._schema')
    rules = rules.replace('1.3.0-a03-static-proposal', '1.4.0-a03-native-proposal')
    rules = rules.replace('in (VERSION, HISTORY_VERSION)', 'in (VERSION,)')
    rules = rules.replace('run["admission"] == "UNIMPLEMENTED_NO_NATIVE_RUN"', 'run["admission"] == "RUNTIME_RECHECK_REQUIRED" and run["snapshot_ref"] == artifact["payload"]["snapshot"]')
    raw(DEST / '_closure.py', rules.encode('utf-8'))


if __name__ == '__main__':
    prepare()
