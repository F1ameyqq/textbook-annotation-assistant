"""Seal A20 evidence only; no product import, network, private read or Git call."""
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
AUTHOR = ROOT / 'docs/evidence/A20/authenticated-source'
REVIEWER = '01a159ab-01ba-7093-89a6-69e7ce572c38'
WORKFLOW = '8619a58874563b6b20ef435a0796355638d25f8b'
PRODUCT = '28203196b4f2dae27b1de4213b27da9a41ae3139'
FINAL = 'b41e88d7756fde9d7f1b348ce5a300d1104e765b'
BASE = '38e86a1c153eb0ad68ebd22d4403602ffaa6852b'
DIGEST = '91db377e44b5b864208cc27a078d25266b3375bba2fdee18b9c648f37b572a7b'
NOW = datetime.now(timezone.utc).isoformat()

def read(path):
    return json.loads(path.read_bytes())

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write(name, value):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as stream:
        if isinstance(value, str):
            stream.write(value.rstrip('\n') + '\n')
        else:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')

def verify_member(item, size_key='size'):
    raw = (ROOT / item['path']).read_bytes()
    assert len(raw) == item[size_key] and sha(raw) == item['sha256'], 'ORIGINAL_INPUT_MUTATED'
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert blob == item['blob'] and item['mode'] == '100644' and item['type'] == 'blob', 'GIT_BLOB_IDENTITY_MISMATCH'
    return item['path']

inputs = read(OUT / 'input-raw-manifest.json')
assert sha((OUT / 'input-raw-manifest.json').read_bytes()) == '5db4d9768e77b72fd06995bdce321d2c1eac706ce0e01926c2f45fc0f964c5b4'
preserved = [verify_member(item) for item in inputs['members']]
assert len(preserved) == 114
candidate_raw = (AUTHOR / 'candidate-manifest.json').read_bytes()
assert sha(candidate_raw) == DIGEST
candidate = json.loads(candidate_raw)
dependencies = [verify_member(item) for item in candidate['members']]
assert len(dependencies) == 27 and len(set(dependencies)) == 27
assert set(dependencies).issubset(set(preserved))
initializers = candidate['package_initialization']
assert initializers['regular'] == ['src/annotation/__init__.py', 'src/annotation/source/usense/current_readonly/__init__.py']
assert all(path in dependencies for path in initializers['regular'])
assert all(not (ROOT / path / '__init__.py').exists() for path in initializers['namespace_without_initializer'])
write('input-preservation-final.json', {'task': 'A20', 'result': 'PRESERVED',
    'raw_members': len(preserved), 'candidate_members': len(dependencies),
    'candidate_sha256': DIGEST, 'checked_after_suite_and_controls': True,
    'same_bytes_size_Git_blob_mode_type': True, 'changed_original_inputs': [],
    'regular_initializers': initializers['regular'],
    'namespace_without_initializer': initializers['namespace_without_initializer'],
    'baseline_31754_and_old_evidence_30522': 'COORDINATOR_FIXED_VERIFICATION_REFERENCE_ONLY_NOT_REEXECUTED_IN_THIS_114_FILE_EXPORT'})

task = Path('D:/1800/docs/tasks/A20-fixed-authenticated-source-independent-review.md').read_bytes()
assert sha(task) == 'fb9b0a13f1217b1393efadec05486ec96274f79a13e121264e6dd467c7b727b4'
with (OUT / 'dispatch-task.md').open('xb') as stream:
    stream.write(task)
suite = read(OUT / 'suite/run01/result.json')
controls = read(OUT / 'controls/run01/result.json')
assert suite['success'] and suite['tests_run'] == 35 and suite['failures'] == suite['errors'] == 0
assert controls['success'] and controls['tests_run'] == 5 and controls['failures'] == controls['errors'] == 0
static = read(OUT / 'static-source-verification.json')
assert static['result'] == 'STATIC_ORIGINAL_SOURCE_VERIFIED' and len(static['fixed_session_GETs']) == 3

