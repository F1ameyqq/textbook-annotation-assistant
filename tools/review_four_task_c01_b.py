"""Freeze a verified four-task baseline, then consume and compare a real new C01.

All paths are explicit. No exporter, public contract, browser or writer is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

A_COMMIT = 'c5aefbc8e995c410b3babf74a251f05a7724a1c2'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
canonical = lambda v: json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def read(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ValueError('DUPLICATE_JSON_KEY:' + key)
            result[key]=value
        return result
    return json.loads(Path(path).read_bytes(),object_pairs_hook=unique)


def write(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)


def diff(old,new,path=''):
    """Complete type-sensitive JSON differences, including array order and extras."""
    if type(old) is not type(new):
        return [dict(path=path or '/',op='replace',old=old,new=new,reason='type')]
    if isinstance(old,dict):
        changes=[]
        for key in sorted(old.keys() | new.keys()):
            here=path+'/'+key.replace('~','~0').replace('/','~1')
            if key not in new:changes.append(dict(path=here,op='remove',old=old[key]))
            elif key not in old:changes.append(dict(path=here,op='add',new=new[key]))
            else:changes.extend(diff(old[key],new[key],here))
        return changes
    if isinstance(old,list):
        changes=[]
        for i in range(max(len(old),len(new))):
            here=path+'/'+str(i)
            if i>=len(new):changes.append(dict(path=here,op='remove',old=old[i]))
            elif i>=len(old):changes.append(dict(path=here,op='add',new=new[i]))
            else:changes.extend(diff(old[i],new[i],here))
        return changes
    return [] if old==new else [dict(path=path or '/',op='replace',old=old,new=new)]


def parts(bundle):
    return {a['kind']:a['payload'] for a in bundle['artifacts']}


def expectations(bundle,sidecar):
    p=parts(bundle);g=p['QuestionGraph']
    q16=next(q for q in g['questions'] if q['external_refs']['printed_number']=='16')
    reading=[q for q in g['questions'] if q['question_id']!=q16['question_id']]
    blanks=[r for b in sidecar['bindings'] for r in b['runs'] if r['format']=='blank']
    return dict(q16_id=q16['question_id'],reading_ids=[q['question_id'] for q in reading],
        shared_fragment_ids=reading[0]['shared_fragment_ids'],
        question_fragments={q['question_id']:q['fragment_ids'] for q in g['questions']},
        answer_candidates={r['question_id']:r['candidate_fragment_ids'] for r in g['answer_relations']},
        blank_ids=[b['blank_id'] for b in blanks],
        formula_slots=[dict(slot=x['slot'],expected_latex=x['expected_latex'],source_bbox=x['source_bbox']) for x in sidecar['q16_formula_slots']],
        originals={a['asset_id']:a['sha256'] for a in p['SourceBundle']['assets']})


def audit(bundle,sidecar,expected,require_selected=False,identity_map=None):
    identity_map=identity_map or {}
    mapping=lambda namespace,value:identity_map.get(namespace,{}).get(value,value)
    p=parts(bundle);g=p['QuestionGraph'];ev=p['EvidenceBundle']
    qs={q['question_id']:q for q in g['questions']};fs={f['fragment_id']:f for f in g['fragments']};rs={r['region_id']:r for r in ev['regions']}
    relations={r['question_id']:r for r in g['answer_relations']}
    checks=[]
    def check(name,value,detail=None):checks.append(dict(check=name,passed=bool(value),detail=detail))
    q16=mapping('question_ids',expected['q16_id']);reading=[mapping('question_ids',q) for q in expected['reading_ids']]
    check('four_independent_task_ids',len(qs)==4 and set(qs)=={q16,*reading} and len(reading)==3 and len(set(reading))==3)
    if not all(q in qs for q in [q16]+reading):
        return checks
    check('q16_is_ordinary_printed_16',qs[q16]['external_refs']['printed_number']=='16')
    check('q16_has_no_reading_shared_material',qs[q16]['shared_fragment_ids']==[])
    shared=[mapping('fragment_ids',f) for f in expected['shared_fragment_ids']]
    check('eight_shared_material_fragments',len(shared)==8 and len(set(shared))==8 and all(f in fs and fs[f]['role']=='shared_material' for f in shared))
    for qid in reading:
        q=qs[qid]
        check('shared_material_exactly_attached_'+qid,q['shared_fragment_ids']==shared)
        check('reading_no_invented_printed_number_'+qid,q['external_refs']['printed_number'] is None)
        check('shared_not_duplicated_as_stem_'+qid,not(set(shared)&set(q['fragment_ids'])))
    for old_id,old_stems in expected['question_fragments'].items():
        qid=mapping('question_ids',old_id)
        check('stem_identity_'+qid,qs[qid]['fragment_ids']==[mapping('fragment_ids',f) for f in old_stems])
        owned=[b for b in sidecar['bindings'] if b.get('owner_id')==qid and b.get('fragment_id') is not None]
        answer_ids=[b['fragment_id'] for b in owned if b['role'] in ['answer','explanation']]
        relation=relations.get(qid)
        check('one_answer_relation_'+qid,len([r for r in g['answer_relations'] if r['question_id']==qid])==1)
        if relation:
            candidates=[mapping('fragment_ids',f) for f in expected['answer_candidates'][old_id]]
            check('answer_candidate_identity_'+qid,relation['candidate_fragment_ids']==candidates)
            check('source_binding_answer_ownership_'+qid,answer_ids==relation['candidate_fragment_ids'])
            if require_selected:
                check('selected_own_answers_'+qid,relation['status']=='SELECTED' and relation['selected_fragment_ids']==candidates)
            check('answer_source_page_'+qid,all(rs[rid]['box']['image']['asset_id']==mapping('asset_ids','viewer-173') for fid in relation['candidate_fragment_ids'] if fid in fs for rid in fs[fid]['region_ids']))
    check('four_relations_only',len(g['answer_relations'])==4)
    for binding in sidecar['bindings']:
        rid=binding['region_id'];region=rs.get(rid)
        check('binding_region_present_'+rid,region is not None)
        if region is None:continue
        rendered=''.join((run.get('token','____') if run['format']=='blank' else '\\('+run['text']+'\\)' if run['format']=='latex' else run['text']) for run in binding['runs'])
        check('bound_runs_match_region_'+rid,region['text']==(None if region['content_type']=='image' else rendered))
        fid=binding.get('fragment_id')
        if fid is not None:
            check('binding_fragment_role_'+rid,fid in fs and fs[fid]['region_ids']==[rid] and fs[fid]['role']==binding['role'])
    for qid in [q16]+reading:
        check('unknown_platform_identity_'+qid,qs[qid]['external_refs']['platform_question_id'] is None and qs[qid]['external_refs']['platform_order'] is None)
        ids=qs[qid]['fragment_ids']+qs[qid]['shared_fragment_ids']
        pages={rs[rid]['box']['image']['asset_id'] for fid in ids if fid in fs for rid in fs[fid]['region_ids']}
        check('independent_source_page_'+qid,pages=={mapping('asset_ids','viewer-15' if qid==q16 else 'viewer-13')})
    blanks=[r for b in sidecar['bindings'] for r in b['runs'] if r['format']=='blank']
    check('six_blank_ids_preserved',[r.get('blank_id') for r in blanks]==[mapping('blank_ids',bid) for bid in expected['blank_ids']] and len(blanks)==6)
    check('all_question_blanks_still_null',all(r.get('value','MISSING') is None for r in blanks))
    slots=[dict(slot=x['slot'],expected_latex=x['expected_latex'],source_bbox=x['source_bbox']) for x in sidecar.get('q16_formula_slots',[])]
    check('eleven_formula_slots_preserved',len(slots)==11 and slots==expected['formula_slots'])
    original={a['asset_id']:a['sha256'] for a in p['SourceBundle']['assets']}
    check('original_image_hashes_preserved',original=={mapping('asset_ids',k):v for k,v in expected['originals'].items()})
    check('four_artifacts_only',len(bundle['artifacts'])==4 and set(p)=={'SourceBundle','EvidenceBundle','QuestionGraph','CheckReport'})
    check('no_execution_artifact',not(set(p)&{'ApplyPlan','PlatformSnapshot','ExecutionReceipt'}))
    return checks


def snapshot(folder,bundle):
    files={p.name:read(p) for p in sorted(Path(folder).glob('*.json')) if p.name!='bundle.json'}
    return dict(bundle=bundle,sidecars=files)


def audit_local_resources(folder,bundle,sidecar):
    from PIL import Image
    folder=Path(folder).resolve();p=parts(bundle)
    assets={a['asset_id']:a for a in p['SourceBundle']['assets']}
    regions={r['region_id']:r for r in p['EvidenceBundle']['regions']}
    def local(name):
        path=(folder/name).resolve()
        if not path.is_relative_to(folder):raise ValueError('SOURCE_PROOF_PATH_ESCAPE')
        return path
    checks=[]
    for proof in sidecar['source_proofs']:
        region=regions[proof['region_id']];asset=assets[region['box']['image']['asset_id']]
        with Image.open(local(asset['path'])) as im:original=im.convert('RGB')
        file=local(proof['path'])
        with Image.open(file) as im:actual=im.convert('RGB')
        bbox=region['box']['bbox'];integer_bbox=all(int(v)==v for v in bbox)
        crop=original.crop(tuple(int(v) for v in bbox))
        passed=integer_bbox and sha(file.read_bytes())==proof['sha256'] and sha(crop.tobytes())==proof['rgb_sha256'] and crop.size==actual.size and crop.tobytes()==actual.tobytes()
        checks.append(dict(check='source_crop_pixels_'+proof['region_id'],passed=passed,detail=None))
    checks.append(dict(check='every_region_has_one_crop_proof',passed=len(sidecar['source_proofs'])==len(regions) and {p['region_id'] for p in sidecar['source_proofs']}==set(regions),detail=None))
    return checks


def prepare(args):
    receipt=read(args.receipt);bundle=read(args.delivery/'bundle.json')
    if receipt['a_commit']!=A_COMMIT or receipt['bundle_sha256']!=sha((args.delivery/'bundle.json').read_bytes()) or not receipt['complete_object_equal'] or canonical(receipt['full_object'])!=canonical(bundle):
        raise ValueError('PREPARE_REQUIRES_ACTUAL_FIXED_A24_FULL_READBACK')
    if args.out.resolve().is_relative_to(args.delivery.resolve()):raise ValueError('OUTPUT_MUST_NOT_MODIFY_SOURCE_DELIVERY')
    args.out.mkdir(parents=True,exist_ok=False)
    sidecar=read(args.delivery/'delivery.json');expected=expectations(bundle,sidecar)
    checks=audit(bundle,sidecar,expected)
    if any(not x['passed'] for x in checks):raise ValueError('HISTORICAL_SCOPE_AUDIT_FAILED')
    write(args.out/'baseline.json',snapshot(args.delivery,bundle));write(args.out/'expectations.json',expected)
    manifest=dict(a_commit=A_COMMIT,historical_bundle_sha256=receipt['bundle_sha256'],actual_complete_object_sha256=receipt['complete_object_sha256'],
        files={name:sha((args.out/name).read_bytes()) for name in ['baseline.json','expectations.json']},
        audit=checks,baseline_relations=[dict(question_id=r['question_id'],status=r['status']) for r in parts(bundle)['QuestionGraph']['answer_relations']],
        status='HISTORICAL_BASELINE_PREPARED_REAL_NEW_PACKAGE_NOT_CONSUMED',platform_requests=0,dispatch=False)
    write(args.out/'baseline-manifest.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['files','audit','baseline_relations']}))


def compare(args):
    manifest=read(args.prepared/'baseline-manifest.json')
    if manifest['a_commit']!=A_COMMIT:raise ValueError('FIXED_A24_REQUIRED')
    for name,digest in manifest['files'].items():
        if name not in ['baseline.json','expectations.json'] or sha((args.prepared/name).read_bytes())!=digest:raise ValueError('PREPARED_BASELINE_CHANGED')
    baseline=read(args.prepared/'baseline.json');expected=read(args.prepared/'expectations.json')
    if sha(canonical(baseline['bundle']))!=manifest['actual_complete_object_sha256']:raise ValueError('BASELINE_FULL_OBJECT_CHANGED')
    if args.out.resolve().is_relative_to(args.new_delivery.resolve()) or args.out.resolve().is_relative_to(args.prepared.resolve()):raise ValueError('OUTPUT_MUST_NOT_MODIFY_SOURCE_OR_BASELINE')
    if sha((args.new_delivery/'bundle.json').read_bytes())!=args.new_bundle_sha256:raise ValueError('NEW_FIXED_BUNDLE_SHA256_MISMATCH')
    label_baseline=None
    if bool(args.label_baseline)!=bool(args.label_baseline_manifest_sha256):raise ValueError('LABEL_BASELINE_AND_FIXED_MANIFEST_SHA256_REQUIRED_TOGETHER')
    if args.label_baseline:
        if args.out.resolve().is_relative_to(args.label_baseline.resolve()):raise ValueError('OUTPUT_MUST_NOT_MODIFY_LABEL_BASELINE')
        fixed=args.label_baseline/'baseline-manifest.json'
        if sha(fixed.read_bytes())!=args.label_baseline_manifest_sha256:raise ValueError('LABEL_BASELINE_MANIFEST_CHANGED')
        label_manifest=read(fixed)
        if label_manifest['a_commit']!=A_COMMIT:raise ValueError('LABEL_BASELINE_FIXED_A24_REQUIRED')
        for name,digest in label_manifest['files'].items():
            if name not in ['baseline.json','expectations.json'] or sha((args.label_baseline/name).read_bytes())!=digest:raise ValueError('LABEL_BASELINE_FILE_CHANGED')
        label_baseline=read(args.label_baseline/'baseline.json')
        if sha(canonical(label_baseline['bundle']))!=label_manifest['actual_complete_object_sha256']:raise ValueError('LABEL_BASELINE_FULL_OBJECT_CHANGED')
        selected=parts(label_baseline['bundle'])['QuestionGraph']['answer_relations']
        if len(selected)!=4 or any(r['status']!='SELECTED' for r in selected):raise ValueError('LABEL_BASELINE_MUST_BE_ADJACENT_FOUR_SELECTED_REVISION')
    args.out.mkdir(parents=True,exist_ok=False)
    receipt=args.out/'actual-new-full-readback.json'
    command=[sys.executable,'-B','-X','utf8',str(args.consumer.resolve()),'--a-source',str(args.a_source.resolve()),'--pins',str(args.pins.resolve()),
        '--pins-sha256',args.pins_sha256,'--bundle',str((args.new_delivery/'bundle.json').resolve()),'--expected-questions','4','--out',str(receipt.resolve())]
    result=subprocess.run(command,cwd=args.out,capture_output=True,text=True,encoding='utf-8')
    (args.out/'fixed-a24-read.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:
        write(args.out/'comparison.json',dict(status='REAL_NEW_PACKAGE_CONTRACT_REJECTED',exit_code=result.returncode,success_receipt_created=receipt.exists(),last_error=result.stderr.splitlines()[-1] if result.stderr else None,command=command,platform_requests=0,dispatch=False))
        return 1
    got=read(receipt);new=snapshot(args.new_delivery,got['full_object'])
    if got['bundle_sha256']!=args.new_bundle_sha256 or sha((args.new_delivery/'bundle.json').read_bytes())!=args.new_bundle_sha256:raise ValueError('NEW_BUNDLE_CHANGED_DURING_READ')
    identity=read(args.identity_map) if args.identity_map else {}
    checks=audit(new['bundle'],new['sidecars']['delivery.json'],expected,True,identity)
    checks.extend(audit_local_resources(args.new_delivery,new['bundle'],new['sidecars']['delivery.json']))
    label_audit=None
    if label_baseline or args.label_source_manifest:
        from verify_q16_label_delta_b import audit_labels_only,audit_historical_source_manifest,bound_digest_checks
        label_audit=audit_labels_only(label_baseline,new,diff) if label_baseline else audit_historical_source_manifest(baseline,new,diff)
        label_audit['checks'].extend(bound_digest_checks(args.new_delivery,new,lambda p:p.read_bytes(),sha))
        label_audit['actual_new_package_consumed']=True
        label_audit['status']='Q16_THREE_LABELS_ONLY' if all(c['passed'] for c in label_audit['checks']) else 'Q16_LABEL_DELTA_REJECTED'
        checks.extend(label_audit['checks'])
    changes=diff(baseline,new)
    old_arts={a['kind']:a for a in baseline['bundle']['artifacts']};new_arts={a['kind']:a for a in new['bundle']['artifacts']}
    revisions=[]
    for kind in sorted(old_arts):
        old=old_arts[kind];current=new_arts[kind]
        same=old['artifact_id']==current['artifact_id']
        valid=not same or (old['content_hash']==current['content_hash'] and old['revision']==current['revision']) or current['revision']>old['revision']
        checks.append(dict(check='immutable_revision_'+kind,passed=valid,detail=None))
        revisions.append(dict(kind=kind,same_artifact_id=same,old={k:old[k] for k in ['artifact_id','revision','content_hash']},new={k:current[k] for k in ['artifact_id','revision','content_hash']}))
    report=dict(status='REAL_NEW_A24_READ_AND_FOUR_TASK_MAPPING_PASS' if all(c['passed'] for c in checks) else 'REAL_NEW_A24_READ_MAPPING_REVIEW_REQUIRED',
        a_commit=A_COMMIT,old_bundle_sha256=manifest['historical_bundle_sha256'],new_bundle_sha256=got['bundle_sha256'],complete_object_sha256=got['complete_object_sha256'],
        complete_object_equal=True,identity_map=identity,checks=checks,failures=[c for c in checks if not c['passed']],
        artifact_revisions=revisions,full_field_delta=changes,field_delta_count=len(changes),label_only_audit=label_audit,
        platform_requests=0,dispatch=False,human_acceptance=False,a_owner_acceptance=False,command=command)
    write(args.out/'comparison.json',report)
    print(json.dumps({k:report[k] for k in ['status','new_bundle_sha256','complete_object_equal','field_delta_count','failures']}))
    return 0 if not report['failures'] else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__);modes=parser.add_subparsers(dest='mode',required=True)
    prep=modes.add_parser('prepare');prep.add_argument('--receipt',type=Path,required=True);prep.add_argument('--delivery',type=Path,required=True);prep.add_argument('--out',type=Path,required=True)
    comp=modes.add_parser('compare')
    for key in ['prepared','new-delivery','a-source','pins','consumer','out']:comp.add_argument('--'+key,type=Path,required=True)
    comp.add_argument('--pins-sha256',required=True);comp.add_argument('--identity-map',type=Path)
    comp.add_argument('--new-bundle-sha256',required=True)
    label_mode=comp.add_mutually_exclusive_group(required=True)
    label_mode.add_argument('--label-baseline',type=Path)
    label_mode.add_argument('--label-source-manifest',action='store_true')
    comp.add_argument('--label-baseline-manifest-sha256')
    args=parser.parse_args();return prepare(args) if args.mode=='prepare' else compare(args)


if __name__=='__main__':raise SystemExit(main())
