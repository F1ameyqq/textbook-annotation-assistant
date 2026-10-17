"""Finalize or read-only verify the bounded review archive, never run a checker."""
import collections
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/tasks/A03-P2-R3-evidence-closure-review-report.md'
MANIFEST=OUT/'sha256-manifest.json'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,value):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def check_files(items,base):
    for x in items:
        raw=(base/x.get('file',x.get('path'))).read_bytes()
        assert len(raw)==x['bytes']and sha(raw)==x['sha256'],x
        if 'raw_git_sha1'in x:
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==x['raw_git_sha1']

inputs=load(OUT/'input-index.json');check_files(inputs['files'],OUT)
assert len(inputs['files'])==161
assert {p.relative_to(OUT).as_posix()for p in(OUT/'input').rglob('*')if p.is_file()}=={x['file']for x in inputs['files']}
guard=load(OUT/'protected-old-review-files.json')['files'];check_files(guard,ROOT);assert len(guard)==2346
delivery=load(OUT/'delivery-byte-index.json')
assert delivery['added_paths']==126 and delivery['author_manifest_entries']==125 and delivery['unchanged_old_git_paths']==27876
stage=OUT/'input/checkout';ev=stage/'docs/evidence/A03/execution/P2-R3-evidence-closure'
# Independently tie the 11 author-copied workflow inputs to raw source Git blobs.
author_inputs=load(ev/'input-index.json')['frozen_workflow_inputs'];assert len(author_inputs)==11
specs=[x['commit']+':'+x['path']for x in author_inputs]
raw=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=('\n'.join(specs)+'\n').encode(),
 stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
pos=0
for x in author_inputs:
    end=raw.index(b'\n',pos);head=raw[pos:end].decode().split();pos=end+1
    assert head[1]=='blob';size=int(head[2]);body=raw[pos:pos+size];pos+=size
    assert raw[pos:pos+1]==b'\n';pos+=1
    assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+body).hexdigest()==head[0]
    assert size==x['bytes']and sha(body)==x['sha256']and body==(stage/x['copy']).read_bytes()
assert pos==len(raw)

result=load(OUT/'independent-static-results.json');assert result['conclusion']=='ACCEPTED_STATIC_LIMITED'
assert len(result['direct_controls'])==10 and sum(x['actual']=='STATIC_ACCEPTED'for x in result['direct_controls'])==3
assert len(result['independent_differential_controls'])==3 and result['total_whole_package_calls']==28
assert result['R2_matrix_once']=={'records':36,'classification':{'STATIC_ACCEPTED':7,'EXPECTED_STATIC_REJECTION':23,'STATIC_MATCH':1,'EXPECTED_STATIC_MISMATCH':5},'whole_package_calls':15}
matrix=load(OUT/'r2-regression/static-results.json')['records'];assert len(matrix)==36
assert dict(collections.Counter(x['result']for x in matrix))==result['R2_matrix_once']['classification']
for x in result['loaded_sources']:assert sha((stage/x['path']).read_bytes())==x['sha256']
original=load(OUT/'original-counterexample.json')
assert original['bundle_raw_sha256']=='b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653'
assert original['actual']=='UNDECLARED_REFERENCE'and len(original['hashes']['correct_artifact_hashes'])==16 and not original['hashes']['stale_artifact_hashes']
assert len(original['consumer_failures'])==13 and original['new_receipt_trace']
direct=load(OUT/'independent-controls/receipt-first-same-original-values/result.json')
assert direct['error']=={'code':'UNDECLARED_REFERENCE','path':'r2-static-complete-receipt'}and direct['all_artifact_hashes_correct']
assert load(OUT/'formal-field-verification.json')['all_17_verified']
assert load(OUT/'controls/formal-evidence-mixed-cycle.json')['hashes']['stale_artifact_hashes']==['r3-neutral-leaf']
assert load(OUT/'reviewer-driver-recovery.json')['completed_controls_rerun']is False
assert load(OUT/'reviewer-driver-second-recovery.json')['completed_controls_rerun']is False
run_names=['freeze-01','static-01','static-02','static-03'];exits=[]
for name in run_names:
    directory=OUT/'runs'/name;registration=load(directory/'registration.json');completion=load(directory/'completion.json')
    assert sha((directory/'entry-source.py').read_bytes())==registration['entry_sha256']
    assert completion['pid']==load(directory/'started.json')['pid']
    assert not completion['timed_out']and not completion['alive_after_wait'];exits.append(completion['exit_code'])
