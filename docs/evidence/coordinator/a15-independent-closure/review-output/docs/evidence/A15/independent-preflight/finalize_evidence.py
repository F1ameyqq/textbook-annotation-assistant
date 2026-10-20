"""Validate fixed receipts/output and seal this one independent delta. Never rerun it."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path('D:/1800-worktrees/a15-independent-fixed')
OUT = ROOT / 'docs/evidence/A15/independent-preflight'
STATIC = ROOT / 'docs/evidence/A15/independent-preflight-static'
EVIDENCE = ROOT / 'docs/evidence/A15/certificate-exception'
DELTA = EVIDENCE / 'first-independent-delta'
CANDIDATE_SHA = '78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652'
AUTHOR_FINAL = '7432122b9fd5602785ebfb2b3f24e407fdf76eda'
AUTHOR_MANIFEST_SHA = 'ef39744d3f0b22a54a24341e70d0e15d445383086000d8253d7454c5d41e7267'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')

def write_new(name, data):
    with (OUT / name).open('xb') as stream:
        stream.write(data)

def read(path):
    return json.loads(path.read_bytes())

preflight = read(OUT / 'fixed-input-preflight.json')
command = read(OUT / 'independent-command-result.json')
suite_raw = (DELTA / 'suite-result.json').read_bytes()
suite = json.loads(suite_raw)
started = read(DELTA / 'suite-started.json')
suite_release = read(DELTA / 'release.json')
spec_raw = (EVIDENCE / 'finite-cases.json').read_bytes()
spec = json.loads(spec_raw)
stdout = (OUT / 'independent-delta-stdout.txt').read_bytes()
stderr = (OUT / 'independent-delta-stderr.txt').read_bytes()
assert command['exit_code'] == 0 and command['invocations'] == 1 and command['timeout'] is False
assert command['stdout_sha256'] == sha(stdout) and command['stderr_sha256'] == sha(stderr)
assert command['stdout_bytes'] == len(stdout) and command['stderr_bytes'] == len(stderr) == 0
assert suite['candidate_sha256'] == started['candidate_sha256'] == CANDIDATE_SHA
assert suite['case_spec_sha256'] == started['case_spec_sha256'] == sha(spec_raw)
assert suite['task'] == 'A15' and suite['mode'] == 'PURE_OFFLINE_ONLY'
assert suite['first_failure'] is None and suite['claim_is_synthetic_only'] is True
assert suite['live_activated'] is False and suite['live_output_or_profile_read'] is False
assert suite['old_suites_run'] is False
assert [item['case'] for item in suite['cases']] == ['E1', 'E2', 'E3', 'E4']
assert all(item['status'] == 'PASS' for item in suite['cases'])
for index, group in enumerate(('E1', 'E2')):
    observed = [(item['id'], item['rejection']) for item in suite['cases'][index]['checks']]
    expected = [(item['id'], item['expected']) for item in spec[group]]
    assert observed == expected
assert len(suite['cases'][0]['checks']) == 10 and len(suite['cases'][1]['checks']) == 29
assert len(suite['cases'][2]['checks']) == len(suite['cases'][3]['checks']) == 1
assert suite['cases'][2]['checks'][0]['exception_only_in_approval'] is True
assert suite['cases'][3]['checks'][0]['rejection'] == 'ACTIVATION_ALREADY_CLAIMED'
assert suite['cases'][3]['checks'][0]['marker_bytes_unchanged'] is True
marker_raw = (DELTA / 'synthetic/claim.json').read_bytes()
marker_sha = sha(marker_raw)
assert marker_sha == suite['cases'][2]['checks'][0]['marker_sha256'] == suite['cases'][3]['checks'][0]['marker_sha256']
marker = json.loads(marker_raw)
assert marker['task'] == 'A15' and marker['run_id'] == spec['synthetic_activation']['run_id']
assert marker['candidate_sha256'] == spec['synthetic_activation']['candidate_manifest_sha256']
assert marker['profile_fingerprint'] == spec['synthetic_activation']['profile_fingerprint']
assert marker['certificate_exception'] is True
assert marker['target'] == 'https://www.usense.com/qieti/annotateUnified'
assert marker['context_limit'] == marker['navigation_limit'] == 1
assert marker['login_submission_limit'] == marker['business_write_limit'] == 0
expected_keys = {'browser', 'live_entry', 'native_api', 'occupancy', 'profile', 'socket', 'subprocess', 'thread'}
assert set(suite['resource_calls']) == expected_keys
assert all(type(value) is int and value == 0 for value in suite['resource_calls'].values())
assert suite_release['resource_calls'] == suite['resource_calls']
assert suite_release['state'] == 'RELEASED'
assert suite_release['subprocesses_created'] == suite_release['threads_started'] == suite_release['browser_contexts_created'] == 0
assert suite_release['profile_or_live_directory_actions'] == 0
assert suite_release['all_file_handles_context_managed'] is True
inputs = list(preflight['members'])
author_manifest_path = EVIDENCE / 'packaging-disposition-delivery/delivery-raw-manifest.json'
inputs.append({'path': author_manifest_path.relative_to(ROOT).as_posix(), 'sha256': AUTHOR_MANIFEST_SHA})
assert len(inputs) == 47
for item in inputs:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
assert sha((ROOT / 'r1-reference.py').read_bytes()) == '3f1e4a425e18ed0e2a28893989f31677ba6b9b7f4b9c3da2800bc925443999c9'
static_manifest_raw = (STATIC / 'manifest.json').read_bytes()
assert sha(static_manifest_raw) == '63ef0c36d0663f89f5a5afa636ce1a160f01949050d652c453a3f0c834470bc2'
for item in json.loads(static_manifest_raw)['members']:
    assert sha((ROOT / item['path']).read_bytes()) == item['sha256']
assert sha((EVIDENCE / 'candidate-manifest.json').read_bytes()) == CANDIDATE_SHA
finished = datetime.now(timezone.utc).isoformat()
write_new('fixed-input-preservation.json', encode({'task': 'A15', 'at': finished,
 'author_final': AUTHOR_FINAL, 'raw_members_including_manifest': 47, 'verified_inputs': inputs,
 'r1_reference_unchanged': True, 'candidate_manifest_unchanged': True,
 'original_31_and_all_16_additions_unchanged': True, 'static_phase_seal_unchanged': True,
 'candidate_source_or_finite_matrix_modified': False, 'old_members_preservation': preflight['prior_final_old_members_preserved'],
 'no_old_suites_run': True, 'no_candidate_or_suite_rerun': True}))
release = {'task': 'A15', 'at': finished, 'state': 'RELEASED_OFFLINE_ONLY',
 'independent_delta_used': 1, 'independent_delta_remaining': 0,
 'independent_interpreter_invocations': 1, 'interpreter_exit_code': 0,
 'resource_calls_by_frozen_delta': suite['resource_calls'], 'product_subprocesses_created': 0,
 'browser_contexts': 0, 'network_attempts': 0, 'profile_reads': 0, 'real_occupancy_checks': 0,
 'native_api_calls': 0, 'login_submissions': 0, 'business_writes': 0, 'B_messages': 0,
 'book_review_or_delivery_submissions': 0, 'live_starts': 0,
 'file_handles': 'Synchronous analysis/capture/JSON operations use context-managed files; suite release recorded closed handles.',
 'preparation_processes': 'Static Git and analysis interpreters completed synchronously; not a claim of zero preparation processes.',
 'process_scan_performed': False, 'retained_OS_identity_for_shell_or_reporter': 'NOT_MEASURED_NOT_CLAIMED',
 'runtime_Job_timeout_cleanup_exercised': False, 'a13_marks_and_profile_locks': 'NOT_TOUCHED',
 'next_state': 'STOP_REVIEW_WAIT_COORDINATOR_ACTIVATION_DECISION'}
write_new('independent-release.json', encode(release))
report = {'task': 'A15', 'phase': 'FIXED_CANDIDATE_INDEPENDENT_PREFLIGHT',
 'decision': 'ACCEPTED_OFFLINE_ONLY', 'at': finished,
 'review_thread_id': '01a157fe-5cc9-7d91-8bbe-73b376cbe2a5',
 'coordinator_thread_id': '01a15768-1e2d-7781-b29f-1f7376270216',
 'product_commit': 'bef0204541eedd86e1fab849e8002a83f432cd7b',
 'author_final_commit': AUTHOR_FINAL, 'prior_failure_final': '25f9083b2c8183196a7b2d7671efd40d2ef78713',
 'author_delivery_manifest_sha256': AUTHOR_MANIFEST_SHA, 'candidate_manifest_sha256': CANDIDATE_SHA,
 'user_decision_sha256': '36ffcbb42c030192313773b510c69598651b2c2ffe5fb54162c46b8041e40763',
 'proposal_sha256': 'eb6aea7ad9b01ccbcaf7710c9c45d7c5c3a80d6efcef4db857838d204d725656',
 'execution_task_sha256': 'f7bdf3f43b0fb467dcb43e37ae97dfc77f69894292e54d2f16ab6d252590b4a6',
 'packaging_disposition_sha256': '1513fa552dd25e1f51dc3ada1d28be936b67c22d96c3fa1165230e30399ab8a7',
 'static_phase_manifest_sha256': sha(static_manifest_raw),
 'static_report_sha256': sha((STATIC / 'report.md').read_bytes()),
 'author_raw_members_verified': 47, 'prior_final_old_members_preserved': 31243,
 'original_base_old_members_preserved': 31212, 'candidate_members_verified': 22,
 'new_author_raw_members': 16, 'r1_invariant_bodies_verified': 21,
 'static_blocking_findings': [], 'independent_delta_invocations': 1,
 'independent_delta_limit': 1, 'independent_delta_remaining': 0,
 'independent_delta_exit_code': command['exit_code'], 'independent_delta_duration_ms': suite['duration_ms'],
 'independent_delta_cases': {item['case']: item['status'] for item in suite['cases']},
 'independent_delta_result_sha256': sha(suite_raw), 'first_failure': suite['first_failure'],
 'finite_E1_variants': 10, 'finite_E2_variants': 29, 'synthetic_marker_sha256': marker_sha,
 'resource_calls': suite['resource_calls'], 'stderr_bytes': len(stderr),
 'raw_stdout_sha256': sha(stdout), 'raw_stderr_sha256': sha(stderr),
 'raw_input_and_prior_static_evidence_preserved': True,
 'first_packaging_failure_preserved': True, 'original_packaging_check_exit_code': None,
 'original_packaging_check_rerun_or_relabeled_pass': False, 'candidate_modified_or_replaced': False,
 'old_suites_N1_N3_D1_D8_run': False, 'old_budgets_restored': False,
 'accepted_scope': 'Finite pure approval gate E1-E4 and static preservation/order/timing/release review of this fixed candidate only.',
 'limitations': ['No real browser/TLS exception or platform action',
   'No runtime network/redirect/WS/DOM suite rerun', 'No native API, process occupancy, Job timeout or OS release exercise',
   'No profile metadata read', 'No authentication, books or first save/readback proof'],
 'A14_TIMING_01_general_guard_accepted': False, 'A13_wrapper_OS_exit_identity': 'UNKNOWN_PRESERVED',
 'next_dependency': 'Coordinator raw verification and exact hash-bound activation/dispatch for at most one new observation by the execution chat.',
 'live_activated_by_reviewer': False, 'live_started': 0, 'login_submissions': 0, 'business_writes': 0,
 'first_save_readback': 'NOT_RUN', 'other_three_cases': 'HOLD', 'Q22_replayed': False,
 'B_messages': 0, 'book_submission': 0, 'state': 'STOP_REVIEW_RELEASED'}
write_new('report.json', encode(report))
markdown = f'''# A15 固定候选正式独立预检

结论：`ACCEPTED_OFFLINE_ONLY`。仅接受本固定候选的有限批准门禁与静态预检资格；本对话已停止 REVIEW 并释放。live 未激活，必须由调度另行核证和固定派发。

产品 `bef0204541eedd86e1fab849e8002a83f432cd7b`，作者新 final `{AUTHOR_FINAL}`，候选清单 SHA256 `{CANDIDATE_SHA}`。独立正式对话 `01a157fe-5cc9-7d91-8bbe-73b376cbe2a5`。机器报告 `report.json` 可供后续调度绑定摘要。

独立唯一一次 E1–E4：**4/4 PASS，{suite['duration_ms']}ms，退出码 0**；E1 固定 10 个拒绝变体及默认严格校验，E2 固定 29 个绑定/额度/时间/摘要/JSON 拒绝变体，E3 一次匹配合成领取，E4 重复拒绝且原标记 bytes 不变。合成标记 SHA256 `{marker_sha}`。stdout 原 bytes 保留，stderr 0 bytes；八类资源入口计数全 0。独立额度已用 1、剩余 0，不补跑。

| 层级 | 本次独立结论 |
| --- | --- |
| 固定交付 | 47 raw 与新 final 固定 Git blob 相符；原失败 final 的 31,243 旧成员 mode/type/blob 保全，仅新增 16；原基线 31,212 亦保全；22 个候选成员未变。运行前后 47 输入及 R1 对照、先前静态封存全部原 bytes 保全。 |
| 权威语义 | 从固定用户决定、提案和执行任务推导任务/候选/调度/target/profile/输出/额度/期限绑定，独立静态确认显式开关与摘要门禁先于真实资源动作；默认严格证书校验，CLI 不替代固定激活字段。 |
| 守卫/生命周期 | 21 个关键 R1 函数/类 raw 比较通过（DOM 观察和最终化只改认证枚举）；逐跳方法/WS/子 target、DOM 后最终判定保持。各进程本地 monotonic 截止无跨进程时基混用；精确保留句柄、OS 退出观测、Job 计数和 wrapper UNKNOWN 边界，仅静态审查。详见先前独立静态报告。 |
| 原打包失败 | 23,514-byte raw diff 可独立精确重建，17 处均为上下文空行。原单项退出码 null、PS 继续 commit、失败/NOT_RUN 原件保持；未重跑原检查或改记 PASS。显式处置只启用原未用一次作者差量，无新候选或追加 suite。 |
| 真实资源 | 本 suite 仅执行纯函数和本轮合成目录。0 产品子进程/browser/network/native API/profile/实际占用，0 登录提交/业务/书级送交/B 消息；未触发任何真实证书例外。 |

复现命令（仅记录已发生的一次调用，**不授权重跑**）：

```text
python -B tools/a15_cert_exception_gate_delta.py --candidate-sha256 {CANDIDATE_SHA} --output docs/evidence/A15/certificate-exception/first-independent-delta
```

`independent-command-result.json`、`independent-delta-stdout.txt`、`independent-delta-stderr.txt` 保存原始命令/输出/退出；唯一差量原始结果在 `../certificate-exception/first-independent-delta/`。`fixed-input-preservation.json` 保存运行后的输入复核，`independent-release.json` 记录本次释放；`manifest.json` 绑定本报告、差量原始输出与先前静态封存。

本次没有执行旧 N1–N3、D1–D8，没有实际网络/DOM/证书/占用/Job 超时释放证明，也没有认证或书籍保存证明。A14-TIMING-01 通用截止守卫仍不接受，A13 wrapper OS 退出 UNKNOWN 保留。首题保存读回仍 NOT_RUN，其他三例 HOLD、Q22 不重放。准备工具及这次差量解释器是同步本地进程；不把资源计数 0 夸大为整个准备过程无进程，也不声称已测量 shell/报告进程自身 OS 身份。

下一依赖：调度核固定报告/清单/释放，再绑定实际独立报告 SHA、候选、用户决定、profile 指纹、唯一输出及 UTC 窗口后，另行派发执行对话至多一次新观测。本离线结论不自动激活 live，也不授权题目写入。
'''
write_new('report.md', markdown.encode('utf-8'))
paths = []
for directory in (STATIC, DELTA, OUT):
    paths.extend(path for path in directory.rglob('*') if path.is_file() and path != OUT / 'manifest.json')
members = []
for path in sorted(paths):
    raw = path.read_bytes()
    members.append({'path': path.relative_to(ROOT).as_posix(), 'size': len(raw), 'sha256': sha(raw)})
write_new('manifest.json', encode({'task': 'A15', 'phase': 'INDEPENDENT_PREFLIGHT',
 'decision': 'ACCEPTED_OFFLINE_ONLY', 'self_excluded': True,
 'candidate_manifest_sha256': CANDIDATE_SHA, 'author_final': AUTHOR_FINAL,
 'author_delivery_manifest_sha256': AUTHOR_MANIFEST_SHA,
 'report_sha256': sha((OUT / 'report.json').read_bytes()),
 'independent_delta_executions': 1, 'members': members}))
print(json.dumps({'decision': report['decision'], 'cases': report['independent_delta_cases'],
 'duration_ms': suite['duration_ms'], 'report_sha256': sha((OUT / 'report.json').read_bytes()),
 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()), 'manifest_members': len(members),
 'release_sha256': sha((OUT / 'independent-release.json').read_bytes()), 'live_activated': False}))
