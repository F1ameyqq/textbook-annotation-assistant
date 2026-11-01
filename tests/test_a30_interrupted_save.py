"""New synthetic interrupted-write recovery checks; no platform/model/OS workloads."""
from pathlib import Path
import copy,json,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
import test_a30_customer as f
from annotation.customer.store import Hold,encoded,byte_hash
from annotation.customer.native_plan import make_plan,source_key
from annotation.customer import wire,interrupted_save
from annotation.customer.retained_readback import reconstruct
from annotation.customer.production import reconcile,produce
from annotation.runtime.usense_live.update import text_digest

def dump(path,v,sort=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(json.dumps(v,ensure_ascii=False,sort_keys=sort).encode('utf-8'))

class InterruptedSave(unittest.TestCase):
    image_job=f.ImageAndProduction.image_job
    def setUp(self):
        f.OrdinaryInputs.setUp(self)
        self.job,before=self.image_job();self.q=self.job['candidates'][0]
        self.plan=make_plan(before,self.q,self.job['lesson']);self.key=self.plan['key']
        self.after,self.receipt=f.apply_native(before,self.plan,910)
        flat={'directory':before['directory'],'frames':before['frames'],'source':f.response({'file_id':self.job['book_id']})}
        for page in before['pages'].values():flat['page_'+str(page['viewer_page'])]=f.response({'file_id':self.job['book_id'],'pages':[{'image':page['image_url'],'page_index':page['viewer_page']-1}]})
        refs=[{'path':p['raw_path'],'sha256':p['raw_sha256']} for p in self.job['pages']]
        self.wire=wire.make_wire_plan(self.plan,flat,refs)
        self.folder=self.store.root/'native'/'synthetic-new-run';self.run=self.folder/'writer-original'
        self.wp=self.folder/('write-'+self.key)/'plan.json';dump(self.wp,self.wire)
        self.profile=self.root/'original-profile';self.profile.mkdir();self.settings={'profile':str(self.profile)}
        self.cfg=self.folder/'config-1.json';dump(self.cfg,{'book_id':self.job['book_id'],'run_id':self.run.name,
            'output_root':str(self.folder),'profile':{'directory':str(self.profile)},'authorization_reference':'SYNTHETIC_ORIGINAL'})
        self.writer={'schema':'UsenseActualCustomerInsert/v1','book_id':self.job['book_id'],'run_id':self.run.name,
            'ledger_key':'customer-'+self.key,'plan_sha256':self.wire['plan_sha256'],'plan_file_sha256':byte_hash(self.wp.read_bytes()),
            'config_sha256':byte_hash(self.cfg.read_bytes()),'authorization_reference':'SYNTHETIC_ORIGINAL',
            'post_attempts':1,'http_status':200,'post_layers':{'context':1,'native':1},'native_body_sha256':'a'*64,
            'runtime_actor_hashes':{'runtime_user_id_sha256':text_digest('server-actor')},
            'status':'INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK','send_intent_at':'2026-10-24T08:00:00+08:00',
            'finished_at':'2026-10-24T08:00:01+08:00','release':{'context_runtime_release_confirmed':True}}
        dump(self.run/'native-receipt.json',self.receipt);self.writer['receipt_sha256']=byte_hash((self.run/'native-receipt.json').read_bytes())
        self.pp=self.folder/'writer-unique.process.json';self.stdout=self.folder/'writer-unique.stdout'
        self.proc={'argv':['python.exe','-I','-B','run_usense_live.py','--insert-writer','--config',str(self.cfg),'--sha256',byte_hash(self.cfg.read_bytes()),
            '--plan',str(self.wp),'--plan-sha256',byte_hash(self.wp.read_bytes()),'--baseline',str(self.wp.parent/'baseline'),
            '--ledger-root',str(self.profile.parent/'usense-existing-ledger'),'--authorization-reference','SYNTHETIC_ORIGINAL'],
            'owned_os_release_confirmed':True,'exit_code':0,'job_active_processes_after':0,'errors':[],
            'observed_processes':[{'pid':777,'exit_signaled':True,'handle_closed':True}],
            'started_at':'2026-10-24T07:59:59+08:00','finished_at':'2026-10-24T08:00:02+08:00'}
        self.publish_writer()
        _,head=self.store.job(self.job['id']);self.q['pending_plan_ref']=self.store.put(self.plan)
        self.q['platform_status']='INTENT_UNKNOWN_UNTIL_READBACK';self.job['platform_status']='RUNNING'
        self.store.begin('save:'+self.job['book_id'],self.key);self.store.save_job(self.job,head,'SAVE_INTENT')

    def publish_writer(self):
        dump(self.stdout,self.writer);dump(self.run/'execution-result.json',self.writer,sort=True)
        send={**self.writer,'status':'SEND_INTENT_RECORDED'};dump(self.run/'send-intent.json',send,sort=True)
        self.proc['stdout']={'bytes':self.stdout.stat().st_size,'sha256':byte_hash(self.stdout.read_bytes())};dump(self.pp,self.proc)

    def recovered(self):return interrupted_save.recover(self.store,self.job,self.plan,self.q,self.settings)

    def partial(self):
        cp=self.folder/'config-2.json';run=self.folder/'reader-first';rp=self.folder/'read-first.process.json'
        config={'operation':'READONLY_CAPTURE','book_id':self.job['book_id'],'output_root':str(self.folder),'run_id':run.name,'authorization_reference':'SYNTHETIC_ORIGINAL'}
        dump(cp,config);captures={}
        for name,v in {'directory':self.after['directory'],'frames':self.after['frames'],'source':f.response({'file_id':self.job['book_id']})}.items():
            p=run/(name+'.json');dump(p,v);captures[name]={'filename':p.name,'sha256':byte_hash(p.read_bytes()),'bytes':p.stat().st_size,
                'status':200,'request_counts':{'context':1,'native':1},'observed_at':'2026-10-24T08:00:04+08:00'}
        summary={'book_id':self.job['book_id'],'run_id':run.name,'config_sha256':byte_hash(cp.read_bytes()),'status':'NATIVE_GETS_CAPTURED',
            'save_attempts':0,'release':{'context_runtime_release_confirmed':True},'captures':captures}
        stdout=self.folder/'read-first.stdout'
        dump(run/'capture-summary.json',summary);dump(stdout,summary)
        record={'argv':['python.exe','-I','-B','run_usense_live.py','capture','--config',str(cp),'--sha256',byte_hash(cp.read_bytes())],
            'owned_os_release_confirmed':True,'exit_code':0,'started_at':'2026-10-24T08:00:03+08:00','finished_at':'2026-10-24T08:00:05+08:00',
            'stdout':{'sha256':byte_hash(stdout.read_bytes()),'bytes':stdout.stat().st_size}}
        dump(rp,record)

    def test_local_receipt_recovery_does_not_mark_success_or_touch_ledger(self):
        before=self.store.operation('save:'+self.job['book_id'],self.key);u=self.recovered()
        self.assertEqual(before,self.store.operation('save:'+self.job['book_id'],self.key));self.assertEqual(before,{'state':'INTENT','output':None})
        self.assertTrue(u['interrupted_receipt_recovered']);self.assertEqual(u['new_save_attempts'],0)

    def test_duplicate_writer_binding_holds(self):
        dump(self.folder/'writer-duplicate.process.json',self.proc)
        with self.assertRaises(Hold):self.recovered()

    def test_changed_receipt_holds_before_new_capture(self):
        (self.run/'native-receipt.json').write_bytes(b'{}')
        with self.assertRaises(Hold):self.recovered()

    def test_writer_release_false_holds(self):
        self.proc['owned_os_release_confirmed']=False;dump(self.pp,self.proc)
        with self.assertRaises(Hold):self.recovered()

    def test_profile_replacement_holds(self):
        self.settings['profile']=str(self.root/'different-profile')
        with self.assertRaises(Hold):self.recovered()

    def test_unbound_stdout_change_holds(self):
        self.stdout.write_bytes(self.stdout.read_bytes()+b' ')
        with self.assertRaises(Hold):self.recovered()

    def test_changed_current_candidate_holds(self):
        self.q['zones']['answer']='different'
        with self.assertRaises(Hold):self.recovered()

    def test_envelope_order_is_ignored_but_types_and_array_order_are_not(self):
        self.assertTrue(interrupted_save._envelope_same({'a':1,'b':[1,2]},{'b':[1,2],'a':1}))
        self.assertFalse(interrupted_save._envelope_same({'a':1},{'a':True}))
        self.assertFalse(interrupted_save._envelope_same({'a':[1,2]},{'a':[2,1]}))

    def test_original_partial_prefix_requires_new_full_read_not_acceptance(self):
        self.partial();u=self.recovered();self.assertIsNone(reconstruct(self.store,self.job,self.plan,u))
        self.assertEqual(len(u['processes']),2)
        u['interrupted_receipt_recovered']=False
        with self.assertRaises(Hold):reconstruct(self.store,self.job,self.plan,u)

    def test_corrupt_partial_response_does_not_fall_back_to_new_read(self):
        self.partial();u=self.recovered();(self.folder/'reader-first/directory.json').write_bytes(b'{}')
        with self.assertRaises(Hold):reconstruct(self.store,self.job,self.plan,u)

    def test_ordinary_reconcile_preserves_intent_history_and_never_writes(self):
        owner=self
        class Reader:
            processes=[];reads=0;writes=0
            def capture(self,*args,**kwargs):self.reads+=1;return owner.after,{}
            def write_once(self,*args):self.writes+=1;raise AssertionError('no resend')
        reader=Reader();reconcile(self.store,self.job['id'],self.settings,transport_factory=lambda *a:reader)
        op=self.store.operation('save:'+self.job['book_id'],self.key);self.assertEqual(op['state'],'COMPLETE')
        receipt=self.store.get(op['output']);previous=self.store.get(receipt['previous_output'])
        self.assertEqual(previous['original_operation'],{'state':'INTENT','output':None})
        self.assertEqual((reader.reads,reader.writes),(1,0))
        with self.assertRaises(Hold):reconcile(self.store,self.job['id'],self.settings,transport_factory=lambda *a:reader)
        self.assertEqual(reader.reads,1)

    def test_failed_reconcile_does_not_retry_or_unblock_production(self):
        class Reader:
            processes=[];reads=0
            def capture(self,*args,**kwargs):self.reads+=1;raise TimeoutError('synthetic fresh read failure')
        reader=Reader()
        with self.assertRaises(TimeoutError):reconcile(self.store,self.job['id'],self.settings,transport_factory=lambda *a:reader)
        with self.assertRaises(Hold):reconcile(self.store,self.job['id'],self.settings,transport_factory=lambda *a:reader)
        with self.assertRaises(Hold):produce(self.store,self.job['id'],{},transport_factory=lambda *a:(_ for _ in ()).throw(AssertionError('must not acquire')))
        self.assertEqual(reader.reads,1)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
