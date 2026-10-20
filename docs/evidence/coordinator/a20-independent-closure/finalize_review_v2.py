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
    'Independent report-sealing attempt first failed source decoding before execution. Original helper and exact tool stderr are preserved in report-packaging/run01; the current observed helper bytes decode as UTF-8, initial decoding cause UNKNOWN. A new ASCII-source sealing helper was used, also correcting its own external candidate-digest comparison before execution; no product code or passed tests changed or reran.',
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
assert all(type(template[key]) is type(DIGEST if key == 'candidate_manifest_sha256' else candidate[key]) and template[key] == (DIGEST if key == 'candidate_manifest_sha256' else candidate[key]) for key in binding_keys)
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
report = '''# A20 \u6709\u9650\u72ec\u7acb\u79bb\u7ebf\u9884\u68c0

\u7ed3\u8bba\uff1a**ACCEPTED_OFFLINE_ONLY**\uff0c\u4ec5\u63a5\u53d7\u56fa\u5b9a\u5019\u9009\u7684\u6709\u754c\u767b\u5f55\u6062\u590d\u4e0e\u540c context \u4e66\u6e90\u8bfb\u53d6\u79bb\u7ebf\u9884\u68c0\u3002\u672a\u53d1\u73b0\u9700\u8981\u963b\u65ad\u672c\u5019\u9009\u7684\u4fdd\u5bc6\u3001\u91cd\u590d\u63d0\u4ea4\u3001\u4e1a\u52a1\u8bef\u5199\u3001\u8d8a\u754c\u3001\u505c\u6b62\u6216\u4e8b\u5b9e\u95ee\u9898\u3002\u771f\u5b9e\u8ba4\u8bc1\u3001\u4e66\u6e90\u4e0e\u9996\u9898\u4fdd\u5b58\u8bfb\u56de\u5747\u672a\u8bc1\u660e\uff1b\u672c\u7ed3\u8bba\u4e0d\u6388\u4e88\u767b\u5f55\u3001\u51ed\u636e\u53d1\u9001\u6216 live \u6fc0\u6d3b\u6743\u3002

\u72ec\u7acb\u804a\u5929 `{reviewer}`\uff1b\u6d3e\u53d1 workflow `{workflow}`\u3002\u57fa\u7ebf `{base}`\uff0c\u51bb\u7ed3\u4ea7\u54c1 `{product}`\uff0cfinal `{final}`\uff0c\u4ea7\u54c1 workflow `52be34a72c43a7331976aba4b286138b9183856b`\uff0c\u5019\u9009 SHA `{digest}`\u3002

\u65b0 suite **35/35\uff0c{suite_ms}ms**\uff1b\u72ec\u7acb\u63a7\u5236 **5/5\uff0c{control_ms}ms**\uff0c\u5747\u4e3a runner \u5b9e\u9645\u8bb0\u5f55\u7684\u5899\u949f\u8017\u65f6\u3002\u53ea\u8fd0\u884c\u672c A20 \u65b0\u6d4b\u8bd5\u548c\u4e94\u9879\u63a7\u5236\uff0c\u5404\u4e00\u6b21\uff0c\u65e0\u65e7 suite/\u5931\u8d25\u91cd\u653e\u3002\u539f runner \u4fdd\u7559\u76f8\u540c\u79c1\u6709\u8def\u5f84 audit\u3001\u5185\u5b58\u4e8b\u4ef6\u5faa\u73af\u53ca\u7f51\u7edc/Popen/native/profile/\u5360\u7528\u963b\u65ad\uff0c\u53ea\u6539\u53d8 ROOT\u3001\u8f93\u51fa\u4f4d\u7f6e\u4e0e\u6d4b\u8bd5\u5165\u53e3\uff1b\u5dee\u5f02\u89c1 runner-transformation.json\u3002\u72ec\u7acb\u63a7\u5236\u8986\u76d6\u4e24\u79cd\u5b88\u536b\u987a\u5e8f\u4e0e\u5e76\u53d1\u91cd\u590d POST\u3001\u8de8\u9636\u6bb5\u8fdf\u5230\u54cd\u5e94\u3001\u586b\u5199\u671f\u95f4\u6765\u6e90\u53d8\u5316\u3001\u8fc7\u671f\u51b3\u5b9a\u524d\u7f6e\u62d2\u7edd\u3001\u610f\u56fe\u6301\u4e45\u5316\u5931\u8d25\u4e0d\u70b9\u51fb\u53ca\u5f02\u5e38\u8131\u654f\u3002

114 \u8f93\u5165\u6210\u5458\u5df2\u5148\u6838 SHA256/Git blob/\u957f\u5ea6/\u58f0\u660e mode/type\uff0c\u672b\u5c3e\u518d\u6b21\u6838\u8bc1\u539f bytes \u5168\u4fdd\u6301\uff1b27 \u5019\u9009\u4f9d\u8d56\u53ca\u7236\u5305\u95ed\u5305\u5168\u5339\u914d\u300230522 \u65e7\u8bc1\u636e\u53ca 31754 \u57fa\u7ebf\u6210\u5458\u5168\u6811\u4fdd\u5168\u5f15\u7528\u8c03\u5ea6\u56fa\u5b9a\u6838\u8bc1\uff0c\u672c\u9694\u79bb\u6ca1\u6709\u91cd\u590d\u5168\u6811\u6838\u9a8c\uff0c\u4ea6\u4e0d\u4fee\u590d/\u8bfb\u53d6\u4f5c\u8005\u6d3b\u52a8\u76ee\u5f55\u3002

\u9759\u6001\u6838\u8bfb\u552f\u4e00\u83b7\u51c6 Script \u539f\u4ef6\uff1a3,065,996 bytes\uff0cSHA d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41\uff0c\u4e0e A19 \u5df2\u6355\u83b7\u5143\u6570\u636e\u4e00\u81f4\u3002\u72ec\u7acb\u68c0\u67e5 15 \u4e2a\u9759\u6001\u4f4d\u7f6e\u3001\u4e09\u6761\u7cbe\u786e session GET \u548c\u4e24\u4e2a\u767b\u5f55\u8df3\u8f6c\u4f4d\u7f6e\uff0c\u786e\u8ba4\u767b\u5f55 POST/\u4e24\u952e/Hn \u6570\u503c\u6210\u529f\u89c4\u5219\u3001UI \u8c03\u7528\u3001SPA push\u3001401 \u5237\u65b0\u4e0e\u539f\u8bf7\u6c42\u91cd\u53d1\uff1b\u539f\u4ef6\u672a\u6267\u884c/\u590d\u5236\uff0csidecar \u672a\u8bfb\uff0cA19 \u89e6\u53d1\u539f\u56e0\u4fdd\u6301 UNKNOWN\u3002

| \u7ec4 | \u7ed3\u8bba | \u8bc1\u636e\u8303\u56f4 |
|---|---|---|
{table}

\u5b9e\u9645\u95e8\u7981\u4e25\u683c\u53d6\u51bb\u7ed3 template \u7684\u5b8c\u6574 **{scope_count} \u9879 scope \u5b57\u6bb5**\uff0c\u5305\u62ec\u4e24\u5bfc\u822a\u987a\u5e8f\u3001\u7cbe\u786e\u767b\u5f55 POST/\u4e24\u952e\u3001\u539f\u914d\u7f6e\u4e0e profile \u6307\u7eb9\u3001session \u6bcf\u8def\u5f84\u6bcf\u9636\u6bb5\u4e00\u6b21/\u4e24\u9636\u6bb5\u3001refresh \u4e0e\u91cd\u53d1\u96f6\u3001\u76f4\u63a5 A20 \u51ed\u636e\u51b3\u5b9a\u8981\u6c42\u3002\u673a\u5668\u7ed3\u679c\u7684 report_path \u4fdd\u7559 gate \u8981\u6c42\u7684\u6839\u63a5\u6536\u8def\u5f84\uff1b\u672c\u6b21\u5b9e\u9645\u6587\u4ef6\u4f4d\u4e8e\u672c\u72ec\u7acb\u76ee\u5f55\uff0c\u7531\u8c03\u5ea6\u6838\u8bc1\u540e\u63a5\u6536\uff0c\u72ec\u7acb\u672a\u5199\u6839\u534f\u8c03\u6587\u4ef6\u3002

\u9650\u5236\uff1a

{limits}

\u672c\u8f6e 0 \u771f\u5b9e\u51ed\u636e/profile/browser/network/native API/\u5360\u7528/\u4ea7\u54c1\u5b50\u8fdb\u7a0b\uff0c0 \u767b\u5f55/\u4e1a\u52a1\u5199\u5165/decision/activation/live\u3002\u53ea\u5bfc\u5165\u56fa\u5b9a Python \u53c2\u8003\u4ee3\u7801\u4f5c\u5185\u5b58\u6d4b\u8bd5\uff0c\u4e0d\u4ee3\u8868\u6267\u884c\u539f native \u5de5\u5177\u3002\u4f5c\u8005\u5931\u8d25\u3001\u9996\u6b21\u5305\u88c5/\u90e8\u5206 raw \u548c\u65e7\u8bc1\u636e\u5747\u4fdd\u7559\u3002\u65e0\u5f85\u6301\u6709\u8d44\u6e90\u548c\u7b49\u5f85\u8fdb\u7a0b\uff0c\u91ca\u653e\u89c1 release.json\u3002\u4e0b\u4e00\u6b65\u7531\u6839\u843d\u5b9e\u672c\u6b21\u5177\u4f53\u51ed\u636e/TLS \u76f4\u63a5\u51b3\u5b9a\uff0c\u4e0d\u501f\u7528 A17 \u53ea\u8bfb\u8bb8\u53ef\uff1b\u5176\u4ed6\u4e09\u4f8b HOLD\uff0cQ22 \u4e0d\u5bfc\u822a/\u6837\u9898/\u91cd\u653e\uff0c0 B \u6d88\u606f\u3001\u65e0\u4e66\u7ea7\u9001\u4ea4\uff0c2026-10-22 \u665a\u622a\u6b62\u4fdd\u6301\u3002
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
