"""Read-only frozen input verification and one metadata-only binding call."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone, timedelta

ROOT = Path('D:/1800-worktrees/a13-reuse-observation')
OUT = ROOT / 'execution-output'
MAIN = Path('D:/1800')
LIVE = MAIN / '.local/stages/a12-native-reuse-live'
FINAL = '81fab23e3e7e9e32a36d3857a253afc69b5bd3e1'
CANDIDATE = '38eb3f836f14b44db77ce516f461bd4f3934df71807c1fac962560603a210920'
PRODUCT_SHA = '3f1e4a425e18ed0e2a28893989f31677ba6b9b7f4b9c3da2800bc925443999c9'
THREAD = '01a157d2-caed-7162-8c48-06ad7117bd90'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())


def main():
    if LIVE.exists() or (OUT / 'launch-intent.json').exists() or (OUT / 'preparation-started.json').exists():
        raise RuntimeError('EXISTING_MARKER_STOP')
    save('preparation-started.json', {'at': datetime.now(timezone.utc).isoformat(),
        'thread_id': THREAD, 'live_directory_absent': True, 'launch_intent_absent': True})
    receipt_path = MAIN / 'docs/evidence/coordinator/a12-r1-independent-accepted/coordinator-receipt.json'
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt['status'] == 'ACCEPTED_PREPARATION_FOR_ONE_REUSE_ONLY_OBSERVATION'
    inputs = receipt['new_execution_inputs']
    assert len(inputs) == 53
    tree_raw = subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(MAIN),
        'ls-tree', '-rz', FINAL], env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'})
    tree = {}
    for entry in tree_raw.split(b'\0'):
        if entry:
            head, path = entry.split(b'\t', 1)
            mode, kind, oid = head.decode('ascii').split()
            tree[path.decode('utf-8')] = (mode, kind, oid)
    for item in inputs:
        path = ROOT / item['path']
        assert not path.is_symlink()
        raw = path.read_bytes()
        assert len(raw) == item['size'] and sha(raw) == item['sha256']
        oid = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
        assert oid == item['git_oid']
        assert tree[item['path']] == (item['mode'], item['type'], item['git_oid'])
    product = ROOT / 'tools/headless_native_reuse_probe_r1.py'
    assert sha(product.read_bytes()) == PRODUCT_SHA
    wrapper = OUT / 'launch_once.py'
    wrapper_raw = wrapper.read_bytes()
    ast.parse(wrapper_raw)
    assert os.environ.get('CODEX_THREAD_ID') == THREAD
    authorities = [
        'docs/tasks/A13-single-reuse-observation.md',
        'docs/tasks/A13-independent-observation-review.md',
        'docs/evidence/coordinator/a12-r1-independent-accepted/report.json',
        'docs/evidence/coordinator/a12-r1-independent-accepted/coordinator-receipt.json',
        'docs/evidence/coordinator/a13-reuse-dispatch/intent.json',
        'docs/evidence/coordinator/a13-reuse-dispatch/execution-creation-receipt.json']
    (OUT / 'authority-snapshot').mkdir(exist_ok=False)
    source_records = []
    for i, name in enumerate(authorities):
        raw = (MAIN / name).read_bytes()
        local = 'authority-snapshot/' + str(i) + '-' + Path(name).name
        with (OUT / local).open('xb') as stream:
            stream.write(raw)
        source_records.append({'source_path': name, 'snapshot': local,
            'sha256': sha(raw), 'size': len(raw)})
    save('raw-input-verification.json', {'status': 'PASS_RAW_IDENTITY',
        'fixed_inputs': inputs, 'fixed_input_count': 53, 'final_commit': FINAL,
        'method': 'Raw byte SHA256/size plus Git blob SHA1 and fixed final ls-tree mode/type/OID',
        'authorities': source_records, 'wrapper_ast_parsed_only': True,
        'wrapper_behavior_preruns': 0})
    spec = importlib.util.spec_from_file_location('a13_frozen_product', product)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    actual = module.candidate(CANDIDATE)
    profile, fingerprint = module.profile_binding()
    del profile
    now = datetime.now(timezone.utc)
    command = [sys.executable, '-B', str(product), '--live', '--candidate-sha256', actual,
               '--profile-fingerprint', fingerprint]
    assert not LIVE.exists() and not (OUT / 'launch-intent.json').exists()
    save('launch-intent.json', {'schema_version': 1, 'at_utc': now.isoformat(),
        'at_local': now.astimezone(timezone(timedelta(hours=8))).isoformat(),
        'thread_id': THREAD, 'workflow_commit': 'abd6a03141cf89a756d9c1ceec70080fc1b86a6f',
        'product_commit': 'd45ed25a98361002ddb28985c1d27687c4421a17',
        'final_commit': FINAL, 'product_sha256': PRODUCT_SHA, 'candidate_sha256': actual,
        'profile_fingerprint': fingerprint, 'binding_origin': 'DEDICATED_PROFILE_METADATA_ONLY',
        'external_candidate_calls': 1, 'external_profile_binding_calls': 1,
        'profile_internal_reads': 0, 'external_occupancy_scans': 0,
        'initial_live_directory_absent': True, 'initial_launch_intent_absent': True,
        'live_starts_limit': 1, 'navigation_limit': 1, 'login_limit': 0,
        'business_write_limit': 0, 'book_reads_limit': 0,
        'target': 'https://www.usense.com/qieti/annotateUnified',
        'navigation_seconds': 45, 'worker_seconds': 75, 'product_hard_seconds': 85,
        'outer_wait_seconds': 88, 'outer_cleanup_seconds': 2,
        'wrapper_sha256': sha(wrapper_raw), 'product_command': command,
        'product_command_sha256': sha(json.dumps(command, separators=(',', ':')).encode('utf-8')),
        'wrapper_preruns': 0, 'old_budgets_restored': False,
        'failure_policy': 'FIRST_ERROR_OR_LOGIN_REQUIRED_STOP_SUCCESSORS_NOT_RUN_NO_RETRY'})
    print(json.dumps({'preparation': 'READY_FOR_SOLE_LAUNCH', 'inputs_verified': 53,
        'intent_sha256': sha((OUT / 'launch-intent.json').read_bytes()),
        'wrapper_sha256': sha(wrapper_raw), 'profile_fingerprint': fingerprint}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        save('preparation-failure.json', {'status': 'BLOCKED',
            'category': 'PREPARATION_FAILED', 'raw_exception_withheld': True,
            'successors': 'NOT_RUN', 'live_starts': 0})
        print('{"status":"BLOCKED","category":"PREPARATION_FAILED"}')
        raise SystemExit(2)
