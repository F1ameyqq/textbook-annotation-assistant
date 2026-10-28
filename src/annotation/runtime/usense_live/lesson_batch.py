"""A28's four reviewed lesson inserts, serial receipt-bound fresh readbacks.

Only this book, lesson, four logical units and observed succeeding stable node
are supported. No recovery resend, old-question update, login or upload path.
"""
import ast
import copy
from datetime import datetime, timezone
import json
from pathlib import Path

from . import update as u
from . import lesson_insert as ins
from .core import sha, write_new, require, LOCKS
from .config import endpoints

SCHEMA = 'A28ReviewedLessonManifest/v1'
KEYS = ('q6', 'q7', 'q8', 'q8-variant')
PAGES = (12, 13, 173)


def read(path):
    return u.loads(Path(path).read_bytes())


def now():
    return datetime.now(timezone.utc).isoformat()


def checked(ref):
    require(type(ref) is dict and set(ref) == {'path', 'sha256'}, 'A28_FILE_REFERENCE')
    path = Path(ref['path'])
    require(path.is_absolute() and path.is_file() and sha(path.read_bytes()) == ref['sha256'], 'A28_FILE_CHANGED')
    return path


def verify_known_info_evidence(ref):
    """Bind the finite known-ID deny list to existing raw/public/code evidence."""
    path = checked(ref)
    proof = read(path)
    require(proof.get('schema') == 'A28KnownOldInfoEvidence/v1' and
            proof.get('book_id') == ins.BOOK, 'A28_KNOWN_INFO_EVIDENCE_SCHEMA')
    rows = proof.get('identities')
    expected = ins.OBSERVED_OLD_INFO_BY_ORDER
    require(type(rows) is list and [r.get('question_order') for r in rows] == sorted(expected),
            'A28_KNOWN_INFO_EVIDENCE_COVERAGE')
    refs = {str(path): ref['sha256']}
    for row in rows:
        order = row['question_order']
        node = ins.TAIL_NODE if order == 23 else ins.OLD_NODES[order-1]
        require(type(order) is int and row.get('info_id') == expected[order] and
                row.get('node_id') == node, 'A28_KNOWN_INFO_EVIDENCE_BINDING')
        source = checked(row['source'])
        refs[str(source)] = row['source']['sha256']
        kind = row.get('source_kind')
        if order >= 18:
            require(kind == 'native_info_raw', 'A28_KNOWN_INFO_SOURCE_KIND')
            info = u._response(read(source))
            require(info.get('id') == expected[order] and info.get('file_id') == ins.BOOK and
                    info.get('order_in_level') == str(order), 'A28_KNOWN_INFO_RAW_BINDING')
        elif order == 1:
            require(kind == 'accepted_public_proof', 'A28_KNOWN_INFO_SOURCE_KIND')
            public = read(source)
            require(public.get('schema') == 'UsenseQ1LiveProofPublic/v1' and
                    public.get('target', {}).get('book_id') == ins.BOOK and
                    public['target'].get('node_id') == node and
                    public['target'].get('info_id') == expected[order] and
                    public['target'].get('question_order') == order, 'A28_KNOWN_INFO_PUBLIC_BINDING')
        else:
            require(order == 7 and kind == 'accepted_code_binding', 'A28_KNOWN_INFO_SOURCE_KIND')
            values = {}
            for statement in ast.parse(source.read_text(encoding='utf-8')).body:
                if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                    target = statement.targets[0]
                    if isinstance(target, ast.Name) and target.id in ('OLD_Q7_NODE', 'OLD_Q7_INFO'):
                        require(target.id not in values, 'A28_KNOWN_INFO_CODE_DUPLICATE')
                        values[target.id] = ast.literal_eval(statement.value)
            require(values == {'OLD_Q7_NODE': node, 'OLD_Q7_INFO': expected[order]},
                    'A28_KNOWN_INFO_CODE_BINDING')
    return refs


