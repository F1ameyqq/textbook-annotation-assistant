"""Seal already-completed independent evidence. No product imports/runs or Git mutation."""
import ast
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
sha = lambda data: hashlib.sha256(data).hexdigest()
read = lambda name: json.loads((OUT / name).read_bytes())
def write(name, value):
    raw = (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')
    with (OUT / name).open('xb') as stream:
        stream.write(raw)

pre = read('raw-preflight.json')
frozen = read('independent-freeze.json')
suite = read('run/suite-result.json')
release = read('run/independent-release.json')
command = read('command-result.json')
assert suite['status'] == 'PASS_FINITE_OFFLINE_DELTA' and suite['first_unexpected_failure'] is None
assert command['exit_code'] == 0
assert release['state'] == 'RELEASED' and release['remaining_independent_delta_runs'] == 0
assert all(suite['cases']['D' + str(i)]['status'] == 'PASS' for i in range(1, 9))
for member in frozen['frozen_output_inputs']:
    assert sha((OUT / member['path']).read_bytes()) == member['sha256']
for member in frozen['fixed_product_inputs']:
    assert sha((ROOT / member['path']).read_bytes()) == member['sha256']
local_input_set = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
                         if p.is_file() and 'review-output' not in p.relative_to(ROOT).parts)
assert local_input_set == sorted(i['path'] for i in pre['inputs'])

def assignments(path):
    result = {}
    for node in ast.parse(path.read_bytes()).body:
        if isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets):
            result[','.join(t.id for t in node.targets)] = ast.dump(node.value, include_attributes=False)
    return result