checks = [
    {'id': 'P01', 'result': 'PASS', 'basis': '114 input raw members and 27 candidate dependencies; raw no-Git export; both regular initializers and intentional namespace packages checked'},
    {'id': 'P02', 'result': 'PASS_STATIC_ONLY', 'basis': 'Authorized original Script SHA/size matches A19; 15 static needles, three exact session GETs and two fixed login redirect offsets verified independently'},
    {'id': 'P03', 'result': 'PASS', 'basis': 'Frozen gate/template full scope and direct A20 credential/TLS decision requirements; missing and changed scope fields rejected by new suite'},
    {'id': 'P04', 'result': 'PASS_OFFLINE_ONLY', 'basis': 'Fixed ordered two-Document reservations and original frame/origin checks; fake duplicate navigation refusal; outer 900s limits inspected without OS execution'},
    {'id': 'P05', 'result': 'PASS_OFFLINE_ONLY', 'basis': 'Root configuration only after live approval plus known form; required original profile fingerprint and username-derived directory; fake origin-change and expired approval controls'},
    {'id': 'P06', 'result': 'PASS_OFFLINE_ONLY', 'basis': 'Durable intent before click, native/context each reserve once, exact two-key payload, no second actual POST; both observation orders and concurrent duplicates checked'},
    {'id': 'P07', 'result': 'PASS_OFFLINE_ONLY', 'basis': 'Refresh/automatic resend/other API writes refused; three fixed session GETs per phase; existing six GET/two original/version1/shared16/sample0 limits retained'},
    {'id': 'P08', 'result': 'PASS_ORCHESTRATION_ONLY', 'basis': 'Login response, SPA transition, protected viewer/current session and book identity remain distinct; fake same-page/guard collect six GETs/two originals/two mappings, unchanged readers mocked in this orchestration test'},
    {'id': 'P09', 'result': 'PASS_OFFLINE_ONLY', 'basis': 'Finite response projections and safe exceptions; fake secret canary absent from runtime outputs; current-session HTTP failure interrupts readiness; prior-phase late response refused'},
    {'id': 'P10', 'result': 'PASS_OFFLINE_ONLY', 'basis': 'First error/UNKNOWN stop/NOT_RUN and fake release controls; fixed native resource-close code inspected, no real OS resource release or platform proof claimed'}
]
limitations = [
    'No real browser/network/profile/config/native API/occupancy or product/launcher child process was used. Fixed native Python reference is imported inertly by the offline tests.',
    'Actual current DOM, CDP complete postData, frontend request order, service responses, authenticated reuse display and protected session behavior remain untested. Any deviation must stop without resend or scope expansion.',
    'The full successful collect test exercises authenticate, real guard methods and collection orchestration with fake page/credentials. get_once/original_once/visible_mapping are fake in that test; it is not new image/geometry/platform acceptance.',
    'Unchanged decode/js_wire/native dependencies are byte-bound. Earlier finite evidence is retained within its prior scope; no old suite was rerun and no historical NOT_RUN was changed.',
    'Baseline 31754 members, four permitted modifications and 30522 old evidence preservation are supplied coordinator fixed verification facts. This independent final comparison covers the supplied 114-file raw export and all 27 candidate dependencies.',
    'Author first fake-clock run failure/error and first packaging failure/partial raw remain byte-identical; this review did not replay them.',
    'A19 actual 401/expiry cause and launcher own OS exit identity remain UNKNOWN; this offline review does not close them.',
    'Authentication, current book source inventory, current mapping and first question save/readback are NOT_PROVEN/NOT_RUN. R02 remains unfixed and disabled; body/schema UNKNOWN; write_eligible=false.',
    'A17 standing readonly TLS permission does not authorize this credential transmission. Coordinator must obtain the concrete A20 direct decision after this preflight, then separately bind/activate its one live round.'
]
template = read(AUTHOR / 'independent-report-template-NONEXECUTABLE.json')
binding_keys = [key for key in template if key != 'result']
assert all(type(template[key]) is type(candidate[key]) and template[key] == candidate[key] for key in binding_keys)
machine = dict(template)
machine.update({
    'result': 'ACCEPTED_OFFLINE_ONLY', 'acceptance_scope': 'BOUNDED_OFFLINE_AUTHENTICATION_AND_SAME_CONTEXT_SOURCE_PREFLIGHT',
    'reviewer_thread_id': REVIEWER, 'review_dispatch_workflow_commit': WORKFLOW,
    'base_commit': BASE, 'product_commit': PRODUCT, 'final_commit': FINAL,
    'input_manifest_sha256': '5db4d9768e77b72fd06995bdce321d2c1eac706ce0e01926c2f45fc0f964c5b4',
    'raw_input_count': 114, 'candidate_dependency_count': 27, 'scope_binding_field_count': len(binding_keys),
    'created_at_utc': NOW, 'actual_review_directory': str(OUT),
    'actual_report_path': str(OUT / 'report.md'),
    'new_suite': {'path': 'suite/run01/result.json', 'tests': 35, 'failures': 0, 'errors': 0, 'runner_duration_ms': suite['duration_ms']},
    'independent_controls': {'path': 'controls/run01/result.json', 'tests': 5, 'failures': 0, 'errors': 0, 'runner_duration_ms': controls['duration_ms']},
    'checks': checks, 'limitations': limitations,
    'real_credential_reads': 0, 'real_profile_inspections': 0, 'real_browser_contexts': 0,
    'real_network_requests': 0, 'real_native_API_calls': 0, 'real_occupancy_checks': 0,
    'product_child_processes': 0, 'real_login_submissions': 0, 'actual_business_writes': 0,
    'old_suites_run': 0, 'decision_created': False, 'activation_created': False, 'live_activated': False,
    'platform_authentication': 'NOT_PROVEN', 'current_book_source_inventory': 'NOT_PROVEN',
    'body_status': 'UNKNOWN', 'schema_status': 'UNKNOWN', 'write_eligible': False,
    'first_question_status': 'NOT_RUN', 'other_three_cases': 'HOLD',
    'Q22_sample_navigation_replay': 0, 'B_messages': 0, 'book_submission': 0,
    'review_resources_state': 'RELEASED_OFFLINE_ONLY',
    'next_dependency': 'Coordinator fixed closure and concrete A20 direct credential/TLS decision; no live authority granted by this review'
})
write('independent-result.json', machine)
table = '\n'.join('| {id} | {result} | {basis} |'.format(**row) for row in checks)
report = '''# A20 有限独立离线预检

结论：**ACCEPTED_OFFLINE_ONLY**，仅接受固定候选的有界登录恢复与同 context 书源读取离线预检。未发现需要阻断本候选的保密、重复提交、业务误写、越界、停止或事实问题。真实认证、书源与首题保存读回均未证明；本结论不授予登录、凭据发送或 live 激活权。

独立聊天 `{reviewer}`；派发 workflow `{workflow}`。基线 `{base}`，冻结产品 `{product}`，final `{final}`，产品 workflow `52be34a72c43a7331976aba4b286138b9183856b`，候选 SHA `{digest}`。

新 suite **35/35，{suite_ms}ms**；独立控制 **5/5，{control_ms}ms**，均为 runner 实际记录的墙钟耗时。只运行本 A20 新测试和五项控制，各一次，无旧 suite/失败重放。原 runner 保留相同私有路径 audit、内存事件循环及网络/Popen/native/profile/占用阻断，只改变 ROOT、输出位置与测试入口；差异见 runner-transformation.json。独立控制覆盖两种守卫顺序与并发重复 POST、跨阶段迟到响应、填写期间来源变化、过期决定前置拒绝、意图持久化失败不点击及异常脱敏。

114 输入成员已先核 SHA256/Git blob/长度/声明 mode/type，末尾再次核证原 bytes 全保持；27 候选依赖及父包闭包全匹配。30522 旧证据及 31754 基线成员全树保全引用调度固定核证，本隔离没有重复全树核验，亦不修复/读取作者活动目录。

静态核读唯一获准 Script 原件：3,065,996 bytes，SHA d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41，与 A19 已捕获元数据一致。独立检查 15 个静态位置、三条精确 session GET 和两个登录跳转位置，确认登录 POST/两键/Hn 数值成功规则、UI 调用、SPA push、401 刷新与原请求重发；原件未执行/复制，sidecar 未读，A19 触发原因保持 UNKNOWN。

| 组 | 结论 | 证据范围 |
|---|---|---|
{table}

实际门禁严格取冻结 template 的完整 **{scope_count} 项 scope 字段**，包括两导航顺序、精确登录 POST/两键、原配置与 profile 指纹、session 每路径每阶段一次/两阶段、refresh 与重发零、直接 A20 凭据决定要求。机器结果的 report_path 保留 gate 要求的根接收路径；本次实际文件位于本独立目录，由调度核证后接收，独立未写根协调文件。

限制：

{limits}

本轮 0 真实凭据/profile/browser/network/native API/占用/产品子进程，0 登录/业务写入/decision/activation/live。只导入固定 Python 参考代码作内存测试，不代表执行原 native 工具。作者失败、首次包装/部分 raw 和旧证据均保留。无待持有资源和等待进程，释放见 release.json。下一步由根落实本次具体凭据/TLS 直接决定，不借用 A17 只读许可；其他三例 HOLD，Q22 不导航/样题/重放，0 B 消息、无书级送交，2026-10-22 晚截止保持。
'''.format(reviewer=REVIEWER, workflow=WORKFLOW, base=BASE, product=PRODUCT, final=FINAL,
    digest=DIGEST, suite_ms=suite['duration_ms'], control_ms=controls['duration_ms'],
    table=table, scope_count=len(binding_keys), limits='\n\n'.join('- ' + x for x in limitations))
