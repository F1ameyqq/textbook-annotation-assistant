"""Offline phase-2 sender boundaries, independent from platform state."""
import asyncio
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from annotation.runtime.usense_live import finalize_writer as m


def fixture():
    old = list(sorted(m.OLD_MAIN_IDS))
    stem='6a1e82cf-d5c8-485d-b2da-7a626a899045'; figure='ace0132c-46d4-402e-ba53-aa8fc99d7484'
    choice='0eed066a-354d-4d6a-9a6d-c9e54c0c8b5f'; answer='e219b027-3b59-4834-8447-dd03c7273a9f'
    ids=[stem,figure,choice,'new-b','new-c','new-d',answer]
    types=['question','question','choice','choice','choice','choice','answer']
    before={'frames':{'data':[{'rect_id':r,'user_id':'old-user'} for r in old+m.RETIRE_IDS+['protected-new-variant']]},
            'q7_info':{'data':{'tilei':None,'tihao':None}}}
    payload={'file_id':'46007447','target_directory_id':m.DIRECTORY,'question_order':7,'is_new_question_insertion':False,
        'insert_after_order':None,'created_by':None,'annotations_upsert':[
            {'rect_id':r,'type':t,'user_id':'old-user' if r in old else None,'order_in_level':'7',
             'directory_id':m.DIRECTORY,'belong_to_level':'question_level','parent_rect_id':None} for r,t in zip(ids,types)],
        'annotations_delete_rect_ids':list(m.RETIRE_IDS),'ocr_delete_zones':[],
        'ocr_submissions':[{'zone':z,'question_order':7} for z in ('question','choice','answer')],
        'question_info':{'tishi':'xuanze','tilei':None,'tihao':None}}
    return payload,before


class PayloadTests(unittest.TestCase):
    def test_exact_main_boundary(self):
        payload,before=fixture(); m.validate_payload_boundary(payload,before)

    def test_full23_168_exact_gets(self):
        result=m.full_endpoints(); self.assertEqual(len(result),168)
        self.assertEqual({k.split('_')[0] for k in result if k.startswith('q')},{f'q{n}' for n in range(1,24)})

    def test_cannot_insert_or_target_variant(self):
        for field,value in [('question_order',8),('is_new_question_insertion',True),('insert_after_order',7),('file_id','other')]:
            payload,before=fixture(); payload[field]=value
            with self.assertRaises(ValueError):m.validate_payload_boundary(payload,before)

    def test_cannot_delete_main_or_variant_new_rect(self):
        for ids in ([*m.RETIRE_IDS,'protected-new-variant'],list(m.OLD_MAIN_IDS)[:2],[]):
            payload,before=fixture(); payload['annotations_delete_rect_ids']=ids
            with self.assertRaises(ValueError):m.validate_payload_boundary(payload,before)

    def test_cannot_replace_old_actor_or_prebind_new_actor(self):
        for index,value in [(0,None),(0,'new-user'),(3,'new-user')]:
            payload,before=fixture(); payload['annotations_upsert'][index]['user_id']=value
            with self.assertRaises(ValueError):m.validate_payload_boundary(payload,before)

    def test_cannot_reuse_protected_variant_id(self):
        payload,before=fixture(); payload['annotations_upsert'][3]['rect_id']='protected-new-variant'
        with self.assertRaises(ValueError):m.validate_payload_boundary(payload,before)

    def test_cannot_move_main_rects_to_other_order_or_directory(self):
        for key,value in [('order_in_level','8'),('directory_id','other'),('parent_rect_id','parent')]:
            payload,before=fixture(); payload['annotations_upsert'][0][key]=value
            with self.assertRaises(ValueError):m.validate_payload_boundary(payload,before)

    def test_cannot_remove_extra_zone_or_change_metadata(self):
        payload,before=fixture(); payload['ocr_delete_zones']=['analysis']
        with self.assertRaises(ValueError):m.validate_payload_boundary(payload,before)
        payload,before=fixture(); payload['question_info']['tilei']='new'
        with self.assertRaises(ValueError):m.validate_payload_boundary(payload,before)


class Binding:
    def check(self):return self


