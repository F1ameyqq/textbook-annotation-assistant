"""Synthetic preview binding and real writer code with a fake owned context."""
import asyncio
import base64
import copy
from datetime import timedelta
import json
import selectors
import time
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_usense_structure as base
from annotation.runtime.usense_live import directory_apply as da,structural_writer as sw,structure as s,update as u
from annotation.runtime.usense_live.batch import file_ref

RELEASE={'context_closed':True,'runtime_stopped':True,'pending_callbacks':0,'errors':[],'context_runtime_release_confirmed':True}


class NoIOSelector(selectors.SelectSelector):
    def select(self,timeout=None):
        assert not self.get_map(),'Unexpected real I/O in fake-context test'
        if timeout:time.sleep(min(timeout,0.01))
        return []


class OfflineLoop(asyncio.SelectorEventLoop):
    """Fake-context tests have no I/O or other threads; no wakeup socket needed.

    Keep normal task/timer/wait_for scheduling. Only avoid the Windows local
    socketpair that is unrelated to the transport mocked by these tests.
    """
    def __init__(self):super().__init__(selector=NoIOSelector())
    def _make_self_pipe(self):pass
    def _write_to_self(self):pass
    def _close_self_pipe(self):pass


class FakeOwner:
    def __init__(self,binding,paths,post,plan_path,plan_sha,*,native,receipt,send_error=None):
        self.binding=binding;self.native=native;self.receipt=receipt;self.send_error=send_error
        self.policy=sw.OnePostPolicy(binding,paths,post,plan_path,plan_sha);self.page=self;self.release=None;self.send_calls=0;self.body=None
    async def __aenter__(self):self.binding.output.mkdir();return self
    async def __aexit__(self,*args):
        self.release=copy.deepcopy(RELEASE)
        base.dump(self.binding.output/'network-events.json',self.policy.events)
        return False
    async def route(self,*args):pass
    async def navigate(self):pass
    async def evaluate(self,expression,arg):
        if expression==sw.FETCH:
            name=next(k for k,v in self.paths.items() if v==arg)
            url=sw.ORIGIN+arg
            for layer in ('context','native'):assert self.policy.decide(layer,'GET',url,'fetch')
            raw=json.dumps(self.native[name],ensure_ascii=False).encode()
            return {'status':200,'body_base64':base64.b64encode(raw).decode()}
        if expression in (sw.PREPARE_APPLY,sw.PREPARE_INSERT):
            payload=copy.deepcopy(arg)
            if expression==sw.PREPARE_INSERT:
                payload['created_by']='synthetic actor'
                for row in payload['annotations_upsert']:row['user_id']='222'
            self.body=json.dumps(payload,ensure_ascii=False,separators=(',',':'))
            return {'sha256':sw.sha(self.body.encode()),'runtime_actor_sha256':u.text_digest('synthetic actor'),'runtime_user_id_sha256':u.text_digest('222')}
        assert expression==sw.SEND
        self.send_calls+=1
        for layer in ('context','native'):assert self.policy.allow_post(layer,'POST',arg,self.body,False)
        if self.send_error:raise self.send_error
        return {'status':200,'body_base64':base64.b64encode(self.receipt).decode()}