def verify_evidence(plan):
    """Re-open original candidate, review, all source and fetched-crop bytes."""
    approved = plan['approved_new_content']
    for kind in ('candidate', 'review', 'crop_evidence'):
        checked({'path': approved[kind + '_ref'], 'sha256': approved[kind + '_sha256']})
    candidate = read(approved['candidate_ref'])
    require(u.json_same(candidate, approved['candidate']), 'A28_CANDIDATE_NOT_EXACT')
    require(candidate['review'] == {'path': approved['review_ref'], 'sha256': approved['review_sha256']},
            'A28_REVIEW_NOT_BOUND')
    for ref in approved['source_evidence']:
        checked(ref)
    verify_known_info_evidence(approved.get('known_info_evidence'))
    proof = read(approved['crop_evidence_ref'])
    require(proof['schema'] == 'A28CropProof/v1' and proof['status'] == 'ALL_CROPS_CAPTURED', 'A28_CROP_PROOF_INCOMPLETE')
    rows = {(row['logical_key'], row['key']): row for row in proof['images']}
    require(len(rows) == len(proof['images']) == 14, 'A28_EXACT_FOURTEEN_CROPS')
    for frame in candidate['frames']:
        checked(frame['source'])
        row = rows[(candidate['logical_key'], frame['key'])]
        x1, y1, x2, y2 = frame['bbox']
        require(row['url'] == frame['image_path'] and row['http_status'] == 200 and
                row['bbox'] == frame['bbox'] and row['dimensions'] == [x2-x1, y2-y1] and
                row['source_sha256'] == frame['source']['sha256'] and row['full_pixel_decode'] is True,
                'A28_CROP_BINDING')
        checked({'path': row['file'], 'sha256': row['sha256']})
    return True


def prepare(manifest_path, manifest_sha, baseline, profile, authorization):
    require(bool(authorization), 'CURRENT_WRITE_AUTHORIZATION_REFERENCE_REQUIRED')
    manifest_path, baseline, profile = Path(manifest_path), Path(baseline), Path(profile)
    require(sha(manifest_path.read_bytes()) == manifest_sha, 'A28_MANIFEST_CHANGED')
    manifest = read(manifest_path)
    require(manifest['schema'] == SCHEMA and manifest['book_id'] == '46007447', 'A28_MANIFEST_SCHEMA')
    require(len(manifest['targets']) == 4, 'A28_EXACT_FOUR_TARGETS')
    summary = read(baseline/'capture-summary.json')
    require(sha((baseline/'capture-summary.json').read_bytes()) == manifest['baseline']['capture_summary_sha256'], 'A28_BASELINE_SUMMARY_CHANGED')
    require(summary['status'] == 'NATIVE_GETS_CAPTURED' and summary['save_attempts'] == 0 and
            summary['release']['context_runtime_release_confirmed'] is True and
            summary['transport'] == {'mode': 'DIRECT', 'proxy_server': None}, 'A28_RELEASED_DIRECT_BASELINE')
    paths = ins.full_endpoints(tail_order=23)
    require(set(paths) == set(manifest['baseline']['files']) == set(summary['captures']), 'A28_BASELINE_SCOPE')
    refs = {str(manifest_path): manifest_sha, str(baseline/'capture-summary.json'): manifest['baseline']['capture_summary_sha256']}
    known_info_ref = manifest.get('known_info_evidence')
    refs.update(verify_known_info_evidence(known_info_ref))
    before = {}
    for name in paths:
        raw = (baseline/(name+'.json')).read_bytes()
        cap = summary['captures'][name]
        require(sha(raw) == manifest['baseline']['files'][name] == cap['sha256'] and
                cap['status'] == 200 and cap['request_counts'] == {'context': 1, 'native': 1}, 'A28_BASELINE_RAW')
        refs[str(baseline/(name+'.json'))] = sha(raw)
        before[name] = u.loads(raw)
    targets, rects = [], set()
    for expected, item in zip(KEYS, manifest['targets']):
        candidate_path = checked(item['candidate'])
        candidate = read(candidate_path)
        require(candidate['logical_key'] == expected, 'A28_FIXED_TARGET_ORDER')
        review = candidate['review']
        crop = manifest['crop_evidence']
        sources = {frame['source']['path']: frame['source']['sha256'] for frame in candidate['frames']}
        approved = {'candidate_ref': str(candidate_path), 'candidate_sha256': item['candidate']['sha256'],
            'review_ref': review['path'], 'review_sha256': review['sha256'],
            'crop_evidence_ref': crop['path'], 'crop_evidence_sha256': crop['sha256'],
            'source_evidence': [{'path': p, 'sha256': h} for p,h in sources.items()],
            'known_info_evidence': known_info_ref,
            'candidate': candidate}
        verify_evidence({'approved_new_content': approved})
        # All four candidates are validated before any runtime, using only an
        # in-memory structural predecessor projection (never server identity).
        for frame in candidate['frames']:
            require(frame['planned_rect_id'] not in rects, 'A28_CROSS_TARGET_RECT_DUPLICATE')
            rects.add(frame['planned_rect_id'])
        for kind in ('candidate', 'review', 'crop_evidence'):
            refs[approved[kind+'_ref']] = approved[kind+'_sha256']
        refs.update(sources)
        targets.append({'logical_key': expected, 'candidate': candidate, 'approved_new_content': approved})
    proof = read(manifest['crop_evidence']['path'])
    for row in proof['images']:
        refs[row['file']] = row['sha256']
    ledger = profile.parent/'usense-existing-ledger'
    require(ledger.is_dir() and not any((profile/name).exists() for name in LOCKS), 'A28_PROFILE_OR_LEDGER_UNREADY')
    ledger_files = {str(p): sha(p.read_bytes()) for p in ledger.iterdir() if p.is_file()}
    # Candidate validation is called independently of sequential identity.
    for item in targets:
        ins.validate_candidate(item['candidate'], before, item['approved_new_content'])
    first = ins.make_insert_plan(before, targets[0]['candidate'], targets[0]['approved_new_content'])
    for item in targets:
        logical_key = item['logical_key']
        require(not list(ledger.glob('book46007447-lesson2-'+logical_key+'*.json')), 'A28_EXISTING_INTENT_NO_RETRY')
    return {'schema': 'A28PreparedLessonBatch/v1', 'manifest_sha256': manifest_sha, 'targets': targets,
        'before': before, 'first_plan': first, 'evidence_file_sha256': refs, 'ledger_root': str(ledger),
        'ledger_files': ledger_files, 'transport': summary['transport']}


