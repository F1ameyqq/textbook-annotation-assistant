"""Pure static five-way comparison, never emits native PASS or run authority."""
import hashlib
import json

def compare(bundle,root,oracle):
    by={a['kind']:a for a in bundle['artifacts']}
    source=by['SourceBundle']['payload'];evidence=by['EvidenceBundle']['payload'];graph=by['QuestionGraph']['payload'];policy=bundle['policies'][0]
    asset=source['assets'][0];raw=(root/asset['path']).read_bytes();tokens=raw.decode('ascii').split()
    o=oracle['source_integrity'];pixels=[int(x) for x in tokens[4:]]
    expected=[0 if any(x0<=x<x1 and y0<=y<y1 for x0,y0,x1,y1 in o['black_rectangles']) else 255 for y in range(o['height']) for x in range(o['width'])]
    source_ok=(tokens[:4]==['P2',str(o['width']),str(o['height']),str(o['maxval'])] and pixels==expected and hashlib.sha256(raw).hexdigest()==asset['sha256'] and asset['width']==o['width'] and asset['height']==o['height'] and source['pages_expected']==source['pages_acquired']==[asset['asset_id']])
    q=graph['questions'];f=graph['fragments'];r=evidence['regions'];a=graph['answer_relations'];c=evidence['coverage_clues']
    structure_ok=(len(q)==oracle['structure']['question_count'] and len(r)==oracle['structure']['region_count'] and [x['box']['bbox'] for x in r]==oracle['structure']['boxes'] and [x['role'] for x in f]==oracle['structure']['roles'] and q[0]['shared_fragment_ids']==[] and not q[0]['cross_page'] and q[0]['fragment_ids']==[x['fragment_id'] for x in f] and [x['region_ids'] for x in f]==[[x['region_id']] for x in r])
    answer_ids=[x['fragment_id'] for x in f if x['role']==oracle['answer_matching']['selected_role']]
    answer_ok=(len(a)==oracle['answer_matching']['relation_count'] and a[0]['status']==oracle['answer_matching']['status'] and len(a[0]['candidate_fragment_ids'])==oracle['answer_matching']['candidate_count'] and a[0]['selected_fragment_ids']==a[0]['candidate_fragment_ids']==answer_ids and a[0]['question_id']==q[0]['question_id'])
    coverage_ok=(source['scope_manifest']==[x['question_id'] for x in q] and len(q)==oracle['coverage']['question_count'] and len(source['pages_expected'])==oracle['coverage']['page_count'] and len(c)==oracle['coverage']['clue_count'] and [x['disposition'] for x in c]==oracle['coverage']['dispositions'] and {rid for x in c for rid in x['region_ids']}=={x['region_id'] for x in r})
    policy_ok=(policy['role_mapping']==oracle['policy']['role_mapping'] and policy['option_grouping']==oracle['policy']['option_grouping'] and all(x['question_type']==oracle['policy']['question_type'] for x in q))
    return {name:{'comparison':'STATIC_MATCH' if good else 'STATIC_MISMATCH','native_qualification':False} for name,good in [('source_integrity',source_ok),('structure',structure_ok),('answer_matching',answer_ok),('coverage',coverage_ok),('policy',policy_ok)]}
