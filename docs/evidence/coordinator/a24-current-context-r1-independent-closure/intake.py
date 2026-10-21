"""Static raw intake and independent output-directed runners; no product import."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
AUTHOR = ROOT / 'docs/evidence/A24/revisions/current-context-r1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def new(name, raw):
    with (OUT / name).open('xb') as stream:
        stream.write(raw)


def verify(document, count):
    assert len(document['members']) == len({row['path'] for row in document['members']}) == count
    for row in document['members']:
        path = (ROOT / row['path']).resolve()
        assert ROOT.resolve() in path.parents
        raw = path.read_bytes()
        assert len(raw) == row.get('size', row.get('bytes')) and sha(raw) == row['sha256'], row['path']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest() == row['blob'], row['path']
        assert row['mode'] == '100644' and row['type'] == 'blob'


manifest_raw = Path('D:/1800/docs/evidence/coordinator/a24-current-context-r1-delivery/input-raw-manifest.json').read_bytes()
assert sha(manifest_raw) == '4ad6a9003ed23442b3f449b8d5216d6011a3df94fefcb5ce980d63e1e20675a1'
manifest = json.loads(manifest_raw)
assert manifest['product'] == 'dde5746600df9854c33c5814a8f41ad85b7b4e16'
assert manifest['final'] == '6740d7533ea7b5bf5f322d768e8688826afe5d43'
verify(manifest, 120)
new('root-input-manifest.json', manifest_raw)
task_raw = Path('D:/1800/docs/tasks/A24-current-context-r1-fixed-independent-review.md').read_bytes()
assert sha(task_raw) == '08587130a3cb0aac84c62269cf963bf39e52d3f235fd890c45a16c4fe70e2a0e'
new('fixed-review-task.md', task_raw)
candidate_raw = (AUTHOR / 'candidate-manifest.json').read_bytes()
assert sha(candidate_raw) == 'c68ce354be516552e1aadafe253cd3f9c12785b3107d2454e59f10446ef31b77'
verify(json.loads(candidate_raw), 42)
delivery_raw = (AUTHOR / 'delivery-manifest.json').read_bytes()
assert sha(delivery_raw) == 'fa17d70cf3d56e3232b548a57d806d6bdecdf1b1af46abbcfe76fc7f1f998610'
verify(json.loads(delivery_raw), 108)
changes = {}
for original, target, replacements in (
    ('run.py', 'new-python-runner.py', [
        ('ROOT = Path(__file__).resolve().parents[2]', 'ROOT = Path(__file__).resolve().parents[4]'),
        ("OUT = ROOT / 'docs/evidence/A24/revisions/current-context-r1/runs'", "OUT = Path(__file__).resolve().parent / 'python-runs'"),
        ("Path(__file__).with_name('test_current_context.py')", "ROOT / 'tests/a24_current_context/test_current_context.py'"),
        ('unittest.TextTestRunner(stream=stderr, verbosity=2)', 'unittest.TextTestRunner(stream=stderr, verbosity=2, failfast=True)')]),
    ('verify_js.py', 'new-js-runner.py', [
        ('ROOT = Path(__file__).resolve().parents[2]', 'ROOT = Path(__file__).resolve().parents[4]'),
        ("OUT = ROOT / 'docs/evidence/A24/revisions/current-context-r1/js-runs'", "OUT = Path(__file__).resolve().parent / 'js-runs'"),
        ("Path(__file__).with_name('js_fake_controls.cjs')", "ROOT / 'tests/a24_current_context/js_fake_controls.cjs'")])):
    raw = (ROOT / 'tests/a24_current_context' / original).read_bytes()
    text = raw.decode('utf-8')
    for before, after in replacements:
        assert text.count(before) == 1
        text = text.replace(before, after)
    if original == 'verify_js.py':
        anchor = "rows = json.loads(run.stdout)['results'] if run.returncode == 0 else []"
        # Preserve original interpreter outputs in the new allowed directory, before parsing.
        text = text.replace(anchor,
            "with (OUT / ('run%02d-node-stdout.txt' % number)).open('xb') as stream: stream.write(run.stdout)\n"
            "with (OUT / ('run%02d-node-stderr.txt' % number)).open('xb') as stream: stream.write(run.stderr)\n" + anchor)
    else:
        for guard in ("patch.object(subprocess, 'Popen', forbidden)",
                "patch.object(socket, 'create_connection', forbidden)",
                "patch.object(module.p, 'occupancy', forbidden)", 'sys.addaudithook(audit)'):
            assert guard in text
    new(target, text.encode('utf-8'))
    changes[target] = {'source_sha256': sha(raw), 'new_sha256': sha(text.encode('utf-8')),
        'replacements': [{'before': a, 'after': b} for a, b in replacements],
        'extra_output_only_change': 'Save Node stdout/stderr before result parsing' if original == 'verify_js.py' else None}
new('intake-result.json', (json.dumps({'result': 'PASS_RAW_INTAKE_ONLY',
    'input_members': 120, 'candidate_dependencies': 42, 'delivery_members': 108,
    'candidate_sha256': sha(candidate_raw), 'raw_size_sha256_git_blob_mode_type_verified': True,
    'runners': changes, 'frozen_inputs_modified': 0, 'real_resources': 0}, indent=2) + '\n').encode('utf-8'))
print(json.dumps({'result': 'PASS_RAW_INTAKE_ONLY', 'inputs': 120, 'candidate': 42, 'delivery': 108}))
