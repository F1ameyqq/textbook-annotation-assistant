"""Apply and independently audit a continuation to a new local graph version.

All operations are local. Graph changes remain unverified/HOLD; no platform plan
or website action is produced. Rollback restores the archived prior graph only
when the derived graph is unchanged and its evidence revision still matches.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from annotation.recognition.baseline import digest
from annotation.recognition.continuation_apply import apply_continuation,rollback_continuation
from annotation.recognition.continuation_quality import audit_continuation_application
from replay_structure_b import run as replay_structure


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def reference(value):
    return {key:value[key] for key in ('artifact_id','revision','content_hash')}


def run(fixture, adjacent_source=None, source=None):
    fixture=Path(fixture)
    structure=replay_structure(fixture,adjacent_source,source)
    evidence=structure['evidence.json']
    base=structure['question-graph-source-extension.json']
    proof=structure['continuation-proof.json']
    review=read(fixture/'image-region-review.json')
    derived=apply_continuation(evidence,base,proof,image_review=review,capture_root=fixture)
    check=audit_continuation_application(evidence,base,derived,proof,image_review=review,capture_root=fixture)
    receipt_payload={'evidence_ref':reference(evidence),'base_graph_ref':reference(base),
                     'derived_graph_ref':reference(derived),'proof_ref':reference(proof),'decision':'HOLD','platform_actions':[]}
    receipt={'schema_version':'b-continuation-application-receipt-trial/0.1','kind':'LocalContinuationApplicationReceiptTrial',
             'artifact_id':'local-application-receipt-'+digest(receipt_payload)[:24],'revision':1,
             'book_id':evidence['book_id'],'scope_id':evidence['scope_id'],
             'content_hash':digest(receipt_payload),'payload':receipt_payload}
    restored=rollback_continuation(evidence,derived,expected_graph_ref=receipt_payload['derived_graph_ref'])
    if restored!=base:
        raise ValueError('rollback differs from the exact original graph')
    answer_id=proof['payload']['from_answer_id']
    answer=next(a for a in derived['payload']['answers'] if a['answer_id']==answer_id)
    summary={'operation':'LOCAL_GRAPH_CONTINUATION','decision':'HOLD','schema':derived['schema_version'],
             'independent_audit_accepted':check['payload']['accepted'],
             'source_trace_fragments':len(answer['fragments']),'render_regions':len(answer['render_regions']),
             'structural_complete':answer['structural_complete'],'transcription_verified':False,
             'questions':len(derived['payload']['questions']),'answers':len(derived['payload']['answers']),
             'local_graph_applied':True,
             'rollback_verified':True,'business_acceptance':False,'platform_actions':0,'website_requests':0,
             'ocr_rerun':False,'original_validation':structure['summary.json']}
    return {'evidence.json':evidence,'base-question-graph.json':base,'question-graph.json':derived,
            'continuation-proof.json':proof,'application-check.json':check,
            'application-receipt.json':receipt,
            'rollback-verification.json':{'restored_equals_original':True,'base_payload_hash':base['content_hash'],
                                          'restored_payload_hash':restored['content_hash'],
                                          'restored_complete_object_digest':digest(restored),'platform_actions':[]},
            'summary.json':summary}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/book46007447')
    parser.add_argument('--source',type=Path)
    parser.add_argument('--adjacent-source',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--rollback-from',type=Path,help='unchanged derived graph to restore locally')
    parser.add_argument('--evidence',type=Path,help='same saved evidence revision, required for rollback')
    parser.add_argument('--receipt',type=Path,help='separately saved original application receipt, required for rollback')
    args=parser.parse_args()
    if args.out.exists():parser.error('--out must be a new directory')
    try:
        if args.rollback_from:
            if not args.evidence or not args.receipt:parser.error('--rollback-from requires --evidence and --receipt')
            evidence,receipt=read(args.evidence),read(args.receipt)
            if (receipt.get('schema_version')!='b-continuation-application-receipt-trial/0.1'
                    or receipt.get('content_hash')!=digest(receipt.get('payload'))
                    or receipt['payload']['evidence_ref']!=reference(evidence)
                    or (receipt.get('book_id'),receipt.get('scope_id'))!=(evidence['book_id'],evidence['scope_id'])):
                raise ValueError('application receipt is invalid or bound to another evidence revision')
            restored=rollback_continuation(evidence,read(args.rollback_from),expected_graph_ref=receipt['payload']['derived_graph_ref'])
            if reference(restored)!=receipt['payload']['base_graph_ref']:
                raise ValueError('restored graph differs from the original application receipt')
            summary={'operation':'LOCAL_GRAPH_ROLLBACK','restored':True,'schema':restored['schema_version'],
                     'content_hash':restored['content_hash'],'decision':'HOLD','platform_actions':0}
            results={'question-graph.json':restored,'summary.json':summary}
        else:
            if args.evidence or args.receipt:parser.error('--evidence/--receipt are only used with --rollback-from')
            results=run(args.fixture,args.adjacent_source,args.source)
    except (ValueError,KeyError,OSError) as exc:parser.error(str(exc))
    args.out.mkdir(parents=True)
    for name,value in results.items():
        (args.out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results['summary.json'],ensure_ascii=True))
    if results['summary.json'].get('independent_audit_accepted') is False:
        parser.exit(1,'Independent application audit rejected the local graph; inspect application-check.json.\n')


if __name__=='__main__':main()
