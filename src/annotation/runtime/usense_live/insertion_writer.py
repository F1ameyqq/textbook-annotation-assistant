"""Q7 copy-first insertion transport. One send; no rollback or automatic retry.

This explicit writer has its own plan-bound all-22 GET scope. A core read config
supplies only the profile, TLS, actors, package hash and bounded execution window.
It does not supply write authority. Run in an externally observed child process;
acceptance requires its exit and a separate all-23 readback/comparator process.
"""
import argparse
import asyncio
import base64
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from .core import (ORIGIN, TARGET, load_binding, tls_launch_arguments, write_new,
                   require, sha, plain_path, parse, utc)
from .config import endpoints
from .capture import FETCH
from .writer import ExactPolicy, SEND, POST
from .release import close_framework, run_owned_writer


PREPARE = r"""async payload => {
 const user=JSON.parse(localStorage.getItem('user')||'null');
 if(!user||typeof user.access_token!=='string'||!user.access_token||
    typeof user.username!=='string'||!user.username.trim()) throw Error('AUTH_REQUIRED');
 if(typeof user.id!=='string'||!/^\d+$/.test(user.id)) throw Error('NATIVE_STRING_USER_ID_REQUIRED');
 if(payload.created_by!==null||payload.annotations_upsert.length!==7||
    payload.annotations_upsert.some(r=>r.user_id!==null)) throw Error('UNBOUND_ACTOR_FIELDS_REQUIRED');
 payload.created_by=user.username;
 for(const row of payload.annotations_upsert) row.user_id=user.id;
 const body=JSON.stringify(payload);
 window.__usenseNativeBody=body;
 const digest=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,'0')).join('');
 return {sha256:await digest(body),runtime_actor_sha256:await digest(user.username),runtime_user_id_sha256:await digest(user.id),
         created_by_bound:true,seven_row_user_ids_bound:true};
}"""


PREPARE_LESSON = PREPARE.replace('payload.annotations_upsert.length!==7',
    '![3,4].includes(payload.annotations_upsert.length)')


def is_lesson(plan):
    return isinstance(plan, dict) and plan.get('schema') == 'A28LessonInsertPlan/v1'


def comparator(plan=None):
    # Kept separate for independent review and reuse by the readback process.
    if is_lesson(plan):
        from . import lesson_insert
        return lesson_insert
    from . import insertion
    return insertion


def full_endpoints(plan=None):
    """Exactly the observed current 22-question book and four source-page reads."""
    if is_lesson(plan):
        return comparator(plan).full_endpoints(plan)
    result = endpoints((), (10, 11, 12, 173), source=True)
    for first in (1, 7, 13, 19):
        result.update(endpoints(range(first, min(first + 6, 23))))
    require(len(result) == 161, 'EXACT_ALL22_AND_FOUR_SOURCE_PAGES_REQUIRED')
    return result


