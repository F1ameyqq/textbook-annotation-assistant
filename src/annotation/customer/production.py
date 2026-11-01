"""Serial prepare/save/fresh-process-readback/export with durable no-retry states."""
from __future__ import annotations

import copy
from html import escape
from pathlib import Path
import time

from .native_plan import make_plan, compare_readback, source_key, check_prewrite
from .prepare import candidate_hash, utcnow
from .source import verify_sources
from .store import Hold, digest, encoded
from .review_features import figure_requirements


def export_local(store, identity):
    job, head = store.job(identity)
    verify_sources(job["pages"])
    if job.get('native_export_ref'):
        receipt = store.get(job['native_export_ref'])
        output = Path(receipt['output'])
        if not (output / 'index.html').is_file(): raise Hold('原生交付文件缺失，保留原记录；不能自动重新导出。')
        return output
    output = store.root / "exports" / identity / head
    if (output / "index.html").is_file():
        return output
    output.mkdir(parents=True, exist_ok=True)
    (output / "job.json").write_bytes(encoded(job))
    parts = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width'><title>课时材料</title>",
             "<style>body{font:17px/1.7 system-ui;max-width:960px;margin:40px auto;padding:0 24px;color:#182330}"
             "article{border-top:1px solid #ccd4dd;padding:24px 0}pre{white-space:pre-wrap;font:inherit}small{color:#596577}</style>",
             "<h1>" + escape(job["lesson"]) + "</h1>",
             "<p>本地准备：" + escape(job["status"]) + "；平台：" + escape(job["platform_status"]) + "</p>",
             "<small>这是本地内容与读回记录导出；不冒充平台原生整书导出或整书完成。</small>"]
    for question in job["candidates"]:
        parts += ["<article><h2>第 " + escape(question["printed_number"]) + " 题</h2>",
                  "<small>" + escape(question["content_status"]) + " · " + escape(question["platform_status"]) + "</small>"]
        for zone, text in question["zones"].items():
            label = {"question": "题干", "choice": "选项", "answer": "答案", "analysis": "解析"}.get(zone, zone)
            parts += ["<h3>" + label + "</h3><pre>" + escape(text) + "</pre>"]
        parts.append("</article>")
    parts.append("</html>")
    (output / "index.html").write_text("\n".join(parts), encoding="utf-8")
    return output


def _check_execution_selection(job, selected, scope):
    if scope is None:
        return
    from .native_plan import require
    require(scope.get('book_id') == job['book_id'] and scope.get('directory_path') == job.get('directory_path', job['lesson']),
            '本次固定执行范围的书籍或目录不一致。')
    expected = scope.get('selection', [])
    require([q['key'] for q in selected] == [q['key'] for q in expected], '本次固定执行范围的题目已变化。')
    for candidate, bound in zip(selected, expected):
        require(candidate_hash(candidate) == bound['content_hash'], '本次固定执行范围的内容已变化。')


def _execution_plan(current, candidate, lesson, scope):
    plan = make_plan(current, candidate, lesson)
    if scope is None:
        return plan
    from .native_plan import require
    matches = [row for row in scope['selection'] if row['key'] == candidate['key']]
    require(len(matches) == 1, '动态计划不在本次固定范围。')
    bound = matches[0]; payload = plan['payload']
    require(plan['book_id'] == scope['book_id'] and payload['target_directory_id'] == scope['directory_id']
            and plan['key'] == bound['source_key'] and candidate_hash(plan['candidate']) == bound['content_hash'],
            '动态计划的目标或内容已变化。')
    require(payload['annotations_delete_rect_ids'] == [] and payload['ocr_delete_zones'] == [], '本轮不允许删除旧框或旧分区。')
    require(sorted(row['zone'] for row in payload['ocr_submissions']) == sorted(bound['zones']), '动态计划的待填分区已变化。')
    if bound['intended_operation'] == 'FILL_EXISTING_EMPTY_ZONES':
        require(plan['schema'] == 'CustomerNativeExistingFillPlan/v1'
                and payload['is_new_question_insertion'] is False
                and plan['target_node'] == bound['expected_existing_node']
                and plan['target_info_id'] == bound['expected_existing_info']
                and payload['annotations_upsert'] == [], '既有题只能填充本次绑定的原 node/info；不能改建新题或改框。')
        original_ids = bound.get('expected_rect_ids_by_zone')
        require(type(original_ids) is dict and set(original_ids) == set(bound['zones']), '本轮既有题缺少原题框身份绑定。')
        for submission in payload['ocr_submissions']:
            expected_ids = original_ids[submission['zone']]
            actual_ids = submission['rect_ids']
            require(type(expected_ids) is list and expected_ids and len(set(expected_ids)) == len(expected_ids)
                    and type(actual_ids) is list and len(set(actual_ids)) == len(actual_ids)
                    and set(actual_ids) == set(expected_ids), '既有题的原分区 rect_id 已变化；停止本轮且不重建题框。')
    else:
        require(bound['intended_operation'] == 'INSERT_NEW_NATIVE_QUESTION'
                and plan['schema'] == 'CustomerNativeInsertPlan/v1'
                and payload['is_new_question_insertion'] is True
                and len(payload['annotations_upsert']) == len(bound['source_frames']),
                '本轮新增题操作或题框数量已变化。')
    return plan


