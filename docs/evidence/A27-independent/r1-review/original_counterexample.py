import copy, hashlib, importlib.util, itertools, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

PRIVATE=Path('D:/1800/.local/stages/a27-independent-20261023')
PRODUCT=PRIVATE/'candidate-ebca4c71/product'
DELIVERY=PRIVATE/'candidate-ebca4c71/delivery'
OUTPUT=Path(os.environ['A27_OUTPUT'])
sys.path[:0]=[str(PRODUCT/'src'),str(PRODUCT/'tools')]
spec=importlib.util.spec_from_file_location('a27_frozen_fixture',PRODUCT/'tests/test_a27_stability.py')
fixture=importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
update,postsave,recovery=fixture.update,fixture.postsave,fixture.recovery
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=fixture.raw

def audit(event,args):
    if event in ('socket.connect','socket.getaddrinfo'):
        raise RuntimeError('INDEPENDENT_NETWORK_FORBIDDEN')
    if event=='subprocess.Popen' and Path(str(args[0])).resolve()!=Path(sys.executable).resolve():
        raise RuntimeError('INDEPENDENT_NON_PYTHON_PROCESS_FORBIDDEN')
sys.addaudithook(audit)

def bundle_at(name):
    root=OUTPUT/name; root.mkdir()
    b=fixture.SyntheticBundle(root)
    b.calls=[]; b.after_configure=None; b.fail_reader=False
    return b

