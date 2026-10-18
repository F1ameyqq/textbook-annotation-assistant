"""Preserve reviewer evidence and release facts, without further business calls."""
import json
from pathlib import Path
import shutil
from audit import SNAP,HERE,EV,GROUPS,load,sha,save,tables,process_audit

run=SNAP/'docs/evidence/A03/T1/execution/validation/independent-01'
semantic=load(EV/'independent-semantic-audit.json')
assert semantic['status']=='INDEPENDENT_STATIC_AUDIT_PASS'
materialization=load(EV/'source-materialization.json')
for p,e in materialization['files'].items():
    assert sha((SNAP/p).read_bytes())==e['materialized_sha256'],'frozen file mutated: '+p
processes={}
for label,root in [('business-descendants',run),('reviewer-roots',EV/'processes'),('bootstrap-git',EV/'bootstrap-processes')]:
    for name,value in process_audit(root).items():processes[label+'/'+name]=value
owners={}
for name in GROUPS:
    stage='after-release' if name=='L1' else 'after-reconcile'
    db=run/'cases'/name/'captures'/stage/'runtime.sqlite3'
    book,=tables(db)['tables']['books']
    assert book['owner'] is None and book['pid'] is None and book['lease']==0 and book['phase']=='RELEASED'
    owners[name]=dict(final_stage=stage,owner=book['owner'],pid=book['pid'],lease=book['lease'],phase=book['phase'],
        generation=book['generation'],runtime_sha256=sha(db.read_bytes()),
        owner_release_sha256=sha((run/'cases'/name/'owner-release.json').read_bytes()))
shutil.copytree(run,EV/'validation/independent-01',copy_function=shutil.copyfile)
shutil.copytree(HERE/'fixture-independent-01',EV/'fixture-independent-01',copy_function=shutil.copyfile)
for name in ('bootstrap.py','audit.py','runner.py','preflight.py','provenance.py','finalize.py'):
    p=HERE/name
    with (EV/name).open('xb') as f:f.write(p.read_bytes())
for name in ('capture.py','fixture.py'):
    with (EV/('frozen-'+name)).open('xb') as f:f.write((SNAP/'examples/a03/T1-capture'/name).read_bytes())
save(EV/'release-proof.json',dict(status='ALL_RECORDED_OWN_POPEN_REAPED_AND_SIX_OWNERS_RELEASED',
    processes=processes,process_count=len(processes),owners=owners,keepers='all recorded keeper threads stopped/joined without error',
    global_PID_scan=False,historical_PIDs_killed=False,business_reruns=0,reviewer_driver_corrections=0,
    retained_frozen_input_files_verified_unchanged=len(materialization['files']),
    current_review_roots='Tool-launched short-lived wrapper roots exited zero; nested Popen raw streams and wait records retained',
    field_reset='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'))
print(json.dumps(dict(processes=len(processes),owners=len(owners),business_stage_databases=semantic['database_originals'],
    frozen_files_unchanged=len(materialization['files']),evidence=str(EV)),indent=2))
