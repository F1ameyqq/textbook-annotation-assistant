"""Independent metadata intake and new runner creation; no product imports."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
AUTH = ROOT / 'docs/evidence/A24/current-contract'
ROOT_MANIFEST = Path('D:/1800/docs/evidence/coordinator/a24-fixed-delivery/input-raw-manifest.json')
DISPATCH = Path('D:/1800/docs/tasks/A24-fixed-current-contract-independent-review.md')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(name, raw):
    with (OUT / name).open('xb') as stream:
        stream.write(raw)


def json_new(name, value):
    write_new(name, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


raw = ROOT_MANIFEST.read_bytes()
assert digest(raw) == 'e13ed9bf40a0fb9a9146ca61eb4657f0d0d501ac728465db99ff6fd4446950cd'
write_new('root-input-manifest.json', raw)
task_raw = DISPATCH.read_bytes()
assert digest(task_raw) == '94d94407e80796593fdd61107875e1ff3dfefd8486ba4c2fc893dfc7f04bd450'
write_new('fixed-review-task.md', task_raw)
manifest = json.loads(raw)
assert manifest['final'] == '3d53a0b670c04cf84387cd77d69b0a9571741328'
assert manifest['product'] == 'eb75fad5ca56daa117929dd1377d2157f2340388'


def verify_members(document, expected_count):
    members = document['members']
    assert len(members) == expected_count
    assert len({m['path'] for m in members}) == expected_count
    for member in members:
        target = (ROOT / member['path']).resolve()
        assert ROOT.resolve() in target.parents
        raw_member = target.read_bytes()
        assert len(raw_member) == member['size'], member['path']
        assert digest(raw_member) == member['sha256'], member['path']
        blob = hashlib.sha1(b'blob ' + str(len(raw_member)).encode('ascii') + b'\0' + raw_member).hexdigest()
        assert blob == member['blob'], member['path']
        assert member['type'] == 'blob' and member['mode'] == '100644'
    return expected_count


input_count = verify_members(manifest, 111)
candidate_raw = (AUTH / 'candidate-manifest.json').read_bytes()
assert digest(candidate_raw) == 'd10e30b4567ba5c4a81b8aa53396e35619e05f191e457a40c371866499161753'
candidate = json.loads(candidate_raw)
candidate_count = verify_members(candidate, 37)
delivery = json.loads((AUTH / 'delivery-manifest.json').read_bytes())
delivery_count = verify_members(delivery, 98)

runner_path = ROOT / 'tests/a24_current_contract/run.py'
runner_original = runner_path.read_text(encoding='utf-8')
changes = [
    ('ROOT = Path(__file__).resolve().parents[2]', 'ROOT = Path(__file__).resolve().parents[4]'),
    ("OUT = ROOT / 'docs/evidence/A24/current-contract/runs'", "OUT = Path(__file__).resolve().parent / 'suite-runs'"),
    ("Path(__file__).with_name('test_current_contract.py')", "ROOT / 'tests/a24_current_contract/test_current_contract.py'"),
    ('unittest.TextTestRunner(stream=stderr, verbosity=2)', 'unittest.TextTestRunner(stream=stderr, verbosity=2, failfast=True)'),
]
runner = runner_original
for before, after in changes:
    assert runner.count(before) == 1
    runner = runner.replace(before, after)
# Retain every author offline socket/subprocess/private-path/native/occupancy guard.
for required in ('sys.addaudithook(audit)', "patch.object(socket, 'create_connection', forbidden)",
        "patch.object(subprocess, 'Popen', forbidden)", "patch.object(module.p, 'load_native', forbidden)",
        "patch.object(module.p, 'occupancy', forbidden)"):
    assert required in runner
write_new('new-suite-runner.py', runner.encode('utf-8'))
json_new('intake-result.json', {
    'result': 'PASS_RAW_INTAKE_ONLY', 'input_members': input_count,
    'candidate_dependencies': candidate_count, 'delivery_members': delivery_count,
    'all_size_sha256_git_blob_mode_type_checks': True,
    'candidate_sha256': digest(candidate_raw), 'product': manifest['product'], 'final': manifest['final'],
    'runner_source_sha256': digest(runner_path.read_bytes()),
    'new_runner_sha256': digest(runner.encode('utf-8')),
    'runner_changes': [{'before': before, 'after': after} for before, after in changes],
    'offline_resource_guards_retained': True, 'product_runs': 0, 'product_imports': 0,
    'real_resources': 0,
    'intake_locator_failure': {
        'attempted': 'isolation/docs/evidence/coordinator/a24-fixed-delivery/input-raw-manifest.json',
        'result': 'PATH_NOT_PRESENT; no product action',
        'resolved': 'root manifest path explicitly named by dispatch; exact SHA verified before use'
    }
})
print(json.dumps({'input_members': input_count, 'candidate_dependencies': candidate_count,
    'delivery_members': delivery_count, 'new_runner_created': True}))