write('report.md', report)
write('release.json', {'task': 'A20', 'reviewer_thread_id': REVIEWER,
    'state': 'RELEASED_OFFLINE_ONLY', 'released_at_utc': NOW,
    'product_commit': PRODUCT, 'final_commit': FINAL, 'candidate_sha256': DIGEST,
    'new_suite_runs': 1, 'independent_control_runs': 1, 'old_suite_runs': 0,
    'real_browser_contexts_created': 0, 'real_runtimes_created': 0,
    'real_profile_leases': 0, 'real_native_API_calls': 0, 'real_occupancy_checks': 0,
    'product_child_processes_started': 0, 'real_network_requests': 0, 'real_credential_reads': 0,
    'decision_or_activation_created': False, 'pending_owned_contexts': 0,
    'pending_owned_product_processes': 0, 'pending_owned_jobs': 0,
    'pending_real_callbacks': 0, 'waiting_processes': 0, 'background_helpers_started': 0,
    'test_event_loops': 'CLOSED_BY_ISOLATED_UNITTEST_MEMORY_EVENT_LOOP',
    'fixed_native_reference_imported_without_API_calls': True,
    'old_runtime_or_Edge_terminated': False,
    'boundary': 'Offline resource release only; no real OS identity, browser cleanup or platform authentication claim'})

