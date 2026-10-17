"""Explain existing four results using pinned source/data; NO Package calls."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];EX=Path(__file__).resolve().parent
OUT=ROOT/'docs/evidence/A03/execution/P2-R4-bridge-registration'
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(json.dumps(v,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
rows=[]
for record in load(OUT/'four-package-results.json')['checks']:
    info=load(ROOT/record['case_path']);bundle=load(ROOT/info['bundle']);index={x['artifact_id']:x for x in bundle['artifacts']}
    pr=info['prefix_resource'];source_file=next(r['file']for r in info['resources']if r['logical']==pr['path']);prefix=load(ROOT/source_file)
    event=prefix['frames'][-1]['event'];p=event['payload'];source=index[p['source_ref']['artifact_id']];snap=index[p['snapshot_ref']['artifact_id']];owner=index['r4-registration-prefix-consumer']
    scoped=(source['kind']=='SourceBundle'and snap['kind']=='PlatformSnapshot'and source['book_id']==snap['book_id']==owner['book_id']and source['scope_id']==snap['scope_id']==p['scope_id'])
    global_scoped=(source['kind']=='SourceBundle'and snap['kind']=='PlatformSnapshot'and source['book_id']==snap['book_id']==None and source['scope_id']==snap['scope_id']==p['scope_id'])
    rows.append({'case':record['case'],'actual':record['actual'],'source_ref':p['source_ref'],'snapshot_ref':p['snapshot_ref'],
      'source_book':source['book_id'],'snapshot_book':snap['book_id'],'actual_consumer_book':owner['book_id'],'global_pool_book':None,
      'source_scope':source['scope_id'],'snapshot_scope':snap['scope_id'],'payload_scope':p['scope_id'],
      'existing_guard_in_actual_consumer_context':scoped,'existing_guard_in_global_pool_context':global_scoped,
      'snapshot_target_id':snap['payload']['target_id'],'event_target_id':event['target_key']['target_id'],
      'target_tuple_matches':snap['payload']['target_id']==event['target_key']['target_id'],
      'semantic_assessment':'positive blocked by contextless global evidence traversal'if record['case']=='registration-positive'else'mismatch reached in actual consumer'if not scoped else'target mismatch masked by global pool context failure; not a proved target rejection'})
source_rows=[]
for relative,needle in [('examples/a03/P2-R3-evidence-closure/closure.py',"source['book_id']==snapshot['book_id']==book"),('examples/a03/P2-R2-proposal/check.py',"self.scan(e['resource'],'E:'+e['evidence_id'],None,None")]:
    p=ROOT/relative;raw=p.read_bytes();lines=raw.decode('utf8').splitlines();hits=[{'line':i+1,'text':line}for i,line in enumerate(lines)if needle in line];assert hits
    source_rows.append({'path':relative,'sha256':hashlib.sha256(raw).hexdigest(),'evidence':hits})
v={'status':'MINIMAL_RESIDUAL_FREEZE_NO_MORE_PACKAGE_RUNS','method':'static predicate/control-flow reasoning from pinned source and already-produced four packages; no extra validator invocation',
   'observed':'positive rejected at FRAME_REGISTRATION_BINDING; three controls same code; prepare process exit1 retained',
   'source_evidence':source_rows,'guard_inputs':rows,
   'local_choices_not_implemented':[
     'Separate contextless global EvidenceRecord byte/graph traversal from actual Artifact/frame contextual validation; do not create a book=None consumer. Preserve all real-context checks and mixed DAG. Do not merely waive equality when book is None.',
     'If coordinator instead restricts placement, explicitly approve a direct Resource consumer field (for example a separately authored unverified Source.history journal reference) and a new bounded package; no rerouting/retesting in this turn.',
     'After the positive entry is unblocked, independently assess Snapshot.target_id against canonical event/registration target; current target negative is masked, not accepted as a valid rejection.'],
   'package_calls_total':4,'old_36_matrix_runs':0,'product_calls':0,'native_sessions':0,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'minimal-residual-assessment.json',v);print(json.dumps({'status':v['status'],'extra_package_calls':0,'source_predicate_context_conflict':True}))
