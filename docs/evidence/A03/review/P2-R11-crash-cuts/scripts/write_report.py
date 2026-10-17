"""Generate a bounded report from completed immutable audits; no product calls."""
from pathlib import Path
from evidence import OUT,ROOT,WORK,TARGET,BASE,WF,load,sha,write
report=ROOT/'docs/tasks/A03-P2-R11-crash-cuts-review-report.md'
audit=load(OUT/'case-and-boundary-review.json');proc=load(OUT/'process-and-import-review.json')
cases=[c for c in audit['cases'] if c['label']=='independent'];root=Path(load(OUT/'independent-run.json')['run_root'])
history=load(OUT/'historical-preservation.json');relative='../evidence/A03/review/P2-R11-crash-cuts/'
def link(label,path):return '['+label+']('+relative+path+')'
lines=['# A03 P2-R11 四个崩溃切点独立验收','',
 '2026-10-18（Asia/Shanghai）。结论：**ACCEPTED_FOUR_CRASH_CUTS_ONLY**。本结论依据 exact target 的四例新独立执行与实际阶段原件，只关闭本次原 V02/R03 单题切点；whole A03 仍为 REWORK，产品本地集成及 I01 未放行，B 版本映射未共同确认。','',
 '**作者证据限制继续有效：F2/F3 切点、恢复前及正式 UNKNOWN 阶段没有独立 SQLite 二进制原件。其现有 SQL 全行、当时 raw SHA、事件和不可变 artifacts/Resource 可支持有限行为核对；不存在的原件无法重新哈希。本轮新独立证据不追溯修复作者遗漏，未要求作者重跑，也未重建中间库。**','',
 '## 固定输入和执行边界','',
 '- 唯一 target：`'+TARGET+'`；直接父提交/base：`'+BASE+'`。',
 '- 验收 workflow：`'+WF+'`；交接单 raw SHA256：`485724252e85c897810b21c91732301c4cb9dd8defc0a683975967ca365c6ef1`。',
 '- raw Git 校验580个新增 blobs、579个作者manifest条目，32413个旧 mode/type/blob 条目全部不变。'+link('逐文件核验','delivery-byte-index.json')+'。',
 '- '+link('输入登记','input-index.json')+'包含677份必要raw导出；新工作区77份源码/固定32×32单题两片段SYNTHETIC夹具/helper/输入索引种子，没有作者数据库或旧validation种子。'+link('工作区种子','isolated-source-index.json')+'。',
 '- 六个schema pins和23个implementation pins均核对。产品、profile/adoption、schema、oracle/producer/verifier、依赖未修改；零网络/平台/浏览器/profile/凭据/OCR/付费模型/安装/推送/B联系/A05题22/书级送交。用户model/thinking保留，无委派。','',
 '## 驱动、事务点和首次运行','',
 '正常 import 冻结 helper；完整复制R11驱动，仅添加独立根路径和阶段原字节采集，'+link('完整差异','driver-diff.patch')+'、'+link('首次功能前冻结','driver-preregistration.json')+'和'+link('静态核对','static-review.json')+'均保留。没有AST/exec裁剪、monkeypatch、SQL业务写入、伪造时钟/PID/lease/私有资格。','',
 '| 组 | 原FaultController切点 | 源码事务边界 |',
 '|---|---|---|',
 '| F1 | BEFORE_INTENT_COMMIT | storage:615，intent事务开始前；计划/动作已接受预留 |',
 '| F2 | AFTER_DISPATCH_STARTED | storage:1101，permit消费和DISPATCH_STARTED提交后、效果授权返回前 |',
 '| F3 | AFTER_READBACK_CAPTURE | recovery:116，执行observe_target返回后、commit_action_result前 |',
 '| F4 | AFTER_RECEIPT_COMMIT | storage:739，结果事务及正式receipt投影提交后、POST/Batch发布前 |','',
 'F1→F2→F3→F4各首轮一次，原FaultController真实os._exit90。父wait确认退出后才启动不同PID的新查询/恢复进程。父watchdog90秒、业务child45秒，产品观察2秒、屏障5秒、lease10秒及原恢复期限不变；F2/F3只走原claim_current有界等待。','',
 '| 组 | 父PID/exit | crash PID/exit | 新进程PID/exit | 效果 | 结果及实际plan状态 |',
 '|---|---|---|---|---|---|']
descriptions={'F1':'仅open/status/query；无intent/permit/receipt；RUNNING',
 'F2':'一次reconcile，ABSENT/NOT_APPLIED；INTERRUPTED','F3':'一次reconcile，MATCH/APPLIED；FINISHED','F4':'仅open/status/query；APPLIED正式回执保留；FINISHED'}