def same(left, right):
    """Preserve JSON key order, number/string distinction and unknown fields."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(same(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def verify_evidence(plan):
    if is_lesson(plan):
        from .lesson_batch import verify_evidence as verify_lesson_evidence
        return verify_lesson_evidence(plan)
    approved = plan['approved_new_content']
    require(isinstance(approved, dict), 'APPROVED_NEW_CONTENT_REQUIRED')
    for key in ('candidate', 'review', 'crop_evidence'):
        ref, digest = approved[key + '_ref'], approved[key + '_sha256']
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'EVIDENCE_DIGEST_REQUIRED')
        file = plain_path(ref)
        require(file.is_file() and sha(file.read_bytes()) == digest, 'EVIDENCE_CHANGED_' + key)
    sources = approved['source_evidence']
    require(isinstance(sources, list) and len(sources) == 2, 'TWO_SOURCE_PAGES_REQUIRED')
    require(len({row['path'] for row in sources}) == 2, 'DISTINCT_SOURCE_PAGES_REQUIRED')
    for row in sources:
        require(set(row) == {'path', 'sha256'}, 'SOURCE_EVIDENCE_FIELDS')
        require(sha(plain_path(row['path']).read_bytes()) == row['sha256'], 'SOURCE_BYTES_CHANGED')
    from .q7_insert_candidate import materialize
    rebuilt = materialize(approved['candidate_ref'], approved['crop_evidence_ref'], approved['review_ref'], plan['before_full'])
    require(same(rebuilt['payload_candidate'], plan['payload_candidate']), 'PAYLOAD_SOURCE_MATERIALIZATION_CHANGED')
    require(all(key in approved and same(value, approved[key]) for key, value in rebuilt['approved_new_content'].items()),
            'APPROVED_CONTENT_MATERIALIZATION_CHANGED')


class BoundExecution:
    """Also freeze the plan bytes for every interception, not just entry."""
    def __init__(self, binding, plan_path, plan_file_sha256):
        self.binding, self.plan_path, self.plan_file_sha256 = binding, plan_path, plan_file_sha256

    def check(self):
        self.binding.check()
        require(sha(self.plan_path.read_bytes()) == self.plan_file_sha256, 'PLAN_FILE_CHANGED')


class InsertPolicy(ExactPolicy):
    def __init__(self, binding, urls):
        super().__init__(binding, urls)
        self.sealed = False

    def allow(self, layer, method, url, body=None, redirected=False):
        if self.sealed or layer not in ('context', 'native'):
            self.blocked = True
        return super().allow(layer, method, url, body, redirected)


def validate_inputs(plan, baseline, ledger_root, authorization_reference):
    api = comparator(plan)
    api.validate_insert_plan(plan)
    require(isinstance(authorization_reference, str) and bool(authorization_reference.strip()),
            'CURRENT_INSERT_AUTHORIZATION_REFERENCE_REQUIRED')
    paths = full_endpoints(plan)
    require(set(plan['before_full']) == set(paths), 'FULL_BASELINE_ENDPOINT_SET_REQUIRED')
    native = {name: parse((baseline / (name + '.json')).read_bytes()) for name in paths}
    require(all(same(native[name], plan['before_full'][name]) for name in paths), 'BASELINE_PLAN_CHANGED')
    require(api.check_prewrite(plan, native)['ok'], 'BASELINE_COMPARATOR_REJECTED')
    payload = plan['payload_candidate']
    allowed_rows = (3, 4) if is_lesson(plan) else (7,)
    require(payload['created_by'] is None and len(payload['annotations_upsert']) in allowed_rows and
            all(row['user_id'] is None for row in payload['annotations_upsert']), 'UNBOUND_SEVEN_ROW_ACTOR_REQUIRED')
    require(payload['annotations_delete_rect_ids'] == [] and payload['ocr_delete_zones'] == [], 'COPY_FIRST_NO_DELETIONS')
    require(re.fullmatch(r'[a-zA-Z0-9_-]{10,150}', plan['ledger_key']) is not None, 'SCOPED_LEDGER_KEY_REQUIRED')
    verify_evidence(plan)
    ledger = plain_path(str(ledger_root))
    require(ledger.is_dir(), 'LEDGER_DIRECTORY_REQUIRED')
    claim = ledger / (plan['ledger_key'] + '.json')
    require(not claim.exists(), 'EXISTING_INSERT_INTENT_READBACK_REQUIRED_NO_RETRY')
    return native, paths, claim


async def record_and_send(*, page, policy, plan, claim, run, result):
    """Atomic durable intent before arming; never erase the intent on error."""
    prepared = await asyncio.wait_for(page.evaluate(PREPARE_LESSON if is_lesson(plan) else PREPARE,
        copy.deepcopy(plan['payload_candidate'])), timeout=10)
    require(prepared.get('created_by_bound') is True and prepared.get('seven_row_user_ids_bound') is True and
            re.fullmatch('[0-9a-f]{64}', prepared.get('sha256', '')) is not None, 'PAGE_ACTORS_NOT_BOUND')
    for field in ('runtime_actor_sha256', 'runtime_user_id_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', prepared.get(field, '')) is not None, 'RUNTIME_ACTOR_HASH_REQUIRED')
    policy.binding.check()
    verify_evidence(plan)
    policy.body_sha = prepared['sha256']
    sent_at = datetime.now(timezone.utc).isoformat()
    write_new(claim, {'operation': plan.get('operation', 'Q7_COPY_FIRST_VARIANT_INSERT'), 'run_id': run.name,
        'ledger_key': plan['ledger_key'], 'plan_sha256': plan['plan_sha256'],
        'native_body_sha256': policy.body_sha, 'intent_at': sent_at, 'automatic_retry_allowed': False,
        'state': 'INTENT_REQUIRES_INDEPENDENT_ALL23_READBACK'})
    result.update(status='SEND_INTENT_RECORDED', post_attempts=1, send_intent_at=sent_at,
                  native_body_sha256=policy.body_sha, actor_binding='username and seven user IDs bound only inside page',
                  runtime_actor_hashes={key: prepared[key] for key in ('runtime_actor_sha256', 'runtime_user_id_sha256')})
    write_new(run / 'send-intent.json', result)
    policy.armed = True
    try:
        response = await asyncio.wait_for(page.evaluate(SEND, POST), timeout=35)
    finally:
        policy.armed = False
        policy.sealed = True
    raw = base64.b64decode(response['body_base64'], validate=True)
    require(len(raw) <= 1000000, 'RECEIPT_TOO_LARGE')
    with (run / 'native-receipt.json').open('xb') as stream:
        stream.write(raw)
    result.update(http_status=response['status'], receipt_sha256=sha(raw),
        post_layers={layer: policy.counts.get((layer, 'POST', POST), 0) for layer in ('context', 'native')})
    require(response['status'] == 200 and not policy.blocked and all(n == 1 for n in result['post_layers'].values()),
            'POST_OR_DUAL_GUARD_UNPROVEN')
    decoded = comparator(plan).decode_receipt(plan, parse(raw))
    require(isinstance(decoded, dict) and decoded.get('ok') is True, 'RECEIPT_DECODER_RESULT_REQUIRED')
    result.update(status='INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK', receipt_validation=decoded)
    if is_lesson(plan):
        result.update(receipt_exact_success=True,
            expected_readback='NEW_QUESTION_AND_REINDEXED_TAIL_WITH_FULL_GLOBAL_PRESERVATION')


async def execute(*, config_path, config_sha256, plan_path, plan_sha256, baseline, ledger_root,
                  authorization_reference):
    plan_file = plain_path(str(plan_path))
    raw = plan_file.read_bytes()
    require(sha(raw) == plan_sha256, 'PLAN_FILE_CHANGED')
    plan = parse(raw)
    binding = load_binding(config_path, config_sha256)
    require(Path(ledger_root).resolve() == Path(binding.data['profile']['directory']).parent / 'usense-existing-ledger',
            'LEDGER_ROOT_MUST_BELONG_TO_BOUND_PROFILE')
    native, paths, claim = validate_inputs(plan, plain_path(str(baseline)), Path(ledger_root), authorization_reference)
    require(binding.data['static_get'] == {'mode': 'DISABLED', 'max_requests': 0}, 'INERT_DOCUMENT_CONFIG_REQUIRED')
    urls = [TARGET] + [ORIGIN + path for path in paths.values()]
    require(all(row['url'] in urls for row in binding.data['allowed_get']), 'CONFIG_GET_OUTSIDE_INSERT_SCOPE')
    binding.check(profile=True)
    run = binding.output
    run.mkdir(exist_ok=False)
    result = {'schema': 'UsenseActualCopyFirstInsert/v1', 'operation': 'Q7_COPY_FIRST_VARIANT_INSERT',
        'book_id': '46007447', 'status': 'PREPARING', 'plan_sha256': plan['plan_sha256'],
        'plan_file_sha256': plan_sha256, 'config_sha256': config_sha256, 'run_id': run.name,
        'process_id': os.getpid(), 'post_attempts': 0, 'save_success': False, 'old_q7_modified_by_request': False,
        'independent_readback': 'PENDING_ALL23', 'authorization_reference': authorization_reference,
        'ledger_key': plan['ledger_key'], 'prewrite_responses': {}}
    if is_lesson(plan):
        result.update(schema='UsenseActualLessonInsert/v1', operation=plan['operation'], independent_readback='PENDING_NEW_AND_TAIL')
    write_new(run / 'claim.json', {'operation': result['operation'], 'config_sha256': config_sha256, 'plan_file_sha256': plan_sha256})
    (run / 'plan.json').write_bytes(raw)
    write_new(run / 'full-read-scope.json', paths)
    context = runtime = None
    pending = set()
    policy = InsertPolicy(BoundExecution(binding, plan_file, plan_sha256), urls)
    try:
        from playwright.async_api import async_playwright
        args = await asyncio.to_thread(tls_launch_arguments, binding)
        runtime = await async_playwright().start()
        context = await runtime.chromium.launch_persistent_context(binding.data['profile']['directory'], channel='msedge',
            headless=True, offline=True, service_workers='block', ignore_https_errors=False, accept_downloads=False,
            timeout=15000, args=['--disable-extensions', '--disable-background-networking'] + args)
        if not context.pages:
            await context.new_page()
        for extra in list(context.pages[1:]):
            await extra.close()
        page = context.pages[0]
        await page.goto('about:blank')
        async def route(r):
            req = r.request
            if policy.allow('context', req.method, req.url, req.post_data, req.redirected_from is not None):
                if req.url == TARGET:
                    await r.fulfill(status=200, content_type='text/html', body='<!doctype html><title>Usense insertion</title><link rel="icon" href="data:,">')
                else:
                    await r.continue_()
            else:
                await r.abort('blockedbyclient')
        await context.route('**/*', route)
        async def block_ws(ws):
            policy.blocked = True
            await ws.close()
        await context.route_web_socket('**/*', block_ws)
        cdp = await context.new_cdp_session(page)
        async def paused(event):
            req = event['request']
            allowed = policy.allow('native', req['method'], req['url'], req.get('postData'), bool(event.get('redirectedRequestId')))
            await cdp.send('Fetch.continueRequest' if allowed else 'Fetch.failRequest',
                {'requestId': event['requestId']} if allowed else {'requestId': event['requestId'], 'errorReason': 'BlockedByClient'})
        def schedule(coro):
            task = asyncio.create_task(coro)
            pending.add(task)
            def done(t):
                pending.discard(t)
                if not t.cancelled() and t.exception() is not None:
                    policy.blocked = True
            task.add_done_callback(done)
        cdp.on('Fetch.requestPaused', lambda event: schedule(paused(event)))
        await cdp.send('Fetch.enable', {'patterns': [{'urlPattern': '*', 'requestStage': 'Request'}]})
        async def extra_page(p):
            policy.blocked = True
            await p.close()
        context.on('page', lambda p: schedule(extra_page(p)))
        page.on('dialog', lambda dialog: schedule(dialog.dismiss()))
        await context.set_offline(False)
        await page.goto(TARGET, wait_until='domcontentloaded', timeout=30000)
        require(not policy.blocked, 'GUARD_BLOCKED')
        fresh = {}
        for name, path in paths.items():
            remaining = (utc(binding.data['expires_at']) - datetime.now(timezone.utc)).total_seconds()
            require(remaining > 45, 'INSUFFICIENT_REMAINING_SEND_WINDOW')
            read = await asyncio.wait_for(page.evaluate(FETCH, path), timeout=min(30, remaining - 40))
            require(read['status'] == 200, 'PREWRITE_READ_FAILED')
            body = base64.b64decode(read['body_base64'], validate=True)
            with (run / ('before-' + name + '.json')).open('xb') as stream:
                stream.write(body)
            fresh[name] = parse(body)
            counts = {layer: policy.counts.get((layer, 'GET', ORIGIN + path), 0) for layer in ('context', 'native')}
            result['prewrite_responses'][name] = {'sha256': sha(body), 'bytes': len(body), 'request_counts': counts,
                'observed_at': datetime.now(timezone.utc).isoformat()}
            require(not policy.blocked and all(n == 1 for n in counts.values()), 'PREWRITE_DUAL_GUARD_UNPROVEN')
            require(same(fresh[name], native[name]), 'BEFORE_CHANGED_' + name)
        require(comparator(plan).check_prewrite(plan, fresh)['ok'], 'PREWRITE_COMPARATOR_REJECTED')
        require(not policy.blocked, 'GUARD_BLOCKED')
        await record_and_send(page=page, policy=policy, plan=plan, claim=claim, run=run, result=result)
    except BaseException as exc:
        result['status'] = 'UNKNOWN_DO_NOT_RETRY' if result['post_attempts'] else 'BLOCKED_BEFORE_SEND'
        result['error_type'] = type(exc).__name__
        result['error_code'] = getattr(exc, 'code', None)
    finally:
        policy.armed = False
        policy.sealed = True
        result['business_status_before_release'] = result['status']
        release = await close_framework(context, runtime, pending)
        release['process_id'] = os.getpid()
        result['release'] = release
        if not release['context_runtime_release_confirmed']:
            result['status'] = 'RELEASE_UNPROVEN_NO_RETRY'
        write_new(run / 'network-events.json', policy.events)
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        write_new(run / 'execution-result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'sha256', 'plan', 'plan-sha256', 'baseline', 'ledger-root', 'authorization-reference'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    result = run_owned_writer(execute(config_path=args.config, config_sha256=args.sha256, plan_path=args.plan,
        plan_sha256=args.plan_sha256, baseline=args.baseline, ledger_root=args.ledger_root,
        authorization_reference=args.authorization_reference))
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if result['status'] == 'INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK' else 2


if __name__ == '__main__':
    raise SystemExit(main())
