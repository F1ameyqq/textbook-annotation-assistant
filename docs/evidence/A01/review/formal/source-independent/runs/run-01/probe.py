"""Offline independent A01 source adversarial probes; no implementation mutation.

Run with --snapshot <verified export> --stage <new temporary directory>.
All rewrapped cases use public seal_artifact and update only resource hashes;
they test cross-record consistency, not authenticity against an attacker who
can replace an entire unsigned exchange and its trusted external reference.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
args_parser = argparse.ArgumentParser()
args_parser.add_argument('--snapshot', required=True, type=Path)
args_parser.add_argument('--stage', required=True, type=Path)
args = args_parser.parse_args()
SNAPSHOT = args.snapshot.resolve()
STAGE = args.stage.resolve()
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SNAPSHOT / 'src'))
os.environ['PYTHONPATH'] = str(SNAPSHOT / 'src')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import PIL
import pydantic
import annotation.source.static.importer as implementation
import annotation.contracts as contracts
from annotation.contracts import artifact_ref, policy_ref, seal_artifact, load_bundle
from annotation.source.static import import_book, load_static_bundle

assert Path(implementation.__file__).resolve().is_relative_to(SNAPSHOT / 'src')
assert Path(contracts.__file__).resolve().is_relative_to(SNAPSHOT / 'src')
STAGE.mkdir(parents=True, exist_ok=False)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def hashes(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}

def reseal(path, data):
    data['artifacts'] = [seal_artifact(a) for a in data['artifacts']]
    write(path, data)

def update_resource(data, relative, digest):
    for record in data['evidence']:
        if record['resource']['path'] == relative:
            record['resource']['sha256'] = digest
    for record in data['artifacts'][0]['payload']['history']:
        if record['resource']['path'] == relative:
            record['resource']['sha256'] = digest

def sidecar(path, name, mutate):
    data = read(path)
    value = read(path.parent / name)
    mutate(value)
    write(path.parent / name, value)
    update_resource(data, name, sha((path.parent / name).read_bytes()))
    reseal(path, data)

environment = {
    'target_commit': 'a8d5e96d128e10d341de935d4856682e50df79d9',
    'command_argv': sys.argv,
    'python_executable': sys.executable, 'python_version': sys.version,
    'platform': platform.platform(), 'pillow': PIL.__version__, 'pydantic': pydantic.__version__,
    'sys_path': sys.path, 'PYTHONPATH': os.environ['PYTHONPATH'],
    'module_files': {'static_importer': implementation.__file__, 'contracts': contracts.__file__},
    'implementation_sha256': sha(Path(implementation.__file__).read_bytes()),
    'script_sha256': sha(Path(__file__).read_bytes()),
    'offline': True, 'network_calls': 0, 'browser_calls': 0, 'model_calls': 0,
}
write(EVIDENCE / 'environment.json', environment)
snapshot_before = hashes(SNAPSHOT)
BASE = {}
for book in ('46006966', '46007447'):
    BASE[book] = import_book(SNAPSHOT, book, STAGE / 'baseline' / book, created_at='2026-10-16T13:00:00Z')
baseline_before = {book: hashes(p.parent) for book, p in BASE.items()}
INPUT_BASE = STAGE / 'input baseline'
for path in BASE.values():
    for item in read(path.parent / 'input-integrity.json')['inputs']:
        relative = item['archive_path']
        target = INPUT_BASE / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SNAPSHOT / relative, target)

RESULTS = []
def case(name, expected, description, action):
    record = {'id': name, 'expected': expected, 'description': description}
    try:
        detail = action(name)
        record.update(actual='ACCEPT', detail=detail)
    except Exception as error:
        record.update(actual='REJECT', error_type=type(error).__name__, error=str(error),
                      code=getattr(error, 'code', None), location=getattr(error, 'location', None),
                      issues=getattr(error, 'issues', None), traceback=traceback.format_exc())
    record['matches_expectation'] = record['actual'] == expected
    RESULTS.append(record)
    write(EVIDENCE / 'cases' / name / 'result.json', record)
    print(name + ': ' + record['actual'] + (' expected' if record['matches_expectation'] else ' UNEXPECTED'), flush=True)

def copied_bundle(name, book='46006966'):
    target = STAGE / 'cases' / name / 'bundle'
    shutil.copytree(BASE[book].parent, target)
    return target / 'exchange.json'

def copied_inputs(name):
    target = STAGE / 'cases' / name / 'inputs'
    shutil.copytree(INPUT_BASE, target)
    return target

def keep_input(name, path, relative):
    target = EVIDENCE / 'cases' / name / 'changed-inputs' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)

def inspect_bundle(name, path, book='46006966'):
    # Keep changed JSON/text and hashes, not a second copy of all original images.
    old = baseline_before[book]
    changed = {k: v for k, v in hashes(path.parent).items() if old.get(k) != v}
    for relative in changed:
        if (path.parent / relative).suffix in ('.json', '.txt'):
            keep_input(name, path.parent / relative, relative)
    write(EVIDENCE / 'cases' / name / 'input.json', {'exchange': str(path), 'book_id': book, 'changed_files': changed})
    public = load_bundle(path, verify_assets=True)
    accepted = load_static_bundle(path, expected_book_id=book)
    return {'path': str(path), 'public_load': 'ACCEPT', 'a01_load': 'ACCEPT',
            'content_hash': accepted.artifacts[0].content_hash,
            'same_public_result': accepted == public}

OLD_MANIFEST = '技术证据/只读样本-46006966/source-images-complete.json'
OLD_IMAGE = '技术证据/只读样本-46006966/viewer-page-0008.jpg'

def import_mutation(name, mutate, book='46006966'):
    root = copied_inputs(name)
    description = mutate(root)
    target = STAGE / 'cases' / name / 'new-output'
    before = hashes(BASE[book].parent)
    try:
        result = import_book(root, book, target, created_at='2026-10-16T13:00:00Z')
        return {'exchange': str(result), 'mutation': description}
    finally:
        detail = {'target_exists_after': target.exists(), 'old_product_unchanged': before == hashes(BASE[book].parent), 'mutation': description}
        write(EVIDENCE / 'cases' / name / 'preservation.json', detail)

def alter_manifest(root, name, field, value):
    data = read(root / OLD_MANIFEST)
    original = data[0][field]
    data[0][field] = value
    write(root / OLD_MANIFEST, data)
    keep_input(name, root / OLD_MANIFEST, OLD_MANIFEST)
    return {'field': field, 'before': original, 'after': value}

case('S00-two-pristine-books', 'ACCEPT', 'Both assigned books load from frozen implementation.',
     lambda name: {b: {'assets': len(load_static_bundle(p, expected_book_id=b).artifacts[0].payload.assets), 'exchange_sha256': sha(p.read_bytes())} for b, p in BASE.items()})
for field, value, label in [('sha256', '0' * 64, 'wrong-hash'), ('width', 1, 'wrong-width'), ('height', 1, 'wrong-height')]:
    name = 'S01-import-' + label
    case(name, 'REJECT', 'Manifest declaration disagrees with original JPEG.',
         lambda n, f=field, v=value: import_mutation(n, lambda root: alter_manifest(root, n, f, v)))

def missing(root):
    (root / OLD_IMAGE).unlink()
    return {'removed': OLD_IMAGE}
case('S02-import-missing-image', 'REJECT', 'Missing selected image must fail before new output creation.', lambda n: import_mutation(n, missing))

def corrupt(root):
    image = root / OLD_IMAGE
    original = image.read_bytes()
    sos = original.index(b'\xff\xda')
    broken = original[:sos + 200]
    image.write_bytes(broken)
    rows = read(root / OLD_MANIFEST)
    rows[0]['sha256'] = sha(broken)
    write(root / OLD_MANIFEST, rows)
    from annotation.contracts.validation import image_size
    header_size = image_size(image, 'image/jpeg')
    keep_input('S03-import-corrupt-pixels-rehashed', root / OLD_MANIFEST, OLD_MANIFEST)
    keep_input('S03-import-corrupt-pixels-rehashed', image, 'corrupt.jpg')
    return {'original_bytes': len(original), 'new_bytes': len(broken), 'header_dimensions_still_valid': header_size,
            'recomputed_sha256': sha(broken), 'pixel_stream_truncated_after_SOS': True}
case('S03-import-corrupt-pixels-rehashed', 'REJECT', 'JPEG size header still valid, entropy data truncated and digest recomputed.', lambda n: import_mutation(n, corrupt))

case('S04-import-source-index-conflict', 'REJECT', 'Assigned viewer/source pairing contradicted.',
     lambda n: import_mutation(n, lambda root: alter_manifest(root, n, 'sourceImageIndex', 8)))

def wrong_book(root):
    relative = 'docs/evidence/A05/review/independent-source-page14.json'
    value = read(root / relative)
    value['data']['file_id'] = '46006966'
    write(root / relative, value)
    keep_input('S05-import-wrong-book', root / relative, relative)
    return {'file': relative, 'file_id': '46006966', 'expected_book_id': '46007447'}
case('S05-import-wrong-book', 'REJECT', 'New-book page response identifies old book.', lambda n: import_mutation(n, wrong_book, '46007447'))
case('S06-consume-wrong-book', 'REJECT', 'Explicit requested book cannot be substituted.', lambda n: load_static_bundle(BASE['46006966'], expected_book_id='46007447'))

def repeat(name):
    before = hashes(BASE['46006966'].parent)
    try:
        return import_book(SNAPSHOT, '46006966', BASE['46006966'].parent)
    finally:
        write(EVIDENCE / 'cases' / name / 'preservation.json', {'old_product_unchanged': before == hashes(BASE['46006966'].parent)})
case('S07-repeat-does-not-overwrite', 'REJECT', 'Existing destination must be rejected without changing any old byte.', repeat)

def simple_bundle_change(name, change, book='46006966'):
    path = copied_bundle(name, book)
    data = read(path)
    change(data, path)
    reseal(path, data)
    return inspect_bundle(name, path, book)

for relative, label in [('../escape.jpg', 'parent'), ('C:/Users/escape.jpg', 'absolute'), ('assets/../../escape.jpg', 'nested-parent')]:
    case('S08-path-' + label, 'REJECT', 'Portable resource must not escape package.',
         lambda n, rel=relative: simple_bundle_change(n, lambda data, path: data['artifacts'][0]['payload']['assets'][0].update(path=rel)))

def loaded_missing(name):
    path = copied_bundle(name)
    relative = read(path)['artifacts'][0]['payload']['assets'][0]['path']
    (path.parent / relative).unlink()
    return inspect_bundle(name, path)
case('S09-loaded-image-missing', 'REJECT', 'A required acquired resource removed after import.', loaded_missing)

def sidecar_change(name, file, mutation, book='46006966'):
    path = copied_bundle(name, book)
    sidecar(path, file, mutation)
    return inspect_bundle(name, path, book)

case('S10-rehashed-known-viewer-conflict', 'REJECT', 'Provenance viewer conflicts with assigned archive mapping even after rehash.',
     lambda n: sidecar_change(n, 'provenance.json', lambda value: value['mappings'][0].update(viewer_page=999)))
case('S11-rehashed-coverage-true', 'REJECT', 'A01 sidecar cannot claim coverage eligibility.',
     lambda n: sidecar_change(n, 'limitations.json', lambda value: value.update(coverage_eligible=True)))

case('S12-rehashed-empty-origins', 'REJECT', 'All original source relations removed while mappings/assets retained.',
     lambda n: sidecar_change(n, 'provenance.json', lambda value: value.update(origins=[])))
case('S13-rehashed-origin-manifest-digest', 'REJECT', 'Origin manifest digest contradicts retained original_manifests digest.',
     lambda n: sidecar_change(n, 'provenance.json', lambda value: value['origins'][0].update(manifest_sha256='0' * 64)))

def fake_printed(name):
    path = copied_bundle(name)
    p = read(path.parent / 'provenance.json')
    asset = p['mappings'][0]['asset_id']
    p['mappings'][0]['printed_page'] = 999
    write(path.parent / 'provenance.json', p)
    data = read(path)
    update_resource(data, 'provenance.json', sha((path.parent / 'provenance.json').read_bytes()))
    for mapping in data['artifacts'][0]['payload']['external_page_mappings']:
        if mapping['asset_id'] == asset:
            value = json.loads(mapping['external_page'])
            value['printed_page'] = 999
            mapping['external_page'] = json.dumps(value, sort_keys=True)
    reseal(path, data)
    return inspect_bundle(name, path)
case('S14-rehashed-unfounded-printed-page', 'REJECT', 'Archive has no printed-page evidence; claim 999 added to sidecar and public mapping only.', fake_printed)
case('S15-rehashed-erased-missing-sources', 'REJECT', 'Known five unavailable sources erased from limitations without changing historical declaration.',
     lambda n: sidecar_change(n, 'limitations.json', lambda value: value.update(missing_sources=[])))
case('S16-rehashed-false-integrity', 'REJECT', 'Required input-integrity states false and before/after digests disagree.',
     lambda n: sidecar_change(n, 'input-integrity.json', lambda value: (value.update(unchanged=False), value['inputs'][0].update(after_sha256='0' * 64))))

def changed_history(name):
    path = copied_bundle(name)
    data = read(path)
    history = next(h for h in data['artifacts'][0]['payload']['history'] if 'manual-annotations' in h['resource']['path'])
    relative = history['resource']['path']
    value = read(path.parent / relative)
    value['bookId'] = '46007447'
    write(path.parent / relative, value)
    update_resource(data, relative, sha((path.parent / relative).read_bytes()))
    reseal(path, data)
    # The input-integrity old original digest remains unchanged: internal mismatch.
    return inspect_bundle(name, path)
case('S17-rehashed-history-book-and-bytes-conflict', 'REJECT', 'Archived history now identifies another book and no longer matches unchanged original input-integrity.', changed_history)

case('S18-resealed-history-promoted-reviewed', 'REJECT', 'A01 requires historical references always UNVERIFIED; no independent business approval added.',
     lambda n: simple_bundle_change(n, lambda data, path: [h.update(quality='REVIEWED') for h in data['artifacts'][0]['payload']['history']]))
case('S19-rehashed-scope-status-complete', 'REJECT', 'Typed-like sidecar status changed to INDEPENDENT_COMPLETE while independent denominator remains UNKNOWN.',
     lambda n: sidecar_change(n, 'limitations.json', lambda value: value.update(scope_manifest_status='INDEPENDENT_COMPLETE')))
case('S20-rehashed-wrong-reference-identities', 'REJECT', 'Reference list no longer matches scope_manifest IDs but count stays unchanged.',
     lambda n: sidecar_change(n, 'provenance.json', lambda value: value['reference_records'][0].update(reference_id='reference-unrelated')))

def symlink_case(name):
    path = copied_bundle(name)
    relative = read(path)['artifacts'][0]['payload']['assets'][0]['path']
    target = path.parent / relative
    external = STAGE / 'cases' / name / 'external sentinel.jpg'
    shutil.copy2(target, external)
    target.unlink()
    try:
        target.symlink_to(external)
    except OSError as error:
        write(EVIDENCE / 'cases' / name / 'skip.json', {'status': 'SKIP', 'error': str(error), 'winerror': getattr(error, 'winerror', None), 'reason': 'No elevation or settings change allowed.'})
        return {'status': 'SKIP', 'winerror': getattr(error, 'winerror', None)}
    return inspect_bundle(name, path)
case('S21-file-symlink-escape', 'REJECT', 'Attempt actual Windows file symlink to temporary external sentinel only.', symlink_case)
if RESULTS[-1].get('detail', {}).get('status') == 'SKIP':
    RESULTS[-1].update(actual='SKIP', matches_expectation=None)
    write(EVIDENCE / 'cases' / RESULTS[-1]['id'] / 'result.json', RESULTS[-1])

def junction_case(name):
    path = copied_bundle(name)
    data = read(path)
    asset = data['artifacts'][0]['payload']['assets'][0]
    external = STAGE / 'cases' / name / 'external sentinel directory'
    external.mkdir()
    shutil.copy2(path.parent / asset['path'], external / 'image.jpg')
    junction = path.parent / 'escape-junction'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(external)], capture_output=True, text=True, check=False)
    write(EVIDENCE / 'cases' / name / 'junction-command.json', {'argv': ['cmd', '/c', 'mklink', '/J', str(junction), str(external)], 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'resolved_target': str(junction.resolve())})
    if result.returncode:
        raise RuntimeError('Unable to create isolated test junction')
    asset['path'] = 'escape-junction/image.jpg'
    reseal(path, data)
    # Avoid recursive tree enumeration traversing junction; inspect direct load.
    keep_input(name, path, 'exchange.json')
    return load_static_bundle(path, expected_book_id='46006966')
case('S22-directory-junction-escape', 'REJECT', 'Directory junction leaves bundle for isolated temporary sentinel.', junction_case)

def s01_machine_gap(name):
    path = copied_bundle(name, '46007447')
    data = read(path)
    source = data['artifacts'][0]
    synthetic_id = 'independent-s01-synthetic-proof'
    relative = 'synthetic-proof.txt'
    (path.parent / relative).write_text('SYNTHETIC: fabricated checks for offline machine-gate demonstration only.\n', encoding='utf-8')
    data['evidence'].append({'evidence_id': synthetic_id, 'resource': {'path': relative, 'sha256': sha((path.parent / relative).read_bytes()), 'media_type': 'text/plain'}, 'mode': 'SYNTHETIC', 'description': 'Synthetic independent review counterexample, not recognition or platform evidence.'})
    def envelope(identity, kind, inputs, payload):
        return seal_artifact({'schema_version': source['schema_version'], 'artifact_id': identity, 'revision': 1,
                             'kind': kind, 'run_id': 'independent-s01-gate-probe', 'book_id': source['book_id'],
                             'scope_id': source['scope_id'], 'input_refs': inputs,
                             'producer': {'module': 'independent.review', 'implementation_version': 'synthetic-1',
                                          'config_version': 'synthetic-1', 'policy_versions': [], 'model_version': None,
                                          'prompt_version': None, 'evidence_mode': 'SYNTHETIC'},
                             'created_at': '2026-10-16T13:00:00Z', 'payload': payload})
    source_ref = artifact_ref(source)
    regions, clues, fragments = [], [], []
    for i, asset in enumerate(source['payload']['assets']):
        binding = {k: asset[k] for k in ('asset_id', 'width', 'height', 'sha256')}
        region_id, clue_id, fragment_id = 's01-region-' + str(i), 's01-clue-' + str(i), 's01-fragment-' + str(i)
        box = {'image': binding, 'bbox': [0.0, 0.0, 1.0, 1.0]}
        regions.append({'region_id': region_id, 'box': box,
                        'crop_transform': {'scale_x': 1.0, 'scale_y': 1.0, 'offset_x': 0.0, 'offset_y': 0.0,
                                           'rotation_degrees': 0.0, 'padding': [0.0] * 4,
                                           'processed_width': asset['width'], 'processed_height': asset['height'], 'invertible': True},
                        'content_type': 'text', 'text': 'SYNTHETIC', 'source': 'SYNTHETIC',
                        'evidence_refs': [synthetic_id], 'printed_number_candidates': [], 'certainty': 'UNCERTAIN'})
        clues.append({'clue_id': clue_id, 'box': box, 'source': 'SYNTHETIC', 'disposition': 'ASSIGNED', 'region_ids': [region_id],
                      'reason': 'Synthetic gate probe only', 'evidence_refs': [synthetic_id]})
        fragments.append({'fragment_id': fragment_id, 'region_ids': [region_id], 'role': 'stem', 'content_type': 'text', 'reading_order': i})
    evidence = envelope('s01-evidence', 'EvidenceBundle', [source_ref], {'source': source_ref, 'regions': regions, 'coverage_clues': clues})
    evidence_ref = artifact_ref(evidence)
    graph = envelope('s01-graph', 'QuestionGraph', [source_ref, evidence_ref],
                     {'source': source_ref, 'evidence': evidence_ref,
                      'questions': [{'question_id': source['payload']['scope_manifest'][0], 'directory_id': source['payload']['directories'][0]['directory_id'],
                                     'question_type': 'free_response', 'fragment_ids': [f['fragment_id'] for f in fragments], 'parent_question_id': None,
                                     'shared_fragment_ids': [], 'cross_page': True,
                                     'external_refs': {'printed_number': None, 'platform_question_id': None, 'platform_order': None}}],
                      'fragments': fragments, 'answer_relations': [], 'identity_notes': 'SYNTHETIC gate probe: historical one-row reference is not independent denominator.'})
    graph_ref = artifact_ref(graph)
    policy = policy_ref(data['policies'][0])
    pre = envelope('s01-preapply', 'CheckReport', [source_ref, evidence_ref, graph_ref],
                   {'stage': 'PRE_APPLY', 'subject': graph_ref, 'graph': graph_ref, 'policy': policy, 'snapshot': None, 'receipt': None,
                    'coverage': {'scope_id': source['scope_id'], 'pages_expected': source['payload']['pages_expected'], 'pages_checked': source['payload']['pages_expected'],
                                 'clue_ids': [c['clue_id'] for c in clues], 'unassigned_region_ids': []},
                    'checks': [{'check_id': key, 'outcome': 'PASS', 'evidence_refs': [synthetic_id], 'reason': 'Fabricated synthetic PASS, not an actual quality finding.'}
                               for key in ('source_integrity', 'structure', 'answer_matching', 'coverage', 'policy')],
                    'issues': [], 'decision': 'PASS', 'reason': 'Synthetic counterexample to missing typed denominator gate; not an authorized platform workflow.'})
    data['artifacts'] += [evidence, graph, pre]
    write(path, data)
    keep_input(name, path, 'exchange.json')
    keep_input(name, path.parent / relative, relative)
    source_before = read(BASE['46007447'])['artifacts'][0]
    assert source_before == source
    accepted = load_bundle(path, verify_assets=True)
    return {'public_load': 'ACCEPT', 'synthetic_preapply_decision': accepted.artifacts[-1].payload.decision,
            'original_a01_source_unchanged': True, 'limitations_coverage_eligible': read(path.parent / 'limitations.json')['coverage_eligible'],
            'limitations_independent_denominator_status': read(path.parent / 'limitations.json')['independent_denominator_status'],
            'scope_manifest_basis': source['payload']['scope_manifest_basis'], 'platform_actions': 0,
            'interpretation': 'Known C01/S01 integration gap: SourceBundle-only consumer stays false; expanded public contract accepts synthetic PASS without denominator eligibility gate.'}
case('S23-S01-public-preapply-gate-gap', 'REJECT', 'Unmodified reference-only A01 source must not count as independent complete denominator for PRE_APPLY PASS.', s01_machine_gap)

baseline_after = {book: hashes(p.parent) for book, p in BASE.items()}
snapshot_after = hashes(SNAPSHOT)
summary = {'target_commit': environment['target_commit'], 'cases': RESULTS,
           'counts': {k: sum(r['actual'] == k for r in RESULTS) for k in ('ACCEPT', 'REJECT', 'SKIP')},
           'unexpected_accepts': [r['id'] for r in RESULTS if r['expected'] == 'REJECT' and r['actual'] == 'ACCEPT'],
           'pristine_frozen_snapshot_unchanged': snapshot_before == snapshot_after,
           'old_baseline_products_unchanged': baseline_before == baseline_after,
           'snapshot_file_count': len(snapshot_before), 'baseline_manifests': baseline_after,
           'scope': 'Independent source review only; parent decides overall A01 acceptance.',
           'authenticity_limit': 'No unsigned self-contained bundle can prove authenticity if every internal record and external trusted reference are replaced. Rewrapped cases test internal contradictions against retained records.'}
write(EVIDENCE / 'results.json', summary)
write(EVIDENCE / 'snapshot-and-baseline-integrity.json', {'snapshot_before': snapshot_before, 'snapshot_after': snapshot_after,
                                                       'baseline_before': baseline_before, 'baseline_after': baseline_after})
manifest = hashes(EVIDENCE)
write(EVIDENCE / 'sha256-manifest.json', {'files': manifest})
print(json.dumps({'counts': summary['counts'], 'unexpected_accepts': summary['unexpected_accepts'],
                  'snapshot_unchanged': summary['pristine_frozen_snapshot_unchanged'], 'old_products_unchanged': summary['old_baseline_products_unchanged']}, indent=2), flush=True)