def produce(store, identity, settings, *, transport_factory=None, selected_keys=None, execution_scope=None):
    """Only the explicit customer start action calls this function.

    Tests substitute a synthetic platform, while the application always uses
    the concrete existing Usense writer/capture transport. There is no agent
    callback, per-question developer artifact, or formal-review-chat input.
    """
    from .transport import UsenseTransport
    started = time.perf_counter()
    job, head = store.job(identity)
    with store.book_lock(job["book_id"]):
        job, head = store.job(identity)
        verify_sources(job["pages"])
        from .selection import select
        selected = select(store, job, selected_keys)
        _check_execution_selection(job, selected, execution_scope)
        for candidate in selected:
            if candidate_hash(candidate) != candidate["content_hash"] or candidate["content_status"] not in {"READY_EXACT_TEXT", "READY_CUSTOMER_REVIEWED", "READY_SOURCE_CHECKED"}:
                raise Hold("候选内容需要重新审校。")
            graph=store.get(job["graph_ref"]) if job.get("graph_ref") else None
            evidence=store.get(job["evidence_ref"]) if job.get("evidence_ref") else None
            if figure_requirements(candidate,job["pages"],graph,evidence):
                raise Hold("明确图引用仍缺少已确认的原图绑定；停止生产并保留原任务。")
        kind = "save:" + job["book_id"]
        with store.connect() as db:
            unresolved = db.execute("SELECT key,state FROM operations WHERE kind=? AND state<>'COMPLETE'", (kind,)).fetchall()
        if unresolved:
            raise Hold("该书已有未知或失败保存。请保留原登录目录、账本和回执，先对账；不重发后继。")
        if transport_factory is None:
            from .legacy_ledger import bootstrap,guard
            bootstrap(store,job['book_id'])
            guard(store,Path(settings['profile']).resolve().parent/'usense-existing-ledger',job['book_id'])
        pending = []
        for candidate in selected:
            key = source_key(job["book_id"], candidate)
            old = store.operation(kind, key)
            if old is None:
                pending.append(candidate)
            else:
                accepted = store.get(old["output"])
                if accepted["candidate_hash"] != candidate_hash(candidate):
                    raise Hold("已有成功保存的来源内容发生变化；需要显式修订对账，不能作为新题重发。")
                candidate["platform_status"] = "REUSED_ACCEPTED"
                candidate["acceptance_ref"] = old["output"]
        transport = None
        current_key = None
        plan = sent = None
        try:
            if pending:
                transport = (transport_factory or UsenseTransport)(store, settings, job["book_id"])
                current, flat = transport.capture(job)
                if execution_scope is not None:
                    from .native_plan import directory_rows, require
                    require(len(directory_rows(current['directory'])[1]) == execution_scope['expected_initial_native_count'],
                            '当前库存与本次固定执行范围不一致。')
                    # Validate every dynamic operation before either current
                    # reuse records or the first send. A full or replaced old
                    # object is a hold for reconciliation, never a new insert.
                    for candidate in pending:
                        _execution_plan(current, candidate, job.get('directory_path', job['lesson']), execution_scope)
                from .legacy_ledger import existing_candidate
                fresh=[]
                for candidate in pending:
                    matched=existing_candidate(current,candidate)
                    if matched is None:fresh.append(candidate);continue
                    receipt={'schema':'CustomerCurrentExistingRead/v1','book_id':job['book_id'],
                        'candidate_hash':candidate_hash(candidate),'comparison':{'new_node_id':matched['node_id'],
                            'existing_record_only':True,'new_save_performed':False},'after':copy.deepcopy(current),
                        'processes':copy.deepcopy(transport.processes),'observed_at':utcnow()}
                    candidate['acceptance_ref']=store.record_read(kind,source_key(job['book_id'],candidate),receipt)
                    candidate['platform_status']='REUSED_CURRENT_EXISTING'
                    head=store.save_job(job,head,'CURRENT_EXISTING_REUSE_RECORDED')
                pending=fresh
                # Preflight all candidates against the same current inventory.
                # A later missing source must not be found after an earlier send.
                for candidate in pending:
                    _execution_plan(current, candidate, job.get('directory_path', job["lesson"]), execution_scope)
                for index, candidate in enumerate(pending):
                    verify_sources(job["pages"])
                    plan = _execution_plan(current, candidate, job.get('directory_path', job["lesson"]), execution_scope)
                    sent = None
                    current_key = plan["key"]
                    candidate["pending_plan_ref"] = store.put(plan)
                    store.begin(kind, current_key)
                    candidate["platform_status"] = "INTENT_UNKNOWN_UNTIL_READBACK"
                    job["platform_status"] = "RUNNING"
                    head = store.save_job(job, head, "SAVE_INTENT")
                    sent = transport.write_once(plan, flat, job)
                    # Concrete capture launches fresh owned child processes
                    # only after the writer's outer OS release has been proven.
                    after, after_flat = transport.capture(job, previous_pages=current["pages"])
                    writer = sent.get("writer", {})
                    window = {"start": writer["send_intent_at"], "end": writer["finished_at"]} if writer else None
                    comparison = compare_readback(plan, after, sent["receipt"],
                        runtime_actor_hashes=writer.get("runtime_actor_hashes"), send_window=window)
                    if transport_factory is None and not comparison["runtime_actor_and_send_window_checked"]:
                        raise Hold("缺少实际操作者和发送窗口证明，不能接受保存。")
                    receipt = {"schema": "CustomerSaveReadback/v1", "book_id": job["book_id"],
                               "candidate_hash": candidate_hash(candidate), "plan": plan,
                               "writer": sent, "comparison": comparison, "after": after,
                               "accepted_at": utcnow(), "processes": copy.deepcopy(transport.processes)}
                    ref = store.finish(kind, current_key, "COMPLETE", receipt)
                    candidate.update(platform_status="SAVED_AND_INDEPENDENTLY_READ_BACK", acceptance_ref=ref)
                    head = store.save_job(job, head, "READBACK_ACCEPTED")
                    current_key = None
                    current, flat = after, after_flat
            job["platform_status"] = "SELECTED_ITEMS_SAVED_AND_READ_BACK_OR_CURRENT_EXISTING_REUSED"
            job['last_production_selection']=[q['key'] for q in selected]
            job['remaining_unaccepted_count']=sum(not q.get('acceptance_ref') for q in job['candidates'])
        except BaseException as exc:
            if current_key is not None and store.operation(kind, current_key)["state"] == "INTENT":
                store.finish(kind, current_key, "UNKNOWN_NO_RETRY", {"type": type(exc).__name__, "message": str(exc),
                    "processes": copy.deepcopy(transport.processes) if transport else [], "at": utcnow(),
                    "plan_ref": store.put(plan), "sent": sent,
                    "native_output": str(transport.out) if hasattr(transport, "out") else None})
            job["platform_status"] = "UNKNOWN_NO_RETRY" if current_key else "BLOCKED_BEFORE_SEND"
            job["last_message"] = str(exc)
            job["metrics"]["production_seconds"] = time.perf_counter() - started
            store.save_job(job, head, "PRODUCTION_STOPPED")
            export_local(store, identity)
            raise
        job["metrics"]["production_seconds"] = time.perf_counter() - started
        store.save_job(job, head, "PRODUCTION_COMPLETE")
        if transport_factory is None:
            from .native_delivery import finish
            if transport is None: transport=UsenseTransport(store,settings,job['book_id'])
            return finish(store,identity,transport)
    return export_local(store, identity)