for c in cases:
    g=c['group'];parent=load(OUT/('result-'+g+'.json'))
    lines.append('| '+g+' | '+str(parent['pid'])+'/0 | '+str(c['processes']['crash']['pid'])+'/90 | '+str(c['processes']['query']['pid'])+'/0 | '+str(c['effects'])+' | '+descriptions[g]+' |')
lines+=['', 'F1未构造未尝试receipt或UNKNOWN。F4未project/reconcile、生成resolution或回退为未执行。两例查询前后runtime/target原字节相同；原死进程owner行generation1/ACTIVE按事实保留，未清锁。','',
 'F2/F3原intent、已消费permit和DISPATCH_STARTED留存，结果fact/receipt在切点尚未提交。先保存pending，再正常project_plan产生正式UNKNOWN，随后各一次reconcile、max_attempts=1。F2观察序列2→3，F3为3→4；新独立观察的store/session、target/source/scope、plan/action/digest/intent、observation/snapshot、readback和正式resolution逐项核对。两例原UNKNOWN保留，前后attempt_fact均为MAY_HAVE_BEEN_ATTEMPTED，旧动作不重发，效果分别保持0和1。F4实际attempt_fact=ATTEMPTED。','',
 '四例POST=0、Batch=0、native_report_reads=0；未补发布或把缺失报告填为成功。所有正式plan/intent/progress/receipt/resolution四元组、SQL登记、当前bundle、原实体及fact/Resource SHA均与实际文件一致，详见'+link('双库与正式边界','case-and-boundary-review.json')+'。','',
 '## 实际阶段保全与证据层级','',
 '独立驱动在首次运行前已冻结采集路径。每例pre-fault、父wait后cut、查询/恢复后各保存双库原字节；F2/F3另在pending-before-projection和UNKNOWN-before-reconcile各保存双库。共32份实际阶段SQLite原件，均附完整SQL、SHA、PID、纳秒时序和writer/keeper状态。pre-fault自己的keeper仍存在；其余阶段无活跃writer/keeper。双库按顺序读取，不称跨库原子快照；实际均无journal/wal/shm sidecar。没有从SQL重建数据库。','',
 '下表SHA为最终原库；阶段原件和采集元数据均在对应cases/F*/stages/目录。独立32份阶段原件，加作者/独立实际pre-run与最终库，共64次自有复制后immutable/query_only SQL审计，quick_check均ok、读前后SHA相同；没有连接作者活动库。','',
 '| 组 | 最终runtime raw SHA256 | 最终target raw SHA256 | 阶段目录 |',
 '|---|---|---|---|']
for c in cases:
    g=c['group'];final=load(root/(g+'-final-SQL.json'))
    stage=(root/'cases'/g/'stages').relative_to(OUT).as_posix()
    lines.append('| '+g+' | `'+final['runtime']['raw_sha256_before']+'` | `'+final['target']['raw_sha256_before']+'` | '+link(g+'原件',stage)+' |')
lines+=['','正式引用抽样（完整四元组和Resource见双库审计）：','', '| 组 | plan / PRE | receipt / resolution |','|---|---|---|']
for c in cases:
    g=c['group'];before=load(root/'cases'/g/'before-run.json')
    def fmt(r):return '`'+r['artifact_id']+'` / `'+r['content_hash']+'`'
    end=c['terminal'];terminal='无正式结果，不伪造'
    if end:terminal=fmt(end['receipt_ref'])+('；'+fmt(end['resolution_ref']) if 'resolution_ref' in end else '')
    lines.append('| '+g+' | '+fmt(before['plan_ref'])+'；'+fmt(before['pre_ref'])+' | '+terminal+' |')
