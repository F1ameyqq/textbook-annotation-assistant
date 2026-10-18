"""Static-only fresh legacy fixture construction, pin update and source freeze."""
import copy
import json
from pathlib import Path
import shutil
import sys
from support import ROOT, HERE, TEST, BASE, FAULTS, sha, write, frozen_files, index

sys.path.insert(0, str(ROOT / 'src'))


def fixture():
    from annotation.contracts import artifact_ref, seal_artifact, validate_bundle, convert_synthetic_fixture, load_recovery_bundle
    source = ROOT / 'tests/fixtures/a02/normal'
    raw = json.loads((source / 'input.json').read_bytes())
    # A new, unexecuted one-page inventory, retaining only the independent beta question.
    changed = {}
    def refs(value):
        if isinstance(value, list):
            return [refs(v) for v in value]
        if isinstance(value, dict):
            if set(value) == {'artifact_id', 'revision', 'kind', 'content_hash'}:
                return copy.deepcopy(changed.get((value['artifact_id'], value['revision']), value))
            return {k: refs(v) for k, v in value.items()}
        return value
    for i, original in enumerate(raw['artifacts']):
        item = refs(original)
        item.update(artifact_id='r12-r1-L1-' + original['artifact_id'], run_id='run-r12-r1-L1',
                    book_id='book-r12-r1-legacy', scope_id='scope-r12-r1-legacy')
        p = item['payload']
        if item['kind'] == 'SourceBundle':
            p['assets'] = [a for a in p['assets'] if a['asset_id'] == 'asset-page-b1']
            p['directories'] = [d for d in p['directories'] if d['directory_id'] == 'directory-b']
            p['pages_expected'] = p['pages_acquired'] = ['asset-page-b1']
            p['external_page_mappings'] = [m for m in p['external_page_mappings'] if m['asset_id'] == 'asset-page-b1']
            p['scope_manifest'] = ['question-beta']
            p['scope_manifest_basis'] = 'Fresh synthetic singleton Unit B inventory for legacy UNKNOWN compatibility.'
            p['metadata_page_count'] = 1
        elif item['kind'] == 'EvidenceBundle':
            p['regions'] = [r for r in p['regions'] if r['region_id'].startswith('region-beta-')]
            p['coverage_clues'] = [c for c in p['coverage_clues'] if c['clue_id'].startswith('clue-beta-')]
        elif item['kind'] == 'QuestionGraph':
            p['questions'] = [q for q in p['questions'] if q['question_id'] == 'question-beta']
            p['fragments'] = [f for f in p['fragments'] if f['fragment_id'].startswith('fragment-beta-')]
            p['answer_relations'] = [r for r in p['answer_relations'] if r['question_id'] == 'question-beta']
            p['identity_notes'] = 'Fresh singleton synthetic input; stable identity independent of printed number.'
        elif item['kind'] == 'PlatformSnapshot':
            p.update(target_id='target-r12-r1-legacy', authorized_scope_id=item['scope_id'], directories=['platform-unit-b'])
        elif item['kind'] == 'CheckReport':
            p['coverage'].update(scope_id=item['scope_id'], pages_expected=['asset-page-b1'], pages_checked=['asset-page-b1'],
                clue_ids=['clue-beta-stem', 'clue-beta-answer'])
        sealed = seal_artifact(item)
        raw['artifacts'][i] = sealed
        changed[(original['artifact_id'], original['revision'])] = artifact_ref(sealed)
    target = HERE / 'legacy-unexecuted'
    target.mkdir(exist_ok=False)
    def resources(value):
        if isinstance(value, dict):
            if {'path', 'sha256', 'media_type'} <= set(value):
                path = value['path']
                if not (target / path).exists():
                    write(target / path, (source / path).read_bytes())
            for v in value.values():
                resources(v)
        elif isinstance(value, list):
            for v in value:
                resources(v)
    resources(raw)
    validate_bundle(raw, asset_root=target)
    write(target / 'input.json', raw)
    conversion = convert_synthetic_fixture(target / 'input.json', HERE / 'legacy-recovery',
        conversion_id='r12-r1-L1-fresh', expected_input_sha256=sha((target / 'input.json').read_bytes()))
    load_recovery_bundle(HERE / 'legacy-recovery/bundle.json', asset_root=HERE / 'legacy-recovery')
    config = json.loads((source / 'config.json').read_bytes())
    config.update(book_id='book-r12-r1-legacy', scope_id='scope-r12-r1-legacy', target_id='target-r12-r1-legacy',
                  directory_map={'directory-b': 'platform-unit-b'})
    write(HERE / 'legacy-config.json', config)
    write(HERE / 'legacy-fixture-provenance.json', {'conversion': conversion, 'source_files': index(source.rglob('*')),
        'kind': 'fresh unexecuted singleton input; no executed artifact converted', 'functional_scenes_run': 0})


def pins():
    profile = ROOT / 'src/annotation/contracts/a03_native/data/profile.json'
    adoption = profile.with_name('adoption.json')
    data = json.loads(profile.read_bytes())
    selected = {'@annotation/runtime/storage/__init__.py', '@annotation/runtime/storage/native.py'}
    rows = []
    for pin in data['implementation_pins']:
        if pin[0] in selected:
            old = {'@annotation/runtime/storage/__init__.py': '93cb82da040346cfba95a312f3615b8bfc5c47edee01ba69584ac338882cfa3a',
                   '@annotation/runtime/storage/native.py': 'c3e2f01ccbfb7b64c49a5272eb51ffbe2f6af8c8abb5a51c4c9c6965166b902a'}[pin[0]]
            pin[1] = sha((ROOT / 'src' / pin[0][1:]).read_bytes())
            rows.append({'path': pin[0], 'before': old, 'after': pin[1]})
    assert len(rows) == 2
    raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    profile.write_bytes(raw)
    adopted = json.loads(adoption.read_bytes())
    adopted['profile_sha256'] = sha(raw)
    adoption.write_bytes((json.dumps(adopted, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    return rows


if __name__ == '__main__':
    if '--create-fixture' in sys.argv:
        fixture()
    pin_rows = pins()
    for path in [*HERE.glob('*.py'), TEST,
                 ROOT / 'src/annotation/runtime/storage/__init__.py', ROOT / 'src/annotation/runtime/storage/native.py']:
        compile(path.read_bytes().decode('utf-8', errors='strict'), str(path), 'exec')
    from annotation.contracts.a03_native import select_native_codec
    codec = select_native_codec()
    inputs = {'base': BASE, 'workflow': '05ba526cbd8575edc778016cf25cee13661a65c6',
        'task_sha256': 'ec269e977ed67276e5b4d1901c32c28acd75ba44870094fa0eb5fecf0cdc0076',
        'expected_branches': FAULTS, 'functional_order': list(FAULTS), 'functional_scenes_run_before_freeze': 0,
        'budgets_seconds': {'parent': 90, 'business_child': 45, 'observer': 2, 'barrier': 5, 'lease': 10},
        'max_reconcile_attempts': 1, 'retries': 0, 'pin_changes': pin_rows,
        'native_profile_sha256': codec.profile_sha256, 'native_adoption_sha256': codec.adoption_sha256,
        'files': index(p for p in frozen_files() if '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != 'inputs.json')}
    path = HERE / 'inputs.json'
    path.write_bytes((json.dumps(inputs, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'static_only': True, 'inputs_sha256': sha(path.read_bytes()), 'source_files': len(inputs['files']),
        'native_profile_sha256': codec.profile_sha256, 'pin_changes': pin_rows}))
