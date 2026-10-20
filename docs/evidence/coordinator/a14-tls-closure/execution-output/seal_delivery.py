"""Seal the existing A14 single-run evidence; no execution or networking."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

OUT = Path('D:/1800-worktrees/a14-tls-diagnostic/execution-output')
PRIVATE = Path('D:/1800/.local/stages/a14-tls-diagnostic')

def raw(path):
    b = path.read_bytes()
    return {'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def main():
    p = json.loads((OUT / 'process-result.json').read_text(encoding='utf-8'))
    w = json.loads((OUT / 'wrapper-os-release.json').read_text(encoding='utf-8'))
    cert = json.loads((OUT / 'public-certificate-results.json').read_text(encoding='utf-8'))
    intent = json.loads((OUT / 'launch-intent.json').read_text(encoding='utf-8'))
    binding_checks = [{'path': k, 'expected': v, 'observed': raw(Path(k)),
                       'matches': v == raw(Path(k))} for k, v in intent['bindings'].items()]
    assert all(c['matches'] for c in binding_checks)
    assert raw(OUT / 'launch-intent.json')['sha256'] == '2d73cef6f535ef7f503bae6d3094e8353005c771feefbfb74ceaa06bf3000aec'
    privacy = {'scope': 'Hash/size only; raw streams and launch claims stay private; no session data included.',
               'members': [{'private_basename': f.name, **raw(f)} for f in sorted(PRIVATE.iterdir()) if f.is_file()]}
    save(OUT / 'private-raw-hash-manifest.json', privacy)
    tls_identity = p['process_creation']['creation_filetime'] == p['process_exit']['creation_filetime']
    wrapper_identity = w['creation']['creation_filetime'] == w['exit']['creation_filetime']
    tls_release = (tls_identity and p['process_exit']['exit_filetime'] > 0 and p['wait_signaled']
                   and p['readers_joined'] and all(v.get('post_close', {}).get('invalid_handle_confirmed') for v in p['release'].values())
                   and all(v['eof_observed'] and v['file_closed'] and v['reader_error_type'] is None for v in p['streams'].values()))
    wrapper_release = (wrapper_identity and w['exit']['exit_filetime'] > 0 and w['wait_signaled']
                       and w['handle_post_close']['invalid_handle_confirmed'] and w['redirect_files_closed'])
    now = datetime.now(timezone.utc)
    report = {
        'task_id': 'A14', 'author_status': 'REVIEW',
        'delivery_state': 'FROZEN_SINGLE_DIAGNOSTIC_FAILURE_EVIDENCE_WITH_RELEASE_AND_TIMING_LIMITATION',
        'execution_id': intent['execution_id'], 'thread_id': intent['thread_id'],
        'independent_review_thread_id': intent['independent_review_thread_id'],
        'workflow_commit': intent['workflow_commit'], 'report_utc': now.isoformat(),
        'report_local': now.astimezone(timezone(timedelta(hours=8))).isoformat(),
        'observation_utc': p['launch_utc'], 'tls_result': cert['category'],
        'strict_validation_succeeded': False,
        'verification_error_codes': cert['observed_verify_error_codes'],
        'verification_return_codes': cert['observed_verify_return_codes'],
        'openssl_exit_code': p['exit_code'], 'leaf_san': cert['certificates'][0]['dns_subject_alt_names'],
        'leaf_san_covers_target': cert['leaf_san_covers_www_usense_com'],
        'leaf_validity_end_utc': cert['certificates'][0]['not_after_utc'],
        'leaf_within_public_validity_interval_at_observation': cert['certificates'][0]['within_validity_at_observation'],
        'validity_interpretation': 'Leaf public notAfter precedes observation; OpenSSL first error was 62. Later validation stages were not established as completed.',
        'server_sent_unique_certificates': cert['unique_public_certificates'],
        'chain_accepted': False, 'root_cause': 'UNKNOWN',
        'root_cause_limits': ['No attribution to website, proxy interception, DNS or another path component.',
                              'Git OpenSSL PEM CA differs from Windows/Edge trust; this is not proof of the Edge cause.',
                              'No authentication, book access, page load, first-question save or refresh/reopen readback was tested.'],
        'counts': {'tls_process_launches': p['tls_process_launches'], 'tls_handshake_intents': p['tls_handshake_intents'],
                   'wrapper_launches': w['wrapper_launches'], 'local_ast_precheck_network_connections': 0,
                   'target_http_requests': 0, 'stdin_application_bytes_written': 0,
                   'proxy_CONNECT_intents': 1, 'browser_profile_login_business_actions': 0,
                   'fallbacks': 0, 'retries': 0, 'postrun_tls_connections': 0, 'B_or_external_messages': 0},
        'budget': {'limit': 1, 'consumed': 1, 'remaining': 0, 'prior_A13_and_A10_budgets_restored': False,
                   'additional_network_successors': 'NOT_RUN'},
        'release': {'tls_exact_creation_exit_identity_matches': tls_identity, 'tls_release_evidence_complete': tls_release,
                    'tls_pid': p['pid'], 'tls_exit_code': p['exit_code'],
                    'wrapper_exact_creation_exit_identity_matches': wrapper_identity,
                    'wrapper_os_exit_evidence_complete': wrapper_release, 'wrapper_pid': w['pid'],
                    'wrapper_exit_code': w['exit_code'], 'wrapper_timeout': w['timeout'],
                    'all_observed_processes_and_owned_handles_released': tls_release and wrapper_release},
        'timing': {'outer_same_process_elapsed_ms_to_wrapper_os_exit': w['elapsed_ms_to_wrapper_observed_exit'],
                   'outer_wrapper_creation_to_exit_ms_from_OS_filetimes': round((w['exit']['exit_filetime'] - w['creation']['creation_filetime']) / 10000, 4),
                   'tls_creation_to_exit_ms_from_OS_filetimes': round((p['process_exit']['exit_filetime'] - p['process_creation']['creation_filetime']) / 10000, 4),
                   'observed_run_and_wrapper_exit_within_22_seconds': w['elapsed_ms_to_wrapper_observed_exit'] <= 22000 and not w['timeout'],
                   'child_reported_launch_elapsed_ms_preserved': p['launch_elapsed_ms'],
                   'child_reported_release_elapsed_ms_preserved': p['elapsed_ms_at_release'],
                   'limitation_id': 'A14-TIMING-01',
                   'limitation': 'The frozen implementation passes a parent perf_counter value into a child; the child reported a negative launch delta (-4.862ms). A shared cross-process clock basis is not established. Child relative values and its 22s assertion cannot prove a general shared deadline guard. Parent same-process elapsed plus exact OS exit independently show this finite run ended in 1.140204s. No code was changed or rerun after this anomaly.',
                   'general_22_second_guard_accepted': False},
        'freeze': {'launch_intent': raw(OUT / 'launch-intent.json'), 'bindings_unchanged': all(c['matches'] for c in binding_checks),
                   'frozen_code_modified_after_run': False, 'raw_manifest': 'raw-output-manifest.json',
                   'raw_private_streams_excluded': True, 'git_commit_created': False},
        'scope_preserved': {'writes_by_this_task': ['D:/1800-worktrees/a14-tls-diagnostic/execution-output/', 'D:/1800/.local/stages/a14-tls-diagnostic/'],
                            'mainline_or_product_writes': 0, 'proxy_or_trust_configuration_changes': 0,
                            'certificate_ignore': False, 'other_three_cases': 'HOLD', 'Q22': 'NOT_REPLAYED', 'book_level_submission': 0},
        'author_acceptance_boundary': 'REVIEW only; no independent acceptance, integration, authentication or live business qualification claimed.',
        'next_dependency': 'Registered independent static review of fixed public evidence and release. No new TLS/HTTP/browser action is authorized by this delivery.'}
    save(OUT / 'report.json', report)
    md = '''# A14 单次公开 TLS 诊断交付

作者状态：**REVIEW**。仅提交本次固定失败证据与精确释放，尚未独立接受。

2026-10-20 14:07:42（UTC+08）经固定 `127.0.0.1:7897` 代理向 `www.usense.com:443` 发起唯一严格 TLS 握手意图。目标、SNI、verify_hostname 同名，启用 verify_return_error；OpenSSL 退出码 **1**，首个校验错误及返回码均为 **62 / HOSTNAME_MISMATCH**。叶证书公开 SAN 仅含 `qt.lingshubao.cn`，未覆盖目标。

叶证书公开字段显示 notAfter 为 **2026-08-30 00:16:04 UTC**，早于本次观测时点。由于首个校验错误为62，不能声称后继链或有效期校验全部完成。共提取4张唯一服务端公开证书；showcerts 输出不能视为已经验证的证书链。完整公开字段与指纹见 [public-certificate-results.json](public-certificate-results.json)，证书见 certificate-01.pem 至 certificate-04.pem。

本次只证明该代理路径返回了上述证书和严格验证失败。网站、代理、DNS或其他环节的根因仍 **UNKNOWN**。Git OpenSSL 的既有 PEM CA 与 Windows/Edge 信任库不同，不能直接认定 Edge 的根因；认证、书籍访问与首题保存读回均未执行。

握手额度 **1/1已耗尽，剩余0**。目标 HTTP 请求0、stdin 应用字节0、浏览器/profile/登录/业务0、重试/回退0。存在必要的代理 CONNECT 意图，故不宣称“任何HTTP字节均为0”。原A13/A10额度不恢复，后续网络步骤 NOT_RUN。

OpenSSL PID 71152：保留的进程句柄确认创建身份一致、OS退出、退出码1、wait已触发；两路输出均EOF并排空，线程join、私有文件关闭，stdin/stdout/stderr及进程句柄关闭后均观察到 ERROR_INVALID_HANDLE。wrapper PID 59584：外层保留句柄确认相同创建身份、OS退出码0、wait已触发、句柄关闭与重定向文件关闭。见 [process-result.json](process-result.json) 和 [wrapper-os-release.json](wrapper-os-release.json)。

**计时限制 A14-TIMING-01 保留：**冻结实现将父进程的 perf_counter 值传入子进程，原记录出现启动差值 **-4.862ms**。公共跨进程时基未获证明，子进程的相对数值及22秒断言不能证明通用共享截止守卫。外层同一进程独立测得 wrapper 完整OS退出用时 **1140.204ms**，本次实际在22秒以内。该异常发现后未修改冻结wrapper、未补跑、未建立第二连接，交由独立验收判断。

原始 stdout 12575 bytes、stderr 241 bytes及wrapper空流留在私有 .local，仅交付长度和SHA256。共享目录只含公开证书、白名单字段、代码、冻结intent、进程元数据和报告；未导出Session-ID、Master-Key、票据、keylog或未脱敏原文。见 [private-raw-hash-manifest.json](private-raw-hash-manifest.json)。

冻结入口：[launch-intent.json](launch-intent.json)、[static-review.json](static-review.json)、[preflight.json](preflight.json)。原始字节清单：[raw-output-manifest.json](raw-output-manifest.json)。所有冻结代码/二进制/CA摘要复核一致。未改主线、产品、代理/信任配置或profile；其他三例HOLD、Q22不重放、0B消息、无书级提交。

本轮执行已经停止并释放。下一步仅为已登记独立对话对固定公开raw的静态核证，不能将交付理解为新握手、证书例外、配置修复或平台操作授权。
'''
    with (OUT / 'report.md').open('x', encoding='utf-8', newline='\n') as f:
        f.write(md)
    audit = {'scope': 'AUTHOR_FINAL_RAW_FREEZE_CHECK_NOT_INDEPENDENT_ACCEPTANCE',
             'frozen_bindings': binding_checks, 'intent_hash_matches_prelaunch': True,
             'tls_release_evidence_complete': tls_release, 'wrapper_release_evidence_complete': wrapper_release,
             'timing_anomaly_preserved': True, 'timing_guard_general_acceptance': False,
             'raw_stream_content_shared': False, 'additional_network_runs': 0}
    save(OUT / 'archive-audit.json', audit)
    manifest = {'task_id': 'A14', 'execution_id': intent['execution_id'], 'status': 'FROZEN_FOR_REVIEW',
                'hash_representation': 'raw on-disk bytes; no Git/CRLF normalization',
                'private_raw_contents_excluded': True, 'self_excluded': 'raw-output-manifest.json',
                'members': [{'path': f.name, **raw(f)} for f in sorted(OUT.iterdir()) if f.is_file() and f.name != 'raw-output-manifest.json']}
    save(OUT / 'raw-output-manifest.json', manifest)
    assert all(raw(OUT / x['path']) == {k: x[k] for k in ('size', 'sha256')} for x in manifest['members'])
    print(json.dumps({'author_status': 'REVIEW', 'tls_result': report['tls_result'],
                      'released': report['release']['all_observed_processes_and_owned_handles_released'],
                      'public_members': len(manifest['members']), 'manifest': raw(OUT / 'raw-output-manifest.json'),
                      'report_json': raw(OUT / 'report.json'), 'report_md': raw(OUT / 'report.md'),
                      'timing_limitation': 'A14-TIMING-01', 'remaining_handshake_budget': 0}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
