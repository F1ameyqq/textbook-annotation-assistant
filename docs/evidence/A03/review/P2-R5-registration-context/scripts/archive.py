# -*- coding: utf-8 -*-
"""Finalize/verify this review archive only. Never imports or calls a checker."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1];STAGE=OUT/'input/checkout';EX=STAGE/'examples/a03/P2-R5-registration-context'
REPORT=ROOT/'docs/tasks/A03-P2-R5-registration-context-review-report.md';MANIFEST=OUT/'sha256-manifest.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def h(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def ref(a):return {k:a[k]for k in ['artifact_id','revision','kind','content_hash']}
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def verify_files(rows,base):
    for row in rows:
        b=(base/row.get('file',row.get('path'))).read_bytes()
        assert len(b)==row['bytes']and sha(b)==row['sha256'],row
        if 'raw_git_sha1'in row:assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['raw_git_sha1']
inputs=load(OUT/'input-index.json');assert len(inputs['files'])==225;verify_files(inputs['files'],OUT)
assert {p.relative_to(OUT).as_posix()for p in(OUT/'input').rglob('*')if p.is_file()}=={x['file']for x in inputs['files']}
guard=load(OUT/'protected-old-files.json')['files'];assert len(guard)==2797;verify_files(guard,ROOT)
delivery=load(OUT/'delivery-byte-index.json');assert delivery['added_paths']==205 and delivery['manifest_entries']==204 and delivery['old_git_paths_unchanged']==28113
results=load(OUT/'independent-results.json');assert results['overall']=='REWORK'and results['Package_calls']==7
assert results['qualified_scenarios']==6 and results['codes_matching_expectation']==7 and not results['invalid_first_case_reexecuted']
case_tags=['case-01','case-02','case-03','case-04','case-05','case-06','case-07-repair-01']
source_pins=load(OUT/'source-pins/case-01.json')['source_files'];source_lookup={x['path']:x['sha256']for x in source_pins}
for tag in case_tags:
    assert load(OUT/'call-counts'/(tag+'.json'))['observed_R3_entry_call_counter']==1
    assert load(OUT/'source-pins'/(tag+'.json'))['source_files']==source_pins
for x in source_pins:assert sha((STAGE/x['path']).read_bytes())==x['sha256']
assert source_lookup['examples/a03/P2-R5-registration-context/registration.py']=='3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'
run_names=['freeze-01',*case_tags,'audit-01'];completions=[]
for name in run_names:
    d=OUT/'runs'/name;reg=load(d/'registration.json');completion=load(d/'completion.json')
    assert sha((d/'entry-source.py').read_bytes())==reg['entry_sha256']
    assert completion['pid']==load(d/'started.json')['pid']and completion['exit_code']==0 and not completion['timed_out']and not completion['alive_after_wait']
    completions.append(dict(name=name,**completion))
ev=STAGE/'docs/evidence/A03/execution/P2-R5-registration-context'
author_runs=[dict(name=p.parent.name,**load(p))for p in sorted((ev/'runs').glob('*/exit.json'))]
assert len(author_runs)==13 and all(not r['alive']and not r['timed_out']for r in author_runs)
assert [(x['name'],x['exit_code'])for x in author_runs if x['exit_code']!=0]==[('case-07',1)]
author_results=[load(p)for p in sorted((ev/'results').glob('case-*.json'))]
assert len(author_results)==8 and {x['overlay_sha256']for x in author_results}=={'3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'}
residual=load(OUT/'mixed-control-residual.json');assert residual['observed_rejection']=='MIXED_CYCLE'and not residual['implementation_defect_proved_by_this_control']
# Explicit data-only proof of the repaired control's intended closed path.
repair=load(STAGE/load(EX/'repair-case-index.json')['cases'][0]['case']);bundle=load(STAGE/repair['bundle'])
over={r['logical']:(STAGE/r['file']).read_bytes()for r in repair['resources']}
source=next(a for a in bundle['artifacts']if a['artifact_id']=='r5-mixed-cycle-source-consumer')
record=next(e for e in bundle['evidence']if e['evidence_id']=='proof-r5-mixed-cycle')
assert any('proof-r5-mixed-cycle'in m['evidence_refs']for m in source['payload']['external_page_mappings'])
prefix=json.loads(over[record['resource']['path']]);frame=next(f for f in prefix['frames']if f['event']['event']=='PLAN_ACCEPTED'and f['consumer_scope_id']==source['scope_id'])
returned=json.loads(over[frame['event']['payload']['evidence']['path']]);assert returned['ordinary_source_ref']==ref(source)and ref(source)in frame['input_refs']
assert source['input_refs']==[prefix['subject_plan_ref']]
assert load(OUT/'runs/case-07-repair-01/stdout.log')['consumer_failures']==[]
cycle_proof={'source_ref':ref(source),'source_book':source['book_id'],'source_scope':source['scope_id'],'formal_evidence_id':record['evidence_id'],
 'prefix_resource':record['resource'],'frame_scope':frame['consumer_scope_id'],'frame_return_resource':frame['event']['payload']['evidence'],
 'return_ref':returned['ordinary_source_ref'],'own_frame_declaration_present':True,'saved_consumer_failures':[],
 'input_residual':residual['internal_head_mismatches'],'new_Package_calls':0}

text='''# A03 P2-R5 登记上下文与控制残余独立复核

2026-10-17，Asia/Shanghai。**整体 REWORK**，原因是任务要求的混合环单故障控制输入证明未闭合。分项：**登记上下文分离及target绑定 ACCEPTED_STATIC_LIMITED**；**原R3正式证据声明／全局Resource摘要两个防回归 ACCEPTED_STATIC_LIMITED**；**混合环控制 REWORK_CONTROL_INPUT_PROOF**。七个预期错误码均匹配不等于七份控制合格；前六项证据保留，不因第七项残余作废。

## 冻结输入与实际入口

| 项目 | 精确版本／SHA256 |
| --- | --- |
| 审阅workflow | `3f99837789a17770ea7a206667c6d2c79c9a33ce` |
| 任务单SHA256 | `712f22734db2a439fa6a76931038eefa0dacbbe0c6c6a0db0366af20fdb4ae88` |
| base | `e608b54b973b14ff55dd2c4530153f5fe7c931f4` |
| target | `323013c4f0dbae75368e56db60147a8057368d1f` |
| 执行workflow | `5fcb2e0084c92c20092cac19e33619128ad86d54` |
| 执行报告SHA256 | `86dd088bc109bf1243cd015d3c2f0dde9c52e2c01397574845766c7bb8208389` |
| 作者清单SHA256 | `2bb118b00b61f1c22109e3eed37777ee5c77cf88acc9c62911e515fac65dd2f7` |
| 新覆盖层registration.py SHA256 | `3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba` |

先从精确workflow raw Git读取[复验任务](../evidence/A03/review/P2-R5-registration-context/input/workflow/docs/tasks/A03-P2-R5-registration-context-review-handoff.md)、R5执行任务、R4收口、AGENTS/coordination与前检；公共架构/合同保持已读字节。保留用户当前思考设置，未改档、委派、合浮动主树或接触执行工作树。开始时根工作区已有coordination-state.json修改及mermaid-diagram.png未跟踪，均非本轮产物，未读取或改写其内容。

[raw Git字节索引](../evidence/A03/review/P2-R5-registration-context/delivery-byte-index.json)独立核对204个清单项及清单自身共205新文件；新增仅在执行任务三处授权范围，28,113旧路径mode/type/blob保持。70项原始输入（68+2补充，含9份workflow文档）逐blob核对长度/SHA1/SHA256及复制副本，未把预检当代码执行或验收。

[隔离输入索引](../evidence/A03/review/P2-R5-registration-context/input-index.json)保存225份必要文件到本轮input目录；未复制旧保全JSONL/tree或全部历史材料，未复制产品源码。执行工作树干净、完成及13个运行结束来自冻结记录，不冒充本轮OS/profile扫描。

## 代码与加载审查

完整读过registration.py、load_static.py、common.py、run_case.py及差异；固定R2/R3源码与此前已审字节相同。新类只新增静态扫描/登记比较，仍通过R3唯一EvidenceRecord ID表、正式字段catalog、每消费者独立found/declared、active consumer递归保护及R2完整validate尾段。没有针对样例ID/路径硬编码通过结果，没有过宽的跨上下文通过缓存。

`scan_prefix`明确以实际contexts区分：真实Artifact/frame路径必须有非空book并核对prefix/event/canonical book；无消费者的全局路径要求book/scope均None，只遍历和连图，不调用consumer伪造一个None-book消费者。全局仍shape检查typed prefix根位置/结构、解析正式ID、读取每个Resource及raw SHA、解析exact ref、检查frame自己的声明并连入同一DAG。None没有变成任意书籍通配符。

真实登记路径先核对Source/Snapshot exact四元组、kind、同book/同scope，再比较已有prefix.target_key、event及观察中的对应target tuple。Snapshot只读取实际存在的target_id/authorized_scope_id，没有发明namespace字段。观察的source/snapshot/scope/registration/store/session，以及已有business/baseline target字段与登记值对应；这些仍是合成值比较，不是native凭据认证。

加载9项pins及实际字节见[source-pins/case-01.json](../evidence/A03/review/P2-R5-registration-context/source-pins/case-01.json)，七次一致：

| 固定静态加载输入 | SHA256 |
| --- | --- |
| 新load_static.py | `@LOADER_SHA@` |
| 新run_case.py | `@DRIVER_SHA@` |
| R3 closure.py | `ff650507bca971f8c9418a09e6e4f8df7c7691016841ffe7bd15ff66382579a5` |
| R2 check.py | `7bf3ea27424f7afaf3d3b264d2ab3d0bfa0fdc8bba1c178e6f488bef09e6257b` |
| R2 schema_check.py | `9630d7e2e0d3700080f7a97a9c883877acf27929be82a41ed5a8f041240ccf7c` |
| R2 oracle_verifier.py | `6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d` |

固定加载器仅重定向未使用的R3 base.EVID赋值并移除其模块级mkdir。R3 Package类AST含位置保持不变，摘要 `df0133704f9cb876a1d530d629a8a65a1f5ff45bf86129a4d68612e66f8085e4`；不改任何基类方法、Schema、版本/pins或判定语义。独立审阅直接运行冻结run_case.py的--readonly模式，没有另行改写加载语义或输出路径；只向本轮父进程已打开的stdout/stderr写结果。固定oracle模块作为依赖加载，没有调用比较、采用oracle、session或conversion。

## 七个冻结场景各一次

每例单独进程；原四个R4 bundle与base原件逐字节相同，所有覆盖资源raw SHA也绑定原件。原R3反例bundle仍为 `b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653`。只选repair-01混合环，首版没有再运行。

| 场景 | 实际结果与到达层 | 分项结论 |
| --- | --- | --- |
| registration-positive | STATIC_ACCEPTED；完整返回，trace依次到MIXED_DAG、声明/book/scope、ARTIFACT_HASH、FULL_R2_TAIL_RETURN | ACCEPTED_STATIC_LIMITED |
| source-binding-negative | FRAME_REGISTRATION_BINDING；真实登记路径scope检查失败 | ACCEPTED_STATIC_LIMITED，预期拒绝 |
| snapshot-binding-negative | FRAME_REGISTRATION_BINDING；真实登记路径scope检查失败 | ACCEPTED_STATIC_LIMITED，预期拒绝 |
| target-tuple-negative | FRAME_REGISTRATION_TARGET，r4-static/target-tuple-negative/prefix.json/registration/target | ACCEPTED_STATIC_LIMITED，预期拒绝 |
| r3-original-undeclared-evidence | UNDECLARED_REFERENCE，origin-a-SourceBundle | ACCEPTED_STATIC_LIMITED，保留正式闭包 |
| global-resource-hash-corruption | RESOURCE_HASH，r5-static/global-only-proof.txt，active_real_contexts=0 | ACCEPTED_STATIC_LIMITED，全局仍实际读取 |
| artifact-resource-frame-mixed-cycle repair-01 | MIXED_CYCLE，仅到MIXED_DAG；输入内部头仍不一致 | REWORK_CONTROL_INPUT_PROOF |

[独立汇总](../evidence/A03/review/P2-R5-registration-context/independent-results.json)连接七次真实结果；原始JSON stdout、stderr、argv/cwd/PID/限时/退出在runs下，counter记录在call-counts。七次继承R3入口计数均为1，总计7，没有以脚本中的字面量次数代替实际计数。七个子进程均退出0只是各输入预期码匹配，**没有记为七项功能或干净控制通过**。

正包有16个真实消费者、6个全局frame、None-book真实消费者0；同prefix先沿真实book/original-a外层消费，再以GLOBAL_GRAPH无上下文遍历，完整返回解决R4的确定错误拒绝。合法frame scope B使用自己的上下文。两个Source/Snapshot负控在全局之前由真实绑定拒绝。target负控的kind/book/scope全通过，Snapshot.target_id及business_target_id比较失败，已由FRAME_REGISTRATION_TARGET直接定位，不再被book=None遮蔽。

原R3反例仍沿正式EvidenceRecord两层JSON Resource展开；源消费者漏声明被拒绝，同一实际扫描也记录新1.3 receipt的results[0].before_evidence_refs路径。全局hash控制只新增未被真实Artifact消费的独立证据，独立读取原始字节确认恰有该Resource声明SHA与实际SHA不同；拒绝trace中的真实contexts数为0，证明没有跳过无消费者证据池。

这些是任务指定六项的有限静态结果。原R3其它接受范围、SESSION-02/CONVERSION-07不重跑、不扩大；资源读取不是目标平台读取，不等同native会话或当前写入资格。

## 混合环：观察到拒绝，控制证明仍有残余

[冻结值审计](../evidence/A03/review/P2-R5-registration-context/frozen-values-audit.json)独立重算每个Artifact内容hash、Resource原字节及event chain/hash、普通exact refs。repair-01的bundle SHA为 `f2f5e5a032271d7890165d49e4c336dbcb5f628bbf18e372e0d7148a54535d67`，cycle-prefix raw SHA为 `4d153e82f0a75d233bb77bb7028a2a3dc2bdbcd4f22bda6514a15d0be4450de0`。它不是R4/R3曾用旧摘要残留leaf的控制；这次Artifact/Resource/event摘要正确。

输入确实构成 `新Source A → 正式EvidenceRecord → cycle-prefix Resource → 合法frame A → cycle-return Resource → 同Source A`。frame自己声明返回的Source四元组，同书同scope；外层Source声明subject plan，保存结果的consumer_failures为空。[循环引用数据证明](../evidence/A03/review/P2-R5-registration-context/mixed-reference-proof.json)保存这些exact refs和scope，不执行校验器。继承DAG实际到达并报MIXED_CYCLE；未到最终声明/hash/返回尾段。

但是该新prefix中READONLY_ABSENCE_STARTED（sequence 8）的内部initial_event_head没有随事件重链更新：

| 字段 | 值 |
| --- | --- |
| 声明的sequence 7 hash | `87f8f86767e923c8fe7eb351c45eb57df3d6d4ebfdf855249fc7f5be025bbf84` |
| 实际新sequence 7 hash／seq8.previous_hash | `28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9` |

详见[独立残余](../evidence/A03/review/P2-R5-registration-context/mixed-control-residual.json)。事件raw hash/链正确和内部语义头绑定正确是两层要求；修正后的外壳hash不能消除这个字段差异。本轮只证明环拒绝被观察到，不能称其余输入自洽的单故障控制已经闭合。

这是**控制输入的证明缺口**，不是已独立证明的新实现缺陷：完整入口已经拒绝该包，没有出现错误接受，当前最先到达的是环检测。不能据此断言实现会放过坏内部头，也没有运行session或改头后试验。代码前六项证据继续成立，完整R5因第七项任务条件未满足仍为REWORK，而非把全部结果废弃或仅写BLOCKED等待不明条件。

首版静态核对另存[无效首版审计](../evidence/A03/review/P2-R5-registration-context/invalid-first-control-static-audit.json)：它向无event_version的legacy PLAN_ACCEPTED封闭payload增加evidence字段；固定Schema该分支没有此字段且additionalProperties=false，作者实际在$/frames/2/event得到SHAPE_oneOf，尚无DAG tail。原输入、stdout/stderr、退出1保留，没有再次调用首版Package。

执行任务准许最多一轮针对局部问题的修正。作者只改第七控制，复用原本就有Resource字段的冻结v3分支，没有改其版本、checker或旧样例；随后冻结残余，符合授权与停止条件，不能写成越权。八个作者结果中的overlay SHA全部仍是3f0281c5…；其余六例没有因这次修正重跑。

最小剩余范围建议：保留已接纳静态代码和前六项证据，由调度另派**只闭合这一控制输入**的任务，补正该内部前驱头及受影响的相关摘要/引用并先作纯数据一致性核对，再仅复验这个混合环。不得覆盖旧失败/修正版材料，也不需要重开接口设计、旧36矩阵、产品或native阶段。本轮未生成此修正版、改checker、追加候选或复测。

## 运行、保全与只读复现

九条有记录的自有命令为raw Git隔离、七例、事后数据审计，均已wait退出0、未超时，无后台worker/native session；审计不导入checker，Package新增调用为0。每条命令启动前保存entry源码/SHA与argv/cwd/限时，预先持久打开原始stdout/stderr，随后记录PID、退出及alive。加载源码与70份pins在每例前核对；PYTHONPATH移除，-X utf8 -B/PYTHONDONTWRITEBYTECODE=1。没有产品模块导入，七个包进程没有启动其他进程；隔离用的Git调用同步结束。

作者13个自有退出及流原样保存，仅case-07首版退出1，其余退出0；八个Package结果与一次局部控制修正分开记录。独立审阅没有工具失败、修后重试或未封装的包调用。[释放记录](../evidence/A03/review/P2-R5-registration-context/process-release.json)用父进程wait/return作为自有释放依据，没有扫描或终止他人进程、profile。

以下为后续只读复现方式，本轮封存时不再执行：

```powershell
python -X utf8 -B D:/1800/docs/evidence/A03/review/P2-R5-registration-context/input/checkout/examples/a03/P2-R5-registration-context/run_case.py registration-positive --readonly

# 实际仍应MIXED_CYCLE且退出0；这个退出码不消除上述输入残余
python -X utf8 -B D:/1800/docs/evidence/A03/review/P2-R5-registration-context/input/checkout/examples/a03/P2-R5-registration-context/run_case.py artifact-resource-frame-mixed-cycle --repair --readonly

# 只核对归档文件、记录和保全，不运行Package
python -X utf8 -B D:/1800/docs/evidence/A03/review/P2-R5-registration-context/scripts/archive.py
```

只新增本报告及本轮审阅目录。225份隔离输入及2,797份旧审阅文件终检字节不变；完整[SHA256清单](../evidence/A03/review/P2-R5-registration-context/sha256-manifest.json)覆盖原件、pins、脚本、七次流/退出、输入审计和报告，仅排除清单自身。[终检记录](../evidence/A03/review/P2-R5-registration-context/final-verification.json)列确切版本、范围、计数和限制。没有提交、推送、集成、改state或联系执行者/B/其他任务。

保留R4有限设计接受及此前R3/SESSION-02/CONVERSION-07有限静态接受；未重审无变化19接口。R17真实链、产品ABI/PRE运行接纳、oracle、原生profile、公共/B采用及I01均未放行。产品/planner/DB打开查询/native session、网络/浏览器/平台/profile/凭据/OCR/模型/付费API、安装依赖均未执行；旧DB只按文件字节保全，没有打开数据库。

字段重置专项保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，未复跑、变形、委派或建议再测。本轮按已证实残余冻结结束，由主调度决定最小后续范围。
'''
text=text.replace('@LOADER_SHA@',source_lookup['examples/a03/P2-R5-registration-context/load_static.py']).replace('@DRIVER_SHA@',source_lookup['examples/a03/P2-R5-registration-context/run_case.py'])
summary={'result':'A03_P2_R5_REVIEW_ARCHIVE_VERIFIED','overall':'REWORK','registration_context_and_target':'ACCEPTED_STATIC_LIMITED',
 'formal_evidence_and_global_resource_hash':'ACCEPTED_STATIC_LIMITED','mixed_cycle_control':'REWORK_CONTROL_INPUT_PROOF',
 'workflow':inputs['workflow'],'base':inputs['base'],'delivery':inputs['delivery'],'new_delivery_paths':205,'manifest_entries_verified':204,
 'old_git_paths_unchanged':28113,'raw_input_entries_verified':70,'frozen_inputs_unchanged':225,'old_review_files_unchanged':2797,
 'independent_Package_calls':7,'codes_matching_expectation':7,'qualified_scenarios':6,'invalid_first_control_reexecuted':False,
 'author_Package_results':8,'author_recorded_runs':13,'own_recorded_runs':9,'own_run_exits':[x['exit_code']for x in completions],
 'reviewer_tool_errors':0,'remaining_owned_background_workers':0,'old_36_matrix_or_session_conversion_product_DB_native_oracle_model_runs':0,
 'I01_released':False,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
if '--finalize'in sys.argv:
    assert not REPORT.exists()and not MANIFEST.exists()
    write(OUT/'mixed-reference-proof.json',cycle_proof)
    write(OUT/'process-release.json',{'owned_runs':completions,'author_exit_records_preserved':[{'name':x['name'],'pid':x['owned_pid'],'exit_code':x['exit_code'],'alive':x['alive']}for x in author_runs],
       'remaining_owned_background_workers':0,'native_sessions':0,'basis':'parent wait/return records; no process/profile scan','captured_at':datetime.now(timezone.utc).isoformat()})
    with REPORT.open('x',encoding='utf8',newline='\n')as f:f.write(text)
    write(OUT/'final-verification.json',dict(summary,captured_at=datetime.now(timezone.utc).isoformat()))
    files=[p for p in OUT.rglob('*')if p.is_file()]+[REPORT]
    write(MANIFEST,{'status':'FROZEN_BOUNDED_REVIEW_REWORK_WITH_LIMITED_STATIC_ACCEPTANCES','excluded_only':[MANIFEST.relative_to(ROOT).as_posix()],
       'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in sorted(files)]})
assert REPORT.read_text(encoding='utf8')==text
for link in re.findall(r'\]\(([^)]+)\)',text):assert (REPORT.parent/link).resolve().is_file(),link
assert not any(line.rstrip()!=line for line in text.splitlines())
manifest=load(MANIFEST);verify_files(manifest['files'],ROOT)
assert {p.relative_to(ROOT).as_posix()for p in OUT.rglob('*')if p.is_file()and p!=MANIFEST}|{REPORT.relative_to(ROOT).as_posix()}=={x['path']for x in manifest['files']}
assert manifest['excluded_only']==[MANIFEST.relative_to(ROOT).as_posix()]
print(json.dumps(dict(summary,archive_files=len(manifest['files']),report_sha256=sha(REPORT.read_bytes()),manifest_sha256=sha(MANIFEST.read_bytes())),ensure_ascii=False))
