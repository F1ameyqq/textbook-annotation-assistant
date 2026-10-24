"""Revise existing C01 answer associations after explicit B source confirmation.

The review JSON is internal evidence, not a new public exchange contract.
Only three explicitly source-bound printed-label prefixes may change text/runs.
Geometry, formulas, blank values, answers, local IDs and shared fragments persist.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

A_COMMIT = 'c5aefbc8e995c410b3babf74a251f05a7724a1c2'
LABEL_RESTORATIONS = {'q16-task1':'（1）','q16-task2':'（2）','q16-task3':'（3）'}
sha = lambda b: hashlib.sha256(b).hexdigest()
canonical = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
encode = lambda x: (json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
ref = lambda a: {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}


def need(value, code):
    if not value:
        raise ValueError(code)


def seal(value):
    value = copy.deepcopy(value)
    value['content_hash'] = sha(canonical({k:v for k,v in value.items() if k!='content_hash'}))
    return value


def load_files(root):
    root = Path(root)
    need(not any(p.is_symlink() for p in root.rglob('*')), 'SOURCE_SYMLINK')
    return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}


def predecessor_files(frozen):
    """Reconstruct exact predecessor members from immutable overlays, no old code."""
    frozen = dict(frozen)
    review = json.loads(frozen['current-review.json'])
    result = {}
    for member in review['predecessor_members']:
        name = member['path']
        need(name and not name.startswith('/') and ':' not in name and '\\' not in name
             and all(p not in ('','.','..') for p in name.split('/')), 'PREDECESSOR_PATH')
        raw = frozen.get('history/v2/'+name, frozen.get(name))
        need(raw is not None and len(raw)==member['bytes'] and sha(raw)==member['sha256'], 'PREDECESSOR_BYTES')
        need(name not in result, 'PREDECESSOR_DUPLICATE')
        result[name] = raw
    return result


def revise(files, review, generation=None):
    original = json.loads(files['bundle.json'])
    old_d = json.loads(files['delivery.json'])
    need(original['format_version']=='c01-exchange-1' and len(original['artifacts'])==4 and len(original['policies'])==1,
         'EXISTING_READONLY_C01_REQUIRED')
    old = {a['kind']:a for a in original['artifacts']}
    need(set(old)=={'SourceBundle','EvidenceBundle','QuestionGraph','CheckReport'}, 'READONLY_ARTIFACT_KINDS')
    need(review['review_kind']=='B_MODEL_SOURCE_CONFIRMED' and review['human_verified'] is False
         and review['a_owner_acceptance'] is False and review['content_issues']==[], 'EXPLICIT_MODEL_CONTENT_CONFIRMATION')
    need(review['predecessor_bundle_sha256']==sha(files['bundle.json']), 'WRONG_PREDECESSOR')
    inventory = [{'path':n,'bytes':len(b),'sha256':sha(b)} for n,b in sorted(files.items())]
    need(review['predecessor_members']==inventory, 'EXACT_PREDECESSOR_INVENTORY')
    source = old['SourceBundle']['payload']
    evidence = old['EvidenceBundle']['payload']
    graph = old['QuestionGraph']['payload']
    changes = review.get('source_text_changes', [])
    by_block = {b['block_id']:b for b in old_d['bindings']}
    by_region = {r['region_id']:r for r in evidence['regions']}
    proofs = {p['region_id']:p for p in old_d['source_proofs']}
    changes_by_region = {}
    required = {bid for bid,prefix in LABEL_RESTORATIONS.items() if bid in by_block and
                not by_region[by_block[bid]['region_id']]['text'].startswith(prefix)}
    need(len(changes)==len({c['block_id'] for c in changes}) and {c['block_id'] for c in changes}==required,
         'EXACT_MISSING_LABEL_RESTORATIONS_REQUIRED')
    for change in changes:
        bid=change['block_id'];prefix=LABEL_RESTORATIONS.get(bid)
        need(prefix is not None,'ONLY_PRINTED_LABEL_RESTORATION_ALLOWED')
        binding=by_block[bid];region=by_region[binding['region_id']];proof=proofs[binding['region_id']]
        runs=copy.deepcopy(binding['runs'])
        need(runs and runs[0]['format']=='plain' and binding['role']=='stem','LABEL_STEM_PLAIN_RUN_REQUIRED')
        runs[0]['text']=prefix+runs[0]['text']
        need(change['operation']=='RESTORE_PRINTED_SUBQUESTION_LABEL' and change['prefix']==prefix and
             change['region_id']==binding['region_id'] and change['before_text']==region['text'] and
             change['after_text']==prefix+region['text'] and change['before_runs']==binding['runs'] and
             change['after_runs']==runs and change['asset_id']==region['box']['image']['asset_id'] and
             change['source_sha256']==region['box']['image']['sha256'] and change['bbox']==region['box']['bbox'] and
             change['crop_path']==proof['path'] and change['crop_png_sha256']==proof['sha256']==sha(files[proof['path']]) and
             change['crop_rgb_sha256']==proof['rgb_sha256'],'SOURCE_BOUND_LABEL_ONLY_DELTA')
        changes_by_region[change['region_id']]=change
    need(review['source_asset_sha256']=={a['asset_id']:a['sha256'] for a in source['assets']}, 'REVIEW_SOURCE_PINS')
    need(review['confirmed_region_ids']==[r['region_id'] for r in evidence['regions']], 'REGION_CONFIRMATION_SCOPE')
    confirmations = review['answer_confirmations']
    need(len(confirmations)==len(graph['questions']) and len({c['question_id'] for c in confirmations})==len(confirmations), 'CONFIRMATION_SCOPE')
    by_q = {c['question_id']:c for c in confirmations}
    need(set(by_q)=={q['question_id'] for q in graph['questions']}, 'EXACT_CONFIRMED_QUESTIONS')
    for relation in graph['answer_relations']:
        qid = relation['question_id']
        owned = [b['fragment_id'] for b in old_d['bindings'] if b.get('owner_id',b.get('item_key'))==qid
                 and b['fragment_id'] is not None and b['role'] in ('answer','explanation')]
        need(owned and owned==relation['candidate_fragment_ids']==by_q[qid]['selected_fragment_ids']
             and by_q[qid]['disposition']=='B_MODEL_SOURCE_CONFIRMED' and by_q[qid]['source_reason'], 'EXPLICIT_OWNED_ANSWER_SELECTION')
    need(len(graph['answer_relations'])==len(graph['questions']), 'ONE_RELATION_PER_QUESTION')
    directory_ids = {d['directory_id'] for d in review['local_directories']}
    need(len(directory_ids)==len(review['local_directories']) and set(review['question_directories'])==set(by_q)
         and set(review['question_directories'].values())<=directory_ids, 'LOCAL_DIRECTORY_SCOPE')
    need(set(review['asset_directories'])=={a['asset_id'] for a in source['assets']}
         and set(review['asset_directories'].values())<=directory_ids, 'LOCAL_PAGE_DIRECTORY_SCOPE')
    context = {'config_version':'b-source-confirmation-revision.2','a_consumer_commit':A_COMMIT,
               'current_review_sha256':sha(encode(review)), 'predecessor_bundle_sha256':sha(files['bundle.json'])}
    if generation is None:
        generation = {'created_at':datetime.now(timezone.utc).isoformat(timespec='seconds'), **context}
    need(set(generation)=={'created_at',*context} and all(generation[k]==v for k,v in context.items())
         and datetime.fromisoformat(generation['created_at'].replace('Z','+00:00')).tzinfo is not None, 'REVISION_GENERATION_CONTEXT')
    output = {n:b for n,b in files.items() if n not in ('bundle.json','delivery.json','current-review.json','generation.json','pending-review.json')}
    for name in ('bundle.json','delivery.json','current-review.json','generation.json','pending-review.json'):
        if name in files:
            output['history/v2/'+name] = files[name]
    output['current-review.json'] = encode(review)
    output['generation.json'] = encode(generation)
    policy = copy.deepcopy(original['policies'][0])
    policy['revision'] += 1
    policy['source_notes'] = ['B content and selected source associations are confirmed. Joint execution policy and full-page target coverage remain outside this bounded revision.']
    policy = seal(policy)
    pref = {k:policy[k] for k in ('policy_id','revision','content_hash')}
    new = {}

    def artifact(kind, payload, dependencies):
        value = copy.deepcopy(old[kind])
        value.update(revision=value['revision']+1, run_id='b-confirmed-'+sha(canonical(generation))[:24],
                     created_at=generation['created_at'], input_refs=[ref(a) for a in dependencies], payload=payload)
        value['producer'].update(module='b-source-confirmed-revision',implementation_version='1',
                                  config_version=generation['config_version'],policy_versions=[pref])
        new[kind] = seal(value)
        return new[kind]

    source = copy.deepcopy(source)
    source['directories'] = copy.deepcopy(review['local_directories'])
    for mapping in source['external_page_mappings']:
        mapping['directory_id'] = review['asset_directories'][mapping['asset_id']]
        mapping['mapping_status'] = 'CONFIRMED'
    source['history'] = source.get('history',[]) + [dict(resource=dict(path=n,sha256=sha(b),media_type='application/json'),
        quality='REVIEWED',reason='Exact predecessor bytes retained; historical HOLD/UNRESOLVED is not the active B content decision.')
        for n,b in output.items() if n.startswith('history/v2/')]
    src = artifact('SourceBundle',source,[])
    evidence = copy.deepcopy(evidence)
    evidence['source'] = ref(src)
    for region in evidence['regions']:
        region['certainty'] = 'CONFIRMED'
        if region['region_id'] in changes_by_region:
            region['text']=changes_by_region[region['region_id']]['after_text']
    for clue in evidence['coverage_clues']:
        if clue['disposition']=='EXCLUDED':
            clue['region_ids'] = []
    ev = artifact('EvidenceBundle',evidence,[src])
    graph = copy.deepcopy(graph)
    graph.update(source=ref(src),evidence=ref(ev))
    for q in graph['questions']:
        q['directory_id'] = review['question_directories'][q['question_id']]
    for relation in graph['answer_relations']:
        relation.update(status='SELECTED',selected_fragment_ids=by_q[relation['question_id']]['selected_fragment_ids'])
    graph['identity_notes'] = 'Stable B local identities and single shared material retained. SELECTED is explicit B model source confirmation, separate from human, A-owner or platform acceptance. HISTORICAL region source preserves frozen model transcription provenance.'
    gr = artifact('QuestionGraph',graph,[src,ev])
    check = copy.deepcopy(old['CheckReport']['payload'])
    check.update(subject=ref(gr),graph=ref(gr),policy=pref,decision='HOLD',
                 reason='B source content ready with no content issues; PRE_APPLY joint execution policy and full-page target coverage remain separate.')
    for result in check['checks']:
        if result['check_id']=='answer_matching':
            result.update(outcome='PASS',reason='Every selected answer is explicitly source-confirmed by B model review; no per-question human signature gate.')
        elif result['check_id']=='policy':
            result.update(outcome='UNAVAILABLE',reason='Formal platform policy adoption is not asserted by this B content revision.')
        elif result['check_id']=='coverage':
            result.update(outcome='UNAVAILABLE',reason='Bounded declared tasks complete; whole-page/full-chapter target coverage is not asserted.')
    check['issues'] = [dict(issue_id='preapply-policy-scope',code='POLICY_UNRESOLVED',scope_type='scope',scope_id=gr['scope_id'],
        evidence_refs=['ev-current-review'],severity='info',blocks=['PLAN','APPLY'],
        suggested_strategy=dict(strategy_id='RECONCILE',max_attempts=0,max_cost=0.0),
        reason='B content is ready. Joint platform policy adoption and whole-page target coverage are separate PRE_APPLY scope limits.')]
    artifact('CheckReport',check,[src,ev,gr])
    records = copy.deepcopy(original['evidence'])
    for record in records:
        resource = record['resource']
        resource['sha256'] = sha(output[resource['path']])
        if record['evidence_id']=='ev-current-review':
            record['description'] = 'Explicit current B model source confirmation; predecessor content and historical states remain preserved byte for byte.'
    output['bundle.json'] = encode(dict(format_version='c01-exchange-1',evidence=records,policies=[policy],artifacts=list(new.values())))
    d = {k:copy.deepcopy(old_d[k]) for k in ('bindings','source_proofs','q16_task_map','q16_formula_slots','reading_task_answers') if k in old_d}
    for binding in d['bindings']:
        if binding['region_id'] in changes_by_region:
            binding['runs']=copy.deepcopy(changes_by_region[binding['region_id']]['after_runs'])
    d['source_text_changes']=copy.deepcopy(changes)
    d.update(schema_version='b-source-confirmed-c01-revision/0.1',a_consumer_commit=A_COMMIT,
        generation_sha256=sha(output['generation.json']),current_review_sha256=sha(output['current-review.json']),
        basis_sha256=sha(output['basis.json']),c01_graph_ref=ref(gr),decision='HOLD',b_content_ready=True,b_content_issues=[],
        b_source_confirmation='B_MODEL_SOURCE_CONFIRMED',historical_pending_is_not_current_content_gate=True,
        human_verified=False,a_owner_acceptance=False,business_acceptance=False,platform_actions=[],
        source_windows_are_platform_frames=False,chapter_denominator=None)
    output['delivery.json'] = encode(d)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--source',type=Path)
    group.add_argument('--frozen',type=Path)
    parser.add_argument('--review',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    if args.frozen:
        frozen = load_files(args.frozen)
        files = predecessor_files(frozen)
        review = json.loads(frozen['current-review.json'])
        generation = json.loads(frozen['generation.json'])
    else:
        need(args.review is not None,'REVIEW_REQUIRED')
        files,review,generation = load_files(args.source),json.loads(args.review.read_bytes()),None
    blobs = revise(files,review,generation)
    args.out.mkdir(parents=True,exist_ok=False)
    for name,raw in blobs.items():
        path = args.out/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
    print(json.dumps(dict(files=len(blobs),bundle_sha256=sha(blobs['bundle.json']),b_content_ready=True,decision='HOLD')))


if __name__=='__main__':
    main()
