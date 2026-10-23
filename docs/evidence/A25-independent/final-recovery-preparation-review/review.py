# -*- coding: utf-8 -*-
"""Static preflight only; never import or execute the recovery runner/product."""
import ast,datetime,hashlib,json
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/final-recovery-preparation-review-20261023')
OLD=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
ACT=Path('D:/1800/.local/stages/a25-independent-20261023/remaining-two-actual-review-20261023')
PRODUCT=Path('D:/1800/.local/stages/a25-independent-20261023/created-zone-reconciliation-review-20261023/snapshot')
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(p):return PureWindowsPath(str(p)).as_posix().lower()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 with p.open('xb') as f:f.write(b)
def entry(p,kind):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'kind':kind}
def strict(a,b):
 if type(a)!=type(b):return False
 if isinstance(a,dict):return list(a)==list(b) and all(strict(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(strict(x,y) for x,y in zip(a,b))
 return a==b
def main():
 reg=json.loads((S/'registry.json').read_bytes());areg=json.loads((ACT/'registry.json').read_bytes());used={}
 def local(suffix):return Path(next(v for k,v in reg.items() if k.endswith(suffix.lower())))
 def read(suffix):return json.loads(local(suffix).read_bytes())
 def reuse(p,digest=None):
  b=p.read_bytes()
  if digest:assert sha(b)==digest
  used[str(p)]=entry(p,'prior_fixed_accepted_dependency');return b
 prior=Path('D:/1800/docs/evidence/A25-independent/remaining-two-actual-review/result.json');reuse(prior,'d74a0705832d8fda580fa9c90707e813517689316c38f5379864aec72e516db5')
 overlap=0
 for k,v in reg.items():
  if k in areg:assert Path(v).read_bytes()==reuse(Path(areg[k]));overlap+=1
 plan=read('/final-recovery-preparation/recovery-plan.json');binding=read('/final-recovery-preparation/binding.json');template=read('/authority-fields.not-activated.json')
 assert template['status']=='NOT_ACTIVATED_TEMPLATE_NOT_AUTHORITY' and plan['status']=='FIXED_PLAN_NOT_ACTIVATED'
 assert template['recovery_plan_sha256']==binding['plan_sha256']=='cd89a2990fbaadf395185a757db9e8848f5821e9dd7cdbc7ccb35b59d83dbc77'
 assert template['limits']==plan['limits_to_bind'] and template['readonly_native_order']==21 and template['write_native_order']==22
 assert template['ledger_snapshot']==plan['ledger_snapshot'] and len(plan['ledger_snapshot'])==6
 for original,digest in plan['ledger_snapshot'].items():assert sha(Path(reg[norm(original)]).read_bytes())==digest
 refs=[]
 for key,value in plan.items():
  if isinstance(value,dict) and set(value)=={'path','sha256'}:
   b=Path(reg[norm(value['path'])]).read_bytes();assert sha(b)==value['sha256'];refs.append(key)
 assert len(refs)==11
 original=read('/remaining-two-live/target-112796c22ae27340da45824a/plan.json');writer=read('/writer-process-result.json');execution=read('/execution-result.json');receipt=read('/native-receipt.json');holder=read('/batch-01.process.json')
 expected_receipt={'code':0,'message':'success','data':{'inserted':False,'question_order':21,'inserted_question_node':None,'success':True,'append_at_global_end':False}}
 assert strict(receipt,expected_receipt) and execution==writer['result'] and execution['release']['context_runtime_release_confirmed'] is False
 assert execution['status']=='RELEASE_UNPROVEN_NO_RETRY' and holder['owned_os_release_confirmed'] is True and holder['job_active_processes_after']==0
 assert len(holder['observed_processes'])==23 and original['target']['question_order']==21
 last=read('/final-recovery-preparation/last-question-target.json');oldtargets=json.loads(reuse(OLD/'project/post-manual-login-source/five-candidates-v2/targets.json'))
 assert strict(last['targets'],oldtargets['targets'][4:]) and strict(last['baseline'],oldtargets['baseline']) and len(last['targets'])==1 and last['targets'][0]['previous_acceptance'] is None
 assert local('/final-recovery-preparation/last-question-plan.json').read_bytes()==reuse(OLD/'project/post-manual-login-source/five-plan-validation/printed-5-materialized-plan.json')
 assert local('/five-candidates-v2/printed-5-candidate.json').read_bytes()==reuse(OLD/'project/post-manual-login-source/five-candidates-v2/printed-5-candidate.json')
 fifth=read('/final-recovery-preparation/last-question-plan.json');assert fifth['target']['question_order']==22 and not any(fifth['ledger_key'] in k for k in reg if '/usense-existing-ledger/' in k)
 runtime=[{'path':p.name,'sha256':sha(reuse(p))} for p in sorted((PRODUCT/'src/annotation/runtime/usense_live').glob('*.py'))]
 assert sha(json.dumps(runtime,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode())==plan['implementation_sha256']=='1c222acdb9d442546cbcff99cde98031fa5ecb7646cc135bb1f30dc9a09cad17'
 runner=local('/run-final-recovery.py');launcher=local('/launch-final-recovery-once.py');rt=runner.read_text(encoding='utf-8');lt=launcher.read_text(encoding='utf-8');ast.parse(rt);ast.parse(lt)
 assert sha(runner.read_bytes())==template['recovery_runner_sha256']==binding['runner_sha256']=='b20ceea1a1a92b50977c0aef7291eaf0222e81ec2a0547dfeac3df6e2a6a8f00'
 assert sha(launcher.read_bytes())==template['outer_launcher_sha256']==binding['launcher_sha256']=='b761d6f102217b8ce23c32f23f4daed88f79335517820928f48ea08966c6b117'
 assert lt.index('os.replace(temporary, authority_path)')<lt.index('result = holder.run(')
 assert rt.index("require(all(checks.values()), 'Q4_LATER_READBACK_NOT_MATCHED')")<rt.index("'LEDGER_CHANGED_DURING_Q4_READ'")<rt.index('prepared = batch.prepare(')<rt.index('last = entry.execute(')
 assert "entry.child(['capture'" in rt and "'--orders', 21, '--pages', 12, 173, '--source'" in rt
 assert 'update.compare_readback(original' in rt and 'reconcile_first_created' not in rt
 assert 'actual_ledger == expected_ledger == original_ledger' in lt and "all(p.is_file() and p.suffix == '.json' for p in ledger.iterdir())" in lt
 assert "'OLD_Q4_EXACT_RECEIPT_UNPROVEN'" in rt and "'OLD_WHOLE_BATCH_OS_RELEASE_UNPROVEN'" in rt and "'KEEP_ORIGINAL_FRAMEWORK_RELEASE_FAILURE'" in rt
 assert "'Q4_LATER_READ_TIME_UNPROVEN'" in rt and "'Q4_LATER_READER_NOT_COMPLETE_RELEASED'" in rt
 assert "new_accepted_marker_created': False" in rt and "revision_predecessor_claim': False" in rt
 assert "a1582782024994d841ddeadc0e2df6c8ef29a35bc8e428dcb4dd8b8cdc589ee8" in lt
 process=read('/final-recovery-preparation/describe-only.process.json');assert process['exit_code']==0
 assert process['stdout_sha256']==sha(local('/final-recovery-preparation/describe-only.stdout').read_bytes()) and process['stderr_sha256']==sha(local('/final-recovery-preparation/describe-only.stderr').read_bytes())
 line_map={}
 for name,text,markers in [('runner',rt,["rp = entry.child(['capture'",'comparison = update.compare_readback',"require(all(checks.values())",'prepared = batch.prepare','last = entry.execute']),('outer',lt,['def verify_fixed','actual_ledger == expected_ledger','os.replace(temporary, authority_path)','result = holder.run('])]:
  line_map[name]={m:next(i+1 for i,l in enumerate(text.splitlines()) if m in l) for m in markers}
 result={'schema':'A25IndependentFinalRecoveryPreparationResult/v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'ACCEPTED_OFFLINE_STATIC_READ4_FIRST_THEN_CONDITIONAL_SINGLE_WRITE5_PLAN_ONLY','reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','raw_members_verified':28,'product_commit':plan['product_commit'],'implementation_sha256':plan['implementation_sha256'],'manifest_sha256':'2f8b5b76602e353d04c3bcbe8dfaf1d1738fb4c98a883df685dae06445d5aa47','recovery_plan_sha256':binding['plan_sha256'],'runner_sha256':binding['runner_sha256'],'outer_sha256':binding['launcher_sha256'],'last_question_manifest_sha256':plan['last_question_manifest']['sha256'],'old_actual_overlap_exact_members':overlap,'top_level_hash_bound_plan_refs':refs,'line_references':line_map,'q4_gate':['new configure/capture only, order21/pages12+173/source; existing guarded12GET and zero writes','new reader exit0 via unchanged child, NATIVE_GETS_CAPTURED, save_attempts0, context/runtime release true','old validated plan, exact success receipt and one POST both layers bound to original fixed execution; old Job0 accepted while original framework failure remains false','each raw response status200, request counts1 per layer, size/SHA equal; every observed_at later than old writer and old holder finish','12 complete responses, different writer/reader PID and run_id; full original strict compare_readback plus source/page12/page173 exact equality','all checks true and six-file ledger unchanged before any q5 preparation or child'], 'conditional_q5':['exact previously accepted single target printed5/native22; candidate and materialized plan byte-identical; previous_acceptance=null; stable ledger branch empty','unchanged batch.prepare/check_resources/execute/child; fresh12GET before at most1POST then different process/context independent12GET','first failure stops; no q4 writer branch, q3/q4 marker or revision predecessor created'],'outer':['clean389d, unchanged implementation digest and Python exe plus accepted supervisor hashes','recovery plan and all11 path/SHA refs, complete old55 actual original+frozen hashes checked before launch; new runner and outer hashes must match authority','same original profile/DIRECT/exactleaf-SPKI, exact six existing JSON ledger files and hashes, no unknown entry and empty q5 identity branch','fresh output+outer paths; one distinct authority and intent then atomic spend before one owned process <=900s'],'limits_to_bind':plan['limits_to_bind'],'root_before_activation':['Bind existing direct user request, this fixed formal report/result and root receipt, old actual acceptance d74a0705/root closure, new plan/runner/outer/last-target hashes','Record fresh exact original-profile process count0 and exclusivity; launcher checks locks, not process inventory','New unique attempt; both old batches remain spent1/0. Six ledger files unchanged; no third/fourth marker.'],'actual_recovery_read4_write5':'NOT_RUN','new_tests_product_runs_or_live_resources':0,'q4_resend_authorized':False,'new_q3_q4_accepted_marker_authorized':False,'revision_predecessor_claim':False,'old_writer_context_runtime_failure':'PRESERVED_FALSE_NOT_COVERED_BY_OLD_OR_FUTURE_JOB0','export_scope':'Original captured readback JSON, stdout/stderr and evidence data only. Paper native export and image rendering remain separate NOT_RUN gaps.','reviewer_read_helper_error':'One inline StopIteration from case-sensitive uppercase suffix against lowercase registry, retained and corrected in helper only; no missing raw input or product failure','review_complete_and_released':True,'automation_1800_a':'PAUSED_UNCHANGED'}
 put(P/'result.json',enc(result))
 report='''# A25 第4补读后条件写第5：固定静态预检

有限接受此固定恢复计划，实际仍NOT_RUN。28原件核证；无产品改动、测试或真实资源运行。第5候选/计划与此前已验字节相同，389d包摘要1c222acd保持。

新runner先用原configure/capture仅对native21执行12GET、零写。新reader须exit0、完整捕获、零保存且context/runtime释放；旧精确成功回执/一次POST、原计划及旧整批Job0均绑定固定原件，并保留旧context/runtime false。每份新响应须200、计数/字节/SHA吻合、观察时间晚于旧writer及holder结束；PID/run_id不同。完整12响应经原严格compare_readback，source/两页一致且原六ledger未变后，才调用第5batch.prepare/execute。新有限键序对账入口不参与这里的严格比较。

第5唯一目标native22、previous_acceptance=null、稳定ledger分支空；复用已验原batch，先新鲜12GET，再最多1POST及不同进程/context完整12GET读回。第4失败或任一步异常即停止，不存在第4writer分支，不补第3/4 marker，不制造revision前驱。第5若正常完成可产生其自身正常intent/accepted文件，原六文件保持。

外层核固定恢复plan及11个path/SHA引用、原55 actual完整原件/副本、清洁389d、包/runtime/监管器摘要、六个原JSON ledger精确快照及第5分支空。根新唯一authority须同时绑定runner b20ceea1、outer b761d6f1、恢复plan cd89a299、最后单题manifest250b9b97、旧actual接受和本报告/根receipt的原字节SHA；原profile独占进程0须根激活前新观察，启动器仅核锁。新intent与原子spend先于唯一监管进程，总上限900秒。

范围：第4首次独立reader12GET；通过门禁后第5writer+reader24GET。最多1POST、2readers、3contexts/惰性导航/TLS、36GET。两旧批1/0不恢复、不转借。第3/4不补marker、不重发，旧writer framework false和所有错误保留；最终Job0仅证明整批OS释放。

本轮只整理原始读回JSON/stdout/stderr和数据证据；paper原生导出及图渲染仍NOT_RUN缺口。NOT_ACTIVATED模板不能当权限；根以实际直接用户授权记录完成绑定。保留一次读取helper大小写suffix导致的StopIteration，修正helper引用后材料完整；未执行runner、outer或旧测试。独立已完成释放，sole1800-a保持PAUSED。
'''
 put(P/'report.md',report.encode('utf-8'))
 rows={}
 for p in sorted(S.rglob('*')):
  if p.is_file():rows[str(p)]=entry(p,'current_frozen_input_or_mapping')
 rows.update(used)
 for p in sorted(P.iterdir()):
  if p.is_file() and p.name not in ('raw-manifest.json','review-files.sha256'):rows[str(p)]=entry(p,'independent_public_report_or_helper')
 values=list(rows.values());put(P/'raw-manifest.json',enc({'schema':'A25IndependentFinalRecoveryPreparationRawManifest/v1','self_and_checksum_excluded':True,'new_inputs':28,'total_files':len(values),'members':values}))
 public=[p for p in sorted(P.iterdir()) if p.is_file() and p.name!='review-files.sha256'];put(P/'review-files.sha256',''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in public).encode())
 for x in values:assert sha(Path(x['path']).read_bytes())==x['sha256'] and len(Path(x['path']).read_bytes())==x['bytes']
 print(json.dumps({'status':result['status'],'raw_files':len(values),'public_files_plus_self':len(public)+1,'result':entry(P/'result.json','result'),'report':entry(P/'report.md','report'),'raw_manifest':entry(P/'raw-manifest.json','manifest'),'checksum':entry(P/'review-files.sha256','checksum')}))
if __name__=='__main__':main()
