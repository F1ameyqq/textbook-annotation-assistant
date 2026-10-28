"""B read-only harness for the unmodified, Git-byte-pinned A C01 consumer.

No A business entry, target, planner, dispatcher, or website module is invoked.
"""
from pathlib import Path
import argparse,hashlib,json,sys

PINS_SHA='01b1c99be3c9bdf9eab858e4690afa59e5d50676c6539076e86753ab11614691'
A_COMMIT='edf125961be9cdc1642652c038d99872b1c8cdc7'
sha=lambda b:hashlib.sha256(b).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--a-source',required=True,type=Path)
    p.add_argument('--pins',required=True,type=Path);p.add_argument('--delivery',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    args=p.parse_args();pins_raw=args.pins.read_bytes().replace(b'\r\n',b'\n')
    if sha(pins_raw)!=PINS_SHA:raise ValueError('FIXED_A_PINS')
    pins=json.loads(pins_raw)
    if pins['commit']!=A_COMMIT or len(pins['members'])!=91:raise ValueError('FIXED_A_COMMIT')
    for member in pins['members']:
        path=member['path']
        if not path.startswith('src/') or '..' in path.split('/'):raise ValueError('A_SOURCE_PATH')
        raw=(args.a_source/path).read_bytes();oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if len(raw)!=member['size'] or oid!=member['sha']:raise ValueError('A_SOURCE_GIT_BYTES:'+path)
    sys.path.insert(0,str((args.a_source/'src').resolve()))
    from annotation.contracts import load_bundle
    bundle=load_bundle(args.delivery/'bundle.json',verify_assets=True).model_dump(mode='json')
    from verify_q16_reading_b import verify
    content=verify(args.delivery,bundle)
    by_kind={a['kind']:a for a in bundle['artifacts']};graph=by_kind['QuestionGraph']['payload'];ev=by_kind['EvidenceBundle']['payload']
    regions={r['region_id']:r for r in ev['regions']};fragments={f['fragment_id']:f for f in graph['fragments']}
    def readback(ids):
        return [dict(fragment_id=fid,role=fragments[fid]['role'],content_type=fragments[fid]['content_type'],
                     regions=[dict(region_id=rid,text=regions[rid]['text'],box=regions[rid]['box']) for rid in fragments[fid]['region_ids']]) for fid in ids]
    projection=[]
    for q,relation in zip(graph['questions'],graph['answer_relations']):
        projection.append(dict(question_id=q['question_id'],external_refs=q['external_refs'],cross_page=q['cross_page'],
            question=readback(q['fragment_ids']),shared_material=readback(q['shared_fragment_ids']),
            answer_candidates=readback(relation['candidate_fragment_ids']),relation_status=relation['status']))
    receipt=dict(status='A_FIXED_C01_READONLY_CONSUMED_HOLD',a_commit=A_COMMIT,a_sources_verified=91,
        bundle_sha256=sha((args.delivery/'bundle.json').read_bytes()),content_audit=content,readback=projection,
        producer_vs_consumer_full_object_equal=bundle==json.loads((args.delivery/'bundle.json').read_bytes()),
        actual_a_owner_acceptance=False,independent_human_acceptance=False,business_acceptance=False,
        native_b_graph_check_consumer_claimed=False,planning_or_simulation_executed=False,website_requests=0,decision='HOLD')
    if not receipt['producer_vs_consumer_full_object_equal']:raise ValueError('CONSUMER_LOSS')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:v for k,v in receipt.items() if k!='readback'}))

if __name__=='__main__':main()