class IndependentControls(unittest.TestCase):
    def test_01_key_permutations_types_and_untouched_objects(self):
        plan,after=fixture.order_fixture.A25CreatedZoneReconciliationTests().example()
        original=(update.digest(plan),update.digest(after))
        accepted=[]
        for keys in itertools.permutations(('rect_ids','ocr_result','success')):
            trial=copy.deepcopy(after)
            for zone in ('question','answer'):
                data=trial['zones'][zone]['data']
                trial['zones'][zone]['data']={key:data[key] for key in keys}
            matched=update.compare_batch_readback(plan,trial)['match']
            self.assertEqual(matched,keys in (('rect_ids','ocr_result','success'),('success','ocr_result','rect_ids')))
            if matched: accepted.append(keys)
        mutations=[
            lambda x:x['zones']['question']['data'].update(ocr_result=None),
            lambda x:x['zones']['answer']['data'].update(success=1.0),
            lambda x:x['zones']['question']['data'].pop('success'),
            lambda x:x['zones']['answer']['data'].update(unexpected=False),
            lambda x:x['zones']['question']['data']['rect_ids'].append('unplanned'),
            lambda x:x.update(frames=dict(reversed(list(x['frames'].items())))),
        ]
        for mutate in mutations:
            trial=copy.deepcopy(after); mutate(trial)
            self.assertFalse(update.compare_batch_readback(plan,trial)['match'])
        self.assertEqual((update.digest(plan),update.digest(after)),original)
        print(json.dumps({'control':'I01','permutations':6,'extra_rejections':len(mutations),'allowed_orders':accepted}))

    def test_02_original_q3_q4_replay_from_local_fixed_copies_only(self):
        items=json.loads((DELIVERY/'private-inputs.json').read_bytes())
        used=set()
        def get(suffix):
            matches=[r for r in items if r['original'].replace('\\','/').endswith(suffix)]
            self.assertEqual(len(matches),1,suffix)
            item=matches[0]; path=DELIVERY/'private-inputs'/Path(item['a27_copy']).name
            data=path.read_bytes()
            self.assertEqual((len(data),sha(data)),(item['bytes'],item['sha256']))
            used.add(str(path)); return data
        qdir='remaining-two-live/target-112796c22ae27340da45824a/'
        wdir='remaining-two-live/usense-readonly-20261023-114833-b92e3c68/'
        writer={k:get(s) for k,s in {'plan':qdir+'plan.json','execution':wdir+'execution-result.json',
            'writer_config':qdir+'writer-config.json','writer_process':qdir+'writer-process-result.json',
            'writer_stdout':qdir+'writer-process-result.stdout','writer_stderr':qdir+'writer-process-result.stderr',
            'receipt':wdir+'native-receipt.json','intent':'usense-existing-07d8c7023207b8d0892e1720b9bab58dd755cd4160b88739903fea52d3abdd08.json',
            'send_intent':wdir+'send-intent.json','writer_events':wdir+'network-events.json','holder':'remaining-two-outer/batch-01.process.json'}.items()}
        before_names=[Path(r['original']).name[7:-5] for r in items if '/before-' in r['original'].replace('\\','/')]
        writer['before']={name:get(wdir+'before-'+name+'.json') for name in before_names}
        old=postsave.verify_writer(writer)
        prefix='final-recovery-live/'; rdir=prefix+'usense-readonly-20261023-120852-7bec089b/'
        reader={k:get(s) for k,s in {'summary':rdir+'capture-summary.json','config':prefix+'q4-independent-reader-config.json',
            'process':prefix+'q4-reader-process-result.json','stdout':prefix+'q4-reader-process-result.stdout',
            'stderr':prefix+'q4-reader-process-result.stderr','events':rdir+'network-events.json'}.items()}
        reader['captures']={name:get(rdir+name+'.json') for name in old['names']}
        result=postsave.verify_reader(old,reader)
        self.assertFalse(result['original_framework_release']['context_runtime_release_confirmed'])
        self.assertEqual(result['status'],'READBACK_MATCHED_AFTER_OS_RELEASE')
        plan=update.loads(get('five-save-live/target-9cd38aa4c3644dfab65d7533/plan.json'))
        prefix='five-save-live/usense-readonly-20261023-111827-7c84da4f/'
        native={n:update.loads(get(prefix+n+'.json')) for n in ['directory','frames','q20_annotations','q20_info',
            'q20_question','q20_choice','q20_answer','q20_analysis','q20_knowledge_point']}
        after=update.from_captured_map(native,'q20_')
        self.assertFalse(update.compare_readback(plan,after)['match'])
        limited=update.compare_batch_readback(plan,after)
        self.assertTrue(limited['match']); self.assertFalse(limited['revision_predecessor_eligible'])
        self.assertEqual(len(used),51)
        print(json.dumps({'control':'I02','verified_copies':len(used),'q3_strict':False,'q3_limited':True,'q4_framework':False,'q4_replay_matched':True}))

    def test_03_cli_writer_dispatch_exits_after_stubborn_close(self):
        # Real CLI dispatch -> writer.main -> run_owned_writer; only execute's
        # browser-dependent body is substituted with a synthetic cleanup case.
        code='''import asyncio,json,sys
from types import SimpleNamespace
sys.path[:0]=[sys.argv[1],sys.argv[2]]
from annotation.runtime.usense_live import writer,release
import run_usense_live
async def stuck():
 try: await asyncio.Future()
 except asyncio.CancelledError: await asyncio.Future()
async def done(): pass
async def fake(**kwargs):
 r=await release.close_framework(SimpleNamespace(close=stuck),SimpleNamespace(stop=done),set(),close_seconds=.01,stop_seconds=.01)
 return dict(status='RELEASE_UNPROVEN_NO_RETRY',business_status_before_release='RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK',post_attempts=1,release=r)
writer.execute=fake
args=['--writer']
for name in ('config','sha256','plan','plan-sha256','baseline','ledger-root','authorization-reference'):args.extend(['--'+name,'synthetic'])
raise SystemExit(run_usense_live.main(args))
'''
        p=subprocess.run([sys.executable,'-I','-B','-c',code,str(PRODUCT/'src'),str(PRODUCT/'tools')],executable=sys.executable,capture_output=True,timeout=3)
        (OUTPUT/'I03.stdout').write_bytes(p.stdout); (OUTPUT/'I03.stderr').write_bytes(p.stderr)
        result=json.loads(p.stdout)
        self.assertEqual(p.returncode,2)
        self.assertFalse(result['release']['context_closed'])
        self.assertTrue(result['release']['runtime_stopped'])
        self.assertEqual(result['release']['os_process_release'],'REQUIRES_OUTER_HOLDER')
        self.assertEqual(result['post_attempts'],1)
        print(json.dumps({'control':'I03','exit_code':p.returncode,'stdout_sha256':sha(p.stdout),'stderr_sha256':sha(p.stderr)}))

    def test_04_unknown_or_wrong_writer_stops_before_resources(self):
        for label,key,mutate in [
            ('receipt','receipt',lambda x:x['data'].update(question_order=4)),
            ('intent','intent',lambda x:x.update(intent_key='wrong-stable-intent')),
            ('held_resource','holder',lambda x:x['observed_processes'][0].update(exit_signaled=False)),
        ]:
            b=bundle_at('I04-'+label); value=update.loads(b.raw[key]); mutate(value); b.raw[key]=raw(value)
            args=b.request(); observer=Mock(side_effect=AssertionError('UNQUALIFIED_OBSERVER_CALLED'))
            with self.assertRaises(ValueError): recovery.execute(*args,run_child=b.child,observe=observer)
            observer.assert_not_called(); self.assertEqual(b.calls,[])
        print(json.dumps({'control':'I04','rejections_before_resources':3}))

    def test_05_second_profile_check_blocks_before_reader(self):
        b=bundle_at('I05'); args=b.request()
        observer=Mock(side_effect=[{'synthetic':'first-empty'},fixture.BindingError('RECOVERY_PROFILE_IN_USE')])
        result=recovery.execute(*args,run_child=b.child,observe=observer)
        self.assertEqual(result['status'],'STOPPED_NO_RETRY')
        self.assertEqual(result['error_code'],'RECOVERY_PROFILE_IN_USE')
        self.assertEqual(b.calls,['configure'])
        self.assertEqual(len(list(b.root.glob('*.spent.json'))),1)
        self.assertEqual(list(b.ledger.glob('*.accepted.json')),[])
        print(json.dumps({'control':'I05','calls':b.calls,'posts':0,'spent_markers':1}))

    def test_06_recovery_sidecar_cannot_be_standard_revision(self):
        b=bundle_at('I06'); old=postsave.verify_writer(b.raw)
        recovered=postsave.verify_reader(old,b.reader())
        qdir=b.root/'previous-target'; qdir.mkdir()
        (qdir/'plan.json').write_bytes(b.raw['plan'])
        path=qdir/'acceptance.json'; path.write_bytes(raw(recovered))
        with self.assertRaisesRegex(ValueError,'PREVIOUS_ACCEPTANCE_NOT_SUCCESS'):
            fixture.verify_previous_acceptance(path,b.plan,{},b.ledger)
        self.assertEqual(b.intent.read_bytes(),b.raw['intent'])
        print(json.dumps({'control':'I06','sidecar_rejected_as_revision':True,'intent_unchanged':True}))

    def test_07_equivalent_profile_path_must_stop_real_recovery_entry(self):
        b=bundle_at('I07-profile-alias'); args=b.request()
        alias=str(b.profile.parent)+'\\.\\'+b.profile.name
        self.assertTrue(Path(alias).samefile(b.profile))
        row={'ProcessId':303,'CreationDate':'2026-10-23T13:00:00Z',
             'CommandLine':'msedge.exe --user-data-dir="'+alias+'"'}
        os_query=Mock(return_value=SimpleNamespace(returncode=0,stdout=raw([row])))
        observations=[]
        def observer(profile):
            value=recovery.exclusive_profile(profile,run=os_query)
            observations.append(value); return value
        error=None; result=None
        try:
            result=recovery.execute(*args,run_child=b.child,observe=observer)
        except ValueError as exc:
            error=str(exc)
        witness={'schema':'A27IndependentProfileAliasWitness/v1','synthetic_only':True,
                 'profile':str(b.profile),'alias':alias,'same_directory_by_os_samefile':True,
                 'os_observer_rows':[row],'observations':observations,'dispatched_commands':b.calls,
                 'result':result,'raised':error,'real_browser_or_platform_calls':0,
                 'intent_unchanged':b.intent.read_bytes()==b.raw['intent']}
        (OUTPUT/'profile-alias-witness.json').write_bytes(raw(witness)+b'\n')
        print(json.dumps({k:witness[k] for k in ('synthetic_only','same_directory_by_os_samefile','dispatched_commands','raised','real_browser_or_platform_calls')}))
        self.assertEqual(b.calls,[], 'Equivalent occupied profile must be rejected before configure/capture; literal substring missed dot-segment alias')
        self.assertIsNotNone(error)

if __name__=='__main__': unittest.main(verbosity=2,failfast=True)
