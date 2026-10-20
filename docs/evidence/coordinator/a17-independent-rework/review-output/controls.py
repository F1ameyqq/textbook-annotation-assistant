"""A17 independent final-settlement counterexample; all transport is fake.

No live entry point, product child, profile or native API is constructed.
The product observe coroutine is exercised with an in-memory lifecycle.
"""
import asyncio
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import urllib.request

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]


def forbidden(*args, **kwargs):
    raise AssertionError('REAL_RESOURCE_FORBIDDEN_INDEPENDENT_A17')


async def counterexample(p):
    main_frame = object()
    page = SimpleNamespace(main_frame=main_frame)
    guard = p.CurrentGuard(None, page, p.ReadPolicy())
    guard.main_frame_id = 'independent-original-main-frame'
    transport = []
    files = {}

    async def send(method, payload):
        transport.append({'method': method, 'payload': payload})
        return {}

    guard.session = SimpleNamespace(send=send)

    async def open_fake(profile, approval, state):
        state['guard'] = guard
        return page, guard

    async def collect_fake(page_arg, guard_arg, result):
        # Isolate the finalizer only. This does not assert real collection.
        result['outcome'] = 'READONLY_REVIEW_WITH_GAPS'
        guard_arg.schedule(guard_arg.paused({
            'requestId': 'independent-late-request',
            'request': {'method': 'GET', 'url': 'https://independent.invalid/late.js'},
            'resourceType': 'Script', 'frameId': guard_arg.main_frame_id}))
        # No yield: the first fatal runs in the finalizer's drain below.

    async def close_fake(state):
        state['release']['state'] = 'RELEASED'

    def save_fake(path, value):
        files[Path(path).name] = copy.deepcopy(value)

    with patch.object(p, 'open_owned', open_fake), \
            patch.object(p, 'collect', collect_fake), \
            patch.object(p.native, 'close_owned', close_fake), \
            patch.object(p, 'save_new', save_fake), \
            patch.object(p, 'load_native', forbidden), \
            patch.object(p.native, 'load_native', forbidden), \
            patch.object(p.native, 'profile_binding', forbidden), \
            patch.object(p, 'occupancy', forbidden):
        code = await p.observe_live('SYNTHETIC_NO_PROFILE_NOT_ACCESSED', None)

    result = files['current-state.json']
    actual = result['error']
    first = guard.failure
    record = {
        'case': 'A17-I-A02-FIRST-FATAL-DURING-FINAL-DRAIN',
        'scope': 'Pure in-memory serialization/finalizer control only',
        'expected': {
            'code': 2, 'outcome': 'ERROR',
            'first_guard_error_codes': ['ORIGIN_BLOCKED'],
            'serialized_primary_error_equals_first_guard_error': True},
        'actual': {
            'code': code, 'outcome': result['outcome'],
            'first_guard_error': first, 'serialized_primary_error': actual,
            'guard_pre_shutdown': result['guard_pre_shutdown'],
            'guard_at_serialization': result['guard_at_serialization'],
            'transport_calls': transport,
            'network_audit': result['network_audit'],
            'remaining_tasks': len(guard.tasks),
            'remaining_callbacks': len(guard.callbacks)},
        'observation_limit': 'First guard error remains in nested snapshots; '
                             'the primary result.error is replaced by its generic drain wrapper.',
        'success': (code == 2 and result['outcome'] == 'ERROR'
                    and first.get('codes') == ['ORIGIN_BLOCKED'] and actual == first)}
    assert all(x['method'] == 'Fetch.failRequest' for x in transport)
    assert not guard.tasks and not guard.callbacks
    record['result'] = 'PASS' if record['success'] else 'FAIL'
    return record


def main():
    started = time.monotonic()
    with patch.object(socket, 'create_connection', forbidden), \
            patch.object(urllib.request, 'urlopen', forbidden), \
            patch.object(subprocess, 'Popen', forbidden):
        import a16_current_state_probe as p
        record = asyncio.run(counterexample(p))
    summary = {
        'task': 'A17', 'kind': 'INDEPENDENT_IN_MEMORY_CONTROL',
        'candidate_manifest_sha256': '43870eac7194cb10d8542826a9a81e2a3c98dde1f191241bd4c1c43f007a787b',
        'product_commit': 'e7ee24245ffaf4d4b81cbddae8b3720aac214c1b',
        'final_commit': '1d2ba3766558fe9cc911756666d962184cc1de57',
        'records': [record], 'tests_run': 1,
        'pass': int(record['success']), 'fail': int(not record['success']),
        'duration_ms': round((time.monotonic() - started) * 1000),
        'successors': 'NOT_RUN_ON_FIRST_SEMANTIC_COUNTEREXAMPLE' if not record['success'] else 'NOT_SCHEDULED',
        'real_native_browser_network_profile_occupancy_login_business_calls': 0,
        'product_child_processes': 0, 'old_suites_run': 0,
        'pending_synthetic_tasks': 0, 'pending_synthetic_callbacks': 0}
    with (OUT / 'control-result.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if record['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