class StructuralWriterTests(unittest.TestCase):
    setUp=base.StructureTests.setUp
    url=base.StructureTests.url
    blocked=base.StructureTests.blocked
    new_inputs=base.StructureTests.new_inputs
    review=base.StructureTests.review
    new_plan=base.StructureTests.new_plan
    new_after=base.StructureTests.new_after

    def apply_plan(self):
        preview=self.root/'preview';reader=self.root/'reader';preview.mkdir();reader.mkdir()
        response={'code':0,'message':'success','data':{'has_changes':True,'directory_additions':[],'directory_renames':[],'directory_deletions':[],
          'directory_moves':[],'question_deletions':[],'question_moves':[{'node_id':t['node_id'],'old_order':t['question_order'],'new_order':t['question_order'],
          'old_directory_id':t['lesson_directory_id'],'new_directory_id':self.dest} for t in self.targets],
          'question_order_changes':[],'risk_summary':[],'summary':{'added_dirs':0,'renamed_dirs':0,'deleted_dirs':0,'moved_dirs':0,'deleted_questions':0,'moved_questions':5,'changed_questions':0}}}
        refs={'request':base.dump(preview/'preview-request.json',self.move['preview_request']),
              'response':base.dump(preview/'preview-response.json',response)}
        execution={'schema':'UsenseDirectoryPreviewCapture/v1','status':'PREVIEW_RESPONSE_CAPTURED_REQUIRES_REVIEW','http_status':200,
          'post_attempts':1,'apply_attempts':0,'commit_attempts':0,'post_counts':{'context':1,'native':1},'release':RELEASE,
          'request_sha256':refs['request']['sha256'],'response_sha256':refs['response']['sha256'],
          'finished_at':(self.now-timedelta(seconds=20)).isoformat()}
        refs['execution']=base.dump(preview/'result.json',execution)
        events=[{'layer':layer,'method':'POST','url_sha256':sw.sha((sw.ORIGIN+s.PREVIEW).encode()),'allowed':True} for layer in ('context','native')]
        refs['network']=base.dump(preview/'network-events.json',events)
        caps={}
        for name in ('directory','frames','source'):
            base.dump(preview/('before-'+name+'.json'),self.before[name]);ref=base.dump(reader/(name+'.json'),self.before[name])
            caps[name]={'sha256':ref['sha256'],'bytes':(reader/(name+'.json')).stat().st_size,'status':200,
              'observed_at':(self.now-timedelta(seconds=10)).isoformat(),'request_counts':{'context':1,'native':1}}
        base.dump(reader/'capture-summary.json',{'status':'NATIVE_GETS_CAPTURED','save_attempts':0,'release':RELEASE,
          'finished_at':(self.now-timedelta(seconds=9)).isoformat(),'captures':caps})
        readback={'schema':'UsenseDirectoryPreviewReadback/v1','status':'PREVIEW_MATCHES_INTENDED_FIVE_MOVES_AND_GLOBAL_STATE_UNCHANGED',
          'checks':{'directory':True,'frames':True,'source':True},'actual_preview_posts':1,'apply_posts':0,'commit_posts':0,
          'response_sha256':refs['response']['sha256'],'readback_directory':str(reader)}
        refs['readback']=base.dump(preview/'readback.json',readback)
        return da.make_apply_plan(self.move,refs)

    def execute_fake(self,plan,mode='apply',receipt=None,native=None,send_error=None):
        baseline=self.root/'baseline';baseline.mkdir(exist_ok=True)
        for name,value in plan['before_full'].items():base.dump(baseline/(name+'.json'),value)
        planfile=self.root/'writer-plan.json';base.dump(planfile,plan)
        ledger=self.root/'usense-existing-ledger';ledger.mkdir(exist_ok=True)
        binding=SimpleNamespace(data={'operation':'READONLY_CAPTURE','static_get':{'mode':'DISABLED','max_requests':0},
          'profile':{'directory':str(self.root/'profile')},'allowed_get':[]},output=self.root/'writer-run',check=lambda **kw:None)
        if receipt is None:receipt=b'{"code":0,"message":"success","data":{"SYNTHETIC_FIRST_APPLY_SHAPE":true}}'
        owners=[]
        def owner(*args):
            obj=FakeOwner(*args,native=native or plan['before_full'],receipt=receipt,send_error=send_error)
            obj.paths=args[1];owners.append(obj);return obj
        with patch.object(sw,'load_binding',return_value=binding),patch.object(sw,'StructuralContext',side_effect=owner):
            loop=OfflineLoop()
            try:
                result=loop.run_until_complete(sw.execute(mode=mode,config_path='synthetic',config_sha256='a'*64,plan_path=planfile,
                  plan_sha256=file_ref(planfile)['sha256'],baseline=baseline,ledger_root=ledger,authorization_reference='SYNTHETIC TEST AUTHORIZATION'))
            finally:loop.close()
        return result,owners,ledger

    def test_complete_preview_binds_same_apply_payload(self):
        plan=self.apply_plan()
        self.assertEqual(plan['request']['path'],s.APPLY)
        self.assertTrue(u.json_same(plan['request']['body'],self.move['preview_request']['body']))

    def test_preview_extra_move_or_boolean_count_rejected(self):
        plan=self.apply_plan();refs=copy.deepcopy(plan['preview_refs'])
        path=Path(refs['execution']['path']);value=json.loads(path.read_bytes());value['post_counts']['context']=True;refs['execution']=base.dump(path,value)
        self.blocked('APPLY_PREVIEW_DUAL_GUARD_COUNTS',lambda:da.make_apply_plan(self.move,refs))

    def test_preview_native_response_or_readback_tamper_rejected(self):
        plan=self.apply_plan();ref=plan['preview_refs']['response'];Path(ref['path']).write_bytes(b'changed')
        self.blocked('BATCH_EVIDENCE_HASH_CHANGED',lambda:da.validate(plan))

    def test_apply_one_send_raw_unknown_shape_is_preserved_not_accepted(self):
        plan=self.apply_plan();raw=b'{"code":0,"message":"success","data":{"SYNTHETIC_FIRST_APPLY_SHAPE":true}}'
        result,owners,ledger=self.execute_fake(plan,receipt=raw)
        self.assertEqual(result['status'],'APPLY_RAW_RESPONSE_REQUIRES_INDEPENDENT_FULL_READBACK')
        self.assertIsNone(result['save_success']);self.assertFalse(result['platform_acceptance']);self.assertEqual(owners[0].send_calls,1)
        self.assertEqual((self.root/'writer-run/native-receipt.json').read_bytes(),raw)
        self.assertTrue((ledger/(plan['ledger_key']+'.json')).exists())
        self.assertEqual(result['release']['save_attempts'],1)
        self.assertEqual(len(owners[0].policy.events),2*len(sw.endpoint_map(plan['before_full']))+2)

    def test_apply_timeout_keeps_intent_and_second_attempt_stops(self):
        plan=self.apply_plan();result,owners,ledger=self.execute_fake(plan,send_error=TimeoutError('synthetic lost response'))
        self.assertEqual(result['status'],'UNKNOWN_DO_NOT_RETRY');self.assertEqual(owners[0].send_calls,1)
        self.blocked('STRUCTURE_EXISTING_INTENT_NO_RETRY',lambda:sw.validate_inputs(plan,'apply',self.root/'baseline',ledger,'explicit'))

    def test_stale_target_or_unrelated_object_stops_before_intent(self):
        plan=self.apply_plan();native=copy.deepcopy(plan['before_full']);native['q1_info']['data']['updated_at']='2026-10-23T22:00:00'
        result,owners,ledger=self.execute_fake(plan,native=native)
        self.assertEqual(result['status'],'BLOCKED_BEFORE_SEND');self.assertEqual(owners[0].send_calls,0)
        self.assertFalse((ledger/(plan['ledger_key']+'.json')).exists())

    def test_non_json_apply_reply_is_raw_preserved_unknown(self):
        plan=self.apply_plan();raw=b'<synthetic failed response>'
        result,owners,ledger=self.execute_fake(plan,receipt=raw)
        self.assertEqual(result['status'],'UNKNOWN_DO_NOT_RETRY')
        self.assertEqual((self.root/'writer-run/native-receipt.json').read_bytes(),raw)

    def test_intent_fsync_failure_never_arms_send_and_cannot_retry(self):
        plan=self.apply_plan()
        with patch.object(sw,'sync_intent',side_effect=OSError('synthetic durability failure')):
            result,owners,ledger=self.execute_fake(plan)
        self.assertEqual(result['status'],'BLOCKED_BEFORE_SEND');self.assertEqual(owners[0].send_calls,0)
        self.assertTrue((ledger/(plan['ledger_key']+'.json')).exists())
        self.blocked('STRUCTURE_EXISTING_INTENT_NO_RETRY',lambda:sw.validate_inputs(plan,'apply',self.root/'baseline',ledger,'explicit'))

    def test_release_failure_does_not_report_captured_execution_success(self):
        plan=self.apply_plan();original=FakeOwner.__aexit__
        async def failed_close(owner,*args):
            await original(owner,*args)
            owner.release['context_runtime_release_confirmed']=False
            owner.release['errors']=[{'phase':'close','type':'SYNTHETIC'}]
        with patch.object(FakeOwner,'__aexit__',failed_close):
            result,owners,ledger=self.execute_fake(plan)
        self.assertEqual(result['status'],'RELEASE_UNPROVEN_NO_RETRY');self.assertEqual(owners[0].send_calls,1)

    def test_generic_insert_uses_one_send_actor_binding_and_known_receipt(self):
        plan=self.new_plan();after,receipt,actor=self.new_after(plan)
        raw=json.dumps(receipt,ensure_ascii=False).encode()
        result,owners,ledger=self.execute_fake(plan,mode='insert',receipt=raw)
        self.assertEqual(result['status'],'INSERT_RAW_RESPONSE_REQUIRES_INDEPENDENT_FULL_READBACK')
        self.assertEqual(result['runtime_actor_hashes'],actor);self.assertEqual(owners[0].send_calls,1)
        self.assertTrue((ledger/(plan['ledger_key']+'.json')).exists())

    def test_generic_insert_unknown_receipt_still_cannot_retry(self):
        plan=self.new_plan();result,owners,ledger=self.execute_fake(plan,mode='insert',receipt=b'{"code":0,"message":"success","data":{}}')
        self.assertEqual(result['status'],'UNKNOWN_DO_NOT_RETRY')
        self.blocked('STRUCTURE_EXISTING_INTENT_NO_RETRY',lambda:sw.validate_inputs(plan,'insert',self.root/'baseline',ledger,'explicit'))

    def test_policy_rejects_unarmed_wrong_endpoint_changed_body_redirect_and_replay(self):
        plan=self.apply_plan();file=self.root/'plan.json';base.dump(file,plan)
        binding=SimpleNamespace(data={'allowed_get':[]},check=lambda:None)
        def policy():return sw.OnePostPolicy(binding,sw.endpoint_map(plan['before_full']),sw.ORIGIN+s.APPLY,file,file_ref(file)['sha256'])
        for arm,url,body,redirect in [(False,sw.ORIGIN+s.APPLY,'{}',False),(True,sw.ORIGIN+s.PREVIEW,'{}',False),
          (True,sw.ORIGIN+s.APPLY,'{"changed":true}',False),(True,sw.ORIGIN+s.APPLY,'{}',True)]:
            p=policy();p.armed=arm;p.body_sha=sw.sha(b'{}');self.assertFalse(p.allow_post('context','POST',url,body,redirect))
        p=policy();p.armed=True;p.body_sha=sw.sha(b'{}')
        self.assertTrue(p.allow_post('context','POST',p.post,'{}',False));self.assertTrue(p.allow_post('native','POST',p.post,'{}',False))
        self.assertFalse(p.allow_post('context','POST',p.post,'{}',False))


if __name__=='__main__':unittest.main()
