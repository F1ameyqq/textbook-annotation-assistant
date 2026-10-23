"""Freeze this finite independent review without Git or active author reads."""
import datetime,hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/five-save-readiness-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def put(p,b):
 with p.open('xb') as f:f.write(b)
def entry(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def main():
 boundary=json.loads((P/'boundary-controls.json').read_bytes());plans=json.loads((P/'plans-review.json').read_bytes());outer=json.loads((P/'outer-review.json').read_bytes())
 assert boundary['status']==plans['status']=='PASS_OFFLINE_ONLY' and outer['status']=='ACCEPTED_STATIC_LAUNCH_CONDITIONS_ONLY'
 helper={'schema':'A25IndependentHelperErrors/v1','original_failures_preserved':3,'product_failures':0,'product_boundary_rerun':False,'errors':[
 {'attempt':1,'error':'AssertionError: assumed package member count20; actual19, matching accepted implementation hash','original_script':entry(S/'static_review.initial.py'),'record':entry(S/'static-review-helper-failure.json'),'raw_stderr_separately_retained':False,'original_tool_returned_error_retained_in_record':True},
 {'attempt':2,'error':'KeyError: historical A05 path is a reference; fixed command copy is exported under transport-revision/inputs','original_script':entry(S/'static_review.second.py'),'raw_stderr':entry(S/'static-review.stderr'),'process':entry(P/'static-review-process.json')},
 {'attempt':3,'error':'AssertionError: reviewer rebuilt absent-zone rect IDs in annotations storage order instead of image_order_in_annotation_zone; product plan is correctly ordered','original_script':entry(S/'static_review.third.py'),'raw_stderr':entry(S/'static-review-repaired.stderr'),'process':entry(P/'static-review-repaired-process.json')}],
 'repair_scope':'Only reviewer static helper; immutable inputs/product/native comparator unchanged. Frozen command copies resolved by declared SHA; zone rect IDs sorted by existing native image order.',
 'final_static_process':entry(P/'static-review-final-process.json'),'final_exit_code':0,'new_live_network_browser_saves':0}
 put(P/'helper-failures.json',enc(helper))
 report='''# A25 五题保存准备有限独立验收

结论：`ACCEPTED_OFFLINE_ONLY`；五个既有题目候选及计划可供根绑定新唯一 authority 后执行，外层仅接受静态启动条件。产品 `8990e1e3c7561bc7403eb29359f0d39ba3a54295`，包内19个Python成员摘要仍为 `5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8`。本报告不激活权限。实际五次保存与独立回读均 `NOT_RUN`。

120个根冻结成员及23个根提供Git原始blob摘要逐一核对；外层另7个原件核对。仅使用本独立私有隔离副本，没有读取作者活动目录、原profile或真实ledger，没有访问平台。主交付manifest SHA256 `128ee3d8e9eb00b0dc033c03b7654f1613fbad83dfeb05713f7e64eb4776ff67`；外层manifest SHA256 `e0f8f59981006cf6d729cc6eabb771a691c1e51ada99972c44dd98b41885abe5`。具体输入及独立产物见 `raw-manifest.json`。

书46007447，印刷1–5题、历史全局17–21、当前native18–22，五个稳定node/info互不重复且与当前第一课时17题不重合。实际父目录仍是原第1课时目录，语义课时标签不触发迁移。两个冻结历史JPEG已人工看图；当前页响应、URL/索引、历史command原件摘要与图像摘要闭合。没有声称远端图片像素新鲜度或既有crop URL的HTTP可用性。

|印刷题|native|内容与数学核对|改动区|
|---|---|---|---|
|1|18|四个直角三角形拼方形；面积恒等式推出c²=a²+b²，原正确答案保持|question|
|2|19|斜坡sqrt(1.5²+2²)=2.5 m，答案D，原四个选项保持|question、answer|
|3|20|树高8 m、断点3 m，落地距离4 m，在既有框补缺失文字和答案|question、answer|
|4|21|两孔中心水平80、竖直60，距离100 mm，原正确答案保持|question|
|5|22|2小时后东西/南北位移48、20 km，距离52 km，解答只去开头杂点|question、answer|

五份before均与接受的40GET原始响应按类型、对象键顺序及数组顺序相等。expected保留完整目录、全部76框、目标3/4/3/4/2框、完整info及未改OCR区；仅改指定文字。第1、5题既有图包含原文和图示，候选完整保留该图；其他题保留当前rect身份对应图。无上传、增删框、迁目录或插题。写入器仅容许目标info.updated_at在原规则下推进，不能扩展为其他字段变化。

最小修正只为runner的plan.json增加保序独占落盘、flush/fsync及重读validate_plan；core通用排序序列化和原生比较器没有削弱。独立边界实际走runner.execute，将全部五份计划落盘后，在第一个configure调用处由审查夹具主动截停；再以原字节重读并逐份调用真实writer.validate_inputs，5/5通过，落盘字节与作者冻结实际五份完全相同。未知路径拒绝，声明私有文件仅重定位到相同原字节副本；真实profile/ledger未触碰。覆盖旧文件被拒且原字节不变；旧排序方式仍被原guard以OCR_ABSENCE_NOT_PROVEN拒绝。该主动截停不是产品失败。未重复运行原成功套件，也未把作者新1/1、实际五计划验证、preflight-only重叠相加。

保留三次独立静态helper错误：错误假定20成员、历史原路径映射KeyError、重建缺失区rect顺序断言。前两者与第三者均只修helper，原脚本及可用错误输出/来源限制写入helper-failures.json；最终静态核对exit0，已通过产品边界未重跑。作者原错误预期PLAN_TAMPERED的AssertionError及命令引号SyntaxError按冻结文档保留；本包未单独冻结其原始初始stderr，不伪称已核其完整输出。历史不完整five-save-plans.json状态保留，当前准备状态以固定checkpoint、产品修正和实际原字节验证为准。

外层启动器SHA256 `940283e0336f2f3936f8f5d6372b90ef8294034e21d07177754077e49c5a5d62`；复用已接受owned_process监管器 `a1582782024994d841ddeadc0e2df6c8ef29a35bc8e428dcb4dd8b8cdc589ee8`。静态可见启动前核120原件及副本、固定checkpoint/manifest、清洁HEAD、runtime/监管器摘要、空ledger/锁和新输出；核新authority完整有限范围后记录intent并原子消费，再仅一次holder.run，总进程上限900秒。写入与TLS引用均替换为同一新authority。NOT_ACTIVATED模板和describe-only记录均不等同启动；本独立没有执行外层或新增产品测试。

根可据本报告完成绑定后直接调度：同一产品、checkpoint SHA256 `7f459e57b8c8d8b9b59a3c2c5b6b3ca162a3b5f2944f8392461acfcc014c4d70`、targets SHA256 `eb3b29c28c80650674f7df24e523dcc7c05e27b6713eda78dec92910b074d792`、本报告及根receipt原字节SHA。新唯一authority须为原profile、DIRECT、原exact leaf/SPKI，一轮五题串行，每题最多1POST及后续不同进程/新context完整回读：5writer+5reader、10context/惰性导航/TLS probe、120业务GET、最多5POST，整批900秒，首次异常停止且后继NOT_RUN，无重试/登录/上传/OCR重放/图下载/增删框/迁目录。泛型runner最多6题不改变本manifest的恰好5题绑定。

启动器只检查profile锁，没有实现占用进程查询；根须在激活前确认原profile独占。协调根报告2026-10-23T11:07:17.0006414Z按原profile精确路径查询msedge匹配0；这是根侧观察，本独立未复查。formal/root报告路径和SHA由根绑定，启动器本身不验证报告内容。writer进程退出、context/runtime释放后才启动独立reader；最终整批Job0/held identities证明整批OS释放，不能证明逐writer顺序OS子进程释放。实际收据、全部新鲜回读、原始stdout/stderr及最终整批释放仍须事后固定独立审查。

本独立审查已完成并释放。旧失败、UNKNOWN、所有耗尽额度保持；sole1800-a保持PAUSED。无Git提交、根状态或自动化变更。
'''
 put(P/'report.md',report.encode('utf-8'))
 result={'schema':'A25IndependentFiveSaveReadinessResult/v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer_thread_id':'01a166e8-3f23-7192-a560-4724adca74b1','status':'ACCEPTED_OFFLINE_ONLY','plan_decision':'ACCEPTED_FIVE_EXISTING_UPDATE_PLAN_FOR_ROOT_BINDING','outer_decision':'ACCEPTED_STATIC_LAUNCH_CONDITIONS_ONLY','product_commit':'8990e1e3c7561bc7403eb29359f0d39ba3a54295','implementation_sha256':'5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8','runtime_python_members':19,'primary_raw_members':120,'root_provided_git_blob_members':23,'outer_raw_members':7,'targets_manifest_sha256':'eb3b29c28c80650674f7df24e523dcc7c05e27b6713eda78dec92910b074d792','checkpoint_sha256':'7f459e57b8c8d8b9b59a3c2c5b6b3ca162a3b5f2944f8392461acfcc014c4d70','content_candidates_accepted':5,'actual_runner_disk_roundtrips_real_writer_inputs_pass':5,'counterexamples':{'overwrite_rejected':True,'old_sorted_plan_rejected':'OCR_ABSENCE_NOT_PROVEN'},'independent_helper_errors_preserved':3,'blocking_findings':[],'actual_five_save':'NOT_RUN','actual_five_independent_readback':'NOT_RUN','new_authority_activated_by_reviewer':False,'real_profile_ledger_access':False,'platform_requests_browser_saves':0,'outer_test_execution':0,'old_suites_rerun':False,'limits':{'batch_attempts':1,'writers':5,'readers':5,'contexts':10,'inert_navigations':10,'tls_probes':10,'business_json_gets':120,'max_post':5,'whole_batch_seconds_max':900,'retry':False},'root_before_activation':['Bind existing user authorization, unique new authority, exact fixed product/checkpoint/targets/launcher and this report SHA plus root receipt','Confirm original profile exclusive: root-reported exact-path msedge count0 at 2026-10-23T11:07:17.0006414Z; no independent reviewer repetition','Original empty ledger/locks, fresh output and clean product are enforced again by outer before spend'],'scope_limits':['Historical JPEG pixels bound to current metadata, remote pixel freshness/crop HTTP availability not asserted','Launcher report content binding is root responsibility','Whole-batch final Job0 does not prove sequential per-writer descendant OS release'],'report':entry(P/'report.md'),'review_released':True,'automation_1800_a':'PAUSED_UNCHANGED','old_failures_unknown_and_budgets_preserved':True}
 put(P/'result.json',enc(result))
 raw=[]
 for p in sorted(S.rglob('*')):
  if p.is_file():raw.append({**entry(p),'kind':'reviewer_private_frozen_input_or_control_output'})
 for p in sorted(P.iterdir()):
  if p.is_file() and p.name not in ('raw-manifest.json','review-files.sha256'):raw.append({**entry(p),'kind':'review_public_report_or_helper'})
 put(P/'raw-manifest.json',enc({'schema':'A25IndependentFiveSaveReviewRawManifest/v1','self_and_checksum_excluded':True,'primary_author_raw':120,'outer_author_raw':7,'primary_git_blob_raw_subset':23,'total_files':len(raw),'members':raw}))
 files=[p for p in sorted(P.iterdir()) if p.is_file() and p.name!='review-files.sha256']
 put(P/'review-files.sha256',(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in files)).encode())
 for item in raw:
  p=Path(item['path']);assert len(p.read_bytes())==item['bytes'] and sha(p.read_bytes())==item['sha256']
 print(json.dumps({'status':result['status'],'raw_files':len(raw),'public_files_plus_checksum':len(files)+1,'report':entry(P/'report.md'),'result':entry(P/'result.json'),'raw_manifest':entry(P/'raw-manifest.json'),'checksum':entry(P/'review-files.sha256')}))
if __name__=='__main__':main()
