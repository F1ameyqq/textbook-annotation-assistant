"""Targeted additional checks for current-session book isolation and replanning."""
import json
import sys
sys.dont_write_bytecode = True
import independent_review as review
from dataclasses import replace
from annotation.contracts import artifact_ref, write_bundle

def replan(case):
    case.prepare()
    first, session = case.execute('not_applied')
    old_history = session.receipt_history(case.plan.book_id)
    old_plan_id = case.plan.artifact_id
    case.prepare()  # independent new TARGET, plan id and action ids; explicit unchanged current snapshot
    assert case.plan.artifact_id != old_plan_id
    assert artifact_ref(session.read_snapshot(case.plan.book_id)) == artifact_ref(case.snapshot)
    second = session.execute(case.planned, artifact_ref(case.plan), case.config, asset_root=case.root,
        receipt_id='review-fresh-after-absence', created_at=review.TIME)
    write_bundle(second,case.root/'replanned-executed.json')
    receipt = next(a for a in second.artifacts if a.artifact_id=='review-fresh-after-absence')
    assert all(r.outcome=='APPLIED' for r in receipt.payload.results)
    assert len(session.read_target(case.plan.book_id)['target']['frames']) == 9
    assert session.receipt_history(case.plan.book_id)[0] == old_history[0]
    review.dump(case.root/'final-target.json',session.read_target(case.plan.book_id))
    review.dump(case.root/'final-log.json',session.action_log)
    review.dump(case.root/'full-history.json',session.receipt_history(case.plan.book_id))
    case.notes['new_plan_applied_after_recheck']=True

def isolated_book(case):
    case.prepare(); first,session=case.execute('lost_response')
    original_book=case.plan.book_id
    old_target=session.read_target(original_book); old_history=session.receipt_history(original_book)
    data=case.bundle.model_dump(mode='json')
    for a in data['artifacts']: a['book_id']='independent-second-book'
    case.bundle=review.validate_bundle(review.reseal(data),asset_root=case.root)
    case.config=replace(case.config,book_id='independent-second-book')
    case.prepare(); session.register_target(case.bundle,artifact_ref(case.snapshot),asset_root=case.root)
    second=session.execute(case.planned,artifact_ref(case.plan),case.config,asset_root=case.root,
        receipt_id='review-second-book-receipt',created_at=review.TIME)
    write_bundle(second,case.root/'second-book-executed.json')
    receipt=next(a for a in second.artifacts if a.artifact_id=='review-second-book-receipt')
    assert all(r.outcome=='APPLIED' for r in receipt.payload.results)
    assert session.is_paused(original_book) and not session.is_paused('independent-second-book')
    assert old_target==session.read_target(original_book) and old_history==session.receipt_history(original_book)
    review.dump(case.root/'second-book-target.json',session.read_target('independent-second-book'))
    review.dump(case.root/'combined-log.json',session.action_log)
    case.notes['separate_packages_book_isolation']='PASS; crossbook.py demonstrates failure when a legal bundle includes foreign UNKNOWN.'

review.run('not-applied-fresh-recheck','U06',replan)
review.run('second-book-separate-package','U05',isolated_book)
review.dump(review.OUT/'final-supplement-results.json',{'commit':'5c9285720c8628c5198bedeadfc9f6bc7826a914','results':review.RESULTS})
sys.exit(any(r['status']!='PASS' for r in review.RESULTS))