old_assign = assignments(ROOT / 'tools/headless_native_reuse_probe.py')
new_assign = assignments(ROOT / 'tools/headless_native_reuse_probe_r1.py')
changed_constants = [k for k in old_assign if old_assign[k] != new_assign.get(k)]
assert changed_constants == ['MANIFEST']
postrun = {
    'status': 'PASS', 'fixed_raw_inputs_rehashed': len(pre['inputs']),
    'changed_raw_inputs': [], 'frozen_review_files_rehashed': len(frozen['frozen_output_inputs']),
    'changed_frozen_review_files': [], 'input_file_set_still_exact_53': True,
    'changed_module_assignments': changed_constants,
    'unchanged_module_assignments': sorted(k for k in old_assign if k not in changed_constants),
    'protected_semantics': 'Original LIVE_OUT/PROFILE_ROOT/TARGET/allowlist/deadline constants unchanged; protected functions equal AST.',
}
write('postrun-integrity.json', postrun)
status = 'ACCEPTED_PREPARATION_FOR_ONE_REUSE_ONLY_OBSERVATION'
at = datetime.now(timezone(timedelta(hours=8))).isoformat()
report = {
    'schema_version': 1, 'task': 'A12-R1 formal independent finite offline acceptance',
    'at': at, 'review_thread_id': suite['review_thread_id'], 'host_id': 'local',
    'status': status, 'qualification_scope': 'R01/R02 fixed-candidate finite offline preparation only',
    'live_authorized_by_this_review': False, 'platform_acceptance': False,
    'source_product_commit': '7f3d42e31be29782f0e09e6c01cc8e277387747c',
    'source_final_commit': pre['source_final_commit'], 'workflow_commit': pre['workflow_commit'],
    'product_commit': pre['product_driver_commit'], 'author_driver_commit': pre['product_driver_commit'],
    'final_commit': pre['final_commit'], 'raw_root': str(ROOT), 'output_root': str(OUT),
    'candidate_manifest_sha256': pre['candidate_manifest_sha256'],
    'delivery_manifest_sha256': pre['delivery_manifest_sha256'],
    'independent_freeze_sha256': sha((OUT / 'independent-freeze.json').read_bytes()),
    'independent_driver_sha256': sha((OUT / 'independent_suite.py').read_bytes()),
    'protocol_child_driver_sha256': sha((OUT / 'protocol_child.py').read_bytes()),
    'input_raw_manifest': 'raw-preflight.json', 'output_raw_manifest': 'raw-output-manifest.json',
    'identity_verification': {
        'raw_inputs': 53, 'new_paths': 31, 'original_A12_files': 22,
        'old_members_preserved': 31181, 'old_changed': 0, 'original_baseline_members': 31159,
        'candidate_members': 21, 'delivery_nonself_members': 30,
        'lineage': '0c30b365 -> d45ed25a -> 81fab23e',
        'method': 'Independent ls-tree -rz mode/type/OID comparison; each of 53 local raw files equals final cat-file blob; SHA/size/tree checks; no lazy fetch.',
        'input_and_driver_hashes_unchanged_after_run': True,
    },
    'checks': [
        {'id': 'C01', 'status': 'PASS', 'item': 'Fixed raw identity and preservation',
         'evidence': ['raw-preflight.json', 'postrun-integrity.json'],
         'conclusion': '31 added paths within author allowlist; all 31,181 old members and 22 original A12 raw files preserved. Candidate/final and delivery identities match.'},
        {'id': 'C02', 'status': 'PASS_STATIC', 'item': 'R01/R02-only product scope and unchanged gates',
         'evidence': ['independent-product-delta.diff', 'raw-preflight.json:ast_same/ast_changed', 'postrun-integrity.json'],
         'conclusion': 'Only MANIFEST assignment changes. NativePolicy/open_owned/close_owned/profile_binding/OwnedJob/supervise/worker_main and Fetch/child/install methods equal original AST. Route/WS exception changes route through first-error retention; stopped assignments add terminal-state bookkeeping. Original TLS, allowlist, original shared LIVE_OUT/markers, profile and Job boundaries remain.'},
        {'id': 'C03', 'status': 'PASS_FINITE_OFFLINE', 'item': 'R01 Windows framing and eight rejects',
         'evidence': ['run/D1-protocol-raw.json', 'run/D2-rejects.json', 'run/protocol-child-release.json'],
         'conclusion': 'Actual Windows Python3.9.13 binary PIPE emits canonical 12-byte LF record via unchanged frozen product emit function; same product parent acceptance function accepts zero. Exactly eight independent malformed/error cases reject. Actual occupancy scan remains unexecuted.'},
        {'id': 'C04', 'status': 'PASS_FINITE_OFFLINE', 'item': 'R02 shared production observation and finalization',
         'evidence': ['run/D3-observation.json', 'run/D4-observation.json', 'run/D5-trace.json',
                      'run/D6-trace.json', 'run/D7-trace.json', 'run/D8-trace.json', 'run/suite-result.json'],
         'conclusion': 'External objects are memory fakes only; real NativeGuard/observe_page/record_observation_error/finalize_observation/close_owned/save_new are used without monkeypatching. D3 clean shutdown-only stopped remains authenticated; D4 login required has zero login actions. D5 stopped without failure during password await ends ERROR. D6 viewer-await first failure survives later close failure. D7 preexisting failure prevents navigation/DOM and retains original error. D8 first failure during close after provisional success changes serialized result to ERROR; second shutdown failure cannot overwrite it.'},
        {'id': 'C05', 'status': 'PASS_FINITE_RECORD', 'item': 'Freeze, one run, bounded counts and no retries',
         'evidence': ['independent-freeze.json', 'run/suite-started.json', 'command-result.json', 'run/suite-result.json'],
         'conclusion': 'Independent driver and exact eight reject inputs frozen before behavior. One run 562ms, one synthetic child, no unexpected failure. Fixed output directory created before import. No postfreeze changes, matrix expansion, author-driver run or second independent run.'},
        {'id': 'C06', 'status': 'PASS_FINITE_SCOPE_NOT_REPLAYED', 'item': 'Original network evidence remains bounded',
         'evidence': ['raw-preflight.json', 'independent-product-delta.diff',
                      '../docs/evidence/A12/native-reuse-probe/suite-run/suite-result.json'],
         'conclusion': 'Original N1-N3 fixed records and their original independent findings remain provenance for unchanged native policy/interception semantics only. New first-error bookkeeping does not establish new live network coverage. Zero original suite/browser/server replay.'},
        {'id': 'C07', 'status': 'PASS', 'item': 'Exact owned release and input immutability',
         'evidence': ['run/independent-release.json', 'run/protocol-child-release.json', 'postrun-integrity.json'],
         'conclusion': 'Sole child PID70780 has creation FILETIME134369469928825883 before/after, exit0 observed; exact retained handle and both output pipes closed. Fake contexts/runtimes closed once each. No real browser/profile resources acquired. All 53 inputs and frozen review files remain unchanged.'},
    ],
    'findings': [],
    'original_findings_disposition': {
        'R01': 'CLOSED_FOR_FIXED_R1_FINITE_OFFLINE_SCOPE',
        'R02': 'CLOSED_FOR_FIXED_R1_FINITE_OFFLINE_SCOPE',
        'old_product_and_final': 'Remain historical REWORK; no original report edited or live qualification restored.',
    },
    'independent_case_results': suite['cases'], 'first_unexpected_failure': suite['first_unexpected_failure'],
    'independent_duration_ms': suite['duration_ms'], 'command_result': command,
    'counters': suite['counters'], 'release': release,
    'authority_accounting': {
        'original_author_candidates_used': 1, 'original_browser_suites_used': 1,
        'new_author_candidates_used': 1, 'new_author_deltas_used': 1,
        'independent_deltas_used': 1, 'independent_deltas_remaining': 0,
        'independent_protocol_children_used': 1, 'independent_protocol_children_remaining': 0,
        'old_limits_restored': False, 'new_live_starts': 0, 'new_live_start_limit': 0,
        'repair_retry_extra_candidate_authority': False,
    },
    'not_verified': [
        'Actual dedicated profile identity, occupancy, credentials, or authenticated session.',
        'Real Usense transport or book46007447, source/frame content, saving, readback or submission.',
        'All child target, iframe, popup, worker and service-worker dynamic variants.',
        'Forced navigation/worker/deadline expiration, blocking native/filesystem/fsync operations, or exceptional Job/context cleanup branches.',
        'Exhaustive asynchronous callback/cancellation interleavings or pending-task branches; only task-defined D3-D8 memory interleavings ran.',
        'Unchanged full native occupancy scanner behavior; D1 only emitted synthetic zero through actual Windows pipe.',
        'B adoption, integration, deployment, or platform root cause.',
        'Author packaging/seal helpers behavior (raw identity only, not executed).',
    ],
    'pre_execution_utility_events': frozen['pre_execution_utility_events'],
    'next_authority': 'STOPPED and released. Only coordinator may separately register the same at-most-one unused reuse-only observation after actual profile binding, occupancy, durable markers and precise deadlines. This review does not start live, restore old budgets, authorize login/writes, or allow another candidate/delta. Other three cases HOLD; Q22 no replay; zero B messages.',
}
write('report.json', report)
case_lines = [
    '| D1 | PASS | Windows binary PIPE 实收 `7b22636f756e74223a307d0a`，产品父协议接受零计数；exit0。 |',
    '| D2 | PASS | 恰好八个固定异常输入全部拒绝，无扩展矩阵。 |',
    '| D3 | PASS | 正常受保护 viewer 观察；shutdown-only stopped 未变成真实失败。 |',
    '| D4 | PASS | LOGIN_REQUIRED，零登录动作。 |',
    '| D5 | PASS | 密码 await 内实际 guard.block_seen，failure=None，最终 ERROR，viewer 未继续。 |',
    '| D6 | PASS | viewer await 内首次错误保留，关闭期间后续错误未覆盖。 |',
    '| D7 | PASS | 预存原错误保留，导航与 DOM 均未运行。 |',
    '| D8 | PASS | DOM 暂定成功后关闭 await 内出现错误，最终 ERROR；再次关闭错误未覆盖首次错误。 |',
]
markdown = f'''# A12-R1 正式独立差量验收

结论：**{status}**。仅有限离线准备通过；本验收不启动或授权 live。

真实验收对话 `{report['review_thread_id']}`，封存时间 `{at}`。

产品/作者驱动 `{report['product_commit']}`；最终交付 `{report['final_commit']}`。
workflow `{report['workflow_commit']}`；来源 `{report['source_final_commit']}`。

候选清单 SHA256 `{report['candidate_manifest_sha256']}`；交付清单 SHA256 `{report['delivery_manifest_sha256']}`。
独立冻结 SHA256 `{report['independent_freeze_sha256']}`；独立驱动 SHA256 `{report['independent_driver_sha256']}`。

独立 raw 核验：53 输入逐一匹配固定 Git blob；31 新增、31,181 旧成员保全（含原 A12 22 文件），0 旧路径变化。网络 allowlist、发送前 Fetch/WS/子目标边界、TLS、profile、原共享 live 输出/启动标记、期限及精确 Job 释放未放宽；受保护实现通过 AST 对比。

唯一一次独立 D1–D8，**8/8 PASS，562 ms**，首意外失败为 null。独立 fake 仅替代外部 page/context/runtime，真实产品观察、错误处理、最终化及序列化路径均未修改。输入和独立驱动已先冻结；原作者 suite 及 N1–N3 均未运行。

| 项目 | 结果 | 实测 |
| --- | --- | --- |
{chr(10).join(case_lines)}

唯一合成协议子进程 PID70780，创建 FILETIME134369469928825883 前后相同，exit0、退出时间已观察，双管道及精确保留句柄均关闭。六项内存 fake 各关闭 context/runtime 一次。运行后重核全部 53 输入及冻结独立文件，原 bytes 均不变。

R01/R02 仅在当前固定 R1 和该有限差量范围关闭；旧产品/交付及原 REWORK 报告保持。原 N1–N3 网络证明仅在未变实现范围有限沿用，没有新浏览器流量证明。

仍未证明真实专用 profile/占用/认证、平台书籍/源/框/保存读回、全部 worker/popup/iframe 动态分支、强制期限和异常释放分支、全部异步交错、B 采用或集成。未运行作者封装工具。本轮无浏览器、服务器、平台、真实占用扫描、profile/凭据访问、登录或业务写入。

独立差量及合成子进程额度均剩余0，已停止并释放；不能修后重跑、增加候选或恢复旧额度。后续仅主调度可另行登记同一个尚未使用的至多一次 reuse-only 观察，并核实际 profile、占用、标记和精确期限。其他三例 HOLD，Q22 不重放，0 B 消息。

证据：[固定 raw 与保全](raw-preflight.json)、[独立冻结](independent-freeze.json)、[逐项原始结果](run/suite-result.json)、[精确释放](run/independent-release.json)、[运行后保全](postrun-integrity.json)、[完整报告](report.json)、[raw 输出清单](raw-output-manifest.json)。
'''
with (OUT / 'report.md').open('xb') as stream:
    stream.write(markdown.encode('utf-8'))
