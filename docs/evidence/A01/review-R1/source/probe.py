"""Independent R1 source review: frozen fixed samples, internal consistency only."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser()
parser.add_argument('--snapshot', type=Path, required=True)
parser.add_argument('--stage', type=Path, required=True)
args = parser.parse_args()
SNAPSHOT = args.snapshot.resolve()
STAGE = args.stage.resolve()
OUT = Path(__file__).resolve().parent
STAGE.mkdir(parents=True, exist_ok=False)
for variable in ('TMP', 'TEMP', 'TMPDIR'):
    os.environ[variable] = str(STAGE)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PYTHONPATH'] = str(SNAPSHOT / 'src')
sys.path.insert(0, str(SNAPSHOT / 'src'))

import PIL
import pydantic
import annotation.contracts as contracts
import annotation.source.static.importer as importer
import annotation.source.static.consistency as consistency
from annotation.contracts import seal_artifact, load_bundle
from annotation.source.static import load_static_bundle

for module in (contracts, importer, consistency):
    assert Path(module.__file__).resolve().is_relative_to(SNAPSHOT / 'src')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def hashes(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}

BASES = {('old', b): SNAPSHOT / 'examples/a01/bundles' / b / 'exchange.json' for b in ('46006966', '46007447')}
BASES.update({('R1', b): SNAPSHOT / 'examples/a01/R1/bundles' / b / 'exchange.json' for b in ('46006966', '46007447')})
SNAPSHOT_BEFORE = hashes(SNAPSHOT)
BASE_HASHES = {version + '/' + book: hashes(path.parent) for (version, book), path in BASES.items()}
write(OUT / 'environment.json', {
    'target_commit': '03c1af41a134945c406a52a48e3d4f6f0da33eb2',
    'implementation_commit': '0ee7e836e3bc1849f91840b4271d233bbd8e72dd',
    'command_argv': sys.argv, 'python_executable': sys.executable, 'python_version': sys.version,
    'platform': platform.platform(), 'pillow': PIL.__version__, 'pydantic': pydantic.__version__,
    'sys_path': sys.path, 'PYTHONPATH': os.environ['PYTHONPATH'],
    'temporary_environment': {k: os.environ[k] for k in ('TMP', 'TEMP', 'TMPDIR')},
    'module_files': {m.__name__: m.__file__ for m in (contracts, importer, consistency)},
    'module_hashes': {m.__name__: sha(Path(m.__file__).read_bytes()) for m in (contracts, importer, consistency)},
    'script_sha256': sha(Path(__file__).read_bytes()), 'offline': True,
    'network_calls': 0, 'browser_calls': 0, 'credential_reads': 0, 'ocr_calls': 0, 'model_calls': 0,
})

RESULTS = []
def run(identifier, expected, description, action, expected_code=None):
    result = {'id': identifier, 'expected': expected, 'description': description, 'expected_code': expected_code}
    try:
        result.update(actual='ACCEPT', detail=action(identifier))
    except Exception as error:
        result.update(actual='REJECT', error_type=type(error).__name__, error=str(error),
                      code=getattr(error, 'code', None), location=getattr(error, 'location', None),
                      issues=getattr(error, 'issues', None), traceback=traceback.format_exc())
    result['matches_expectation'] = result['actual'] == expected and (expected_code is None or expected_code == result.get('code'))
    RESULTS.append(result)
    write(OUT / 'cases' / identifier / 'result.json', result)
    print(identifier + ': ' + result['actual'] + (' expected' if result['matches_expectation'] else ' UNEXPECTED'), flush=True)

def reseal(path, data):
    data['artifacts'] = [seal_artifact(a) for a in data['artifacts']]
    write(path, data)

def resource_hash(data, relative, digest):
    for item in data['evidence']:
        if item['resource']['path'] == relative:
            item['resource']['sha256'] = digest
    for item in data['artifacts'][0]['payload']['history']:
        if item['resource']['path'] == relative:
            item['resource']['sha256'] = digest

def sidecar(path, relative, mutation):
    value = read(path.parent / relative)
    mutation(value)
    write(path.parent / relative, value)
    data = read(path)
    resource_hash(data, relative, sha((path.parent / relative).read_bytes()))
    reseal(path, data)

def history_with_consistent_digest(path, relative, archive, mutation):
    """Keep byte-hash records consistent to reach semantic raw-record checks."""
    value = read(path.parent / relative)
    mutation(value)
    write(path.parent / relative, value)
    digest = sha((path.parent / relative).read_bytes())
    data = read(path)
    resource_hash(data, relative, digest)
    integrity = read(path.parent / 'input-integrity.json')
    entry = next(e for e in integrity['inputs'] if e['archive_path'] == archive)
    entry.update(before_sha256=digest, after_sha256=digest)
    write(path.parent / 'input-integrity.json', integrity)
    resource_hash(data, 'input-integrity.json', sha((path.parent / 'input-integrity.json').read_bytes()))
    reseal(path, data)

def inspect(identifier, path, book, before):
    now = hashes(path.parent)
    changes = {relative: digest for relative, digest in now.items() if before.get(relative) != digest}
    for relative in changes:
        if (path.parent / relative).suffix in ('.json', '.txt'):
            target = OUT / 'cases' / identifier / 'changed-inputs' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path.parent / relative, target)
    write(OUT / 'cases' / identifier / 'input.json', {'exchange': str(path), 'expected_book_id': book,
            'baseline': str(BASES[('R1', book)]), 'changed_file_sha256': changes})
    public = load_bundle(path, verify_assets=True)
    write(OUT / 'cases' / identifier / 'public-load.json', {'actual': 'ACCEPT', 'source_hash': public.artifacts[0].content_hash})
    accepted = load_static_bundle(path, expected_book_id=book)
    return {'a01_load': 'ACCEPT', 'public_load': 'ACCEPT', 'same_public_result': public == accepted,
            'source_hash': accepted.artifacts[0].content_hash, 'path': str(path)}

def mutate(identifier, mutation, book='46006966'):
    target = STAGE / identifier / 'bundle'
    shutil.copytree(BASES[('R1', book)].parent, target)
    before = hashes(target)
    path = target / 'exchange.json'
    mutation(path)
    return inspect(identifier, path, book, before)

def mutate_sidecar(identifier, relative, mutation, book='46006966'):
    return mutate(identifier, lambda path: sidecar(path, relative, mutation), book)

for (version, book), path in BASES.items():
    run('C-' + version + '-' + book, 'ACCEPT', 'Consume exact frozen fixed ' + version + ' sample; no rebuild or reserialization.',
        lambda identifier, p=path, b=book: {'source_hash': load_static_bundle(p, expected_book_id=b).artifacts[0].content_hash,
                                         'exchange_sha256': sha(p.read_bytes()), 'exchange': str(p)})

run('S12-empty-origins', 'REJECT', 'Replay original empty origins with assets/mappings kept.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p.update(origins=[])), 'SOURCE_ORIGINS')
run('S13-origin-manifest-digest', 'REJECT', 'Replay original origin manifest digest contradiction.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['origins'][0].update(manifest_sha256='0'*64)), 'SOURCE_MANIFEST')

def invented_printed(path):
    p = read(path.parent / 'provenance.json')
    asset = p['mappings'][0]['asset_id']
    p['mappings'][0]['printed_page'] = 999
    write(path.parent / 'provenance.json', p)
    data = read(path)
    resource_hash(data, 'provenance.json', sha((path.parent / 'provenance.json').read_bytes()))
    for mapping in data['artifacts'][0]['payload']['external_page_mappings']:
        if mapping['asset_id'] == asset:
            external = json.loads(mapping['external_page'])
            external['printed_page'] = 999
            mapping['external_page'] = json.dumps(external, sort_keys=True)
    reseal(path, data)
run('S14-unfounded-printed-page', 'REJECT', 'Replay original same invented printed_page=999 in provenance/public mapping.',
    lambda n: mutate(n, invented_printed), 'MAPPING_EVIDENCE')
run('S15-erased-missing-sources', 'REJECT', 'Replay original known missing declarations erased.',
    lambda n: mutate_sidecar(n, 'limitations.json', lambda p: p.update(missing_sources=[])), 'MISSING_SOURCES')
run('S16-false-integrity', 'REJECT', 'Replay original unchanged=false and before/after contradiction.',
    lambda n: mutate_sidecar(n, 'input-integrity.json', lambda p: (p.update(unchanged=False), p['inputs'][0].update(after_sha256='0'*64))), 'INPUT_CHANGED')

def cross_book_bytes(path):
    relative = 'history/01-manual-annotations.json'
    sidecar(path, relative, lambda value: value.update(bookId='46007447'))
run('S17-history-book-bytes-conflict', 'REJECT', 'Replay original archived book changed but original digest retained.',
    lambda n: mutate(n, cross_book_bytes), 'HISTORY_BYTES')

def promote(path):
    data = read(path)
    for item in data['artifacts'][0]['payload']['history']:
        item['quality'] = 'REVIEWED'
    reseal(path, data)
run('S18-promoted-history', 'REJECT', 'Replay original history promoted with no approval evidence.',
    lambda n: mutate(n, promote), 'HISTORY_QUALITY')
run('S19-scope-status-conflict', 'REJECT', 'Replay original COMPLETE status contradicting retained UNKNOWN/false.',
    lambda n: mutate_sidecar(n, 'limitations.json', lambda p: p.update(scope_manifest_status='INDEPENDENT_COMPLETE')), 'DENOMINATOR_UNKNOWN')
run('S20-reference-identity-conflict', 'REJECT', 'Replay original reference identity differs from public scope_manifest.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['reference_records'][0].update(reference_id='reference-unrelated')), 'REFERENCE_RECORDS')

run('N01-origin-omitted', 'REJECT', 'Only one required origin removed.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['origins'].pop()), 'SOURCE_ORIGINS')
run('N02-origin-duplicated', 'REJECT', 'Origin inventory length unchanged but one origin duplicated.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['origins'].__setitem__(-1, dict(p['origins'][0]))), 'SOURCE_ORIGINS')
run('N03-manifest-inventory-digest', 'REJECT', 'Manifest inventory digest conflicts with retained input inventory.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['original_manifests'][0].update(sha256='0'*64)), 'SOURCE_MANIFEST')
run('N04-history-input-omitted', 'REJECT', 'Required history input digest removed while history file stays.',
    lambda n: mutate_sidecar(n, 'input-integrity.json', lambda p: p.update(inputs=[e for e in p['inputs'] if not e['archive_path'].endswith('/manual-annotations.json')])), 'INPUT_INVENTORY')
run('N05-before-after-disagree', 'REJECT', 'unchanged=true but before/after disagree.',
    lambda n: mutate_sidecar(n, 'input-integrity.json', lambda p: p['inputs'][0].update(after_sha256='0'*64)), 'INPUT_CHANGED')

def wrong_directory(path):
    data = read(path)
    data['artifacts'][0]['payload']['directories'][0]['label'] = 'Invented directory'
    reseal(path, data)
run('N06-directory-projection-conflict', 'REJECT', 'Public directory projection differs from retained archived tree.',
    lambda n: mutate(n, wrong_directory), 'HISTORY_DIRECTORY')
run('N07-outliers-erased', 'REJECT', 'Outlier declaration erased but historical out-of-bounds box retained.',
    lambda n: mutate_sidecar(n, 'limitations.json', lambda p: p.update(historical_box_issues=[])), 'HISTORY_DATA')
run('N08-workspace-declared-digest', 'REJECT', 'Available workspace declaration digest conflicts with history/input inventory.',
    lambda n: mutate_sidecar(n, 'limitations.json', lambda p: next(e for e in p['missing_sources'] if e['file']=='workspace1.jpg').update(declared_sha256='0'*64)), 'MISSING_SOURCES')
run('N09-reference-position', 'REJECT', 'Reference position differs while identity and original input stay.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['reference_records'][0].update(position=999)), 'REFERENCE_RECORDS')
run('N10-historical-date', 'REJECT', 'Historical observation date conflicts with retained session receipt.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['observation'].update(date='2000-01-01')), 'OBSERVATION_CONFLICT')

NEW_RELATIVE = 'history/00-independent-source-page14.json'
NEW_ARCHIVE = 'docs/evidence/A05/review/independent-source-page14.json'
def semantic_history(identifier, mutation):
    return mutate(identifier, lambda path: history_with_consistent_digest(path, NEW_RELATIVE, NEW_ARCHIVE, mutation), '46007447')
run('N11-new-history-index', 'REJECT', 'History/input hashes consistently updated; retained response source index differs from assigned mapping.',
    lambda n: semantic_history(n, lambda p: p['data']['pages'][0].update(page_index=172)), 'MAPPING_CONFLICT')
run('N12-new-history-book', 'REJECT', 'History/input hashes consistently updated; raw book_id conflicts with bundle book_id.',
    lambda n: semantic_history(n, lambda p: p['data'].update(file_id='46006966')), 'BOOK_CONFLICT')

run('N13-acquired-page-declared-missing', 'REJECT', 'source index 7 acquired in assets/mapping, but simultaneously selected_missing_source_indices=[7].',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p.update(selected_missing_source_indices=[7])))
run('N14-selected-page-declared-outside-unacquired', 'REJECT', 'source index 7 selected/acquired, but appended to outside_selected_scope_unacquired_indices.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['outside_selected_scope_unacquired_indices'].append(7)))
run('N15-date-only-precision-promoted-live', 'REJECT', 'Retained historical session has date only but observation precision claims LIVE_OBSERVATION.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['observation'].update(precision='LIVE_OBSERVATION')))
run('N16-new-history-image-wrong-book', 'REJECT', 'Raw response image URL book conflicts with same response file_id, mapping and archive path; hashes consistently updated.',
    lambda n: semantic_history(n, lambda p: p['data']['pages'][0].update(image='https://offline.invalid/upload_images/46006966/46006966_page_13.jpg')))
run('N17-new-history-image-wrong-index', 'REJECT', 'Raw response page_index=13 but URL says source172; hashes consistently updated; no external authenticity assumption.',
    lambda n: semantic_history(n, lambda p: p['data']['pages'][0].update(image='https://offline.invalid/upload_images/46007447/46007447_page_172.jpg')))
run('N18-observation-index-digest', 'REJECT', 'Observation index declaration digest conflicts with corresponding retained input-integrity entry.',
    lambda n: mutate_sidecar(n, 'provenance.json', lambda p: p['observation']['observation_index_source'].update(sha256='0'*64), '46007447'))

def archived_total(path):
    relative, archive = 'history/03-independent-book.json', 'docs/evidence/A05/review/independent-book.json'
    history_with_consistent_digest(path, relative, archive, lambda p: p['data'].update(page_count=215))
run('N19-new-history-total', 'REJECT', 'History/input hashes consistently updated; archived book total215 conflicts with retained metadata/source214.',
    lambda n: mutate(n, archived_total, '46007447'), 'METADATA_CONFLICT')

snapshot_after = hashes(SNAPSHOT)
summary = {'target_commit': '03c1af41a134945c406a52a48e3d4f6f0da33eb2', 'cases': RESULTS,
           'counts': {key: sum(r['actual']==key for r in RESULTS) for key in ('ACCEPT','REJECT')},
           'original_S12_S20_all_rejected_with_expected_code': all(r['matches_expectation'] for r in RESULTS if r['id'].startswith('S')),
           'unexpected_accepts': [r['id'] for r in RESULTS if r['actual']=='ACCEPT' and r['expected']=='REJECT'],
           'pristine_samples_all_accepted': all(r['matches_expectation'] for r in RESULTS if r['id'].startswith('C-')),
           'frozen_snapshot_unchanged': snapshot_after==SNAPSHOT_BEFORE, 'snapshot_file_count': len(SNAPSHOT_BEFORE),
           'fixed_sample_files_before': BASE_HASHES,
           'authenticity_boundary': 'Tests compare mutually retained records only; no unsigned archive external authentication assumed.',
           'S01_D01_status': 'Known unresolved integration limitations; not fixed or exercised as success here.'}
write(OUT / 'results.json', summary)
write(OUT / 'snapshot-integrity.json', {'before': SNAPSHOT_BEFORE, 'after': snapshot_after, 'unchanged': snapshot_after==SNAPSHOT_BEFORE})
print(json.dumps({k: summary[k] for k in ('counts','original_S12_S20_all_rejected_with_expected_code','unexpected_accepts','pristine_samples_all_accepted','frozen_snapshot_unchanged')}, indent=2), flush=True)