def reconcile(store, identity, settings, *, transport_factory=None):
    """One explicit read-only recovery; no call to a writer on any branch."""
    from .transport import UsenseTransport
    job, head = store.job(identity)
    kind = "save:" + job["book_id"]
    with store.book_lock(job["book_id"]):
        job, head = store.job(identity)
        verify_sources(job["pages"])
        candidates = [q for q in job["candidates"] if q.get("pending_plan_ref") and q["platform_status"] == "INTENT_UNKNOWN_UNTIL_READBACK"]
        if len(candidates) != 1:
            raise Hold("当前没有唯一可对账的未知保存。保留原记录；不会重新发送。")
        candidate = candidates[0]
        plan = store.get(candidate["pending_plan_ref"])
        key = source_key(job["book_id"], candidate)
        previous = store.operation(kind, key)
        if previous is not None and previous['state']=='INTENT' and previous['output'] is None:
            from .interrupted_save import recover
            unknown = recover(store,job,plan,candidate,settings)
            store.finish(kind,key,'UNKNOWN_NO_RETRY',unknown)
            previous = store.operation(kind,key)
            job['platform_status']='UNKNOWN_NO_RETRY'
            head=store.save_job(job,head,'INTERRUPTED_WRITER_RECEIPT_RECOVERED_NO_RESEND')
        if previous is None or previous["state"] != "UNKNOWN_NO_RETRY":
            raise Hold("原保存状态不是可自动核对的 UNKNOWN；需要保留原始记录进一步核查。")
        unknown = store.get(previous["output"])
        sent = unknown.get("sent")
        if sent is None:
            raise Hold("缺少明确的原始保存回执；本次不启动新读取或重发。")
        writer = sent.get("writer", {})
        if transport_factory is None:
            if writer.get("post_attempts") != 1 or writer.get("release", {}).get("context_runtime_release_confirmed") is not True:
                raise Hold("原保存发送次数或释放未证，先保留原运行记录。")
            from annotation.runtime.usense_live.update import loads
            from .store import byte_hash
            # Only the original writer's process records, never a copied
            # accepted marker, establish exit before this read-only recovery.
            for process in sent["processes"]:
                path = Path(process["record"])
                if byte_hash(path.read_bytes()) != process["sha256"] or loads(path.read_bytes()).get("owned_os_release_confirmed") is not True:
                    raise Hold("原进程释放记录未证。")
        recovery_key = digest([identity, previous["output"]])
        if store.operation("reconcile", recovery_key) is not None:
            raise Hold("这条原记录已有一次对账；查看原结果，不能自动重读。")
        retained = None
        if transport_factory is None:
            from .retained_readback import reconstruct
            retained = reconstruct(store, job, plan, unknown)
        transport = None if retained is not None else (transport_factory or UsenseTransport)(store, settings, job["book_id"])
        store.begin("reconcile", recovery_key)
        try:
            if retained is not None:
                after = retained['after']
            else:
                after, _ = transport.capture(job, previous_pages=plan["before"]["pages"])
            window = {"start": writer["send_intent_at"], "end": writer["finished_at"]} if writer else None
            comparison = compare_readback(plan, after, sent["receipt"], runtime_actor_hashes=writer.get("runtime_actor_hashes"), send_window=window)
            if transport_factory is None and not comparison["runtime_actor_and_send_window_checked"]:
                raise Hold("缺少原发送窗口或操作者身份。")
            receipt = {"schema": "CustomerSaveReadback/v1", "book_id": job["book_id"], "candidate_hash": candidate_hash(candidate),
                       "plan": plan, "writer": sent, "comparison": comparison, "after": after,
                       "accepted_at": utcnow(), "processes": copy.deepcopy(retained['processes'] if retained is not None else transport.processes), "reconciled_readonly": True}
            if retained is not None:
                receipt['retained_readback_provenance'] = {key: copy.deepcopy(value) for key, value in retained.items() if key != 'after'}
            store.finish("reconcile", recovery_key, "COMPLETE", receipt)
            candidate["acceptance_ref"] = store.resolve(kind, key, previous, receipt)
            candidate["platform_status"] = "SAVED_AND_INDEPENDENTLY_READ_BACK"
            job["platform_status"] = "RECONCILED_SUCCESSORS_NOT_RUN"
            store.save_job(job, head, "READONLY_RECONCILIATION")
        except BaseException as exc:
            if store.operation("reconcile", recovery_key)["state"] == "INTENT":
                store.finish("reconcile", recovery_key, "FAILED_NO_RETRY", {"type": type(exc).__name__, "message": str(exc)})
            raise
    return export_local(store, identity)
