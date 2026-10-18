"""Read-only corroboration of the frozen R12 prerequisite review; no product import."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R12-prerequisite'
TARGET = '394fe51f5ed14c5ed312073a20faac0f5cbb9990'
BASE = 'cc5966dc58c62017a27266c40ca0cedc5c68485c'
REPORT = 'docs/tasks/A03-P2-R12-prerequisite-review-report.md'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def git(*args, data=None):
    result = subprocess.run(['git', '-c', 'core.longpaths=true', *args],
                            cwd=ROOT, input=data, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    return result.stdout


expected = {
    REPORT: '33c224427aa86bce6d4966aa8eafd7fae51e5bf2823c09a56745d1fc6cdaff95',
    'docs/evidence/A03/review/P2-R12-prerequisite/sha256-manifest.json': '4db73db5d3f6a5c9e25d35f040dc5185c8ce550f065f0f63b1a7d52438e4e217',
    'docs/evidence/A03/review/P2-R12-prerequisite/process-release.json': 'a206d6d2558c4de268a56dee0dbfed31c0bc6dab11b61311477ff3d7485042a5',
}
for path, digest in expected.items():
    assert sha((ROOT / path).read_bytes()) == digest, path
manifest = read_json(REVIEW / 'sha256-manifest.json')
assert manifest['target'] == TARGET and manifest['base'] == BASE
members = set()
for item in manifest['files']:
    path = item['path']
    assert path not in members
    members.add(path)
    data = (ROOT / path).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], path
actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file()}
actual.add(REPORT)
actual.remove('docs/evidence/A03/review/P2-R12-prerequisite/sha256-manifest.json')
assert members == actual, (members - actual, actual - members)

index = read_json(REVIEW / 'input-index.json')
entries = index['exports']
request = ''.join(e['commit'] + ':' + e['path'] + '\n' for e in entries).encode('utf-8')
response = git('cat-file', '--batch', data=request)
offset = 0
sources = {}
for entry in entries:
    end = response.index(b'\n', offset)
    object_id, kind, size = response[offset:end].split()
    assert kind == b'blob'
    size = int(size)
    blob = response[end + 1:end + 1 + size]
    assert response[end + 1 + size:end + 2 + size] == b'\n'
    offset = end + 2 + size
    assert object_id.decode() == entry['raw_git_sha1']
    assert size == entry['bytes'] and sha(blob) == entry['sha256'], entry['path']
    assert blob == (REVIEW / entry['file']).read_bytes(), entry['file']
    sources[(entry['commit'], entry['path'])] = blob
assert offset == len(response)

release = read_json(REVIEW / 'process-release.json')
assert release['registered_current_children'] == len(release['records']) == 7
for record in release['records']:
    folder = REVIEW / record['record']
    completed = read_json(folder / 'completed.json')
    started = read_json(folder / 'started.json')
    prereg = read_json(folder / 'preregistered.json')
    assert completed['pid'] == record['pid'] == started['pid']
    assert completed['exit_code'] == record['exit_code'] == 0
    assert completed['alive'] is False and record['alive'] is False
    assert completed['timed_out'] is False and record['timed_out'] is False
    assert prereg['argv'] == record['argv'] and prereg['cwd'] == record['cwd']
    for stream in ['stdout', 'stderr']:
        path = next(p for p in [folder / (stream + suffix) for suffix in ['.bin', '.txt', '.log']] if p.exists())
        assert sha(path.read_bytes()) == record[stream + '_sha256'] == completed[stream + '_sha256']
static_prereg = read_json(REVIEW / 'runs/static-review-01/preregistered.json')
assert sha((REVIEW / 'scripts/review_static.py').read_bytes()) == static_prereg['source_sha256']
assert sha((REVIEW / 'source-preflight.json').read_bytes()) == static_prereg['source_preflight_sha256']

storage_path = 'src/annotation/runtime/storage/__init__.py'
native_path = 'src/annotation/runtime/storage/native.py'
schema_path = 'src/annotation/contracts/a03_native/data/schemas/exchange.json'
storage = sources[(BASE, storage_path)].decode('utf-8')
native = sources[(BASE, native_path)].decode('utf-8')
schema = json.loads(sources[(BASE, schema_path)])


def class_methods(text, cls):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == cls)
    return node, {n.name: n for n in node.body if isinstance(n, ast.FunctionDef)}


_, methods = class_methods(storage, 'RuntimeStore')
native_cls, native_methods = class_methods(native, 'NativeRuntimeStore')
assert any(isinstance(b, ast.Name) and b.id == 'RuntimeStore' for b in native_cls.bases)
for method in ['commit_action_result', 'project_plan', '_project_plan_locked', '_new_artifact']:
    assert method not in native_methods
project = methods['_project_plan_locked']
post_call = next(n for n in ast.walk(project) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == '_new_artifact'
                 and len(n.args) > 2 and isinstance(n.args[1], ast.Constant)
                 and n.args[1].value == 'CheckReport')
payload = post_call.args[2]
fields = {k.value for k in payload.keys if isinstance(k, ast.Constant)}
post_schema = schema['$defs']['AmendedCheckReport']['properties']['payload']['oneOf'][2]
assert post_schema['additionalProperties'] is False
missing = sorted(set(post_schema['required']) - fields)
extra = sorted(fields - set(post_schema['properties']))
assert missing == ['action_bindings', 'content_check_status', 'frame_structure', 'report_observation', 'report_snapshot_ref', 'submission_status']
assert extra == ['checks', 'coverage', 'reason', 'snapshot']
calls = lambda node: {n.func.attr for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
assert 'project_plan' in calls(methods['commit_action_result'])
assert '_project_plan_locked' in calls(methods['project_plan'])
assert '_validate' in calls(native_methods['_append'])
assert 'context' in calls(native_methods['bridge_for'])

report = (ROOT / REPORT).read_text(encoding='utf-8')
links = re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', report)
assert all((ROOT / REPORT).parent.joinpath(link).exists() for link in links)
result = {
    'at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
    'status': 'STATIC_BLOCKER_CONFIRMED_NOT_FUNCTIONAL_ACCEPTANCE',
    'target': TARGET, 'base': BASE,
    'review_report_sha256': expected[REPORT],
    'review_manifest_sha256': expected['docs/evidence/A03/review/P2-R12-prerequisite/sha256-manifest.json'],
    'review_release_sha256': expected['docs/evidence/A03/review/P2-R12-prerequisite/process-release.json'],
    'manifest_members_verified': len(members), 'raw_git_exports_verified': len(entries),
    'registered_children_exited': 7, 'report_links_verified': len(links),
    'own_AST_method_ranges': {k: [methods[k].lineno, methods[k].end_lineno] for k in ['commit_action_result', 'project_plan', '_project_plan_locked', '_new_artifact']},
    'native_inherits_projection_and_validates_append': True,
    'missing_native_fields': missing, 'forbidden_legacy_fields': extra,
    'coordinator_product_calls': 0, 'coordinator_SQL_connections': 0,
    'actual_runtime_error_and_transaction_effects': 'NOT_OBSERVED',
    'U1_U5_executed': False, 'whole_A03': 'REWORK',
    'product_integrated': False, 'I01_released': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
}
destination = Path(__file__).with_name('r12-static-corroboration.json')
destination.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps(result, ensure_ascii=False))
