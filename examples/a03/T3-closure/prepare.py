"""Static-only M schema/input/pin preparation; imports no product, opens no DB."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DATA = ROOT / 'src/annotation/contracts/a03_native/data'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def ref(value):
    return {k: value[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}


def schemas():
    basis = json.loads((DATA / 'schemas/basis.json').read_bytes())
    props = basis['properties']
    props['format_version'] = {'const': 'a03-unattempted-basis-M1'}
    for key in ('binding', 'gate_binding'):
        props[key]['properties']['source_ref'] = copy.deepcopy(props[key]['properties']['plan_ref'])
        if 'source_ref' not in props[key]['required']:
            props[key]['required'].append('source_ref')
    props['observations'].update(minItems=3, maxItems=3)
    props['entry_deadline'] = props['parent_deadline'] = {'type': 'number'}
    write(DATA / 'schemas/basis.json', basis)
    prefix = json.loads((DATA / 'schemas/prefix.json').read_bytes())
    branches = prefix['properties']['frames']['items']['properties']['event']['oneOf']
    branches[:] = [b for b in branches if b['properties']['event'].get('const', '').startswith('M_') is False]
    template = copy.deepcopy(next(b for b in branches if b['properties']['event']['const'] == 'PLAN_STARTED' and 'event_version' not in b['properties']))
    binding = copy.deepcopy(props['binding'])
    resource = copy.deepcopy(props['complete_uncalled_prefix'])
    head = copy.deepcopy(props['initial_event_head'])
    payloads = {
        'M_READONLY_STARTED': {'initial_event_head': head},
        'M_READONLY_READ_STARTED': {'ordinal': {'type': 'integer', 'minimum': 1, 'maximum': 3}, 'in_final_gate': {'type': 'boolean'}},
        'M_READONLY_READ_FINISHED': {'ordinal': {'type': 'integer', 'minimum': 1, 'maximum': 3}, 'observation': resource},
        'M_READONLY_ABORTED': {'used_count': {'type': 'integer', 'minimum': 0, 'maximum': 3}, 'reason': {'type': 'string', 'minLength': 1}},
        'M_UNATTEMPTED_COMMITTED': {'fact': resource, 'expected_event_head': head},
    }
    for name, fields in payloads.items():
        branch = copy.deepcopy(template)
        branch['properties']['event'] = {'const': name}
        branch['properties']['event_version'] = {'const': 'a03-M-event-1'}
        branch['required'].append('event_version')
        fields = dict(binding=binding, **fields)
        branch['properties']['payload'] = {'type': 'object', 'properties': fields,
            'required': list(fields), 'additionalProperties': False}
        branches.append(branch)
    write(DATA / 'schemas/prefix.json', prefix)
    fact = json.loads((DATA / 'schemas/fact.json').read_bytes())
    fact['description'] = 'Native M: unattempted facts consume a03-unattempted-basis-M1; no intent or old-tail authority.'
    write(DATA / 'schemas/fact.json', fact)
    api = json.loads((DATA / 'api.json').read_bytes())
    api['M_adoption'] = {'decision': '4fa7237d1114ed2c89f65cbb28579a8956812062',
        'language': '1..3 questions, one 32x32 PGM and stem/answer per question',
        'record_hold_candidate': ['registration_id', 'bundle', 'plan_ref', 'config', 'hold_id', 'owner_id', 'generation', 'expected_head'],
        'unattempted_request': ['registration_id', 'plan_ref', 'action_id', 'action_digest', 'expected_event_head', 'entry_id', 'parent_call_id', 'read_fault(optional)'],
        'readonly_entry': 'unique book/plan/action; persistent count <=3; no retry/reset/new entry for same action',
        'hold_transition': 'readonly POST_HOLD candidate -> final read/CAS clear -> genuinely new INITIAL PRE/planner',
        'converter': 'LEGACY_INITIAL_ONLY', 'migration': 'NOT_IMPLEMENTED_BLOCKED'}
    write(DATA / 'api.json', api)
    oracle = json.loads((DATA / 'oracle.json').read_bytes())
    oracle.update(oracle_id='a03-M-fixed-upto-three-questions', status='ADOPTED_FOR_M_IMPLEMENTATION_NOT_ACCEPTANCE')
    oracle['structure']['question_count_range'] = [1, 3]
    oracle['structure'].pop('question_count', None)
    oracle['structure']['regions_per_question'] = oracle['structure'].pop('region_count', 2)
    oracle['source_integrity']['page_count_range'] = [1, 3]
    oracle['source_integrity'].pop('page_count', None)
    oracle['answer_matching']['relations_per_question'] = oracle['answer_matching'].pop('relation_count', 1)
    oracle['coverage']['question_count_range'] = [1, 3]
    oracle['coverage']['page_count_range'] = [1, 3]
    oracle['coverage']['clues_per_page'] = oracle['coverage'].pop('clue_count', 2)
    oracle['coverage'].pop('question_count', None)
    oracle['coverage'].pop('page_count', None)
    oracle['M_language'] = 'Each independently drawn page is identical fixed 32x32 language; unique image/question/region/fragment IDs and per-page enumeration.'
    write(DATA / 'oracle.json', oracle)


def fixture(count, tag):
    seed_dir = ROOT / 'tests/fixtures/a03/P2-R8-R3-post-hold'
    seed = json.loads((seed_dir / 'initial.json').read_bytes())
    base = {a['kind']: a for a in seed['artifacts']}
    dest = HERE / 'inputs' / tag
    dest.mkdir(parents=True, exist_ok=True)
    page_raw = (seed_dir / 'assets/page.pgm').read_bytes()
    proof_raw = b'New fixed synthetic M input; no historical execution or native authority.\n'
    (dest / 'assets').mkdir(exist_ok=True)
    (dest / 'assets/proof.txt').write_bytes(proof_raw)
    proof_id = 'proof-M-' + tag
    book, scope = 'book-M-' + tag, 'scope-M-' + tag
    asset_ids = ['page-M-' + tag + '-' + str(i) for i in range(1, count+1)]
    qids = ['question-M-' + tag + '-' + str(i) for i in range(1, count+1)]
    source = copy.deepcopy(base['SourceBundle'])
    source['payload'].update(assets=[], pages_expected=asset_ids, pages_acquired=asset_ids,
        scope_manifest=qids, metadata_page_count=count, external_page_mappings=[],
        scope_manifest_basis='Independent explicit M per-page fixed synthetic inventory')
    source['payload']['directories'] = [{'directory_id': 'directory-M', 'label': 'M synthetic', 'parent_id': None}]
    evidence = copy.deepcopy(base['EvidenceBundle'])
    evidence['payload'].update(regions=[], coverage_clues=[])
    graph = copy.deepcopy(base['QuestionGraph'])
    graph['payload'].update(questions=[], fragments=[], answer_relations=[], identity_notes='Fresh M synthetic input; planner has not run')
    for index in range(count):
        number = index + 1
        asset = copy.deepcopy(base['SourceBundle']['payload']['assets'][0])
        asset.update(asset_id=asset_ids[index], path='assets/page-' + str(number) + '.pgm')
        (dest / asset['path']).write_bytes(page_raw)
        source['payload']['assets'].append(asset)
        source['payload']['external_page_mappings'].append({'asset_id': asset['asset_id'], 'directory_id': 'directory-M',
            'evidence_refs': [proof_id], 'external_page': str(number), 'mapping_status': 'CONFIRMED'})
        fids = []
        for position, role in enumerate(('stem', 'answer')):
            rid = 'region-M-' + tag + '-' + str(number) + '-' + role
            fid = 'fragment-M-' + tag + '-' + str(number) + '-' + role
            cid = 'clue-M-' + tag + '-' + str(number) + '-' + role
            region = copy.deepcopy(base['EvidenceBundle']['payload']['regions'][position])
            region.update(region_id=rid, evidence_refs=[proof_id], text='Synthetic M ' + role + ' ' + str(number))
            region['box']['image']['asset_id'] = asset['asset_id']
            evidence['payload']['regions'].append(region)
            clue = copy.deepcopy(base['EvidenceBundle']['payload']['coverage_clues'][position])
            clue.update(clue_id=cid, region_ids=[rid], evidence_refs=[proof_id])
            clue['box']['image']['asset_id'] = asset['asset_id']
            evidence['payload']['coverage_clues'].append(clue)
            frag = copy.deepcopy(base['QuestionGraph']['payload']['fragments'][position])
            frag.update(fragment_id=fid, region_ids=[rid], reading_order=2*index+position)
            graph['payload']['fragments'].append(frag)
            fids.append(fid)
        question = copy.deepcopy(base['QuestionGraph']['payload']['questions'][0])
        question.update(question_id=qids[index], directory_id='directory-M', fragment_ids=fids)
        question['external_refs']['printed_number'] = str(number)
        graph['payload']['questions'].append(question)
        relation = copy.deepcopy(base['QuestionGraph']['payload']['answer_relations'][0])
        relation.update(relation_id='relation-M-' + tag + '-' + str(number), question_id=qids[index],
            evidence_refs=[proof_id], candidate_fragment_ids=[fids[-1]], selected_fragment_ids=[fids[-1]])
        graph['payload']['answer_relations'].append(relation)
    inventory = {'origin': 'SYNTHETIC', 'basis': 'FIXTURE', 'complete': True, 'book_id': book, 'scope_id': scope,
        'assets': [{k:a[k] for k in ('asset_id','path','sha256','width','height')} for a in source['payload']['assets']],
        'pages_expected': asset_ids, 'pages_acquired': asset_ids, 'scope_manifest': qids,
        'per_page_questions': [{'asset_id': a, 'question_ids': [q], 'enumeration_complete': True} for a,q in zip(asset_ids,qids)]}
    write(dest / 'assets/inventory.json', inventory)
    source['payload']['scope_integrity']['proof']['sha256'] = hashlib.sha256((dest / 'assets/inventory.json').read_bytes()).hexdigest()
    snapshot = copy.deepcopy(base['PlatformSnapshot'])
    snapshot['payload'].update(target_id='target-M-' + tag, authorized_scope_id=scope, directories=['platform-M'])
    for cap in snapshot['payload']['capabilities']:
        cap['evidence_refs'] = [proof_id] if cap['evidence_refs'] else []
    snapshot['payload']['evidence_refs'] = [proof_id]
    result = dict(format_version=seed['format_version'], policies=copy.deepcopy(seed['policies']),
        evidence=[{'evidence_id': proof_id, 'description': 'Fresh independent M synthetic declaration', 'mode': 'SYNTHETIC',
                   'resource': {'path':'assets/proof.txt','sha256':hashlib.sha256(proof_raw).hexdigest(), 'media_type':'text/plain','origin':'SYNTHETIC'}}], artifacts=[])
    for artifact in (source, evidence, graph, snapshot):
        kind = artifact['kind']
        artifact.update(artifact_id='input-M-' + tag + '-' + kind, book_id=book, scope_id=scope, run_id='input-M-' + tag, input_refs=[])
        artifact['producer'].update(module='a03-M-fixed-input', implementation_version='static-input-1', config_version='M-input-1')
        if kind in ('EvidenceBundle','QuestionGraph'):
            artifact['payload']['source'] = ref(source)
            artifact['input_refs'].append(ref(source))
        if kind == 'QuestionGraph':
            artifact['payload']['evidence'] = ref(evidence)
            artifact['input_refs'].append(ref(evidence))
        if kind == 'PlatformSnapshot':
            artifact['input_refs'] = [ref(source)]
        artifact['content_hash'] = digest({k:v for k,v in artifact.items() if k != 'content_hash'})
        result['artifacts'].append(artifact)
    write(dest / 'initial.json', result)


def pins():
    # Raw staged Git identity, not checkout EOL representation, is authoritative.
    def staged(path):
        return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(ROOT),'show',':'+path], cwd=str(ROOT))
    profile = json.loads((DATA / 'profile.json').read_bytes())
    for item in profile['implementation_pins']:
        relative = item[0]
        path = 'src/' + relative[1:] if relative.startswith('@') else 'src/annotation/contracts/a03_native/' + relative
        item[1] = hashlib.sha256(staged(path)).hexdigest()
    for item in profile['schema_pins']:
        item[1] = hashlib.sha256(staged('src/annotation/contracts/a03_native/data/' + item[0])).hexdigest()
    for key,name in [('api_sha256','api.json'),('oracle_sha256','oracle.json')]:
        profile[key] = hashlib.sha256(staged('src/annotation/contracts/a03_native/data/'+name)).hexdigest()
    profile['M_adoption'] = 'D-M adopted for this implementation; legacy converter, fresh native only; not functional acceptance'
    write(DATA / 'profile.json', profile)
    adoption = json.loads((DATA / 'adoption.json').read_bytes())
    adoption['profile_sha256'] = hashlib.sha256((DATA / 'profile.json').read_bytes()).hexdigest()
    write(DATA / 'adoption.json', adoption)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pins', action='store_true')
    args = parser.parse_args()
    if args.pins:
        pins()
    else:
        schemas()
        fixture(1, 'single')
        fixture(3, 'three')
