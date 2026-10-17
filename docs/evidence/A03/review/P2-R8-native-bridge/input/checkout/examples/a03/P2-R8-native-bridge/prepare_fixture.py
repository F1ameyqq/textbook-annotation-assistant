"""Author fresh R8 fixed-language input data. No old PRE/plan/driver is used."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'tests/fixtures/a03/P2-R8-native-bridge'


def raw(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def ref(value):
    return {key: value[key] for key in ('artifact_id', 'revision', 'kind', 'content_hash')}


def main():
    DEST.mkdir(parents=True, exist_ok=False)
    (DEST / '.gitattributes').write_bytes(b'* -text whitespace=trailing-space,space-before-tab,cr-at-eol\n')
    assets = DEST / 'assets'
    assets.mkdir()
    pixels = [' '.join('0' if 4 <= x < 28 and (4 <= y < 10 or 18 <= y < 24) else '255' for x in range(32)) for y in range(32)]
    pgm = ('P2\n# Fresh R8 fixed synthetic two-rectangle page\n32 32\n255\n' + '\n'.join(pixels) + '\n').encode()
    (assets / 'page.pgm').write_bytes(pgm)
    page_sha = hashlib.sha256(pgm).hexdigest()
    proof_bytes = b'R8 synthetic fixture declaration. No OCR, model or real source.\n'
    (assets / 'proof.txt').write_bytes(proof_bytes)
    old = json.loads((ROOT / 'examples/a03/P2-R2-proposal/candidate-final/original/new-authored-initial-a.json').read_bytes())
    mapping = {'page-a': 'page-r8', 'original-a': 'scope-r8', 'question-a': 'question-r8',
        'directory-a': 'directory-r8', 'platform-a': 'platform-r8', 'synthetic-r2-target': 'target-r8',
        'synthetic-a02-policy': 'policy-r8', 'proof': 'proof-r8'}

    def rename(value):
        if isinstance(value, str):
            return mapping.get(value, value.replace('-a', '-r8') if value.startswith(('region-', 'fragment-', 'relation-', 'clue-')) else value)
        if isinstance(value, list):
            return [rename(v) for v in value]
        if isinstance(value, dict):
            return {k: rename(v) for k, v in value.items()}
        return value
    selected = [a for a in old['artifacts'] if a['kind'] in ('SourceBundle', 'EvidenceBundle', 'QuestionGraph', 'PlatformSnapshot')]
    policy = rename(copy.deepcopy(old['policies'][0]))
    policy.pop('content_hash')
    policy['content_hash'] = digest(policy)
    policy_reference = {key: policy[key] for key in ('policy_id', 'revision', 'content_hash')}
    converted = {}
    artifacts = []
    for original in selected:
        value = rename(copy.deepcopy(original))
        value.update(artifact_id='input-r8-' + original['kind'], book_id='book-r8-synthetic',
            scope_id='scope-r8', run_id='input-r8', schema_version='1.4.0-a03-native-proposal')
        value['producer'].update(module='r8-fresh-input-author', config_version='r8-input-1', policy_versions=[policy_reference])
        value['content_hash'] = '0' * 64

        def fix(node):
            if isinstance(node, dict):
                if set(node) == {'artifact_id', 'revision', 'kind', 'content_hash'}:
                    return ref(converted[node['kind']])
                result = {k: fix(v) for k, v in node.items()}
                if result.get('asset_id') == 'page-r8' and 'sha256' in result:
                    result['sha256'] = page_sha
                    if 'path' in result:
                        result.update(path='assets/page.pgm', source_label='Fresh R8 fixed synthetic page')
                return result
            if isinstance(node, list):
                return [fix(v) for v in node]
            return node
        value = fix(value)
        if value['kind'] == 'SourceBundle':
            payload = value['payload']
            inventory = {'origin': 'SYNTHETIC', 'basis': 'FIXTURE', 'complete': True,
                'book_id': value['book_id'], 'scope_id': value['scope_id'],
                'pages_expected': ['page-r8'], 'pages_acquired': ['page-r8'], 'scope_manifest': ['question-r8'],
                'assets': [{k: a[k] for k in ('asset_id', 'path', 'sha256', 'width', 'height')} for a in payload['assets']],
                'per_page_questions': [{'asset_id': 'page-r8', 'enumeration_complete': True, 'question_ids': ['question-r8']}]}
            inventory_raw = raw(inventory)
            (assets / 'inventory.json').write_bytes(inventory_raw)
            payload['scope_integrity']['proof'].update(path='assets/inventory.json', sha256=hashlib.sha256(inventory_raw).hexdigest())
        if value['kind'] == 'PlatformSnapshot':
            payload = value['payload']
            payload['observed_version'] = 'a03-target-epoch-0'
            target = {k: payload[k] for k in ('platform_version', 'capabilities', 'directories', 'questions', 'frames')}
            state = {'target_key': {'platform_namespace': 'a03-r8-native', 'target_id': payload['target_id'], 'book_id': value['book_id']},
                'source_ref': ref(converted['SourceBundle']), 'scope_id': value['scope_id'],
                'internal_bindings': {}, 'frame_projections': {}, **target}
            payload['observed_hash'] = digest(state)
        value.pop('content_hash')
        value['content_hash'] = digest(value)
        converted[value['kind']] = value
        artifacts.append(value)
    evidence = [{'evidence_id': 'proof-r8', 'description': 'Fresh synthetic declaration only', 'mode': 'SYNTHETIC',
        'resource': {'path': 'assets/proof.txt', 'sha256': hashlib.sha256(proof_bytes).hexdigest(), 'media_type': 'text/plain', 'origin': 'SYNTHETIC'}}]
    (DEST / 'initial.json').write_bytes(raw({'format_version': 'a03-exchange-4-proposal', 'policies': [policy], 'evidence': evidence, 'artifacts': artifacts}))
    print(json.dumps({'artifacts': [a['kind'] for a in artifacts], 'old_PRE_or_plan': False, 'page_sha256': page_sha}))


if __name__ == '__main__':
    main()
