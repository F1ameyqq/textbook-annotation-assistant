"""New finite reconciliation boundary only; no old test suite or live resources."""
import ast,copy,hashlib,importlib.util,io,json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/created-zone-reconciliation-review-20261023')
OLD=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
ACT=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-actual-review-20261023')
AP=Path('D:/1800/docs/evidence/A25-independent/five-save-actual-review')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 with p.open('xb') as f:f.write(b)
def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def main():
 def audit(event,args):
  if event in ('socket.connect','socket.getaddrinfo','socket.bind','subprocess.Popen'):raise RuntimeError('INDEPENDENT_OFFLINE_NO_NETWORK_OR_CHILD')
 sys.addaudithook(audit)
 registry=json.loads((S/'registry.json').read_bytes());areg=json.loads((ACT/'registry.json').read_bytes());used={}
 def local(suffix):return Path(next(v for k,v in registry.items() if k.endswith(suffix)))
 def read(suffix):return json.loads(local(suffix).read_bytes())
 # Bind prior completed deep review, rather than rerun its accepted actual audit.
 for name,expected in [('raw-manifest.json','04e370fcd532abb1aa812282074524bf3005fd4c674eb35cb07854620ed11bc2'),('result.json','d4e226f886cf23063f73258f7178778746cf48a22fa8e13af92a6c89e4a8e65b')]:
  p=AP/name;assert sha(p.read_bytes())==expected;used[str(p)]=expected
 frozen_actual_overlap=0
 for k,v in registry.items():
  if k in areg:
   prior=Path(areg[k]);assert Path(v).read_bytes()==prior.read_bytes();used[str(prior)]=sha(prior.read_bytes());frozen_actual_overlap+=1
 newfile=S/'snapshot/src/annotation/runtime/usense_live/update.py';oldfile=OLD/'snapshot/src/annotation/runtime/usense_live/update.py'
 def functions(p):return {n.name:n for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
 old=functions(oldfile);new=functions(newfile);unchanged=[]
 for name,node in old.items():
  if name!='_compare_validated_readback':assert ast.dump(node,include_attributes=False)==ast.dump(new[name],include_attributes=False);unchanged.append(name)
 assert set(new)-set(old)=={'reconcile_first_created_zone_key_order'}
 # Default strict comparator changes only its internal optional expected copy.
 oldhelper=copy.deepcopy(old['_compare_validated_readback']);newhelper=copy.deepcopy(new['_compare_validated_readback'])
 newhelper.args=oldhelper.args;newhelper.body[1]=oldhelper.body[1]
 assert ast.dump(newhelper,include_attributes=False)==ast.dump(oldhelper,include_attributes=False)
 for file in (S/'snapshot/src/annotation/runtime/usense_live').glob('*.py'):
  if file.name!='update.py':assert file.read_bytes()==(OLD/'snapshot/src/annotation/runtime/usense_live'/file.name).read_bytes()
 assert (S/'snapshot/tools/run_usense_reviewed_batch.py').read_bytes()==(OLD/'snapshot/tools/run_usense_reviewed_batch.py').read_bytes()
 runtime=[{'path':p.name,'sha256':sha(p.read_bytes())} for p in sorted((S/'snapshot/src/annotation/runtime/usense_live').glob('*.py'))]
 implementation=sha(json.dumps(runtime,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode());assert implementation=='1c222acdb9d442546cbcff99cde98031fa5ecb7646cc135bb1f30dc9a09cad17'
 module=load_module('independent_new_created_zone_tests',S/'snapshot/tests/test_a25_created_zone_reconciliation.py');stream=io.StringIO()
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.A25CreatedZoneReconciliationTests)
 tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);put(S/'new-three-tests.log',stream.getvalue().encode('utf-8'))
 assert tests.testsRun==3 and tests.wasSuccessful()
 update=module.update
 plan=update.loads(local('/five-save-live/target-9cd38aa4c3644dfab65d7533/plan.json').read_bytes())
 run='/five-save-live/usense-readonly-20261023-111827-7c84da4f'
 captured={name:update.loads(local(run+'/'+name+'.json').read_bytes()) for name in ['directory','frames','source','q20_annotations','q20_info','q20_question','q20_choice','q20_answer','q20_analysis','q20_knowledge_point','page_12','page_173']}
 after=update.from_captured_map(captured,'q20_');plan_before=update.digest(plan);after_before=update.digest(after)
 actual=update.reconcile_first_created_zone_key_order(plan,after);author=read('/created-zone-reconciliation/third-reconciliation.json')['limited_reconciliation']
 assert update.json_same(actual,author) and actual['match'] is True and actual['strict_comparison']['match'] is False
 assert update.compare_readback(plan,after)['match'] is False
 assert update.digest(plan)==plan_before and update.digest(after)==after_before==actual['original_after_sha256']
 # Minimal extra reviewer controls target the exact real boundary, not old suites.
 controls=[]
 def refused(name,mutate):
  changed=copy.deepcopy(after);mutate(changed);got=update.reconcile_first_created_zone_key_order(plan,changed);assert got['match'] is False;controls.append({'name':name,'result':'REJECTED'})
 refused('real_rect_array_reversal',lambda a:a['zones']['question']['data']['rect_ids'].reverse())
 refused('real_success_bool_to_int',lambda a:a['zones']['answer']['data'].update(success=1))
 refused('real_unrelated_unknown_field',lambda a:a['info']['data'].update(review_unknown_field=False))
 refused('real_different_new_zone_key_permutation',lambda a:a['zones']['question'].update(data={k:a['zones']['question']['data'][k] for k in ['ocr_result','success','rect_ids']}))
 badplan=copy.deepcopy(plan);badplan['before']['zones']['question']['data']=dict(reversed(list(badplan['before']['zones']['question']['data'].items())))
 try:update.reconcile_first_created_zone_key_order(badplan,after);raise AssertionError('malformed absence accepted')
 except update.UpdateError as exc:assert exc.code=='OCR_ABSENCE_NOT_PROVEN';controls.append({'name':'malformed_before_absence_order','result':'REJECTED','error':exc.code})
 assert actual['ledger_accepted_by_this_function'] is actual['new_send_authorized'] is False
 # Exact remaining two are an unchanged subset; no old five-plan suite replay.
 remaining=read('/created-zone-reconciliation/remaining-two/targets.json');oldtargets=json.loads((OLD/'project/post-manual-login-source/five-candidates-v2/targets.json').read_bytes())
 assert update.json_same(remaining['targets'],oldtargets['targets'][3:]) and update.json_same(remaining['baseline'],oldtargets['baseline'])
 assert sha(local('/created-zone-reconciliation/remaining-two/targets.json').read_bytes())=='769ea9b78906f689776613942799581966a9a0e690e62cc1af8e43117988f6c7'
 planrefs=read('/created-zone-reconciliation/remaining-two/save-readback-plan.json')['plans'];ledger_keys=[]
 for i,row in zip([4,5],planrefs):
  original=OLD/f'project/post-manual-login-source/five-plan-validation/printed-{i}-materialized-plan.json';assert local(f'/created-zone-reconciliation/remaining-two/printed-{i}-plan.json').read_bytes()==original.read_bytes();used[str(original)]=sha(original.read_bytes())
  assert row['printed_question']==i and row['previous_acceptance'] is None and row['existing_same_identity_ledger_files']==0
  candidate=Path(json.loads((OLD/'registry.json').read_bytes())[row['candidate']['path'].replace('\\','/').lower()]);assert sha(candidate.read_bytes())==row['candidate']['sha256'];used[str(candidate)]=sha(candidate.read_bytes())
  ledger_keys.append(update.loads(original.read_bytes())['ledger_key'])
 assert all(not any('/usense-existing-ledger/'+key in k for k in registry) for key in ledger_keys)
 # Every original ledger and authority copy remains the exact original actual byte.
 cp=read('/checkpoint-created-zone-reconciliation.json');ledger=cp['ledger_original_file_sha256'];assert len(ledger)==5
 for original,digest in ledger.items():
  key=original.replace('\\','/').lower();assert sha(Path(registry[key]).read_bytes())==digest and Path(registry[key]).read_bytes()==Path(areg[key]).read_bytes()
 assert update.digest(plan)==plan_before and update.digest(after)==after_before
 result={'schema':'A25IndependentCreatedZoneControls/v1','status':'PASS_OFFLINE_ONLY','new_author_tests':3,'author_negative_cases_within_three_tests':16,'independent_extra_rejections':controls,'actual_third_new_pure_reconciliation':'MATCH','actual_third_strict_result':'FAIL_RETAINED','actual_after_sha256_unchanged':after_before,'plan_sha256_unchanged':plan_before,'original_actual_overlap_exact_members':frozen_actual_overlap,'unchanged_existing_update_functions':unchanged,'other_runtime_writer_revision_core_and_runner_bytes_unchanged':True,'implementation_sha256':implementation,'remaining_targets_exact_previous_subset':[4,5],'remaining_plans_exact_previously_validated_materialized_bytes':True,'previous_acceptance_for_both':None,'five_old_ledger_bytes_unchanged':ledger,'third_future_write_gate':'Unchanged writer rejects existing intent; unchanged revision requires original ACCEPTED + all checks true + accepted ledger and strict predecessor. Reconciliation sidecar is not such evidence.','receipt_and_fresh_reader_provenance':'Reused previously completed fixed actual independent result d4e226f8; exact overlapping raw bytes checked. No platform replay.','network_browser_save_children_inside_controls':0,'real_ledger_profile_touched':False,'old_suites_rerun':False,'reused_files':used}
 put(P/'controls-result.json',enc(result));put(S/'actual-new-pure-result.json',enc(actual));print(json.dumps({'status':result['status'],'new_tests':3,'extra_rejections':len(controls),'third_reconciled':True,'remaining_two_unchanged':True}))
if __name__=='__main__':main()
