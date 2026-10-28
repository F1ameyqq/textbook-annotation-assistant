"""Q7 phase-2 main finalization transport. One send after verified copy-first insertion.

This explicit writer has its own plan-bound all-23 GET scope. A core read config
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
                   require, sha, plain_path, parse, utc, canonical)
from .config import endpoints
from .capture import FETCH
from .writer import SEND, POST
from .insertion_writer import InsertPolicy, BoundExecution, same

OLD_MAIN_IDS = {'6a1e82cf-d5c8-485d-b2da-7a626a899045', 'ace0132c-46d4-402e-ba53-aa8fc99d7484',
                '0eed066a-354d-4d6a-9a6d-c9e54c0c8b5f', 'e219b027-3b59-4834-8447-dd03c7273a9f'}
RETIRE_IDS = ['74ec414b-e400-4477-b652-af4c49ed48eb', '9ade4dc7-7ea2-42ad-b991-26bf96a7795b']
DIRECTORY = 'dir-1792063578574-2a6vq8zom'
LEDGER_KEY = 'book-46007447-node-1792066417325-info-2110705653289365506-finalize-main-after-copy-first'

PREPARE = r"""async payload => {
 const user=JSON.parse(localStorage.getItem('user')||'null');
 if(!user||typeof user.access_token!=='string'||!user.access_token||
    typeof user.username!=='string'||!user.username.trim()) throw Error('AUTH_REQUIRED');
 if(typeof user.id!=='string'||!/^\d+$/.test(user.id)) throw Error('NATIVE_STRING_USER_ID_REQUIRED');
 const rows=payload.annotations_upsert, fresh=rows.filter(r=>r.user_id===null), old=rows.filter(r=>r.user_id!==null);
 if(payload.created_by!==null||rows.length!==7||fresh.length!==3||old.length!==4||
    fresh.some(r=>r.type!=='choice')||old.some(r=>typeof r.user_id!=='string'||!/^\d+$/.test(r.user_id)))
    throw Error('EXACT_FOUR_PRESERVED_THREE_FRESH_ACTORS_REQUIRED');
 payload.created_by=user.username;
 for(const row of fresh) row.user_id=user.id;
 const body=JSON.stringify(payload); window.__usenseNativeBody=body;
 const digest=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,'0')).join('');
 return {sha256:await digest(body),runtime_actor_sha256:await digest(user.username),runtime_user_id_sha256:await digest(user.id),
         created_by_bound:true,new_row_user_ids_bound:3,preserved_row_user_ids:4};
}"""

def comparator():
    # Kept separate for independent review and reuse by the readback process.
    from . import finalize
    return finalize


def full_endpoints():
    """Exactly the observed current 23-question book and four source-page reads."""
    result = endpoints((), (10, 11, 12, 173), source=True)
    for first in (1, 7, 13, 19):
        result.update(endpoints(range(first, min(first + 6, 24))))
    require(len(result) == 168, 'EXACT_ALL23_AND_FOUR_SOURCE_PAGES_REQUIRED')
    return result




def verify_evidence(plan):
    approved = plan['approved_main_content']
    require(isinstance(approved, dict), 'APPROVED_MAIN_CONTENT_REQUIRED')
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
    require(same(parse(plain_path(approved['candidate_ref']).read_bytes()), approved['candidate']),
            'CANDIDATE_FILE_AND_APPROVED_CONTENT_DIVERGED')
    # The reviewed main candidate carries actual source and remote crop records.
    candidate = approved['candidate']
    require(candidate['logical_owner'] == 'main', 'MAIN_SOURCE_CANDIDATE_REQUIRED')
    proof = parse(plain_path(approved['crop_evidence_ref']).read_bytes())
    review = parse(plain_path(approved['review_ref']).read_bytes())
    require(review['status'] == 'PASS_SOURCE_CONTENT_AND_BOUNDARIES' and review['main_answer'] == 'C' and
            review['variant_answer'] == 'B' and review['crop_fetch_proof_sha256'] == approved['crop_evidence_sha256'],
            'ACTUAL_ROOT_VISUAL_REVIEW_REQUIRED')
    remote = {row['key']: row for row in proof['results']}
    require(len(remote) == 14 and proof['status'] == 'ALL_14_HTTP200_DIMENSIONS_MATCH', 'ACTUAL_FOURTEEN_CROP_RESPONSES_REQUIRED')
    for frame in candidate['frames']:
        row = remote[frame['key']]
        require(row['status'] == 200 and row['url'] == frame['image_path'] and row['bbox'] == frame['bbox'] and
                row['source_sha256'] == frame['source_sha256'] and row['sha256'] == frame['crop_sha256'] and
                sha(plain_path(row['file']).read_bytes()) == row['sha256'], 'ACTUAL_REMOTE_CROP_CHANGED')
    # Rebuild the pure contract, which owns exact payload/source geometry matching.
    comparator().validate_finalize_plan(plan)


def verify_predecessor_evidence(plan, native):
    """Recheck parent-generated actual process/file evidence, never invent it."""
    prior = plan['predecessor']
    from .finalize_files import verify_predecessor_files
    require(verify_predecessor_files(prior)['ok'] is True, 'PREDECESSOR_FULL_MANIFEST_BYTES_UNPROVEN')
    embedded = {'plan': prior['phase1_plan'], 'receipt': prior['phase1_receipt'],
                'comparison': prior['phase1_comparison'], 'outer_acceptance': prior['outer_acceptance']}
    for role, ref in prior['artifact_refs'].items():
        raw = plain_path(ref['path']).read_bytes()
        require(sha(raw) == ref['sha256'] and same(parse(raw), embedded[role]), 'PREDECESSOR_ARTIFACT_CHANGED_' + role)
    outer = prior['outer_acceptance']
    resolved = outer['status'] == 'RESOLVED_UNKNOWN_COPY_FIRST_WITH_EXTERNAL_RELEASE'
    if resolved:
        observed = prior['observed_resolution']
        for role, ref in observed['artifact_refs'].items():
            raw = plain_path(ref['path']).read_bytes()
            require(sha(raw) == ref['sha256'] and same(parse(raw), observed[role]),
                    'OBSERVED_RESOLUTION_ARTIFACT_CHANGED_' + role)
        require(outer.get('phase2_only') is True and outer.get('phase1_retry_allowed') is False,
                'RESOLUTION_CANNOT_AUTHORIZE_REINSERTION')
    evidence = {}
    for role, ref in outer['evidence_refs'].items():
        raw = plain_path(ref['path']).read_bytes()
        require(sha(raw) == ref['sha256'], 'PREDECESSOR_EVIDENCE_CHANGED_' + role)
        evidence[role] = parse(raw)
    writer_process = evidence['writer_host_release']
    writer = evidence['writer_execution']
    expected_exit = 2 if resolved else 0
    expected_status = 'UNKNOWN_DO_NOT_RETRY' if resolved else 'INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK'
    require(type(writer_process.get('pid')) is int and writer_process['pid'] > 0 and
        type(writer_process.get('exit_code')) is int and writer_process['exit_code'] == expected_exit and
        canonical(writer_process['result']) == canonical(writer) and writer['process_id'] == writer_process['pid'],
        'PHASE1_REAL_WRITER_EXIT_REQUIRED')
    require(writer['status'] == expected_status and writer['post_attempts'] == 1 and
        writer['release']['context_runtime_release_confirmed'] is True and same(writer['post_layers'], {'context': 1, 'native': 1}) and
        writer['run_id'] == outer['writer_run_id'] and writer['plan_sha256'] == prior['phase1_plan']['plan_sha256'] and
        writer['receipt_sha256'] == prior['artifact_refs']['receipt']['sha256'] and
        same(writer['runtime_actor_hashes'], prior['runtime_actor_hashes']), 'PHASE1_WRITER_BINDING_REQUIRED')
    ledger = evidence['ledger_intent']
    require(ledger['operation'] == 'Q7_COPY_FIRST_VARIANT_INSERT' and ledger['run_id'] == writer['run_id'] and
        ledger['ledger_key'] == prior['phase1_plan']['ledger_key'] and ledger['plan_sha256'] == writer['plan_sha256'] and
        ledger['native_body_sha256'] == writer['native_body_sha256'] and ledger['automatic_retry_allowed'] is False,
        'PHASE1_ONCE_LEDGER_BINDING_REQUIRED')
    host = evidence['reader_host_release']
    require(host.get('schema') == 'Q7ReaderProcessRelease/v1' and isinstance(host.get('processes'), list) and
        len(host['processes']) == 4, 'FOUR_ACTUAL_READER_PROCESSES_REQUIRED')
    readers = host['processes']
    require(len({row['pid'] for row in readers}) == 4 and all(type(row['pid']) is int and row['pid'] > 0 and
        row['pid'] != writer_process['pid'] and row['exit_code'] == 0 for row in readers), 'DISTINCT_READER_PIDS_AND_EXITS_REQUIRED')
    require([row['result']['run_id'] for row in readers] == outer['reader_run_ids'], 'EXACT_READER_RUN_BINDING_REQUIRED')
    if resolved:
        actual = prior['observed_resolution']['execution_evidence']
        require(canonical(actual['writer_process']) == canonical(writer_process) and
                canonical(actual['reader_processes']) == canonical(readers) and
                canonical(actual['ledger_intent']) == canonical(ledger) and
                actual['native_receipt_raw_sha256'] == prior['artifact_refs']['receipt']['sha256'],
                'RESOLUTION_EXECUTION_EVIDENCE_MUST_BE_ACTUAL_RECORDS')
    records = {}
    for process in readers:
        reader = process['result']
        require(reader['status'] == 'NATIVE_GETS_CAPTURED' and reader['save_attempts'] == 0 and
            reader['release']['context_runtime_release_confirmed'] is True and
            utc(process['started_at']) > utc(writer_process['finished_at']), 'READERS_MUST_FOLLOW_WRITER_EXIT')
        for name, meta in reader['captures'].items():
            require(utc(meta['observed_at']) > utc(writer['finished_at']) and same(meta['request_counts'], {'context': 1, 'native': 1}),
                    'READ_AFTER_WRITE_WITH_DUAL_GUARD_REQUIRED')
            key = (reader['run_id'], name)
            records[key] = {'name': name, 'run_id': reader['run_id'], 'sha256': meta['sha256'], 'observed_at': meta['observed_at']}
    capture_index = evidence['full_capture_index']
    require(capture_index.get('schema') == 'Q7FullCaptureIndex/v1' and capture_index.get('unique_names') == 168,
            'ACTUAL_FULL_CAPTURE_INDEX_SCHEMA_REQUIRED')
    index = capture_index['records']
    require(isinstance(index, list) and len(index) == len(records), 'COMPLETE_READBACK_RECORD_COUNT_REQUIRED')
    for row in index:
        require(set(row) == {'name', 'path', 'sha256', 'run_id', 'observed_at'}, 'READBACK_RECORD_FIELDS')
        meta = {key: row[key] for key in ('name', 'run_id', 'sha256', 'observed_at')}
        require(same(meta, records.get((row['run_id'], row['name']))), 'FULL_READBACK_INDEX_MUST_MATCH_READER_RECORDS')
        raw = plain_path(row['path']).read_bytes()
        require(sha(raw) == row['sha256'] and same(parse(raw), native[row['name']]), 'ACTUAL_READBACK_RAW_FILE_CHANGED')
    require({row['name'] for row in index} == set(native), 'ALL168_READBACK_RESPONSES_REQUIRED')
    for name in native:
        hashes = {row['sha256'] for row in index if row['name'] == name}
        require(len(hashes) == 1, 'COMMON_READBACK_RAW_BYTES_CHANGED')
    return {'status': 'VERIFIED_ACTUAL_PREDECESSOR_FILES_AND_PROCESSES', 'writer_pid': writer_process['pid'],
            'reader_pids': [row['pid'] for row in readers], 'raw_response_names': len(native),
            'outer_acceptance_sha256': prior['artifact_refs']['outer_acceptance']['sha256']}


def validate_payload_boundary(payload, before):
    require(payload['file_id'] == '46007447' and payload['target_directory_id'] == DIRECTORY and
            type(payload['question_order']) is int and payload['question_order'] == 7 and
            payload['is_new_question_insertion'] is False and payload['insert_after_order'] is None,
            'ONLY_EXISTING_MAIN_Q7_FINALIZATION_ALLOWED')
    rows = payload['annotations_upsert']
    require(payload['created_by'] is None and len(rows) == 7, 'EXACT_SEVEN_MAIN_ROWS_REQUIRED')
    ids = {row['rect_id'] for row in rows}
    require(len(ids) == 7 and OLD_MAIN_IDS <= ids, 'FOUR_EXISTING_MAIN_IDS_MUST_BE_PRESERVED')
    old_ids = {row['rect_id'] for row in before['frames']['data']}
    require(ids & old_ids == OLD_MAIN_IDS, 'ONLY_THREE_NEW_MAIN_OPTION_IDS_ALLOWED')
    old_by_id = {row['rect_id']: row for row in before['frames']['data']}
    require(all(same(row['user_id'], old_by_id[row['rect_id']]['user_id']) if row['rect_id'] in OLD_MAIN_IDS else row['user_id'] is None
                for row in rows), 'PRESERVE_FOUR_HISTORICAL_ACTORS_BIND_THREE_NEW_ONLY')
    require(all(row['order_in_level'] == '7' and row['directory_id'] == DIRECTORY and
                row['belong_to_level'] == 'question_level' and row['parent_rect_id'] is None for row in rows),
            'ONLY_MAIN_Q7_FRAME_OWNERSHIP_ALLOWED')
    require([row['type'] for row in rows] == ['question', 'question', 'choice', 'choice', 'choice', 'choice', 'answer'],
            'EXACT_MAIN_SEVEN_FRAME_LAYOUT_REQUIRED')
    require(payload['annotations_delete_rect_ids'] == RETIRE_IDS and payload['ocr_delete_zones'] == [],
            'ONLY_TWO_OLD_VARIANT_RECT_DELETIONS_ALLOWED')
    require([row['zone'] for row in payload['ocr_submissions']] == ['question', 'choice', 'answer'] and
            all(type(row['question_order']) is int and row['question_order'] == 7 for row in payload['ocr_submissions']),
            'ONLY_THREE_MAIN_OCR_ZONES_ALLOWED')
    original = before['q7_info']['data']
    require(payload['question_info'] == {'tishi': 'xuanze', 'tilei': original['tilei'], 'tihao': original['tihao']},
            'ONLY_TISHI_SINGLE_CHOICE_CHANGE_ALLOWED')






def validate_inputs(plan, baseline, ledger_root, authorization_reference):
    api = comparator()
    api.validate_finalize_plan(plan)
    require(isinstance(authorization_reference, str) and bool(authorization_reference.strip()),
            'CURRENT_FINALIZE_AUTHORIZATION_REFERENCE_REQUIRED')
    paths = full_endpoints()
    require(set(plan['before_full']) == set(paths), 'FULL_BASELINE_ENDPOINT_SET_REQUIRED')
    native = {name: parse((baseline / (name + '.json')).read_bytes()) for name in paths}
    require(all(same(native[name], plan['before_full'][name]) for name in paths), 'BASELINE_PLAN_CHANGED')
    require(api.check_prewrite(plan, native)['ok'], 'BASELINE_COMPARATOR_REJECTED')
    payload = plan['payload_candidate']
    validate_payload_boundary(payload, native)
    require(plan['ledger_key'] == LEDGER_KEY, 'FIXED_MAIN_FINALIZATION_ONCE_LEDGER_REQUIRED')
    verify_evidence(plan)
    verify_predecessor_evidence(plan, native)
    ledger = plain_path(str(ledger_root))
    require(ledger.is_dir(), 'LEDGER_DIRECTORY_REQUIRED')
    claim = ledger / (plan['ledger_key'] + '.json')
    require(not claim.exists(), 'EXISTING_FINALIZE_INTENT_READBACK_REQUIRED_NO_RETRY')
    return native, paths, claim


async def record_and_send(*, page, policy, plan, claim, run, result):
    """Atomic durable intent before arming; never erase the intent on error."""
    prepared = await asyncio.wait_for(page.evaluate(PREPARE, copy.deepcopy(plan['payload_candidate'])), timeout=10)
    require(prepared.get('created_by_bound') is True and prepared.get('new_row_user_ids_bound') == 3 and
            prepared.get('preserved_row_user_ids') == 4 and
            re.fullmatch('[0-9a-f]{64}', prepared.get('sha256', '')) is not None, 'PAGE_ACTORS_NOT_BOUND')
    for field in ('runtime_actor_sha256', 'runtime_user_id_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', prepared.get(field, '')) is not None, 'RUNTIME_ACTOR_HASH_REQUIRED')
    current_actor = {key: prepared[key] for key in ('runtime_actor_sha256', 'runtime_user_id_sha256')}
    require(current_actor == plan['predecessor']['runtime_actor_hashes'], 'ACTOR_CHANGED_BEFORE_FINALIZE_SEND')
    policy.binding.check()
    verify_evidence(plan)
    verify_predecessor_evidence(plan, plan['before_full'])
    policy.body_sha = prepared['sha256']
    sent_at = datetime.now(timezone.utc).isoformat()
    write_new(claim, {'operation': 'Q7_FINALIZE_MAIN_AFTER_VERIFIED_VARIANT', 'run_id': run.name,
        'ledger_key': plan['ledger_key'], 'plan_sha256': plan['plan_sha256'],
        'native_body_sha256': policy.body_sha, 'intent_at': sent_at, 'automatic_retry_allowed': False,
        'state': 'INTENT_REQUIRES_INDEPENDENT_ALL23_READBACK'})
    result.update(status='SEND_INTENT_RECORDED', post_attempts=1, send_intent_at=sent_at,
                  native_body_sha256=policy.body_sha, actor_binding='four old row user IDs preserved; username and three new row IDs bound only inside page',
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
    decoded = comparator().decode_receipt(plan, parse(raw))
    require(isinstance(decoded, dict) and decoded.get('ok') is True, 'RECEIPT_DECODER_RESULT_REQUIRED')
    result.update(status='FINALIZE_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK', receipt_validation=decoded)


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
    result = {'schema': 'UsenseActualQ7Finalize/v1', 'operation': 'Q7_FINALIZE_MAIN_AFTER_VERIFIED_VARIANT',
        'book_id': '46007447', 'status': 'PREPARING', 'plan_sha256': plan['plan_sha256'],
        'plan_file_sha256': plan_sha256, 'config_sha256': config_sha256, 'run_id': run.name,
        'process_id': os.getpid(), 'post_attempts': 0, 'save_success': False, 'old_q7_modified_by_request': True,
        'independent_readback': 'PENDING_ALL23', 'authorization_reference': authorization_reference,
        'ledger_key': plan['ledger_key'], 'prewrite_responses': {}}
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
                    await r.fulfill(status=200, content_type='text/html', body='<!doctype html><title>Usense main finalization</title><link rel="icon" href="data:,">')
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
        require(comparator().check_prewrite(plan, fresh)['ok'], 'PREWRITE_COMPARATOR_REJECTED')
        require(not policy.blocked, 'GUARD_BLOCKED')
        await record_and_send(page=page, policy=policy, plan=plan, claim=claim, run=run, result=result)
    except BaseException as exc:
        result['status'] = 'UNKNOWN_DO_NOT_RETRY' if result['post_attempts'] else 'BLOCKED_BEFORE_SEND'
        result['error_type'] = type(exc).__name__
        result['error_code'] = getattr(exc, 'code', None)
    finally:
        policy.armed = False
        policy.sealed = True
        release = {'context_closed': context is None, 'runtime_stopped': runtime is None, 'errors': [],
                   'os_process_release': 'REQUIRES_PARENT_PID_EXIT_OBSERVATION', 'process_id': os.getpid()}
        if context is not None:
            try:
                await asyncio.wait_for(context.close(), timeout=15)
                release['context_closed'] = True
            except BaseException as exc:
                release['errors'].append({'phase': 'context_close', 'type': type(exc).__name__})
        for task in list(pending):
            task.cancel()
        if pending:
            try:
                await asyncio.wait_for(asyncio.gather(*list(pending), return_exceptions=True), timeout=5)
            except BaseException as exc:
                release['errors'].append({'phase': 'callbacks', 'type': type(exc).__name__})
        if runtime is not None:
            try:
                await asyncio.wait_for(runtime.stop(), timeout=15)
                release['runtime_stopped'] = True
            except BaseException as exc:
                release['errors'].append({'phase': 'runtime_stop', 'type': type(exc).__name__})
        release['pending_callbacks'] = len(pending)
        release['context_runtime_release_confirmed'] = bool(release['context_closed'] and release['runtime_stopped'] and not release['errors'] and not pending)
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
    result = asyncio.run(execute(config_path=args.config, config_sha256=args.sha256, plan_path=args.plan,
        plan_sha256=args.plan_sha256, baseline=args.baseline, ledger_root=args.ledger_root,
        authorization_reference=args.authorization_reference))
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if result['status'] == 'FINALIZE_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK' else 2


if __name__ == '__main__':
    raise SystemExit(main())