def recheck(prepared):
    for path,digest in prepared['evidence_file_sha256'].items():
        require(sha(Path(path).read_bytes()) == digest, 'A28_FIXED_EVIDENCE_CHANGED')
    for path,digest in prepared['ledger_files'].items():
        require(Path(path).is_file() and sha(Path(path).read_bytes()) == digest, 'A28_EXISTING_LEDGER_CHANGED')


def execute(prepared, out, baseline, profile, authorization, tls, run_child, write_plan):
    summary = {'schema': 'A28LessonBatch/v1', 'status': 'RUNNING', 'started_at': now(),
        'results': [{'logical_key': key, 'status': 'NOT_RUN'} for key in KEYS],
        'previously_accepted_count': 5, 'new_completed_count': 0, 'lesson_denominator': 9,
        'old_question_content_updates': 0, 'human_interventions': 0, 'ocr_calls': 0}
    before = prepared['before']
    accepted_new = {}
    accepted_info_ids = set()
    current = None
    try:
        for index,item in enumerate(prepared['targets']):
            recheck(prepared)
            current = summary['results'][index]
            current['status'] = 'PREPARING'
            qout = out/item['logical_key']; qout.mkdir()
            plan = ins.make_insert_plan(before, item['candidate'], item['approved_new_content'])
            ins.validate_insert_plan(plan)
            plan_path = qout/'plan.json'
            # This contract validates its own schema, not the old update schema.
            with plan_path.open('xb') as f:
                f.write(json.dumps(plan, ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8'))
                f.flush()
                import os
                os.fsync(f.fileno())
            ins.validate_insert_plan(read(plan_path))
            prepared['evidence_file_sha256'][str(plan_path)] = sha(plan_path.read_bytes())
            current.update(new_order=plan['new_order'], plan_sha256=plan['plan_sha256'], plan_file=str(plan_path))
            def configure(label, orders):
                recheck(prepared)
                cfg = qout/(label+'-config.json')
                result = run_child(['configure','--profile',profile,'--output-root',out,'--config',cfg,
                    '--coordinator','A28-root','--executor',label+'-process','--reviewer','A28-independent-reviewer',
                    '--authorization-reference',authorization,'--tls-approval-reference',tls,
                    '--orders',*orders,'--pages',*PAGES,'--source','--seconds',900],qout/(label+'-configuration-result.json'))
                return cfg,result['result']['sha256']
            cfg,digest = configure('writer',[plan['new_order']])
            wp = run_child(['--insert-writer','--config',cfg,'--sha256',digest,'--plan',plan_path,
                '--plan-sha256',sha(plan_path.read_bytes()),'--baseline',baseline,
                '--ledger-root',prepared['ledger_root'],'--authorization-reference',authorization],qout/'writer-process-result.json')
            w=wp['result']
            require(wp['exit_code']==0 and w['receipt_exact_success'] is True and
                    w['release']['context_runtime_release_confirmed'] is True, 'A28_WRITER_UNKNOWN_OR_UNRELEASED')
            current.update(writer_run=w['run_id'], post_attempts=w['post_attempts'])
            reader_orders=list(range(23,plan['new_order']+2))
            cfg,digest=configure('independent-reader',reader_orders)
            rp=run_child(['capture','--config',cfg,'--sha256',digest],qout/'reader-process-result.json')
            recheck(prepared)
            r=rp['result']; reader_dir=out/r['run_id']
            names=endpoints(reader_orders,PAGES,source=True)
            require(set(r['captures'])==set(names), 'A28_READER_EXACT_SCOPE')
            after={name:read(reader_dir/(name+'.json')) for name in names}
            for name,cap in r['captures'].items():
                require(cap['status']==200 and cap['request_counts']=={'context':1,'native':1} and
                        sha((reader_dir/(name+'.json')).read_bytes())==cap['sha256'] and
                        datetime.fromisoformat(cap['observed_at'])>datetime.fromisoformat(wp['finished_at']),
                        'A28_READER_RAW_COUNTS_TIME')
            receipt=read(out/w['run_id']/'native-receipt.json')
            comparison_names=endpoints([plan['new_order'],plan['new_order']+1],PAGES,source=True)
            comparison=ins.compare_insert_readback(plan,{name:after[name] for name in comparison_names},receipt,runtime_actor_hashes=w['runtime_actor_hashes'],
                send_window={'start':w['send_intent_at'],'end':w['finished_at']})
            checks={'writer_exit_zero':wp['exit_code']==0,'reader_exit_zero':rp['exit_code']==0,
                'reader_success':r['status']=='NATIVE_GETS_CAPTURED','reader_writes_zero':r['save_attempts']==0,
                'reader_released':r['release']['context_runtime_release_confirmed'],
                'different_processes':wp['pid']!=rp['pid'],'different_contexts':w['run_id']!=r['run_id'],
                'reader_started_after_writer_exit':datetime.fromisoformat(rp['started_at'])>datetime.fromisoformat(wp['finished_at']),
                'receipt_raw_hash':sha((out/w['run_id']/'native-receipt.json').read_bytes())==w['receipt_sha256'],
                'one_send':w['post_attempts']==1 and w['post_layers']=={'context':1,'native':1},
                'full_comparison':comparison['ok'],
                'all_prior_new_native_content_unchanged':all(u.json_same(value,after[name]) for name,value in accepted_new.items()),
                'new_info_distinct_from_prior_new':after[f"q{plan['new_order']}_info"]['data']['id'] not in accepted_info_ids}
            accepted=all(checks.values())
            current.update(status='ACCEPTED_LESSON_INSERT' if accepted else 'FAILED_STOP', checks=checks,
                comparison=comparison,reader_run=r['run_id'],candidate_sha256=item['approved_new_content']['candidate_sha256'])
            write_new(qout/'acceptance.json',current)
            require(accepted,'A28_READBACK_MISMATCH_NO_RETRY')
            accepted_info_ids.add(after[f"q{plan['new_order']}_info"]['data']['id'])
            accepted_new.update({f"q{plan['new_order']}_{suffix}":after[f"q{plan['new_order']}_{suffix}"] for suffix in ins.SUFFIXES})
            # Do not write the old existing-update accepted marker or make this
            # new result a revision predecessor. Bind the actual prior readback.
            prepared['evidence_file_sha256'][str(qout/'acceptance.json')]=sha((qout/'acceptance.json').read_bytes())
            for path in Path(prepared['ledger_root']).iterdir():
                if path.is_file() and str(path) not in prepared['ledger_files']:
                    require(path.name.startswith(plan['ledger_key']), 'A28_UNEXPECTED_LEDGER_ADDITION')
                    prepared['ledger_files'][str(path)]=sha(path.read_bytes())
            next_names=ins.full_endpoints(tail_order=plan['new_order']+1)
            before={name:after[name] for name in next_names}
            baseline=reader_dir
            for name in names:
                prepared['evidence_file_sha256'][str(reader_dir/(name+'.json'))]=r['captures'][name]['sha256']
            summary['new_completed_count']+=1
        recheck(prepared)
        summary['status']='ALL_FOUR_ACCEPTED'
    except BaseException as exc:
        if current is not None and current['status'] not in ('ACCEPTED_LESSON_INSERT','FAILED_STOP'):
            current['status']='STOPPED_NO_RETRY'
        summary.update(status='STOPPED_NO_RETRY',error_type=type(exc).__name__,error_code=getattr(exc,'code',str(exc)))
    finally:
        summary.update(finished_at=now(),lesson_cumulative_count=5+summary['new_completed_count'])
        write_new(out/'batch-summary.json',summary)
    return summary
