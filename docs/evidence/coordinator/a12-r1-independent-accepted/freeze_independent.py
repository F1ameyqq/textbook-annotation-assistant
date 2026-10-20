"""Syntax and hash sealing only. Do not import or execute reviewed code here."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
preflight = json.loads((OUT / 'raw-preflight.json').read_bytes())
assert preflight['status'] == 'PASS_RAW_IDENTITY_AND_STATIC_SCOPE'
assert not (OUT / 'run').exists()
frozen_files = ['verify_raw.py', 'independent-product-delta.diff', 'raw-preflight.json',
                'protocol_child.py', 'independent_suite.py', 'freeze_independent.py']
for name in ['protocol_child.py', 'independent_suite.py', 'verify_raw.py', 'freeze_independent.py']:
    raw = (OUT / name).read_bytes()
    ast.parse(raw, filename=name)
    compile(raw, name, 'exec')
for item in preflight['inputs']:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
frozen = {
    'at': datetime.now(timezone.utc).isoformat(),
    'review_thread_id': '01a157a5-495a-7bf3-bc17-299ad85c48a7',
    'product_commit': preflight['product_driver_commit'], 'final_commit': preflight['final_commit'],
    'candidate_manifest_sha256': preflight['candidate_manifest_sha256'],
    'delivery_manifest_sha256': preflight['delivery_manifest_sha256'],
    'frozen_output_inputs': [{'path': name, 'size': len((OUT / name).read_bytes()),
                             'sha256': sha((OUT / name).read_bytes())} for name in frozen_files],
    'fixed_product_inputs': preflight['inputs'],
    'behavior_executions_before_freeze': 0,
    'static_syntax_only_before_freeze': True,
    'independent_case_order': ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8'],
    'D2_exact_fixed_rejects': ['nonzero_count', 'negative_count', 'boolean_count', 'extra_field',
                             'multiple_records', 'trailing_garbage', 'stderr', 'nonzero_exit'],
    'D5_injection': 'actual NativeGuard.block_seen during password visibility await; no failure object',
    'D6_injection': 'actual record_failure during viewer await; later close error must not replace first',
    'D7_injection': 'actual record_failure before observe_page; no navigation/DOM successors',
    'D8_injection': 'first actual record_failure during context.close await after successful DOM; second during runtime.stop',
    'production_functions_unmodified': True,
    'fake_boundaries': ['page navigation/DOM', 'context.close', 'runtime.stop'],
    'real_protocol_child_limit': 1, 'independent_behavior_run_limit': 1,
    'outer_seconds': 60, 'cleanup_watchdog_seconds': 55,
    'browser_server_platform_profile_credentials_occupancy_scan_limit': 0,
    'once_only_output_directory': str(OUT / 'run'),
    'failure_policy': 'First unexpected failure fixed; successors NOT_RUN; no edits/retries',
    'pre_execution_utility_events': [
        'An inline read-only metadata display expected a members key on delivery manifest and raised KeyError; no product import/run or file write occurred. Correct members_excluding_this_manifest key used by independent raw checker.',
        'Static review adjusted the unfrozen independent driver to ignore preexisting supervisor asyncio tasks when checking for newly leaked fake tasks; no behavior run occurred.',
    ],
}
raw = (json.dumps(frozen, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')
with (OUT / 'independent-freeze.json').open('xb') as stream:
    stream.write(raw)
print(json.dumps({'status': 'FROZEN_BEFORE_FIRST_BEHAVIOR', 'freeze_sha256': sha(raw),
                  'driver_sha256': sha((OUT / 'independent_suite.py').read_bytes()),
                  'protocol_child_sha256': sha((OUT / 'protocol_child.py').read_bytes()),
                  'python': sys.executable, 'version': sys.version,
                  'behavior_runs': 0, 'case_order': frozen['independent_case_order']}))