# The fake fixture's literal is read as AST metadata, without importing it again.
tree = ast.parse((ROOT / 'tests/a20_authenticated_source/test_authenticated_source.py').read_text(encoding='utf-8'))
canary = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == 'SECRET' for target in node.targets))
runtime_outputs = [OUT / folder / 'run01' / name for folder in ('suite', 'controls')
    for name in ('stdout.txt', 'stderr.txt', 'result.json')]
runtime_outputs += [OUT / 'report.md', OUT / 'independent-result.json', OUT / 'release.json']
assert all(canary.encode() not in path.read_bytes() for path in runtime_outputs), 'FAKE_PRIVATE_VALUE_IN_RUNTIME_OUTPUT'
write('output-redaction-check.json', {'task': 'A20', 'result': 'PASS',
    'check': 'Fake credential/returned-token canary absent from the actual suite/control stdout/stderr/results and report/result/release',
    'files_checked': [str(path.relative_to(OUT)).replace('\\', '/') for path in runtime_outputs],
    'real_credential_values_available_to_reviewer': False,
    'claim_boundary': 'Finite fake output check plus code inspection; no real credential or live screenshot was acquired'})

for item in inputs['members']:
    verify_member(item)
members = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw = path.read_bytes()
        members.append({'path': str(path.relative_to(OUT)).replace('\\', '/'),
            'bytes': len(raw), 'sha256': sha(raw)})
write('sha256-manifest.json', {'schema': 'A20-independent-review-output-manifest/v1',
    'task': 'A20', 'reviewer_thread_id': REVIEWER, 'root': str(OUT),
    'candidate_sha256': DIGEST, 'member_count': len(members), 'members': members,
    'self_excluded': True, 'self_sha256': 'Returned externally in final handoff',
    'result': 'ACCEPTED_OFFLINE_ONLY', 'real_live_authorized': False})
print(json.dumps({'result': machine['result'], 'scope_binding_fields': len(binding_keys),
    'input_raw_preserved': 114, 'candidate_dependencies': 27, 'output_members': len(members),
    'manifest_sha256': sha((OUT / 'sha256-manifest.json').read_bytes()),
    'report_sha256': sha((OUT / 'report.md').read_bytes()),
    'machine_result_sha256': sha((OUT / 'independent-result.json').read_bytes()),
    'release_sha256': sha((OUT / 'release.json').read_bytes())}))