class Decoder:
    def decode_receipt(self,plan,value):
        if value!={'code':0,'data':{'inserted':False,'question_order':7}}:raise ValueError('UNKNOWN_RECEIPT')
        return {'ok':True,'status':'VALID_FINALIZE_RECEIPT'}


class Page:
    def __init__(self,policy,claim,error=None,unknown=False):
        self.policy,self.claim,self.error,self.unknown=policy,claim,error,unknown;self.sent=0
    async def evaluate(self,script,arg):
        if script==m.PREPARE:return {'sha256':m.sha(b'{}'),'created_by_bound':True,'new_row_user_ids_bound':3,
            'preserved_row_user_ids':4,'runtime_actor_sha256':m.sha(b'actor'),'runtime_user_id_sha256':m.sha(b'id')}
        if script!=m.SEND:raise AssertionError('UNEXPECTED_SCRIPT')
        assert self.claim.exists();self.sent+=1
        for layer in ('context','native'):assert self.policy.allow(layer,'POST',m.POST,'{}')
        if self.error:raise self.error
        value={'code':0,'data':{'inserted':False,'question_order':7}}
        if self.unknown:value['unknown_metadata']=True
        return {'status':200,'body_base64':base64.b64encode(json.dumps(value).encode()).decode()}


class SendTests(unittest.IsolatedAsyncioTestCase):
    async def attempt(self,error=None,unknown=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'run';run.mkdir();claim=root/(m.LEDGER_KEY+'.json')
            p=m.InsertPolicy(Binding(),[]); page=Page(p,claim,error,unknown)
            plan={'payload_candidate':{},'before_full':{},'ledger_key':m.LEDGER_KEY,'plan_sha256':'a'*64,
                'predecessor':{'runtime_actor_hashes':{'runtime_actor_sha256':m.sha(b'actor'),'runtime_user_id_sha256':m.sha(b'id')}}}
            result={'post_attempts':0}
            caught=None
            with patch.object(m,'verify_evidence'),patch.object(m,'verify_predecessor_evidence'),patch.object(m,'comparator',return_value=Decoder()):
                try:await m.record_and_send(page=page,policy=p,plan=plan,claim=claim,run=run,result=result)
                except Exception as exc:caught=exc
                self.assertTrue(claim.exists());self.assertEqual(page.sent,1);self.assertTrue(p.sealed);self.assertFalse(p.armed)
                again=Page(m.InsertPolicy(Binding(),[]),claim);plan['plan_sha256']='b'*64
                with self.assertRaises(FileExistsError):await m.record_and_send(page=again,policy=again.policy,plan=plan,claim=claim,run=run,result={})
                self.assertEqual(again.sent,0)
            return result,caught

    async def test_receipt_is_not_final_acceptance(self):
        result,caught=await self.attempt();self.assertIsNone(caught)
        self.assertEqual(result['status'],'FINALIZE_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK')

    async def test_timeout_does_not_retry(self):
        result,caught=await self.attempt(error=asyncio.TimeoutError());self.assertIsInstance(caught,asyncio.TimeoutError)

    async def test_unknown_metadata_does_not_retry(self):
        result,caught=await self.attempt(unknown=True);self.assertIsInstance(caught,ValueError)

    async def test_changed_actor_never_creates_intent_or_sends(self):
        for field in ('runtime_actor_sha256','runtime_user_id_sha256'):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);run=root/'run';run.mkdir();claim=root/(m.LEDGER_KEY+'.json')
                policy=m.InsertPolicy(Binding(),[]);page=Page(policy,claim)
                expected={'runtime_actor_sha256':m.sha(b'actor'),'runtime_user_id_sha256':m.sha(b'id')}
                expected[field]=m.sha(b'different-actor')
                plan={'payload_candidate':{},'predecessor':{'runtime_actor_hashes':expected}}
                result={'post_attempts':0}
                with self.assertRaisesRegex(ValueError,'ACTOR_CHANGED_BEFORE_FINALIZE_SEND'):
                    await m.record_and_send(page=page,policy=policy,plan=plan,claim=claim,run=run,result=result)
                self.assertEqual(page.sent,0)
                self.assertFalse(claim.exists())
                self.assertFalse(policy.armed)
                self.assertEqual(result['post_attempts'],0)


if __name__=='__main__':unittest.main()
