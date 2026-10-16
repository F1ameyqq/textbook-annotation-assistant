"""Replay source-backed image regions and composed continuation boundaries.

No network, OCR engine, site action or graph merge. Structural continuation
acceptance remains an unverified proposal, not business/content acceptance.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from annotation.recognition.baseline import digest,load_source
from annotation.recognition.boundary import build_boundary_candidate,validate_boundary
from annotation.recognition.image_regions import build_image_regions,validate_image_regions
from annotation.recognition.continuation import build_continuation_proof,validate_continuation
from replay_recovery_b import replay
from verify_continuation_b import prepare_continuation,load_continuation_fixture


def run(fixture, adjacent_source=None, source=None):
    fixture=Path(fixture)
    e,review,g,check=replay(fixture)
    if source:
        manifest,_=load_source(Path(source))
        if sorted(manifest['assets'],key=lambda a:a['reading_order']) != sorted((p['source'] for p in e['payload']['pages']),key=lambda a:a['reading_order']):
            raise ValueError('source descriptors differ from recovery evidence')
    cf,original_check=load_continuation_fixture(fixture/'continuation-evidence.json',adjacent_source)
    extension=prepare_continuation(e,g,cf)
    extended,graph=extension['evidence'],extension['graph']
    def read(name):return json.loads((fixture/name).read_text(encoding='utf-8'))
    image_review=read('image-region-review.json')
    images=build_image_regions(extended,image_review,fixture)
    image_check=validate_image_regions(extended,images,image_review,fixture)
    heading=read('boundary-review.json')
    if heading['content_hash'] != digest(heading['payload']):raise ValueError('boundary review hash mismatch')
    h=heading['payload']
    page=next(p for p in extended['payload']['pages'] if p['asset_id']==h['asset']['asset_id'])
    if (page['source']['sha256'],page['source']['width'],page['source']['height']) != (h['asset']['sha256'],h['asset']['width'],h['asset']['height']):
        raise ValueError('boundary review source mismatch')
    active={l['line_id']:l for l in page['ocr_lines']}
    for member in h['members']:
        line=active[member['line_id']]
        if line['text']!=member['raw_text'] or line['bbox']!=member['bbox']:
            raise ValueError('frozen boundary OCR reference changed')
    boundary=build_boundary_candidate(extended,asset_id=h['asset']['asset_id'],line_spans=h['line_spans'],source_bbox=h['source_bbox'],review_basis=h['review_basis'])
    boundary_check=validate_boundary(extended,boundary)
    p=extension['proof']['payload']
    proof=build_continuation_proof(extended,graph,from_answer_id=p['from_answer_id'],to_asset_id=p['to_asset']['asset_id'],
                                  to_line_ids=p['to_line_ids'],source_tail_line_id=p['source_tail_line_id'],
                                  adjacency_receipt=extension['adjacency_receipt'],review_basis=p['review_basis'],
                                  image_regions=images,boundary_candidate=boundary)
    continuation=validate_continuation(extended,graph,proof,image_review=image_review,capture_root=fixture)
    summary={'decision':'HOLD','source_assets':len(extended['payload']['pages']),'continuation_prefix_lines':len(p['to_line_ids']),
             'image_regions':len(images['payload']['regions']),'image_region_check_accepted':image_check['payload']['accepted'],
             'image_semantics_verified':False,'boundary_check_accepted':boundary_check['payload']['accepted'],
             'continuation_status':continuation['payload']['status'],'continuation_structurally_accepted':continuation['payload']['accepted'],
             'continuation_issue_codes':sorted({i['code'] for i in continuation['payload']['issues']}),
             'original_adjacent_validation':original_check,'original_five_assets_revalidated':bool(source),
             'graph_merge_performed':False,'platform_actions':0,'business_acceptance':False,'ocr_rerun':False}
    return {'evidence.json':extended,'question-graph-source-extension.json':graph,'recovery-check.json':check,
            'image-regions.json':images,'image-check.json':image_check,'boundary-candidate.json':boundary,
            'boundary-check.json':boundary_check,'continuation-proof.json':proof,'continuation-check.json':continuation,'summary.json':summary}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/book46007447')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--adjacent-source',type=Path)
    parser.add_argument('--source',type=Path)
    args=parser.parse_args()
    if args.out.exists():parser.error('--out must be a new directory')
    try:results=run(args.fixture,args.adjacent_source,args.source)
    except (ValueError,KeyError,OSError) as exc:parser.error(str(exc))
    args.out.mkdir(parents=True)
    for name,value in results.items():(args.out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results['summary.json'],ensure_ascii=True))


if __name__=='__main__':main()
