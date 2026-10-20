"""Seal existing A13 evidence only; never imports product or touches profile."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path('D:/1800-worktrees/a13-reuse-observation')
OUT = ROOT / 'execution-output'
LIVE = Path('D:/1800/.local/stages/a12-native-reuse-live')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())


def read(name):
    return json.loads((OUT / name).read_bytes())


def same_identity(record):
    before, after = record['before'], record['after']
    return (before['pid'] == after['pid'] and
            before['created_filetime'] == after['created_filetime'] and after['exit_observed'])


def main():
    intent = read('launch-intent.json')
    verification = read('raw-input-verification.json')
    preserved = []
    for item in verification['fixed_inputs']:
        raw = (ROOT / item['path']).read_bytes()
        assert sha(raw) == item['sha256'] and len(raw) == item['size']
        preserved.append({'path': item['path'], 'sha256': sha(raw), 'size': len(raw),
                          'unchanged': True, 'git_oid': item['git_oid']})
    expected_names = {'live-started.json', 'worker-claimed.json', 'profile-binding.json',
                      'occupancy.json', 'observation.json', 'worker-release.json'}
    assert {p.name for p in LIVE.iterdir()} == expected_names
    copies = []
    (OUT / 'live-records').mkdir(exist_ok=False)
    for name in sorted(expected_names):
        raw = (LIVE / name).read_bytes()
        json.loads(raw)
        with (OUT / 'live-records' / name).open('xb') as stream:
            stream.write(raw)
        assert (LIVE / name).read_bytes() == (OUT / 'live-records' / name).read_bytes()
        copies.append({'source': str(LIVE / name), 'copy': 'live-records/' + name,
                      'sha256': sha(raw), 'size': len(raw), 'raw_bytes_equal': True,
                      'review': 'Enumerated frozen product redacted JSON schema; no response body, account, secret or profile child name.'})
    observation = read('live-records/observation.json')
    worker = read('live-records/worker-release.json')
    occupancy = read('live-records/occupancy.json')
    binding = read('live-records/profile-binding.json')
    marker = read('live-records/live-started.json')
    claim = read('live-records/worker-claimed.json')
    outer = read('outer-release.json')
    assert binding['fingerprint'] == marker['profile_fingerprint'] == intent['profile_fingerprint']
    assert marker['candidate_sha256'] == claim['candidate_sha256'] == intent['candidate_sha256']
    assert claim['pid'] == worker['before']['pid']
    assert occupancy['matching_processes'] == 0 and same_identity(occupancy) and occupancy['handle_closed']
    assert occupancy['after']['exit_code'] == 0 and not occupancy['timeout']
    assert same_identity(worker) and worker['state'] == 'RELEASED'
    assert worker['job_active_final'] == 0 and worker['worker_handle_closed'] and worker['job_closed']
    assert same_identity(outer) and outer['state'] == 'RELEASED' and outer['handle_closed'] and outer['pipes_closed']
    assert observation['release']['state'] == 'RELEASED'
    assert observation['outcome'] == 'ERROR' and observation['navigation_intents'] == 1
    assert observation['error']['codes'] == ['ERR_CERT_COMMON_NAME_INVALID']
    assert observation['login_submissions'] == observation['business_writes'] == 0
    assert all(e['method'] == 'GET' and e['category'] == 'NAVIGATION' and e['decision'] == 'ALLOW'
               for e in observation['network_audit'])
    save('postrun-integrity.json', {'status': 'PASS_RAW_PRESERVATION',
        'fixed_input_count': len(preserved), 'unchanged_inputs': preserved,
        'shared_live_originals': copies, 'shared_markers_preserved': True,
        'product_modified': False, 'wrapper_modified_after_intent':
            sha((OUT / 'launch_once.py').read_bytes()) != intent['wrapper_sha256']})
    assert sha((OUT / 'launch_once.py').read_bytes()) == intent['wrapper_sha256']
    save('command-result.json', {
        'command': ['python', '-B', str(OUT / 'launch_once.py'), '--intent-sha256',
                    sha((OUT / 'launch-intent.json').read_bytes())],
        'cwd': str(ROOT), 'initial_tool_chunk_id': '8d086f', 'exec_session_id': 59779,
        'completion_tool_chunk_id': 'a62858', 'tool_reported_shell_exit_code': 1,
        'product_returncode_from_exact_handle': 2,
        'wrapper_expected_exit_from_frozen_source': 2,
        'shell_exit_normalization': 'Tool shell reports 1; preserved exact process evidence records product exit 2. Wrapper process OS exit identity was not retained by this wrapper.',
        'completion_stdout': '{"outer_release": "RELEASED", "product_returncode": 2, "duration_ms": 10391, "timeout": false}',
        'product_stdout_raw_withheld': True, 'product_stderr_bytes': 0,
        'launch_count': 1, 'retry_count': 0})
    now = datetime.now(timezone.utc)
    release = {'state': 'RELEASED', 'at_utc': now.isoformat(),
        'outer_exact_popen': outer, 'worker_and_job': worker,
        'occupancy_exact_child': occupancy, 'browser_context_and_runtime': observation['release'],
        'no_additional_process_scan_or_cleanup': True,
        'further_action': 'STOPPED_NO_RETRY_NO_LOGIN_NO_BUSINESS',
        'remaining_live_starts': 0, 'original_shared_markers_retained': True}
    save('execution-release.json', release)
    report = {
        'schema_version': 1, 'status': 'BLOCKED', 'observation_outcome': 'ERROR',
        'at_utc': now.isoformat(), 'at_local': now.astimezone(timezone(timedelta(hours=8))).isoformat(),
        'task': 'A13 single dedicated headless reuse-only observation',
        'execution_thread_id': intent['thread_id'], 'host_id': 'local',
        'workflow_commit': intent['workflow_commit'], 'product_commit': intent['product_commit'],
        'final_commit': intent['final_commit'], 'product_sha256': intent['product_sha256'],
        'candidate_manifest_sha256': intent['candidate_sha256'],
        'independent_manifest_sha256': '59d23a1dbe6e20abe92e7abf0ac89ba13834d6c6d90a01bcfae073e6072b72e7',
        'input_count': 53, 'input_verification': 'raw-input-verification.json',
        'input_postrun_integrity': 'postrun-integrity.json',
        'launch_intent_sha256': sha((OUT / 'launch-intent.json').read_bytes()),
        'wrapper_sha256': intent['wrapper_sha256'],
        'profile_fingerprint': intent['profile_fingerprint'],
        'observation': observation,
        'first_unexpected_failure': {'stage': 'SOLE_ANNOTATE_UNIFIED_NAVIGATION',
            'exception_type': 'Error', 'code': 'ERR_CERT_COMMON_NAME_INVALID',
            'root_cause': 'UNKNOWN', 'http_status': None,
            'details': 'Frozen browser navigation returned the enumerated TLS error. No certificate bypass or second navigation.'},
        'finite_checks': {
            '53_raw_inputs_equal_fixed_final_before_and_after': True,
            'candidate_product_wrapper_bindings_match': True,
            'shared_output_and_intent_absent_before_preparation': True,
            'one_external_candidate_call_one_metadata_binding_call': True,
            'sole_internal_occupancy_zero_before_context_and_navigation': True,
            'strict_tls_no_certificate_exception': True,
            'audit_only_two_layer_GET_navigation_events': True,
            'guard_final_failure_null_pending_zero': True,
            'first_error_retained_and_successors_not_run': True,
            'outer_worker_job_context_runtime_released': True,
            'original_live_records_copied_raw_without_changes': True},
        'counters': {'live_starts_used': 1, 'live_starts_remaining': 0,
            'product_parent_processes': 1, 'worker_processes': 1, 'occupancy_processes': 1,
            'dedicated_headless_contexts': 1, 'navigation_intents': 1,
            'network_audit_events': 2, 'network_audit_note': 'Same sole navigation seen at Fetch and context guards; not two navigation intents.',
            'external_candidate_calls': 1, 'external_profile_binding_calls': 1,
            'internal_profile_binding_calls': 1, 'actual_occupancy_scans': 1,
            'external_occupancy_scans': 0, 'login_submissions': 0, 'business_writes': 0,
            'book_source_frame_interface_reads': 0, 'retries_reloads': 0,
            'old_suite_driver_runs': 0, 'product_candidates_or_modifications': 0,
            'credential_or_profile_internal_reads_by_execution_scripts': 0,
            'certificate_bypasses': 0, 'external_messages': 0},
        'successors': {'authentication_observation': 'NOT_PROVEN',
            'login': 'NOT_RUN', 'book_source_target_read': 'NOT_RUN',
            'first_question_save': 'NOT_RUN', 'refresh_reopen_content_frame_readback': 'NOT_RUN',
            'submission': 'NOT_RUN'},
        'release': release, 'raw_output_manifest': 'raw-output-manifest.json',
        'old_budgets_restored': False, 'shared_live_output': str(LIVE),
        'limitations': [
            'Only failure archive and exact owned release are delivered for independent static review; author does not declare acceptance.',
            'No authenticated viewer or LOGIN_REQUIRED state was established because navigation failed first.',
            'The TLS error code does not establish a network, proxy or certificate root cause; no further diagnostic was performed.',
            'No book availability, source/target state, text wire, frame save/readback, B acceptance or integration is proved.',
            'Popen product parent identity and child/job release are exact. Tool shell exit 1 is preserved separately from held product exit 2.',
            'Wrapper is a bounded best effort; no universal OS blocking guarantee is claimed.'],
        'next_action': 'STOPPED. Coordinator may dispatch fixed evidence to formal independent static review. No replay or login authority.',
        'other_three_cases': 'HOLD', 'q22': 'NO_REPLAY'}
    save('report.json', report)
    markdown = '''# A13 唯一专用无头复用观测：BLOCKED，待独立静态核证

执行对话：`01a157d2-caed-7162-8c48-06ad7117bd90`。固定产品 `d45ed25a` / 最终交付 `81fab23e`，53 输入在启动前后 raw bytes、SHA256、size 及 Git blob 身份一致，未修改产品或旧证据。

北京时间 2026-10-20 13:42:39 发起唯一启动；约 10.391 秒后停止。原专用 profile 仅由执行准备调用一次元数据绑定，实际占用仅冻结 worker 内一次四秒有界扫描，确认 0。随后创建一次专用无头 context 并发出一次 annotateUnified 导航；首次返回 `ERR_CERT_COMMON_NAME_INVALID`，观察结果 `ERROR`。认证及 LOGIN_REQUIRED 均未建立，HTTP 状态未记录，根因 UNKNOWN。严格 TLS 保持，无证书忽略、重试、重载或后续诊断。

两条 GET/NAVIGATION audit 分别来自 Fetch 与 context 守卫，是同一次导航的两层事件。最终 guard failure=null、pending_tasks=0。0 登录填写或提交、0 书籍/源/框接口、0 业务写入、0 旧 suite/driver、0 新候选、0 B 或其他对话消息。所有后继读取、首题保存、刷新重开及题框读回均 NOT_RUN。

占用子进程 PID75784、worker PID16076、外层持有的产品 Popen PID75280 均有保留句柄的同 PID/创建 FILETIME 与退出证据。占用子进程 exit0，worker 与产品 exit2。context/runtime 关闭，worker handle 与 Job 均关闭，Job 活动数最终为 0；外层 pipes/handle 已关闭，未超时。工具壳报告 exit1，原值单独保留，不覆盖确切产品退出码2；wrapper 自身 OS 退出身份未被该 wrapper 持有。

`live-records/` 为六个已检查脱敏产品 JSON 的原 bytes 副本，共享 `.local/stages/a12-native-reuse-live` 原件和标记保留，不改不删。原始异常/产品 stdout 文本不外传，仅保留摘要与长度。`raw-output-manifest.json` 包含53固定输入及全部新增输出成员，不自引用。

本轮 live 额度已用1、剩余0，失败不恢复旧额度。作者结论仅 BLOCKED 和释放交付，不自宣独立接受、认证通过或平台可用。完成封存后停止，由调度收取固定材料并交正式独立静态验收。其他三例 HOLD，Q22 不重放，书籍送审送交未运行。
'''
    with (OUT / 'report.md').open('xb') as stream:
        stream.write(markdown.encode('utf-8'))
    output_members = []
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name != 'raw-output-manifest.json':
            raw = path.read_bytes()
            output_members.append({'path': path.relative_to(OUT).as_posix(),
                                   'size': len(raw), 'sha256': sha(raw)})
    save('raw-output-manifest.json', {'schema_version': 1,
        'input_root': str(ROOT), 'output_root': str(OUT),
        'fixed_input_count': 53, 'fixed_inputs': verification['fixed_inputs'],
        'output_members_excluding_this_manifest': output_members,
        'shared_live_raw_originals': copies,
        'manifest_self_reference': False, 'report': 'report.json'})
    print(json.dumps({'status': 'BLOCKED', 'outcome': 'ERROR',
        'error_code': 'ERR_CERT_COMMON_NAME_INVALID', 'release': 'RELEASED',
        'fixed_inputs': 53, 'output_nonself_members': len(output_members),
        'report_sha256': sha((OUT / 'report.json').read_bytes()),
        'manifest_sha256': sha((OUT / 'raw-output-manifest.json').read_bytes()),
        'remaining_live_starts': 0}))


if __name__ == '__main__':
    main()