outputs = []
for p in sorted(OUT.rglob('*')):
    if p.is_file() and p.name != 'raw-output-manifest.json':
        raw = p.read_bytes()
        outputs.append({'path': p.relative_to(OUT).as_posix(), 'size': len(raw), 'sha256': sha(raw)})
manifest = {'schema_version': 1, 'review_thread_id': report['review_thread_id'], 'at': at,
    'status': status, 'product_commit': report['product_commit'], 'final_commit': report['final_commit'],
    'inputs': pre['inputs'], 'inputs_count': len(pre['inputs']),
    'output_members_excluding_this_manifest': outputs, 'output_nonself_count': len(outputs),
    'self_rule': 'Manifest has no self-content hash. Exact manifest SHA256 returned in final response for coordinator sealing.',
    'further_action': 'STOPPED_NO_RETRY_NO_LIVE'}
write('raw-output-manifest.json', manifest)
print(json.dumps({'status': status, 'report_sha256': sha((OUT / 'report.json').read_bytes()),
    'raw_output_manifest_sha256': sha((OUT / 'raw-output-manifest.json').read_bytes()),
    'raw_input_count': len(pre['inputs']), 'output_nonself_count': len(outputs),
    'independent_cases': 8, 'independent_runs_used': 1, 'remaining': 0,
    'release': release['state']}, indent=2))
