"""R12 static prerequisite audit only; never import or execute product code."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R12-inconclusive-readback'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def read_source(name):
    raw = (ROOT / name).read_bytes()
    text = raw.decode('utf-8', errors='strict')
    compile(text, name, 'exec')  # Syntax only; no exec/eval/import.
    return raw, text, ast.parse(text, filename=name)


def function(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


def segment(text, node):
    return {'line': node.lineno, 'end_line': node.end_lineno,
        'source': '\n'.join(text.splitlines()[node.lineno - 1:node.end_lineno])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', default='docs/evidence/A03/execution/P2-R12-inconclusive-readback/preflight')
    args = parser.parse_args()
    folder = (ROOT / args.output_root).resolve()
    assert folder.is_relative_to(OUT)
    storage = 'src/annotation/runtime/storage/__init__.py'
    native = 'src/annotation/runtime/storage/native.py'
    schema_path = 'src/annotation/contracts/a03_native/data/schemas/exchange.json'
    contract = 'src/annotation/contracts/a03_native/__init__.py'
    rows = {}
    for name in (storage, native, contract, 'src/annotation/delivery/mock/persistent.py',
                 'src/annotation/delivery/planner/__init__.py', 'src/annotation/runtime/recovery/__init__.py'):
        raw, text, tree = read_source(name)
        rows[name] = {'raw_sha256': sha(raw), 'bytes': len(raw), 'utf8_strict_compile_ok': True}
        if name == storage:
            source_text, source_tree = text, tree
        if name == native:
            native_text, native_tree = text, tree
        if name == contract:
            contract_text, contract_tree = text, tree
    projection = function(source_tree, '_project_plan_locked')
    posts = [n for n in ast.walk(projection) if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute) and n.func.attr == '_new_artifact'
        and len(n.args) > 2 and isinstance(n.args[1], ast.Constant) and n.args[1].value == 'CheckReport']
    assert len(posts) == 1 and isinstance(posts[0].args[2], ast.Dict)
    payload = posts[0].args[2]
    generated_keys = [n.value for n in payload.keys]
    stage = next(value.value for key, value in zip(payload.keys, payload.values) if key.value == 'stage')
    assert stage == 'POST_APPLY'
    raw_schema = (ROOT / schema_path).read_bytes()
    schema = json.loads(raw_schema.decode('utf-8', errors='strict'))
    branches = schema['$defs']['AmendedCheckReport']['properties']['payload']['oneOf']
    post_schema = next(b for b in branches if b['properties']['stage'].get('const') == 'POST_APPLY')
    missing = sorted(set(post_schema['required']) - set(generated_keys))
    extra = sorted(set(generated_keys) - set(post_schema['properties']))
    assert post_schema['additionalProperties'] is False and missing and extra
    assert not any(isinstance(n, ast.FunctionDef) and n.name == '_new_artifact' for n in ast.walk(native_tree))
    parents = {child: parent for parent in ast.walk(projection) for child in ast.iter_child_nodes(parent)}
    node, conditions = posts[0], []
    while node in parents:
        node = parents[node]
        if isinstance(node, ast.If):
            conditions.append({'line': node.lineno, 'condition': ast.unparse(node.test)})
    assert any(x['condition'] == 'issues' for x in conditions)
    record = {'status': 'PREPARATION_BLOCKED_STATIC_NATIVE_UNKNOWN_POST_CONTRACT',
        'base': 'cc5966dc58c62017a27266c40ca0cedc5c68485c', 'product_calls': 0,
        'analysis_method': 'Read-only strict UTF-8/compile/AST literal-field analysis and JSON Schema comparison; no AST slicing for execution, no product import or validation call.',
        'actual_python': sys.executable, 'source_index': rows,
        'schema': {'path': schema_path, 'raw_sha256': sha(raw_schema),
            'pointer': '/$defs/AmendedCheckReport/properties/payload/oneOf/2',
            'POST_required': post_schema['required'], 'additionalProperties': False,
            'root_artifact_union': schema['properties']['artifacts']['items']},
        'producer': {'path': storage, 'call': segment(source_text, posts[0]), 'enclosing_conditions': conditions,
            'generated_POST_payload_keys': generated_keys,
            'missing_required_fields': missing, 'forbidden_extra_fields': extra},
        'call_chain_source': {'commit_action_result': segment(source_text, function(source_tree, 'commit_action_result')),
            '_project_plan_locked': segment(source_text, projection), '_new_artifact': segment(source_text, function(source_tree, '_new_artifact')),
            'native_append': segment(native_text, function(native_tree, '_append')),
            'native_reports': segment(contract_text, function(contract_tree, '_reports'))},
        'reason': 'The required single-action UNKNOWN fact makes issues nonempty; projection emits legacy-shaped POST_APPLY. Native append validates the 1.4 AmendedCheckReport unchanged, so this output cannot satisfy the fixed native schema. No dynamic outer error code is asserted.',
        'functional_groups': {'U1': 'NOT_RUN_STATIC_PREREQUISITE_CONFLICT',
            'U2': 'NOT_RUN_AFTER_REQUIRED_U1_PREREQUISITE_STOP', 'U3': 'NOT_RUN_AFTER_REQUIRED_U1_PREREQUISITE_STOP',
            'U4': 'NOT_RUN_AFTER_REQUIRED_U1_PREREQUISITE_STOP', 'U5': 'NOT_RUN_AFTER_REQUIRED_U1_PREREQUISITE_STOP'},
        'database_stages': 'NOT_CREATED: no init/register/PRE/dispatch/UNKNOWN/reconcile process started; no binary or zero-row evidence fabricated.',
        'nominal_unexecuted_reconcile_expectations': {
            'U1': 'partial removes one of two frames; comparator CONFLICT/UNKNOWN, nominal STILL_UNKNOWN',
            'U2': 'applied target plus duplicate identity read; comparator CONFLICT/UNKNOWN, no duplicate added to stored business state',
            'U3': 'CONTRADICTORY read; comparator INDETERMINATE/UNKNOWN',
            'U4': 'TRUNCATED read with incomplete scope; comparator INDETERMINATE/UNKNOWN',
            'U5': 'UNAVAILABLE read with null sequence/hash/version and no snapshot; comparator INDETERMINATE/UNKNOWN'},
        'nominal_expectation_limit': 'Source-derived planning only; no admission, capture, resolution, failure-record or paused outcome has been dynamically verified.',
        'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION', 'I01': 'NOT_RELEASED'}
    write(folder / 'static-prerequisite-conflict.json', record)
    print(json.dumps({'status': record['status'], 'missing_required': missing, 'forbidden_extra': extra,
        'functional_runs': 0, 'product_calls': 0}))
