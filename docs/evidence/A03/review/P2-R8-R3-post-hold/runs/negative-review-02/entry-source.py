# -*- coding: utf-8 -*-
"""Read finite N3-N5 results and exact live input snapshots; no product re-evaluation."""
import json
from pathlib import Path
from evidence import OUT,WORK,EV,TARGET,INDEX,load,raw,sha,canon,write,author_read
root=Path(load(OUT/'independent-run.json')['run_root']).resolve()
def own(path):
    p=Path(path);p=p if p.is_absolute() else root/path;p=p.resolve();assert p.is_relative_to(root);return p.read_bytes()
labels={'author':(author_read,EV+'validation/native-r3-01/'),'independent':(own,str(root)+'/')}
reviews=[]
for label,(read,prefix) in labels.items():
    local=json.loads(read(prefix+'local-result.json'));n3=json.loads(read(prefix+'N3-result.json'));n4=json.loads(read(prefix+'N4-result.json'));n5=json.loads(read(prefix+'N5-result.json'))
    assert {r['control']:r['actual_code'] for r in local['controls']}=={'POST_HOLD_without_hold':'NATIVE_PRE_CONTEXT_INVALID','stale_generation':'OWNER_GENERATION_STALE','real_pending_intent':'BOOK_WRITE_PAUSED'}
    assert (local['pending'],local['permits'],local['target_effects'])==(1,0,0)
    assert {r['control'] for r in n3}=={'source_integrity','structure','answer_matching','coverage','policy'}
    for r in n3:
        assert [k for k,v in r['comparison'].items() if v=='FAIL']==[r['control']] and r['admitted'] is False and r['effects']==0
    assert {r['control']:r['actual_code'] for r in n4['refusals']}=={'missing_run':'NATIVE_RUN_HANDLE_REQUIRED','serialized_run':'NATIVE_RUN_HANDLE_REQUIRED',
      'foreign_run':'NATIVE_RUN_HANDLE_REQUIRED','foreign_observation':'NATIVE_PRE_OBSERVATION_FOREIGN'}
    assert n4['permit_count']==n4['effect_count']==0
    assert len(n5['refusals'])==7 and {r['actual_code'] for r in n5['refusals']}=={'NATIVE_CONTEXT_REQUIRED'}
    legacy=raw('examples/a03/P2-R2-proposal/candidate-final/original/new-authored-initial-a.json')
    assert n5['legacy_1_1_read_sha256']==sha(legacy) and json.loads(legacy)['format_version']=='a03-exchange-1'
    assert n5['R7_static_validated'] and not n5['legacy_1_1_archive_validator_acceptance_claim']
    controls=load(OUT/(label+'-control-database-review.json'))['records']
    foreign=[r for r in controls if '/N4-' in r['source'].replace('\\','/') and '/runtime/' in r['source'].replace('\\','/')]
    assert len(foreign)==2
    for r in foreign:assert r['counts']['plans']==r['counts']['intents']==r['counts']['permits']==0 and r['runs'][0]['status']=='ADMITTED'
    pending=[r for r in controls if '/local-pending/runtime/' in r['source'].replace('\\','/')]
    assert len(pending)==1 and pending[0]['pending']==1 and pending[0]['counts']['permits']==0
    bindings=[json.loads(r['runs'][0]['binding']) for r in foreign]
    assert bindings[0]['registry_id']!=bindings[1]['registry_id'] and bindings[0]['registration_id']!=bindings[1]['registration_id']
    reviews.append({'label':label,'local':local,'N3':n3,'N4':n4,'N5':n5,'N4_registered_bindings':bindings,
      'N3_scope':'direct five-check comparison; admission was not invoked; no N3 databases or target effects',
      'N5_scope':'actual legacy JSON read and validated R7 static object; no 1.1 archive-validator acceptance'})
trace=load(OUT/'N3-readonly-trace.json')['actual_input_snapshots'];assert len(trace)==5
source_proofs=[]
for r in trace:
    data=load(OUT/r['input_file']);assert sha(canon(data))==r['input_canonical_sha256']==r['compare_input_canonical_sha256']
    assert r['schema_returned'] and not r['schema_exception']
    assert [k for k,v in r['comparison_result'].items() if v=='FAIL']==[r['control']]
    for artifact in data['artifacts']:assert sha(canon({k:v for k,v in artifact.items() if k!='content_hash'}))==artifact['content_hash']
    source=next(a for a in data['artifacts'] if a['kind']=='SourceBundle');files=[]
    for asset in source['payload']['assets']:
        p=Path(r['asset_root'])/asset['path'];assert p.resolve().is_relative_to(root)
        assert sha(p.read_bytes())==asset['sha256'];files.append({'path':str(p),'sha256':asset['sha256'],'bytes':p.stat().st_size})
    assert not list(Path(r['asset_root']).rglob('*.sqlite3'))
    source_proofs.append({'control':r['control'],'actual_input':r['input_file'],'canonical_sha256':r['input_canonical_sha256'],
      'schema_completed_before_comparison':True,'artifact_hashes_recomputed_and_verified':True,'actual_assets':files,
      'comparison':r['comparison_result'],'admission_attempted':False})
write(OUT/'negative-controls-review.json',{'status':'FINITE_N3_N4_N5_AND_LOCAL_BOUNDARIES_VERIFIED','results':reviews,'actual_N3_inputs':source_proofs,
 'native_product_reexecutions_by_auditor':0,'N6_N7_run':False,
 'reviewer_preparation_failure':'negative-review-01 used slash-only matching on Windows control source paths; v2 checks the already-saved SQL rows with normalized path identity, no DB or product rerun',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'status':'FINITE_N3_N4_N5_AND_LOCAL_BOUNDARIES_VERIFIED','N3_actual_inputs':len(trace),'N4_exact_refusals':4,'N5_exact_refusals':7}))
