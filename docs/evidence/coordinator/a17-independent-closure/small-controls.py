"""Two new memory-only ordering controls; no old suite or helper imported."""
import asyncio
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import SimpleNamespace as NS
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]


def forbidden(*args, **kwargs):
    raise AssertionError('REAL_RESOURCE_FORBIDDEN_A17_R1_INDEPENDENT')


async def one(p, guard_before_fallback):
    page = NS(main_frame=object())
    guard = p.CurrentGuard(None, page, p.ReadPolicy())
    guard.main_frame_id = 'independent-r1-original-frame'
    transport, files = [], {}
    ready = asyncio.Event()

    async def send(method, parameters):
        transport.append({'method': method, 'parameters': parameters})
        return {}

    guard.session = NS(send=send)

    async def illegal():
        await guard.paused({'requestId': 'independent-r1-request',
            'frameId': guard.main_frame_id, 'resourceType': 'Script',
            'request': {'method': 'GET', 'url': 'https://independent-r1.invalid/synthetic.js'}})

    async def deferred():
        await ready.wait()
        await illegal()

    async def open_fake(profile, approval, state):
        state['guard'] = guard
        return page, guard

    async def collect_fake(page_arg, guard_arg, result):
        if guard_before_fallback:
            await illegal()
            raise p.Stop('SYNTHETIC_LATER_EXECUTION_FAILURE')
        guard_arg.schedule(deferred())
        raise p.Stop('SYNTHETIC_EARLIER_BUSINESS_FAILURE')

    real_drain = p.drain

    async def drain_fake(guard_arg):
        ready.set()
        await real_drain(guard_arg)

    async def close_fake(state):
        state['release']['state'] = 'RELEASED'

    def save_fake(path, value):
        files[Path(path).name] = copy.deepcopy(value)

    with patch.object(p, 'open_owned', open_fake), patch.object(p, 'collect', collect_fake), \
            patch.object(p, 'drain', drain_fake), patch.object(p.native, 'close_owned', close_fake), \
            patch.object(p, 'save_new', save_fake):
        code = await p.observe_live('SYNTHETIC_PROFILE_NOT_ACCESSED', None)
    result = files['current-state.json']
    # These are the current disposition's actual bounded-readonly criteria.
    assert code == 2 and result['outcome'] == 'ERROR'
    assert result['guard_pre_shutdown']['failure']['codes'] == ['ORIGIN_BLOCKED']
    assert result['guard_at_serialization']['failure']['codes'] == ['ORIGIN_BLOCKED']
    assert len(transport) == 1 and transport[0]['method'] == 'Fetch.failRequest'
    assert not result['production_ready'] and not result['write_eligible']
    assert result['sample_limit'] == 0 and result['sample']['status'] == 'NOT_RUN'
    assert not guard.tasks and not guard.callbacks
    if not guard_before_fallback:
        assert result['error']['codes'] == ['SYNTHETIC_EARLIER_BUSINESS_FAILURE']
    residual = guard_before_fallback and result['error'] != guard.failure
    return {
        'case': 'GUARD_FIRST_THEN_CURRENT_EXCEPT_FALLBACK' if guard_before_fallback
                else 'EXISTING_TOP_LEVEL_BUSINESS_THEN_LATE_GUARD',
        'result': 'PASS_BOUNDED_PREFLIGHT_WITH_REPORT_RESIDUAL' if residual else 'PASS_BOUNDED_PREFLIGHT',
        'exit_code': code, 'serialized_result': result, 'fake_transport_calls': transport,
        'pending_tasks': 0, 'pending_callbacks': 0,
        'report_only_residual': residual,
        'residual_detail': 'Current except fallback is retained as primary even though guard.failure '
                           'was already specific. Specific first guard error and denial remain in '
                           'snapshots/audit; final ERROR and write ineligibility are correct.' if residual else None,
        'earlier_top_level_vs_new_fallback_distinguished': True,
        'actual_collect_or_live_proof': False}


def main():
    started = time.monotonic()
    with patch.object(socket, 'create_connection', forbidden), \
            patch.object(urllib.request, 'urlopen', forbidden), \
            patch.object(subprocess, 'Popen', forbidden):
        import a16_current_state_probe as p
        with patch.object(p, 'load_native', forbidden), patch.object(p.native, 'load_native', forbidden), \
                patch.object(p.native, 'profile_binding', forbidden), patch.object(p, 'occupancy', forbidden):
            async def run():
                return [await one(p, True), await one(p, False)]
            records = asyncio.run(run())
    result = {'task': 'A17', 'revision': 'first-cause-r1',
        'acceptance_basis': 'BOUNDED_READONLY_PREFLIGHT',
        'tests_run': 2, 'blocking_failures': 0,
        'nonblocking_report_residual_cases': sum(r['report_only_residual'] for r in records),
        'duration_ms': round((time.monotonic() - started) * 1000), 'records': records,
        'old_suites_run': 0, 'old_counterexample_entry_run': 0,
        'real_native_browser_network_profile_credentials_occupancy_login_business_calls': 0,
        'product_children': 0, 'pending_synthetic_tasks_and_callbacks': 0}
    with (OUT / 'small-control-result.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}))


if __name__ == '__main__':
    main()