assert exits==[0,1,1,0]
assert load(OUT/'process-release.json')['pid']==load(OUT/'runs/static-03/completion.json')['pid']
assert (OUT/'scripts/review_static.attempt-01.py').read_bytes()==(OUT/'runs/static-01/entry-source.py').read_bytes()
assert (OUT/'scripts/review_static.attempt-02.py').read_bytes()==(OUT/'runs/static-02/entry-source.py').read_bytes()
assert result['R17_version_bridge']=='BLOCKED'and result['registration_derived_scope_positive']=='BLOCKED_NOT_POSITIVELY_VERIFIED'
assert result['oracle_adopted']is False and result['I01_released']is False and result['field_reset']=='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'

text='''# A03 P2-R3 EvidenceRecord 消费者闭包独立复验报告

2026-10-17，Asia/Shanghai。本轮唯一结论：**ACCEPTED_STATIC_LIMITED（EvidenceRecord 消费者闭包）**。冻结交付的 `R2-SCOPE-EVIDENCE-ID-01` 已在修正后的完整包入口按消费者声明拒绝，并独立确认新1.3 receipt的真实消费路径。不是A03整体功能验收、公共合同或native采用；R17版本桥接和登记推导scope正包继续阻断，oracle未采用，I01不释放。

## 固定版本与原字节

| 项目 | 精确版本或SHA256 |
| --- | --- |
| 本轮复验workflow | `3ad5269fdb87802cc56c2c171e4ba69d8efafab0` |
| base | `526d264284f36f856c306db88c1d7e71c04152e1` |
| 交付 | `87606b73e0754fa670491d9fb958a416c26bfe88` |
| 执行workflow | `c3b5f38c7e9a3a4a51ae8cbe16a3821ff2f36970` |
| 复验任务单SHA256 | `32f94a69537080e62624a5870820e144267e6a4584f275a8829cd1a2cec5f197` |
| 执行报告SHA256 | `c4831f0ceec0036b0bccfcc596a4a704b802f6a0ed31b9a500d341b52a0bc328` |
| 作者清单SHA256 | `16909b0445495e8a1dbbc0af8831947a06907c29714cbe8a8e6d218aeee64d72` |
| R2 profile SHA256（不变） | `f7385ba20090b5df8aa062c417e3d5c66a889a30f464facff994d9929b94f9ea` |

先读固定workflow的[复验任务](../evidence/A03/review/P2-R3-evidence-closure/input/workflow/docs/tasks/A03-P2-R3-evidence-closure-review-handoff.md)、执行任务、R2报告/调度收口、前检及架构/合同/coordination。保留用户当前思考设置，未据历史xhigh调整；没有委派智能体或联系其他对话。

通过一次 `git cat-file --batch` 逐blob核对125个清单项及清单自身共126新文件；27,876旧Git路径的mode/type/blob均不变，新增路径只在授权三处。原字节SHA1、长度及SHA256见[交付字节索引](../evidence/A03/review/P2-R3-evidence-closure/delivery-byte-index.json)。执行工作树干净、五个自有运行结束来自冻结前检及执行记录，不冒充当前OS或profile扫描。

[输入索引](../evidence/A03/review/P2-R3-evidence-closure/input-index.json)导出161份必要输入到 `D:/1800/docs/evidence/A03/review/P2-R3-evidence-closure/input/`，包括53份固定R2输入及当前源码/控制/诊断；没有复制7MB历史baseline、产品planner或历史证据全集。11份作者workflow副本另与原执行workflow raw Git逐字节核对。原反例也与复验workflow副本独立比对。未合浮动主树、未触碰执行工作树。

## 实际加载及唯一入口

| 实际加载源码 | SHA256 |
| --- | --- |
| `examples/a03/P2-R3-evidence-closure/closure.py` | `ff650507bca971f8c9418a09e6e4f8df7c7691016841ffe7bd15ff66382579a5` |
| 固定R2 `check.py` | `7bf3ea27424f7afaf3d3b264d2ab3d0bfa0fdc8bba1c178e6f488bef09e6257b` |
| 固定R2 `schema_check.py` | `9630d7e2e0d3700080f7a97a9c883877acf27929be82a41ed5a8f041240ccf7c` |
| 固定R2 `oracle_verifier.py` | `6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d` |
| 原最短 `replay.py` | `f208986004498e67f41005510b28f6a79f208863a6061bb4b9b3569347cd8902` |

先完整阅读覆盖层、controls与replay，确认只用stdlib和固定静态依赖；R2依赖与上轮已审字节相同。未运行作者controls生成器，只对冻结控制值调用修正后的 `closure.Package.validate`，原最短replay执行一次；R2模块的Package指向同一覆盖类，矩阵中的15次完整包调用也经过它。其余条目是既有局部字段诊断，不冒称全包功能测试。

为原件只读，加载时只将覆盖层唯一的输出mkdir重定向到本轮目录，随后重定向R2 EVID；未更改任何加载源码或验证分支。PYTHONPATH移除，使用 `-X utf8 -B` 及PYTHONDONTWRITEBYTECODE=1。输入161文件在结束时全部保持原字节、文件集合不变。

## 原反例闭合与新receipt独立定位

原bundle SHA256=`b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653`；inner=`ebd3f42cc53726b05919f27e6ee7b3866cbff7c36454473fe8dfda85e10b33af`；outer=`e14cf14a7a585ad528f7f01807d26a205cfa227c94a23dd51ff537f079dc32f6`。16个Artifact内容摘要独立重算全部相等，资源raw SHA、版本及四元组正确；没有改版本、删除证据或靠损坏摘要拒绝。

原最短回放实际 `UNDECLARED_REFERENCE at origin-a-SourceBundle`，进程内期待拒绝匹配为退出0。同一次全包扫描已记录13个不合规消费者，新1.3 receipt的确切路径是：

`r2-static-complete-receipt/results/0/before_evidence_refs → EvidenceRecord(proof) → outer.json → inner.json → review-isolated-source-b`。

receipt属于original-a，目标属于original-b，且自身未声明该普通ref。该路径不含typed frame。详见[原例实际诊断](../evidence/A03/review/P2-R3-evidence-closure/original-counterexample.json)。

另作一个有界定位控制：仅将同一原包的receipt排列到首位，所有Artifact值/摘要、资源、版本均保持；完整入口明确报 `UNDECLARED_REFERENCE at r2-static-complete-receipt`。因此结论不只依据旧Source先报错，也不是只调用旁路辅助函数。[独立差量结果](../evidence/A03/review/P2-R3-evidence-closure/independent-controls/receipt-first-same-original-values/result.json)同时保存实际 `Artifact → E:proof → outer Resource → inner Resource → Artifact` 图边。

## 有界控制及真实分类

原例加作者其余九份冻结控制只复核一次：3项静态接受、7项预期静态拒绝。每份实际结果、必要资源和声明上下文均留档；一项duplicate-ID分类按下文说明从已执行断言控制流恢复。

| 控制 | 实际结果 |
| --- | --- |
| 原反例 | UNDECLARED_REFERENCE，新receipt路径已观察 |
| 合法递归JSON evidence、同scope且声明完整 | STATIC_ACCEPTED |
| 普通消费者漏声明 | UNDECLARED_REFERENCE |
| 同资源两个消费者、另一scope | ORDINARY_SCOPE，两者独立trace |
| 正式ID缺失／重复 | EVIDENCE_ID_MISSING／EVIDENCE_ID_DUPLICATE |
| 正式证据进入混合环 | MIXED_CYCLE，存在故意未重算leaf摘要，限图阶段定位 |
| 普通JSON内同名字符串 | STATIC_ACCEPTED，不自动成为正式ID |
| typed frame消费scope-b正式证据 | STATIC_ACCEPTED，沿frame自己的scope和声明 |
| 上述frame漏自己的声明 | UNDECLARED_REFERENCE |

混合环控制只证明图检测先于最终内容摘要检查；不能称为摘要自洽的完整循环包。原反例、合法正包及其余控制独立核对的Artifact摘要正确。typed frame中Resource内完整Artifact的正式字段沿实际frame消费者展开，其自带scope不另生消费者边界；frame到EvidenceRecord可以经过Resource，不能要求必须直接连边。

另外三个小差量控制均按预期拒绝：①receipt优先的同一原例；②同scope的第二消费者去掉自己的声明，首个消费者声明完整仍不能替代它；③正式Schema字段换为未登记ID，由该字段的EVIDENCE_ID_MISSING定位。不是新反例、大候选或native实验。

[正式字段核对](../evidence/A03/review/P2-R3-evidence-closure/formal-field-verification.json)逐一解引用冻结Schema的17个唯一指针，确认它们是Identifier数组，且与覆盖层registry精确集合一致。Source/PageMapping、Region/CoverageClue、AnswerRelation、Snapshot/Capability、CheckResult/Issue、ActionResult、旧Batch提交证据等按定义解析；Resource型evidence不误当ID，未知JSON同名字段不赋予正式语义。

既有R2矩阵仅运行一次，分类保持7 STATIC_ACCEPTED、23 EXPECTED_STATIC_REJECTION、1组五项STATIC_MATCH、5逐项STATIC_MISMATCH；不是36项功能通过，不另加五比较凑数。[独立汇总](../evidence/A03/review/P2-R3-evidence-closure/independent-static-results.json)与[原矩阵输出](../evidence/A03/review/P2-R3-evidence-closure/r2-regression/static-results.json)保留原分类。两scope/typed frame正包及scope、声明、跨书、伪frame、混合环、SESSION-02和CONVERSION-07关联值维持预期。总计28次唯一全包调用：十个直接控制、三个独立差量、矩阵内十五次；其余矩阵条目是局部检查。

## 审阅工具失败、原始流与释放

两个审阅驱动错误完整保留，均不归为交付缺陷，也不记为成功进程：

1. static-01退出1：路径写成WindowsPath加str。已完成原例和duplicate-ID控制，后者在实际值等于期待值的断言及摘要计算之后，写文件时报错；该分类从冻结源码、原始traceback与控制顺序恢复，未冒称当时已有独立JSON/stdout结果。原例有独立stdout和完整诊断。
2. static-02退出1：补完剩余八个直接控制后，额外审阅断言误要求frame直接指向EvidenceRecord，忽略中间Resource。八项结果已持久化；未以这个错误图断言否定交付。

保留[首错续接记录](../evidence/A03/review/P2-R3-evidence-closure/reviewer-driver-recovery.json)、[第二错续接记录](../evidence/A03/review/P2-R3-evidence-closure/reviewer-driver-second-recovery.json)、原始源码快照及stderr。static-03只继续三个未运行差量、字段核对和一次矩阵，退出0；没有重跑已经完成的十个控制，也没有再次执行矩阵。两次失败仍列在完整清单，结果恢复的证据限制明确保留。

四条有记录命令依次为freeze-01/static-01/static-02/static-03，退出码0/1/1/0，均未超时、父进程wait已确认结束；PID及argv/cwd、启动前源码SHA、原始stdout/stderr分别在runs目录。静态驱动没有自建子进程或后台worker，Git导出只启动已同步结束的只读Git命令。没有全系统/profile扫描或终止他人进程。[释放记录](../evidence/A03/review/P2-R3-evidence-closure/process-release.json)与父进程completion共同构成自有运行释放证据。

原最短replay在static-01中从固定文件实际加载。只读复现包装如下；它只抑制导入时输出mkdir，不修改验证源码，符合期待拒绝时退出0。该新包装提供复现入口，本轮没有为包装再次运行已完成控制。

```powershell
python -X utf8 -B D:/1800/docs/evidence/A03/review/P2-R3-evidence-closure/scripts/replay_frozen.py

# 只核对归档，不运行静态检查器或产品
python -X utf8 -B D:/1800/docs/evidence/A03/review/P2-R3-evidence-closure/scripts/archive.py
```

## 限制与冻结结论

仅本轮EvidenceRecord消费者闭包给ACCEPTED_STATIC_LIMITED。有限Schema解释器、固定合成样例和既有oracle比较不构成全JSON Schema认证、真实质量验收或native资格。SESSION-02、CONVERSION-07原有限静态接受保留；真实锁/fence/读取/持久计数/lease/唯一约束/CAS、转换与重开均NOT_EXECUTED。

R17新1.3初始/PRE与旧1.1 observation bridge没有获准兼容合同，仍BLOCKED；登记推导scope仍BLOCKED_NOT_POSITIVELY_VERIFIED。没有补登记分支正包、adapter、新profile或跨侧合同。oracle不采用，A03功能未接受，I01不释放。

产品/planner/DB查询/native session、网络/浏览器/平台/profile/凭据/OCR/模型/依赖安装、提交推送集成及联系其他任务/B均未执行。旧DB只按原字节哈希保全，没有打开数据库。既有字段重置专项保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，未复跑、变形、委派或建议再测。

只新增本报告及本轮审阅目录，旧审查材料2,346文件及161输入结束时字节保持。完整产物含失败、原件、脚本、差量、日志、退出及报告列于[SHA256清单](../evidence/A03/review/P2-R3-evidence-closure/sha256-manifest.json)，仅排除清单自身；[终检记录](../evidence/A03/review/P2-R3-evidence-closure/final-verification.json)列冻结核对结果。本轮到此冻结结束，由主调度决定后续范围。
'''

