"""Snapshot frozen review documents and prepare NOT_RUN acceptance mappings only.

This tool never imports repository modules or opens any database/target.
All new files are confined to the explicitly authorized preparation directory.
"""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path('D:/1800')
OUT=ROOT/'docs/evidence/A03/review/P2-preparation'
WORKFLOW='6b77c436742cf2826083b109d8ed86b85539cba6'
DESIGN_FINAL='940a5de33a24b1a3a9ded6e69ade1dd0609ed83a'
DESIGN='a250a76dc0b3f13b9dee3bcd2c3d7414032b9768'
REASON='PREPARATION_ONLY; frozen P2 implementation/report/manifest/release and coordinator continuation not delivered'
def digest(b):return hashlib.sha256(b).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def write(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def git_bytes(commit,path):
 r=subprocess.run(['git','cat-file','blob',commit+':'+path],cwd=ROOT,capture_output=True,timeout=30)
 if r.returncode:raise RuntimeError((commit,path,r.stderr.decode('utf-8','replace')))
 oid=subprocess.run(['git','rev-parse',commit+':'+path],cwd=ROOT,capture_output=True,timeout=30)
 assert oid.returncode==0
 b=r.stdout;actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 assert oid.stdout.decode().strip()==actual
 return b,actual
def protect():
 paths={p for p in (ROOT/'docs/evidence/A03/review').rglob('*') if p.is_file() and not p.is_relative_to(OUT)}
 paths|={p for p in (ROOT/'docs/tasks').glob('A03*review*.md') if p.name!='A03-P2-review-preparation.md'}
 return [{'path':rel(p),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(paths)]

assert not (OUT/'input-index.json').exists(),'Do not overwrite an existing preparation archive.'
write(OUT/'protected-old-review-files.json',{'purpose':'metadata only; no historical evidence tree copied','files':protect()})
workflow_paths=['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-dispatch.md','docs/tasks/A03-P1-coordinator-acceptance.md',
 'docs/tasks/A03-independent-review.md','docs/tasks/A03-runtime-recovery.md']
design_paths=['docs/a03-recovery-contract-v1-proposal.md','docs/a03-recovery-contract-v1-r1-proposal.md',
 'docs/a03-recovery-contract-v1-r2-proposal.md','examples/a03/P1-R2/README.md','examples/a03/P1-R2/api-proposal.json']
api_b,_=git_bytes(DESIGN_FINAL,'examples/a03/P1-R2/api-proposal.json')
api=json.loads(api_b)
assert digest(api_b)=='e2b0865fc1a25206181f3094155b059a6d34eb851afc750e813f0c2e89960f85'
for entry in api['candidate_profile']['schema_files'].values():design_paths.append('examples/a03/P1-R2/'+entry['path'])
inputs=[];texts={}
for label,commit,paths in [('workflow',WORKFLOW,workflow_paths),('accepted-design',DESIGN_FINAL,design_paths)]:
 for path in paths:
  b,oid=git_bytes(commit,path);q=OUT/'inputs'/label/path;q.parent.mkdir(parents=True,exist_ok=True)
  with q.open('xb') as f:f.write(b)
  inputs.append({'source_commit':commit,'source_path':path,'git_blob':oid,'bytes':len(b),'sha256':digest(b),'copy':rel(q),'copied':True})
  texts[path]=b.decode('utf-8')
for path,expected in [('docs/tasks/A03-P1-R2-review-report.md','7a3d02a07042efb8a3f1854ae297b231e3dc8362805144760ee72e46d371eb36'),
 ('docs/evidence/A03/review/P1-R2/sha256-manifest.json','f9db0d7e3e0a77416c945d1483e95f589e61fb9573fec5d288e3ec23c1ccbb75')]:
 b,oid=git_bytes(WORKFLOW,path);assert digest(b)==expected
 inputs.append({'source_commit':WORKFLOW,'source_path':path,'git_blob':oid,'bytes':len(b),'sha256':digest(b),'copied':False,'reason':'accepted review provenance; metadata only, no old evidence copy'})
assert digest(texts['docs/a03-recovery-contract-v1-r2-proposal.md'].encode())=='acd67720e905a45b85c0943648b239b2dfd1fdb36eaf3095e56803c1de564f9d'
schema_pins=[]
for name,e in api['candidate_profile']['schema_files'].items():
 path='examples/a03/P1-R2/'+e['path'];record=next(x for x in inputs if x['source_path']==path)
 assert record['sha256']==e['sha256'];schema_pins.append({'name':name,**record})
write(OUT/'input-index.json',{'workflow_commit':WORKFLOW,'accepted_final_commit':DESIGN_FINAL,'design_commit':DESIGN,
 'export_method':'git cat-file blob; exact raw bytes and Git blob SHA1; no checkout/archive/import/run',
 'selection':'20 relevant documents/API/Schema only; no source, tests, database, fixture or old evidence tree copied',
 'files':inputs})

group_map={'G1':['V01','V06','V08','R01','R04','R08','R09','R14'],
 'G2':['V01','V02','V04','V06','R02','R03','R09','R11','R12'],
 'G3':['V03','V04','V07','R05','R11','R13'],
 'G4':['V05','V06','V08','V09','R06','R07','R08','R10','R14','R15']}
groups=[{'id':g['id'],'name':g['name'],'source_json_path':'groups/'+str(i)+'/proposed',
 'entries':g['proposed'],'mapped_checks':group_map[g['id']],'functional_actual':'NOT_RUN'} for i,g in enumerate(api['groups'])]
write(OUT/'accepted-api-schema-map.json',{'status':'ACCEPTED_DESIGN_PINS_ONLY; IMPLEMENTATION_NOT_REVIEWED',
 'accepted_final_commit':DESIGN_FINAL,'design_commit':DESIGN,'api_sha256':digest(api_b),
 'schema_version':api['schema_version'],'exchange_version':api['exchange_version'],
 'candidate_profile':api['candidate_profile'],'schemas':schema_pins,'design_constants':api['design_constants'],
 'groups':groups,'contracts_entries':api['contracts_api'],'runtime_authority':api['runtime_authority_protocol'],
 'two_stage_gate':api['two_stage_gate'],'unattempted_absence':api['unattempted_absence_protocol'],
 'event_prefix_profile':api['event_prefix_resource_profile'],
 'note':'Snapshot values are accepted design, not evidence of current runtime authority. Historical UNIMPLEMENTED/REVIEW labels are preserved.'})

relationships={
 'V01':['R01','R02','R04','R08','R17'], 'V02':['R03','R04','R09','R14','R18'],
 'V03':['R05','R12','R13'], 'V04':['R02','R03','R05','R06','R11','R17','R18'],
 'V05':['R06','R07','R08','R10'], 'V06':['R06','R08','R09','R13','R18'],
 'V07':['R02','R06','R08','R12','R13'], 'V08':['R01','R04','R08','R14','R15'],
 'V09':['R02','R15','R16'], 'V10':['R11','R17','R18']}
methods={
 'R01':('先验证精确Git/raw blob、允许路径、独立合同提交/实现提交/报告提交、旧文件摘要；隔离副本固定PYTHONPATH并记录所有实际模块__file__。','E0,E7'),
 'R02':('经公共入口分别扰动计划/动作/书scope/四元组/资源字节/递归声明/混合环；合同PASS后另用伪造handle/JSON许可挑战runtime与target。','E0,E1,E2,E3,E4'),
 'R03':('六个冻结fault_points逐一用独立worker到屏障后终止/退出90；新observer/recovery进程核对；前效果0、后效果1、恢复增量0，不以标记代替目标事实。','E1,E2,E3,E4,E5'),
 'R04':('记录runtime/target不同物理SQLite文件、连接/事务/身份；worker退出后独立只读进程查询目标业务表/ID/效果日志；重启前后同store，禁止初始化重建。','E1,E2,E3'),
 'R05':('独立合成MATCH/完整ABSENT/部分/重复身份/矛盾/失败/截断读回；自身oracle从固定初态及动作计算；前后业务digest/效果计数不变，观察read_sequence可增加。','E1,E2,E3,E4'),
 'R06':('保留原UNKNOWN与resolution字节，构造错receipt/义务、分叉/循环、终局后继和解决后新UNKNOWN；只精确解决当前义务，旧证明不得解新项。','E3,E4,E7'),
 'R07':('在受控当前库登记同书多run/scope历史并保留当前固定target；当前包省略另scope/传空账本仍暂停；逐scope全账本与独立行查询对照，不放宽普通scope引用。','E2,E3,E4'),
 'R08':('变action/question/run/scope或旧代次、漏登记、指向替换空目录/库；支持入口fail closed。副本故障只在自有新case目录，不能init/open重置历史。','E1,E2,E3,E4'),
 'R09':('两真实进程由事件/屏障控制claim与dispatch交错；检查runtime CLAIMING→target fence→runtime ACTIVE各窗口，闸内重验至target commit；旧owner保持/过期且确认退出/受控交接分别核对。','E1,E2,E3,E5'),
 'R10':('另书独立包及合法多书包含外书UNKNOWN；原A02 R1跨书失败输入按冻结字节保留，另造邻例；全包历史不裁剪，仅按稳定target_key投影暂停。','E1,E2,E3,E7'),
 'R11':('APPLIED/UNKNOWN/未尝试完整清单分别做充分/不足ABSENT；未知前序影响C相关事实须拒绝；专用两新读只读事务不走写就绪gate，不造intent/义务，保留其他UNKNOWN及INTERRUPTED。','E1,E2,E3,E4'),
 'R12':('ABSENT后旧计划直接重放/只换ID均拒绝；后续效果必须新实际snapshot+PRE_APPLY+TARGET+新计划及当前账本许可；原动作/预约永久不复用。','E1,E2,E3,E4'),
 'R13':('切换当前图谱/快照/政策/授权/能力及终局后目标变化；旧资格失效，TARGET_DRIFT_HOLD需新证据与当前事务按精确hold解除，不能重写旧终局或直接READY。','E1,E2,E3,E4'),
 'R14':('在新case副本制造资源缺失/坏hash、DB/索引/事务失败、未知版本/目录替换/迁移中断；核对失败前后原始行/文件/事件，保留孤儿诊断文件而不授予许可。','E0,E2,E3,E4,E7'),
 'R15':('旧load/新load/archive/convert分开；转换新目录有输入SHA和身份映射、原字节不动；旧无intent UNKNOWN=LEGACY_UNRECORDED，导入/改版本/重封签不造本地提交。','E0,E3,E4,E7'),
 'R16':('递归在source/asset/producer/evidence/readback/proof/resource嵌入ORIGINAL/OBSERVED/真实/缺来源；最外层合成标签不能掩盖。拒绝发生于效果前；S01真实完整性仍阻断。','E0,E1,E2,E4'),
 'R17':('新BatchReport/POST_APPLY消费精确原receipt+终局链+progress；旧报告/直接VERIFIED拒绝；不足事实只progress，框MATCH保持PENDING/NOT_SUBMITTED且不COMPLETED。','E3,E4,E6,E7'),
 'R18':('独立固定范围清单含异常/跳过/未入图谱，未知/null和零题[]不生成完整BatchReport/0÷0；每intent每call读前持久登记≤3，崩溃同call额度不重置，期限逐层实测且NOT_VISITED显式保留。','E1,E2,E3,E4,E5,E6')}
rows=[]
for prefix,path in [('V','docs/tasks/A03-runtime-recovery.md'),('R','docs/tasks/A03-independent-review.md')]:
 for line in texts[path].splitlines():
  cells=[x.strip() for x in line.strip().strip('|').split('|')]
  if len(cells)<3 or len(cells[0])!=3 or not cells[0].startswith(prefix) or not cells[0][1:].isdigit():continue
  key=cells[0]
  related=relationships[key] if prefix=='V' else [v for v,rr in relationships.items() if key in rr]
  method='；'.join(f'{r}: {methods[r][0]}' for r in related) if prefix=='V' else methods[key][0]
  evidence=sorted(set(','.join(methods[r][1] for r in related).split(','))) if prefix=='V' else methods[key][1].split(',')
  rows.append({'id':key,'source_commit':WORKFLOW,'source_path':path,'original_check':cells[1],
   'original_acceptance':cells[2],'related_checks':related,'independent_method':method,
   'evidence_classes':evidence,'actual':'NOT_RUN','reason':REASON})
assert {x['id'] for x in rows}=={f'V{i:02}' for i in range(1,11)}|{f'R{i:02}' for i in range(1,19)}
write(OUT/'acceptance-matrix.json',{'scope':'future independent P2 review only; methods, not executed results','rows':rows})

write(OUT/'deadline-and-fault-plan.json',{'all_actuals':'NOT_RUN','approved_by':WORKFLOW+':docs/tasks/A03-P1-coordinator-acceptance.md',
 'intent_reconcile':{'maximum_reads_per_intent_per_call':3,'per_read_s':2,'per_intent_s':8,'whole_call_s':60,
  'sqlite_busy_s':1,'effect_gate_s':5,'barrier_s':5,'owner_lease_s':10,'renew_s':2,
  'rules':['persist call_id and attempt before actual read, including failed/crashed reads',
   'restart same call_id does not reset budget; new explicit call needs actual new reads; no automatic loop',
   'absolute monotonic earliest applicable deadline; record actual starts/ends/timeouts and queue NOT_VISITED',
   'deterministic structure/version/hash/reference failure immediately rejects without read retries']},
 'unattempted_absence':api['unattempted_absence_protocol']['bounds'],
 'unattempted_unknown_commit':'Query current full-book context by permanent (journal_id,canonical_target_key,action_id); verify event/resource hashes. Never resubmit for discovery.',
 'exit_codes':{'0':'query/reconcile completed or NO_ACTIONS; not quality success or automatic dispatch','2':'INVALID_INPUT','3':'HOLD_PENDING',
 '4':'OWNER_BUSY_OR_STALE','5':'STORAGE_FAILURE','6':'DEADLINE_EXCEEDED','7':'ADMISSION_REJECTED','90':'INJECTED_PROCESS_EXIT; not success'},
 'frozen_fault_points':api['fault_points'],
 'additional_observation_windows':['atomic plan acceptance/reservation',
  'permit issue/consume and target precommit gate','CLAIMING/fence activation/ACTIVE across independent stores',
  'unattempted first/second read, prewritten resources, final CAS and fact/event/index commit',
  'reconciliation observation and event-head CAS','attempt pre-registration then crash and same-call restart'],
 'timing_evidence':'Use actual monotonic intervals and parent harness finite deadline. Record scheduling allowance as observation; do not silently raise approved implementation bounds or use fixed sleeps as concurrency proof.'})
write(OUT/'scope-declaration.json',{'phase':'P2_REVIEW_PREPARATION_ONLY','functional_conclusion':'NOT_ASSESSED',
 'workflow_commit':WORKFLOW,'accepted_design_final':DESIGN_FINAL,'p2_executor_authorized':True,
 'reviewer_functional_execution_authorized_this_turn':False,'i01_released':False,
 'allowed_writes':['docs/tasks/A03-P2-review-preparation.md','docs/evidence/A03/review/P2-preparation/'],
 'repository_source_imports_or_execution':0,'floating_implementation_reads':0,'databases_opened':0,'target_effects':0,
 'browser_network_platform_credentials_profile_ocr_model_api':0,'paid_model_calls':0,'real_quality_cost':'NOT_MEASURED',
 'test_or_target_worker_processes_started':0,'remaining_owned_background_os_processes':0,
 'helper_processes':'bounded synchronous Git/Python document tooling only; no test or target process',
 'other_processes_stopped':0,'messages_to_executor_B_other_chats':0,'polling_or_automation_created':0,
 'source_contract_dependency_state_changes_commit_integration_push':False,
 'agents':'two read-only static document-analysis helpers; no implementation or fixture execution',
 'next_gate':'stop after preparation; coordinator must separately deliver exact frozen P2 commits/report/manifest/release and authorize formal review'})
print(json.dumps({'result':'P2_PREPARATION_DOCUMENTS_CREATED','copied_frozen_inputs':sum(x['copied'] for x in inputs),
 'provenance_only':sum(not x['copied'] for x in inputs),'matrix_rows':len(rows),'functional_actuals':'ALL_NOT_RUN'}))
