"""A-side offline receipt audit of one immutable B handoff; no B runtime imports."""
import datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

from PIL import Image
import PIL

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
STAGE = ROOT / '.local/stages/coordinator/b-handoff-0e5434f'
ZIP = STAGE / 'B-46007447-Q16-offline-HOLD-2026-10-17.zip'
COMMIT = '0e5434f0ecf57152ec03f66bd7d0cf48b7c0700f'
ZIP_SHA = 'b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')

def write(name, value):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

def walk(value, path=''):
    if isinstance(value, dict):
        yield path, value
        for k, v in value.items():
            yield from walk(v, path + '/' + k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, path + '/' + str(i))

def ref(value):
    return {k: value[k] for k in ('artifact_id', 'revision', 'content_hash')}

assert sha(ZIP.read_bytes()) == ZIP_SHA
verifier = STAGE / 'verify_b_handoff.py'
assert sha(verifier.read_bytes()) == 'a8ffa647321da8ed06032b8b5d71e8a86e40af54827e9f370b9b02e4bbdc1778'
# This exact script was inspected: standard-library ZIP/JSON/hash checks only.
command = [sys.executable, '-X', 'utf8', '-B', str(verifier), str(ZIP), '--self-test']
with (OUT / 'b-verifier.stdout.txt').open('xb') as stdout, (OUT / 'b-verifier.stderr.txt').open('xb') as stderr:
    proc = subprocess.Popen(command, cwd=STAGE, stdout=stdout, stderr=stderr)
    write('b-verifier.start.json', {'argv': command, 'cwd': str(STAGE), 'pid': proc.pid,
          'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'timeout_seconds': 60, 'script_sha256': sha(verifier.read_bytes())})
    timed_out = False
    try:
        code = proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        code = proc.wait(timeout=5)
write('b-verifier.exit.json', {'pid': proc.pid, 'exit_code': code, 'timed_out': timed_out,
      'alive': proc.poll() is None, 'completed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()})
assert code == 0 and not timed_out

with zipfile.ZipFile(ZIP) as archive:
    infos = archive.infolist()
    names = [info.filename for info in infos]
    assert len(names) == len(set(names))
    for info in infos:
        p = PurePosixPath(info.filename)
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in info.filename
        assert ':' not in info.filename and not info.is_dir()
        assert (info.external_attr >> 16) & 0o170000 != 0o120000
    data = {name: archive.read(name) for name in names}
manifest = json.loads(data['manifest.json'])
rows = manifest['files']
assert len({row['path'] for row in rows}) == len(rows)
assert {row['path'] for row in rows} == set(names) - {'manifest.json'}
for row in rows:
    assert len(data[row['path']]) == row['bytes'] and sha(data[row['path']]) == row['sha256']
assert data['verify_b_handoff.py'] == verifier.read_bytes()
documents = {name: json.loads(raw) for name, raw in data.items() if name.endswith('.json')}
report = documents['artifacts/pipeline-report.json']
evidence = documents['artifacts/evidence.json']
graph = documents['artifacts/graph.json']
check = documents['artifacts/check.json']
assert manifest['book_id'] == '46007447'
assert report['run_id'] == manifest['run_id']
assert ref(report) == manifest['report_ref']
assert report['payload']['final_outputs'] == manifest['final_outputs']
assert report['payload']['pipeline_state'] == 'READY'
assert report['payload']['decision'] == graph['payload']['decision'] == check['payload']['decision'] == 'HOLD'
assert check['payload']['business_acceptance'] is False and check['payload']['transcription_verified'] is False
assert check['payload']['graph_ref'] == ref(graph) and check['payload']['evidence_ref'] == ref(evidence)
for label, value in [('evidence', evidence), ('graph', graph), ('quality', check)]:
    assert value['book_id'] == '46007447'
    assert ref(value) == manifest['final_outputs'][label + '_ref']
    assert sha(canonical(value['payload'])) == value['content_hash']
stage_details = []
for stage in report['payload']['stages']:
    desc = stage['output']
    assert sha(data[desc['path']]) == desc['sha256']
    wrapper = documents[desc['path']]
    result = wrapper['payload']['result']
    assert ref(wrapper) == desc['artifact_ref'] and ref(result) == stage['result_ref']
    assert sha(canonical(wrapper['payload'])) == wrapper['content_hash']
    assert sha(canonical(result['payload'])) == result['content_hash']
    assert stage['current_run_receipt']['run_id'] == manifest['run_id']
    stage_details.append({'stage_id': stage['stage_id'], 'wrapper_schema': wrapper['schema_version'],
                          'result_schema': result['schema_version'], 'result_ref': ref(result)})

images = []
for name, raw in data.items():
    if name.lower().endswith(('.png', '.jpg', '.jpeg', '.pgm')):
        with Image.open(BytesIO(raw)) as image:
            image.load()
            images.append({'path': name, 'size': list(image.size), 'format': image.format, 'sha256': sha(raw)})
image_index = {image['path']: image for image in images}
for asset in report['payload']['source_manifest']['assets']:
    image = image_index['source/' + asset['path']]
    assert image['size'] == [asset['width'], asset['height']] and image['sha256'] == asset['sha256']
adjacent = manifest['adjacent_source']
assert image_index[adjacent['path']]['sha256'] == adjacent['sha256']
assert image_index[adjacent['path']]['sha256'] != image_index['source/assets/46007447_viewer_173.jpg']['sha256']

receipt_hashes = set()
for _, value in walk(report['payload']['input_receipts']):
    if 'file_sha256' in value:
        receipt_hashes.add(value['file_sha256'])
receipt_rows = manifest['receipt_files']
assert {row['sha256'] for row in receipt_rows} == receipt_hashes
for row in receipt_rows:
    assert sha(data[row['path']]) == row['sha256']
inline = report['payload']['input_receipts']['inline']
inline_package = documents['inputs/inline-package.json']
assert sha(canonical(inline_package)) == inline['package']['reference']['content_hash']
inner_images = 0
with zipfile.ZipFile(BytesIO(data['inputs/inline-observed.zip'])) as inner:
    assert len(inner.namelist()) == len(set(inner.namelist()))
    for name, receipt in inline['members'].items():
        raw = inner.read(name)
        assert len(raw) == receipt['bytes'] and sha(raw) == receipt['sha256']
        if name.lower().endswith(('.png', '.jpg', '.jpeg', '.pgm')):
            with Image.open(BytesIO(raw)) as image:
                image.load()
            inner_images += 1

# Inventory formal input_refs only. This is a location/closure diagnostic, not a new trial schema.
index = {}
formal = []
payload_objects = set()
for name, document in documents.items():
    for pointer, value in walk(document):
        if 'artifact_id' not in value:
            continue
        location = name + '#' + pointer
        if 'payload' in value and 'content_hash' in value and 'schema_version' in value:
            assert sha(canonical(value['payload'])) == value['content_hash'], location
            key = (value['artifact_id'], value.get('revision'), value['content_hash'])
            index.setdefault(key, []).append(location)
            payload_objects.add(key)
            for i, dependency in enumerate(value.get('input_refs', [])):
                formal.append((location + '/input_refs/' + str(i), dependency))
        elif 'content_hash' not in value and len(value) > 2:
            key = (value['artifact_id'], value.get('revision'), sha(canonical(value)))
            index.setdefault(key, []).append(location)
unresolved = {}
for location, dependency in formal:
    aid, digest, revision = dependency.get('artifact_id'), dependency.get('content_hash'), dependency.get('revision')
    matches = [key for key in index if key[0] == aid and key[2] == digest and (revision is None or key[1] == revision)]
    if not matches:
        key = json.dumps(dependency, sort_keys=True)
        record = unresolved.setdefault(key, {'reference': dependency, 'occurrences': 0, 'first_locations': []})
        record['occurrences'] += 1
        if len(record['first_locations']) < 3:
            record['first_locations'].append(location)

result = {
    'scope': 'A-side offline package receipt and interoperability preflight; not B algorithm acceptance or A public-contract compatibility.',
    'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'B_commit': COMMIT,
    'B_code_baseline': 'c3cc2df7a0be24c125c83681c0499c0d328d78f6',
    'A_coordinator_start_commit': '0360ec9902d63e0d36d7afcd93ae17b2f3252ab9',
    'archive_sha256': ZIP_SHA, 'archive_bytes': ZIP.stat().st_size,
    'manifest_sha256': sha(data['manifest.json']), 'manifest_entries': len(rows), 'zip_members': len(names),
    'uncompressed_bytes': sum(len(raw) for raw in data.values()), 'all_manifest_bytes_verified': True,
    'run_id': manifest['run_id'], 'package_schema': manifest['schema_version'],
    'package_scope': manifest['scope_id'], 'final_graph_scope': graph['scope_id'],
    'final_schemas': {n: v['schema_version'] for n, v in [('evidence', evidence), ('graph', graph), ('check', check)]},
    'stage_count': len(stage_details), 'stage_details': stage_details,
    'question_candidates': len(graph['payload']['questions']), 'answer_candidates': len(graph['payload']['answers']),
    'check_issues': len(check['payload']['issues']), 'decision': 'HOLD',
    'historical_receipt_hashes_verified': len(receipt_hashes), 'inline_members_verified': len(inline['members']),
    'outer_images_fully_decoded': len(images), 'inner_consumed_images_fully_decoded': inner_images,
    'original_dimensions_verified': len(report['payload']['source_manifest']['assets']),
    'viewer_173_resource_173_kept_distinct': True, 'images': images,
    'payload_artifact_identities_hash_verified': len(payload_objects),
    'formal_input_ref_occurrences_inventoried': len(formal),
    'unresolved_formal_reference_identities': list(unresolved.values()),
    'B_verifier_self_test': json.loads((OUT / 'b-verifier.stdout.txt').read_bytes()),
    'B_self_test_boundary': 'Three helper-level checks; not three full A-consumer archive tests.',
    'requirements_docx_in_package': any(name.lower().endswith('.docx') for name in names),
    'cases_or_expected_directories_present': any(name.startswith(('cases/', 'expected/')) for name in names),
    'A_public_consumer_run': False, 'shared_mapping_confirmed': False,
    'crop_transform_semantics_verified': False, 'content_accuracy_verified': False,
    'platform_actions': 0, 'model_calls': 0, 'branch_merged': False, 'remote_push': False,
    'python': sys.version.split()[0], 'Pillow': PIL.__version__
}
write('package-audit.json', result)
print(json.dumps({k: result[k] for k in ('archive_sha256', 'manifest_entries', 'zip_members', 'stage_count',
    'question_candidates', 'answer_candidates', 'check_issues', 'decision', 'historical_receipt_hashes_verified',
    'inline_members_verified', 'outer_images_fully_decoded', 'inner_consumed_images_fully_decoded',
    'payload_artifact_identities_hash_verified')}, ensure_ascii=False))
print(json.dumps({'unresolved_formal_reference_identities': result['unresolved_formal_reference_identities']}, ensure_ascii=False))