def report_checks():
    body=REPORT.read_text(encoding='utf8')
    assert body==text
    assert not any(line.rstrip()!=line for line in body.splitlines())
    for target in re.findall(r'\]\(([^)]+)\)',body):
        assert (REPORT.parent/target).resolve().is_file(),target

summary={'result':'A03_P2_R3_REVIEW_ARCHIVE_VERIFIED','conclusion':'ACCEPTED_STATIC_LIMITED',
 'scope':'EvidenceRecord consumer closure only','workflow':inputs['workflow'],'base':inputs['base'],'delivery':inputs['delivery'],
 'raw_added_paths_verified':126,'author_manifest_entries':125,'old_git_paths_unchanged':27876,
 'author_workflow_inputs_raw_verified':11,'R2_input_pins':53,'frozen_inputs_unchanged':161,'old_review_files_unchanged':2346,
 'direct_controls':{'STATIC_ACCEPTED':3,'EXPECTED_STATIC_REJECTION':7},'additional_bounded_controls':3,
 'matrix_once':result['R2_matrix_once'],'whole_package_calls':28,'reviewer_driver_errors_preserved':2,
 'duplicate_ID_result_basis':'asserted control flow at first reviewer output-write error, recovered without rerun',
 'owned_recorded_run_exits':exits,'remaining_owned_background_workers':0,'native_functions':'ALL_NOT_EXECUTED',
 'oracle_adopted':False,'I01_released':False,'R17':'BLOCKED','registration_scope':'BLOCKED_NOT_POSITIVELY_VERIFIED',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
if '--finalize'in sys.argv:
    assert not MANIFEST.exists()and not REPORT.exists()
    with REPORT.open('x',encoding='utf8',newline='\n')as f:f.write(text)
    write(OUT/'final-verification.json',dict(summary,captured_at=datetime.now(timezone.utc).isoformat()))
    paths=[p for p in OUT.rglob('*')if p.is_file()]+[REPORT]
    write(MANIFEST,{'status':'FROZEN_INDEPENDENT_STATIC_LIMITED_REVIEW','excluded_only':[MANIFEST.relative_to(ROOT).as_posix()],
     'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in sorted(paths)]})
report_checks()
manifest=load(MANIFEST);check_files(manifest['files'],ROOT)
assert {p.relative_to(ROOT).as_posix()for p in OUT.rglob('*')if p.is_file()and p!=MANIFEST}|{REPORT.relative_to(ROOT).as_posix()}=={x['path']for x in manifest['files']}
assert manifest['excluded_only']==[MANIFEST.relative_to(ROOT).as_posix()]
print(json.dumps(dict(summary,archive_files=len(manifest['files']),report_sha256=sha(REPORT.read_bytes()),manifest_sha256=sha(MANIFEST.read_bytes())),ensure_ascii=False))
