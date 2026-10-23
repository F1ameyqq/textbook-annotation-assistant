# -*- coding: utf-8 -*-
"""Static intake of exact-two outer packet, then freeze finite review."""
import ast,datetime,difflib,hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/created-zone-reconciliation-review-20261023')
R=Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/remaining-two-outer-root-frozen')
OLD=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def entry(p,kind):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'kind':kind}
def main():
 mb=(R/'manifest.json').read_bytes();ib=(R/'root-index.json').read_bytes()
 assert sha(mb)=='f19de00e491dd95bd5466aff795f4bbe24aa8383a73b96ecaf80c819294977b5' and sha(ib)=='140b15d3a4d4abfc0241ee7515ab39e48911fbed6e40f028decd9690c98ca944'
 m=json.loads(mb);ix=json.loads(ib);assert len(m['members'])==len(ix['members'])==7
 out=S/'outer';out.mkdir(exist_ok=False);put(out/'manifest.json',mb);put(out/'root-index.json',ib);outer_inputs=[]
 for a,e in zip(m['members'],ix['members']):
  assert all(e[k]==v for k,v in a.items());source=Path(e['root_frozen_path']);assert source.parent==R;b=source.read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];target=out/source.name;put(target,b);outer_inputs.append({'original':e['source_path'],**entry(target,'outer_frozen_input')})
 launcher=out/'raw-01-launch-remaining-two-once.py';text=launcher.read_text(encoding='utf-8');ast.parse(text)
 assert sha(launcher.read_bytes())=='804bd183a4cf6bbb48bcc704e7355295164516c6d33eea7f7355891aced6736e'
 template=json.loads((out/'raw-03-authority-fields.NOT-ACTIVATED.json').read_bytes());binding=json.loads((out/'raw-04-binding.json').read_bytes())
 registry=json.loads((S/'registry.json').read_bytes());cp=json.loads(Path(next(v for k,v in registry.items() if k.endswith('/checkpoint-created-zone-reconciliation.json'))).read_bytes())
 assert template['ledger_snapshot']==cp['ledger_original_file_sha256'] and len(template['ledger_snapshot'])==5 and template['optional_existing_third_accepted_marker_sha256'] is None
 assert template['remaining_two_plans']==cp['remaining_two']['plans'] and template['status']=='NOT_ACTIVATED_TEMPLATE_NOT_AUTHORITY'
 assert template['implementation_sha256']==cp['implementation_sha256']=='1c222acdb9d442546cbcff99cde98031fa5ecb7646cc135bb1f30dc9a09cad17'
 assert binding['actual_new_process_starts']==binding['actual_new_saves']==0
 assert binding['caps']=={'posts':2,'per_target_posts':1,'readers':2,'contexts':4,'json_gets':48,'tls_probes':4,'total_seconds':900}
 assert text.index('os.replace(temporary, authority_path)')<text.index('result = holder.run(')
 assert 'actual_ledger == expected_ledger' in text and "not list(ledger.glob(stable_key + '*.json'))" in text
 assert "command[command.index('--authorization-reference') + 1] = str(authority_path)" in text and "command[command.index('--tls-approval-reference') + 1] = str(authority_path)" in text
 previous_outer=OLD/'outer/raw-01-launch-five-save-once.py';assert sha(previous_outer.read_bytes())=='940283e0336f2f3936f8f5d6372b90ef8294034e21d07177754077e49c5a5d62'
 put(P/'outer-diff.txt',''.join(difflib.unified_diff(previous_outer.read_text(encoding='utf-8').splitlines(True),text.splitlines(True),fromfile='accepted_five_outer',tofile='fixed_exact_two_outer')).encode('utf-8'))
 description=json.loads((out/'raw-05-describe-only.process.json').read_bytes());assert description['exit_code']==0
 assert description['stdout_sha256']==sha((out/'raw-07-describe-only.stdout').read_bytes()) and description['stderr_sha256']==sha((out/'raw-06-describe-only.stderr').read_bytes())
 outer={'schema':'A25IndependentRemainingTwoOuterStatic/v1','status':'ACCEPTED_STATIC_EXACT_TWO_OUTER_ONLY','raw_members':7,'manifest_sha256':sha(mb),'root_index_sha256':sha(ib),'launcher_sha256':sha(launcher.read_bytes()),'inputs':outer_inputs,'not_executed_by_reviewer':True,'template_not_authority':True,'caps':binding['caps'],'static_conditions':['389d clean HEAD, 87 original and frozen hashes, checkpoint and exact two-target hash, new implementation, original Python and accepted supervisor hashes','same profile/ledger; all five original ledger hashes unchanged and entire JSON ledger snapshot equals authority snapshot','both remaining stable identity branches have no ledger files','fresh remaining-two-live and remaining-two-outer','one fresh distinct authority, exact DIRECT original leaf/SPKI, both write/TLS references replaced','one intent and atomic authority spend before one supervised <=900s process; first failure stop and no retry'],'required_root_binding':['Bind current finite independent report/result SHA and root receipt plus exact new product/checkpoint/targets/outer hash','Bind ledger_snapshot exactly the five original files, optional_existing_third_accepted_marker_sha256=null; no third marker creation or optional marker branch approved here','Fresh exact original-profile process count0/exclusive observation before activation; launcher checks locks, not process inventory'],'release_scope':'Final whole-batch Job0/held identities only; each process proves context/runtime release and writer process exit before reader. No per-writer descendant OS release inference.','optional_third_marker_branch':'Static existence acknowledged only. This review accepts the exact five-file/no-new-marker branch for this dispatch; optional branch is outside this acceptance.'}
 put(P/'outer-review.json',enc(outer))
 control=json.loads((P/'controls-result.json').read_bytes());assert control['status']=='PASS_OFFLINE_ONLY' and json.loads((P/'control-process.json').read_bytes())['exit_code']==0
 result={'schema':'A25IndependentCreatedZoneReconciliationResult/v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','status':'ACCEPTED_FINITE_RECONCILIATION_THIRD_EXISTING_SAVE_READBACK_AND_EXACT_TWO_OFFLINE_PLANS_STATIC_OUTER','product_commit':'389d2e7a282d21efa25db8d01c02d115ce9e83b7','implementation_sha256':cp['implementation_sha256'],'raw_primary_members':87,'git_blob_members':24,'outer_raw_members':7,'primary_manifest_sha256':'271c7ca122beeba5511b08619d9dc6cc356d777363eaf1051f372b9205d667b7','checkpoint_sha256':'d71016829898da16b8c56fd2d9f2b321e0511be5aa499584eef0c306bbceee33','new_code_decision':'ACCEPTED_OFFLINE_ONLY','new_boundary_tests':3,'negative_cases_inside_new_tests':16,'independent_extra_rejections':5,'third_decision':'ACCEPTED_EXISTING_REAL_SAVE_AND_ORIGINAL_FRESH_INDEPENDENT_READBACK_UNDER_EXACT_CREATED_ZONE_RULE','third_original_strict_failure':'PRESERVED_FAIL','third_original_after_sha256':control['actual_after_sha256_unchanged'],'third_acceptance_basis':['Earlier fixed actual independent review proves one exact success receipt, distinct writer/reader process+context, all12 reads after writer exit, complete raw/hash closure and final release','Earlier deep review traversed2163 nodes and1796 scalar leaves with only two direct data-object order differences','New narrow pure rule matches the same original plan/after; no source/after/plan/FAIL/intent bytes changed'],'third_ledger_marker_created':False,'third_report_is_revision_predecessor':False,'third_future_write_authorized':False,'third_future_write_gate':'Original failed acceptance.json and unresolved stable intent preserved. Unchanged writer rejects existing intent; unchanged revision requires original strict accepted evidence+accepted marker, which this reconciliation sidecar does not supply.','first_two_prior_successes':'PRESERVED_NO_REPLAY','remaining_two_decision':'ACCEPTED_OFFLINE_EXACT_PRINTED4_5_NATIVE21_22_PLANS_FOR_NEW_DISTINCT_AUTHORITY','remaining_manifest_sha256':'769ea9b78906f689776613942799581966a9a0e690e62cc1af8e43117988f6c7','remaining_previous_acceptance':None,'remaining_actual_save_readback':'NOT_RUN','outer_decision':outer['status'],'outer_launcher_sha256':outer['launcher_sha256'],'approved_ledger_snapshot':cp['ledger_original_file_sha256'],'optional_third_marker_authorized':False,'limits_to_bind':binding['caps'],'root_dispatch_conditions':outer['required_root_binding'],'prior_batch':{'spent':1,'remaining':0,'capacity_transferred':False},'new_platform_requests_or_profile_ledger_access':0,'old_test_suites_rerun':False,'initial_author_import_failure':'PRESERVED ModuleNotFoundError fixture import; frozen initial error+script and v2/v3 raw success retained, not converted into a product pass','reviewer_helper_failures':1,'blocking_findings':[],'review_complete_and_released':True,'automation_1800_a':'PAUSED_UNCHANGED'}
 put(P/'result.json',enc(result))
 report='''# A25 新增缺失区键序对账与最后两题有限验收

接受389d产品的有限纯对账规则；第三题既有真实保存及原新鲜独立读回在该规则下正式接受。原strict FAIL、原after/摘要、原intent和失败acceptance.json全部保留，本结论不创建accepted marker，不构成第三题revision predecessor，也不授权未来第三题写入。

87原件/24 Git blob及外层7原件核证。已有产品仅update.py发生差异：新入口先validate_plan及原strict比较，仅对本plan从严格absent新增的data、精确三字段和逐值类型/数组均一致、恰好rect_ids,ocr_result,success→success,ocr_result,rect_ids的直接对象键序，在私有expected副本调整后再完整strict比较。所有其他原函数AST保持，原私有比较helper只增加可选副本参数，其余逻辑保持；core、writer、revision、runner字节未改。新3项（含16反例）及5独立拒绝控制通过，保留作者首次fixture导入失败原件。未运行旧套件、OCR或平台。

第三题复用刚完成的固定实际独立结论与完整原件事实：一次200/code0成功回执，不同PID/context reader在writer退出后12原始响应均完成；完整快照2163节点/1796标量逐项核对只剩两处新增区data直接对象键序。重叠冻结原件逐字节相同；新纯入口对同一plan/after匹配，原strict仍失败，输入摘要不变。新函数的receipt/context/live标记仍false，实际保存/独立性由先前正式原件验收独立提供。五个原ledger文件及旧耗尽authority不变；原第三未解决intent继续阻止重发，旧revision严格前驱门不被此旁证替代。

剩余targets恰好原清单印刷4/5、native21/22子集；两候选及两计划字节与先前验收相同，previous_acceptance=null，自身稳定分支在冻结观察中无ledger。无需借第三题权限。接受该具体增量计划，实际两次保存/回读仍NOT_RUN。实际运行仍须逐题新鲜12GET检查，再各最多1POST、新进程/context完整12GET回读；异常即停止无重试。

接受launcher804bd183的静态启动条件，复用已验监管器a1582782：原profile/DIRECT/exactleaf-SPKI、清洁389d、87原件/副本及新checkpoint/targets/runtime/hash、新输出、原五ledger逐hash及完整JSON快照相等、剩余两identity分支空。根绑定新唯一authority、本报告/机器结论/根receipt原字节SHA及最新原profile独占进程0观察；启动器只检查锁，不代替该观察。范围exact2 writer+2 reader、4context/惰性导航/TLS、48业务GET、最多2POST、整批900秒，原五题批1/0不恢复或转借。写入/TLS引用替换同一新authority，intent及原子消费先于唯一监管启动。

本次仅接受ledger_snapshot为原五文件且optional_existing_third_accepted_marker_sha256=null分支；启动器可选第三marker白名单分支未获本次授权，且启动器不创建marker。所有外层只静态核查，未新增外层测试或启动。最终整批Job0不证明逐writer子进程在下一reader前全部OS退出。报告固定helper曾出现一次UTF-8声明错误；原脚本与工具返回错误记录保留，仅加显式UTF-8声明修helper，未重跑已通过边界。完成并释放，sole1800-a保持PAUSED；未改产品、ledger、根状态或Git。
'''
 put(P/'report.md',report.encode('utf-8'))
 # Inventory current isolated bytes and only the reused fixed bytes actually read.
 rows={}
 for p in sorted(S.rglob('*')):
  if p.is_file():rows[str(p)]=entry(p,'current_frozen_input_or_independent_output')
 for name,digest in control['reused_files'].items():
  p=Path(name);assert sha(p.read_bytes())==digest;rows[str(p)]=entry(p,'prior_fixed_reused_input')
 oldfiles=[*list((OLD/'snapshot/src/annotation/runtime/usense_live').glob('*.py')),OLD/'snapshot/tools/run_usense_reviewed_batch.py',OLD/'project/post-manual-login-source/five-candidates-v2/targets.json',OLD/'registry.json',previous_outer]
 for p in oldfiles:rows[str(p)]=entry(p,'prior_fixed_static_dependency')
 for p in sorted(P.iterdir()):
  if p.is_file() and p.name not in ('raw-manifest.json','review-files.sha256'):rows[str(p)]=entry(p,'independent_public_report_or_helper')
 values=list(rows.values());put(P/'raw-manifest.json',enc({'schema':'A25IndependentCreatedZoneReviewRawManifest/v1','self_and_checksum_excluded':True,'new_primary_members':87,'new_outer_members':7,'total_files':len(values),'members':values}))
 public=[p for p in sorted(P.iterdir()) if p.is_file() and p.name!='review-files.sha256'];put(P/'review-files.sha256',''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in public).encode())
 for x in values:assert sha(Path(x['path']).read_bytes())==x['sha256'] and len(Path(x['path']).read_bytes())==x['bytes']
 print(json.dumps({'status':result['status'],'public_files_plus_self':len(public)+1,'raw_files':len(values),'result':entry(P/'result.json','result'),'report':entry(P/'report.md','report'),'raw_manifest':entry(P/'raw-manifest.json','manifest'),'checksum':entry(P/'review-files.sha256','checksum')}))
if __name__=='__main__':main()
