# -*- coding: utf-8 -*-
"""Write only the A14 independent review artifacts; no author imports or networking."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path('D:/1800-worktrees/a14-tls-review')
OUT = ROOT / 'review-output'
EX = ROOT / 'execution-output'

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def raw(path):
    value = path.read_bytes()
    return {'size': len(value), 'sha256': hashlib.sha256(value).hexdigest()}

def save(name, value):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

baseline = load(OUT / 'input-precheck.json')
checks = load(OUT / 'independent-checks.json')
proc = load(EX / 'process-result.json')
outer = load(EX / 'wrapper-os-release.json')
intent = load(EX / 'launch-intent.json')
now = datetime.now(timezone.utc)

criteria = [
    ('C01', 'PASS', 'Fixed inputs', '23 files / 101468 bytes; all size/SHA256 match. Author manifest has 18 nonself files plus itself. No missing/extra/reparse/symlink inputs.'),
    ('C02', 'PASS_STATIC_FIXED_PATH', 'Strict target/argv', 'connect www.usense.com:443; SNI/verify_hostname www.usense.com; verify_return_error; fixed CA; shell=False; no reconnect, weakened check, alternate target or credentials.'),
    ('C03', 'PASS_STATIC_FIXED_PATH', 'Proxy guard', 'Frozen enabled 127.0.0.1:7897, no PAC/auth syntax. Parser rejects disabled/PAC/nonloopback/auth syntax/ambiguous or missing https/invalid port. No proxy credential args; narrow environment. Registry not reread.'),
    ('C04', 'SUPPORTED_DECLARED_SINGLE_RUN', 'Freeze and one-time scope', 'One Popen site at each layer and exclusive x-mode claims. Code, standard, preflight/static-review, recorded binary/CA digests agree across fixed intent/audit. Private claim contents not reopened; no external OS/network census.'),
    ('C05', 'PASS_STATIC_AND_FIXED_METADATA', 'No target HTTP', 'TLS stdin PIPE has no write call; EOF follows explicit verification failure. Declared target HTTP0/application bytes0; necessary proxy CONNECT intent1. No claim of zero HTTP bytes everywhere.'),
    ('C06', 'PASS_PUBLIC_PACKAGE_ONLY', 'Privacy', 'Only PEM, public fields, numeric error codes and raw length/hash exported. Secret-value patterns absent from all23 fixed public inputs. No keylogfile/sess_out/trace/msg. Private raw streams/claims not read; extraction not replayed.'),
    ('C07', 'PASS_INDEPENDENT_PUBLIC_PEM', 'Certificate facts', 'Four PEMs independently decoded with matching public fields and DER/PEM hashes. Sole leaf DNS SAN qt.lingshubao.cn does not cover target. Public notAfter 2026-08-30T00:16:04Z precedes observation 2026-10-20T06:07:42.316294Z.'),
    ('C08', 'LIMITED_SANITIZED_FAILURE_EVIDENCE', 'Error and trust', 'Fixed sanitized extraction reports error/return62; explicit failure signal and exit1 agree. Private original error text not reread. Issuer/subject naming sequence is not signature/trust proof; showcerts is not a validated chain. No root-cause or Edge equivalence conclusion.'),
    ('C09', 'PASS_FINITE_EXACT_HANDLE_METADATA', 'OpenSSL release', 'PID71152 same creation FILETIME on retained-handle exit1, signaled wait; EOF/drain files closed, readers joined; pipe/process handles closed with invalid-handle result. No live process query.'),
    ('C10', 'PASS_FINITE_EXACT_HANDLE_METADATA', 'TLS wrapper release', 'PID59584 same creation FILETIME on retained-handle exit0, signaled wait, handle invalid after close, redirects closed. No session-wide/outer-ancestor OS-exit claim.'),
    ('C11', 'PASS_FINITE_DURATION_ONLY', 'Observed duration', 'Parent same-process1140.204ms; independently recomputed wrapper OS1136.5958ms and TLS OS974.7273ms, nested lifetimes. This finite run exited below22s.'),
    ('C12', 'NOT_ACCEPTED_GENERAL_GUARD', '20s/22s guarantee', 'A14-TIMING-01: child launch-4.862ms leaves shared clock unproved. Outer timeout only records UNKNOWN and closes handle; child final kill requires being before inherited deadline. General deadline/cleanup not accepted; timeout branch not executed.'),
    ('C13', 'PASS_LIMITED_REPORT_SEMANTICS', 'Failure semantics', 'process-result first_failure=null/REVIEW means supervisor captured a result, not successful TLS. Public expiry is a separate field observation; later OpenSSL validation stages not established.'),
    ('C14', 'PASS_PRESERVED_HISTORY', 'A13 UNKNOWN', 'Prior wrapper PID31208 OS exit identity remains UNKNOWN; A14 does not repair or replace that history.'),
    ('C15', 'PASS_NO_SUCCESSOR_AUTHORITY', 'Scope and quota', 'TLS intent1/1 consumed, remaining0, old budgets not restored. Authentication/book/save/refresh/reopen NOT_RUN. Other3 HOLD; Q22 not replayed; B0; no certificate exception, repair or successor connection authorized.')
]

finding = {
    'id': 'A14-TIMING-01',
    'disposition': 'OPEN_GENERAL_DEADLINE_GUARD_NOT_ACCEPTED',
    'blocks_finite_failure_archive': False,
    'blocks': ['general shared 20s/22s deadline acceptance', 'general timeout cleanup/release guarantee'],
    'observed_anomaly': {'child_launch_elapsed_ms': -4.862, 'parent_same_process_elapsed_ms': 1140.204},
    'source_evidence': [
        {'path': 'execution-output/launch_once.py', 'line': 23, 'end_line': 25,
         'fact': 'Passes parent perf_counter start to child.'},
        {'path': 'execution-output/tls_wrapper.py', 'line': 98, 'end_line': 100,
         'fact': 'Child combines inherited start with its local perf_counter.'},
        {'path': 'execution-output/launch_once.py', 'line': 29, 'end_line': 38,
         'fact': 'Outer timeout records UNKNOWN, polls and closes handle; no timeout termination of wrapper/descendant.'},
        {'path': 'execution-output/tls_wrapper.py', 'line': 219, 'end_line': 224,
         'fact': 'Final child kill/wait is conditional on being before inherited deadline.'}
    ],
    'interpretation': 'Finite fast failure and exact two observed OS exits remain accepted. Child timing and parent wait do not establish the general cleanup guarantee. No cause of the clock offset is attributed.',
    'repair_or_rerun_performed': False,
    'new_repair_or_execution_authority': False
}

report = {
    'schema_version': 1, 'task_id': 'A14', 'review_mode': 'FIXED_PUBLIC_STATIC_ONLY',
    'status': 'ACCEPTED_FAILURE_ARCHIVE_PUBLIC_CERTIFICATE_AND_EXACT_OWNED_RELEASE_ONLY',
    'general_deadline_guard_status': 'NOT_ACCEPTED_A14_TIMING_01',
    'at_utc': now.isoformat(), 'at_local': now.astimezone(timezone(timedelta(hours=8))).isoformat(),
    'coordinator_thread_id': '01a15768-1e2d-7781-b29f-1f7376270216',
    'execution_thread_id': '01a157e6-628a-75d2-b685-6cb98e5fb0af',
    'review_thread_id': '01a157e7-1425-7f53-8e84-1382566ffce6',
    'workflow_commit': intent['workflow_commit'], 'execution_id': intent['execution_id'],
    'fixed_execution_manifest_sha256': baseline['expected_execution_manifest_sha256'],
    'input_root': str(ROOT), 'input_count': 23, 'input_bytes': 101468,
    'input_groups': {'execution_output_with_manifest': 19, 'standards': 2, 'prior_A13_reports': 2},
    'input_precheck': {'path': 'input-precheck.json', **raw(OUT / 'input-precheck.json')},
    'independent_checks': {'path': 'independent-checks.json', **raw(OUT / 'independent-checks.json')},
    'criteria': [{'id': a, 'status': b, 'criterion': c, 'evidence': d} for a,b,c,d in criteria],
    'findings': [finding],
    'accepted_scope': [
        'Fixed sanitized single declared failure archive and four publicly decoded certificates.',
        'Independent SAN/date/fingerprint fields; published error62 remains a sanitized record, not a private raw replay.',
        'Finite creation/exit and owned pipe/handle metadata for OpenSSL PID71152 and TLS wrapper PID59584.'
    ],
    'not_accepted_or_proved': [
        'General shared 20s/22s deadline or timeout cleanup guarantee.',
        'Private TLS extraction replay, private claim contents or global count of all launches/connections.',
        'Installed executable/CA bytes or launch-time memory image independently rehashed; recorded digest/audit consistency only.',
        'Signatures, complete validated chain, trust acceptance, website/proxy/DNS root cause or Windows/Edge equivalence.',
        'Session-wide or outer launcher/tool-shell OS exit identity; only two observed lifetimes accepted.',
        'Authentication, book source/target access, first-question save, content/frame refresh/reopen readback.'
    ],
    'observation': {
        'at_utc': proc['launch_utc'], 'target': 'www.usense.com:443', 'proxy': intent['proxy'],
        'published_sanitized_verify_error_codes': [62], 'published_sanitized_verify_return_codes': [62],
        'category': 'HOSTNAME_MISMATCH', 'strict_TLS_success': False, 'root_cause': 'UNKNOWN',
        'leaf_SAN': ['qt.lingshubao.cn'], 'leaf_SAN_covers_target': False,
        'leaf_not_after_utc': '2026-08-30T00:16:04+00:00', 'leaf_expired_by_public_dates': True,
        'server_sent_unique_public_certificates': 4, 'raw_PEM_occurrences_reported': 8,
        'chain_accepted': False, 'OpenSSL_trust_equals_Edge': False
    },
    'release_evidence': {
        'TLS': {'pid': proc['pid'], 'retained_handle': proc['process_handle'],
                'creation': proc['process_creation'], 'exit': proc['process_exit'], 'exit_code': proc['exit_code'],
                'wait_signaled': proc['wait_signaled'], 'readers_joined': proc['readers_joined'],
                'streams': proc['streams'], 'closed_handles': proc['release']},
        'TLS_wrapper': outer,
        'scope': 'Two observed retained-handle lifetimes and owned stream/handle metadata; not all shells/ancestors/session processes.'
    },
    'timing': checks['timing'],
    'declared_author_counts': {'TLS_launches': 1, 'TLS_handshake_intents': 1, 'wrapper_launches': 1,
        'target_HTTP_requests': 0, 'proxy_CONNECT_intents': 1, 'stdin_application_bytes': 0,
        'browser_profile_login_business': 0, 'retry_or_fallback': 0},
    'reviewer_counters': {'author_imports_or_runs': 0, 'TLS_network_or_HTTP': 0, 'browser_profile_login_business': 0,
        'process_scans': 0, 'private_raw_reads': 0, 'registry_or_trust_reads_or_writes': 0,
        'installed_binary_CA_reads': 0, 'Git_commands': 0, 'mainline_writes': 0,
        'B_or_other_chat_messages': 0, 'local_public_PEM_decodes': 4, 'local_x509_processes': 0,
        'independent_static_utility_runs': 1, 'independent_static_utility_exit_code': 0},
    'static_utility_events': [{
        'event': 'REPORT_GENERATION_SOURCE_DECODING_FAILED_BEFORE_EXECUTION',
        'exit_code': 1,
        'error': 'SyntaxError: Non-UTF-8 code starting with byte 0xe6 in stdin on line120; no encoding declared.',
        'cause_boundary': 'PowerShell-piped report source rejected before any Python statements ran.',
        'outputs_created_by_failed_attempt': 0, 'network_or_author_runs': 0,
        'correction': 'Write this independent report generator as UTF-8 file; no frozen author code changed.'
    }],
    'budget': {'author_TLS_limit': 1, 'author_TLS_used': 1, 'author_TLS_remaining': 0,
        'reviewer_network_limit': 0, 'old_A13_A10_budgets_restored': False, 'successor_execution_authorized': False},
    'historical_A13': {'wrapper_pid': 31208, 'wrapper_OS_exit_identity': 'UNKNOWN', 'changed_by_A14': False},
    'scope_preserved': {'other_three_cases': 'HOLD', 'Q22': 'NOT_REPLAYED', 'B_messages': 0,
        'book_submission': 0, 'first_question_save_and_readback': 'NOT_RUN'},
    'input_postreview': {'path': 'input-postcheck.json', 'unchanged_count': 23},
    'reviewer_release': {
        'state': 'RELEASED_NO_RUNTIME_RESOURCES_ACQUIRED', 'owned_product_browser_profile_resources': 0,
        'background_threads_or_child_processes_created_by_checker': 0, 'source_files_changed': 0,
        'writes_only_below': str(OUT),
        'basis': 'Static checker exit0; PEM decode in-process only; all artifact files use closing contexts; no runtime handles acquired.',
        'further_action': 'STOPPED_NO_RETRY_NO_REPAIR_NO_CONNECTION_NO_MESSAGES'
    },
    'output_manifest': {'path': 'raw-output-manifest.json', 'self_excluded': True,
                        'hash_representation': 'raw bytes, UTF-8, no Git normalization'},
    'next_dependency': 'Coordinator may record this limited archive/release decision. No diagnostic, repair, certificate exception, login or business successor is authorized.'
}

save('report.json', report)
md = '''# A14 独立静态核证

结论：`ACCEPTED_FAILURE_ARCHIVE_PUBLIC_CERTIFICATE_AND_EXACT_OWNED_RELEASE_ONLY`。仅接受固定公开失败归档、公开证书字段与两项自有进程的精确释放。通用截止守卫仍为 `NOT_ACCEPTED_A14_TIMING_01`，不释放平台或业务后继。

独立对话 `01a157e7-1425-7f53-8e84-1382566ffce6`；执行对话 `01a157e6-628a-75d2-b685-6cb98e5fb0af`；工作流 `cae8275555a7a77b303dae50fe9d8d3a3b4ce2c9`。作者清单 SHA256 `aaf8a90ed9b82d707d6f736deb1f6ba9c409ab582c8dc2bf89cdac58d07bba8d`。

隔离输入23项、101468 bytes：19执行输出、2标准、2历史A13报告，size/SHA256全匹配，无缺失、额外或reparse/symlink；作者18项非自身清单和清单自身匹配。[前检](input-precheck.json)、[后检](input-postcheck.json)保留全部23项摘要；[独立计算](independent-checks.json)包含AST、PEM字段、时序和释放核对。

固定argv采用严格目标 `www.usense.com:443`，SNI/verify_hostname同名、verify_return_error、固定CA、shell=False；无reconnect、弱化验证、凭据或回退。冻结代理 `127.0.0.1:7897`；源码拒绝禁用/PAC/非loopback/认证语法/歧义或端口异常，单一固定代理与明确https项区分。未重查registry；二进制/CA摘要仅核包内intent/preflight/audit一致及执行前摘要守卫，未重读本机安装文件。

单次声明由一个OpenSSL和一个TLS wrapper保留句柄生命周期支持，独占x-mode claims在源码中固定；私有claim内容未读，不作全系统启动/连接计数证明。TLS stdin无write调用，本次明确验证失败后EOF；目标HTTP0、应用字节0，另记必要代理CONNECT意图1，不称所有HTTP字节0。1/1额度耗尽、剩余0，A13/A10额度不恢复。

4张公开PEM独立解码，subject/issuer/SAN/日期和DER/PEM指纹一致。叶证书唯一DNS SAN为 `qt.lingshubao.cn`，不覆盖目标。公开notAfter `2026-08-30 00:16:04 UTC`早于观测 `2026-10-20 06:07:42.316294 UTC`。固定脱敏提取记录错误/返回码62、进程exit1；验收未重读私有错误原文。issuer/subject名称相接不等于签名/信任通过；showcerts的8次PEM出现对应4张唯一证书，不由此推断额外握手或完整已验证链。后继有效期/链校验阶段未证明完成。根因UNKNOWN，不归因网站、代理、DNS；Git OpenSSL的PEM CA不等同Windows/Edge信任。

OpenSSL PID71152同一保留句柄创建FILETIME匹配退出记录，exit1、wait触发；两流EOF/排空、文件关闭、线程join，stdin/stdout/stderr及进程句柄关闭后记录invalid handle。TLS wrapper PID59584同一创建身份exit0、wait触发，句柄和重定向文件关闭。仅接受这两项已观察生命周期及其资源，不扩称最外层launcher/工具壳或整个会话所有进程均有OS退出证明。验收未作实时进程扫描。

`A14-TIMING-01`保持开放。父进程同一时基1140.204ms；OS FILETIME独立重算wrapper1136.5958ms、TLS974.7273ms且后者寿命包含于前者。本次已有限退出且低于22秒。子进程以父perf_counter数值相减却得到启动-4.862ms，共享时基未证明，子进程within22断言不能证明通用守卫。另核[外层源码](../execution-output/launch_once.py)29–38行：超时只记UNKNOWN并关闭wrapper句柄；[子层源码](../execution-output/tls_wrapper.py)219–224行：最终kill/wait以尚未超过继承deadline为条件。父层wait不能单独证明超时清理。该分支未执行或补测，冻结码未改，未补握手。

脱敏代码只导出公开PEM/字段、数值错误、长度和摘要；23项输入无实际私钥、Session-ID/Master-Key/keylog/票据值模式。私有原文未读、提取未重放，原流摘要仅核包内跨记录一致。`first_failure=null`/REVIEW只表示监督器取得结果，不表示TLS成功。

A13历史wrapper PID31208的OS退出身份仍UNKNOWN，A14不覆盖。认证、书籍、首题保存及内容/题框刷新重开读回均NOT_RUN；其他三例HOLD、Q22不重放、0B消息、无书级提交。

验收只做本地文件/JSON/AST/hash及4张公开PEM解码：0作者代码导入/运行、0TLS/HTTP/浏览器/profile/凭据/进程扫描、0私有原文、0主线写入。报告生成曾因PowerShell管道编码在Python解析阶段exit1，未写任何报告或执行Python语句；仅改用UTF-8报告生成文件，失败记录保留在JSON。静态检查器exit0，无子进程或后台线程、自有平台资源0；输出文件使用关闭上下文，完成后停止。全部23项输入前后原bytes保全。完整限制见[报告](report.json)，固定输出见[清单](raw-output-manifest.json)。不授权修复、重跑、证书例外或后续连接。
'''
with (OUT / 'report.md').open('x', encoding='utf-8', newline='\n') as f:
    f.write(md)

post = []
for item in baseline['inputs']:
    observed = raw(ROOT / item['path'])
    if observed != {k: item[k] for k in ('size', 'sha256')}:
        raise RuntimeError('POSTREVIEW_INPUT_CHANGED:' + item['path'])
    post.append({'path': item['path'], **observed, 'matches_precheck_and_expected': True})
actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and OUT not in p.parents}
if actual != {x['path'] for x in baseline['inputs']}:
    raise RuntimeError('POSTREVIEW_INPUT_SET_CHANGED')
save('input-postcheck.json', {'status': 'PASS_ALL_23_INPUTS_UNCHANGED', 'input_count': 23,
     'input_bytes': 101468, 'changed': 0, 'missing': 0, 'extra': 0, 'inputs': post})

manifest = {
    'task_id': 'A14', 'review_thread_id': report['review_thread_id'], 'status': 'FROZEN_STATIC_REVIEW_RELEASED',
    'decision': report['status'], 'general_deadline_guard_status': report['general_deadline_guard_status'],
    'hash_representation': 'raw on-disk bytes; UTF-8; no Git/CRLF normalization',
    'self_excluded': 'raw-output-manifest.json',
    'fixed_execution_manifest_sha256': baseline['expected_execution_manifest_sha256'],
    'members': [{'path': p.name, **raw(p)} for p in sorted(OUT.iterdir())
                if p.is_file() and p.name != 'raw-output-manifest.json']
}
save('raw-output-manifest.json', manifest)
for item in manifest['members']:
    if raw(OUT / item['path']) != {k: item[k] for k in ('size', 'sha256')}:
        raise RuntimeError('OUTPUT_CHANGED')
print(json.dumps({'status': report['status'], 'guard': report['general_deadline_guard_status'],
    'postreview_inputs_unchanged': 23, 'output_nonself_members': len(manifest['members']),
    'output_total_with_manifest': len(manifest['members']) + 1,
    'report_json': raw(OUT / 'report.json'), 'report_md': raw(OUT / 'report.md'),
    'manifest': raw(OUT / 'raw-output-manifest.json'),
    'reviewer_released': True, 'network_or_author_runs': 0}, ensure_ascii=False, indent=2))