lines+=['', '作者F1/F4最终字节与其切点记录一致，可重新核验。作者F2/F3只对其实际存在的pre-run和最终二进制重新核验；中间阶段仅核对SQL/事件/正式引用等现存证据，不声称缺失的中间SHA已重算。'+link('作者原保全声明','input/target/docs/evidence/A03/execution/P2-R11-crash-cuts/stage-binary-preservation.json')+'保持原样。新独立32份阶段原件满足本次独立复验的阶段保全要求；作者归档完整性限制不被这一有限接受覆盖。','',
 '## 进程、归档和复现','',
 '作者19条实际进程记录、四个exit90以及源文件/正常导入记录均经raw冻结文件核对；本轮所有实际登记Popen子进程逐项核对wait/exit/timeout/alive及真实原始输出。os._exit不执行finally，四个crash-exit imports确实不存在；使用实际故障前before-run imports，不补造退出记录。独立观察worker以精确源码快照、request SHA、parent PID、stdout PID/观察正文及SQLite原行交叉核对。'+link('进程和实际导入','process-and-import-review.json')+'。','',
 '功能失败/超时/重跑均0。一次归档静态纠正：首次进程审计把包含4个附加Resource/路径字段的返回包装与持久化观察正文直接判等，导致审计脚本exit1；原源码、stderr和完成记录保留。依据persistent.py:476–479修正为正文逐字段一致，并验证四个附加字段和Resource原字节/SHA/JSON；第二次纯文件审计exit0，没有重调产品、功能驱动或数据库。'+link('唯一纠正记录','post-functional-metadata-correction.json')+'和'+link('首错','runs/process-audit-01/stderr.log')+'。两次只读路径探查未命中文件的工具错误另见'+link('原探查记录','read-only-probe-note.json')+'，未创建缺失文件或伪造PID/分离流。','',
 '历史9079份review文件/报告共276681374字节保持原SHA，排序清单摘要`'+history['inventory_sha256']+'`。'+link('历史保全','historical-preservation.json')+'。固定输入和77份种子读前读后原样；只新增本报告与本轮review目录，不改调度state，不提交、不推送。','',
 '本次实际命令在D:/1800按下列顺序执行（exclusive输出，已存在路径不可覆盖；不是追加功能轮次授权）：','', '```powershell',
 "$py='C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe'",
 "$r='D:/1800/docs/evidence/A03/review/P2-R11-crash-cuts/scripts'",
 '& $py -X utf8 -B "$r/run_recorded.py" freeze-01 90 "$r/freeze.py"',
 '& $py -X utf8 -B "$r/run_recorded.py" static-preparation-01 45 "$r/prepare_review.py"',
 '& $py -X utf8 -B "$r/run_group.py" F1', '& $py -X utf8 -B "$r/run_group.py" F2', '& $py -X utf8 -B "$r/run_group.py" F3', '& $py -X utf8 -B "$r/run_group.py" F4',
 '& $py -X utf8 -B "$r/run_recorded.py" boundary-audit-01 90 "$r/audit_review.py"',
 '& $py -X utf8 -B "$r/run_recorded.py" process-audit-01 45 "$r/process_review.py" # first metadata failure preserved',
 '& $py -X utf8 -B "$r/run_recorded.py" correction-record-01 30 "$r/record_correction.py"',
 '& $py -X utf8 -B "$r/run_recorded.py" process-audit-02 45 "$r/process_review.py" # file-only correction, no product calls',
 '& $py -X utf8 -B "$r/seal_review.py"', '```','',
 '最终'+link('进程释放证明','process-release.json')+'、'+link('最终核验','final-verification.json')+'及'+link('SHA256 manifest','sha256-manifest.json')+'覆盖本报告和全部新增文件，仅manifest排除自身。最终工具回执提供报告/manifest/释放证明完整SHA，避免自引用。','',
 '## 有限结论','',
 '**ACCEPTED_FOUR_CRASH_CUTS_ONLY**：只接受本次四个原V02/R03单题崩溃切点的新独立证据。旧AFTER_INTENT_COMMIT、丢回执N1、R9/R10、旧R3 N7、其他故障点和整套回归未运行；多动作/混合尾段及其他原清单缺口未由本轮自动豁免。whole A03=REWORK；产品本地集成、INTEGRATED登记和I01均未放行，最终由调度核验登记。B映射未共同确认。','',
 '字段重置始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，未运行、变体、委派或建议重测。','']
with report.open('x',encoding='utf8',newline='\n') as f:f.write('\n'.join(lines))
write(OUT/'coverage-map.json',{'status':'ACCEPTED_FOUR_CRASH_CUTS_ONLY','target':TARGET,'base':BASE,
 'cases':[{'group':c['group'],'independent_rounds':1,'effects':c['effects'],'actual_plan_status':c['plan_status'],'reconcile_calls':c['result']['reconcile_calls']} for c in cases],
 'author_F2_F3_missing_intermediate_binaries':'LIMIT_REMAINS_NOT_RETROACTIVELY_REPAIRED',
 'functional_failures':0,'functional_reruns':0,'post_functional_static_metadata_corrections':1,'first_metadata_failure_preserved':True,
 'whole_A03':'REWORK','local_product_integration_released':False,'I01_released':False,'B_mapping_jointly_confirmed':False,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(__import__('json').dumps({'report_sha256':sha(report.read_bytes()),'status':'ACCEPTED_FOUR_CRASH_CUTS_ONLY','product_calls':0}))
