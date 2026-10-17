"""R3 bounded conclusion, imports, and creation-time-aware own PID closeout."""
import importlib.metadata,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
from process_identity import probe
OUT=Path(__file__).resolve().parents[1];F=Path('D:/1800/.local/stages/A04-review/coordinate-R3/frozen source with spaces')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
exact=read(OUT/'exact-replay/result.json');reg=read(OUT/'initial/regression-result.json');ind=read(OUT/'independent-cases/results.json')
assert exact['sha256']=='205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd'
assert exact['public_cli_returncode']==2 and not exact['defect_reproduced'] and not exact['final_bundle_created']
assert not (OUT/'exact-replay/output').exists() and not (OUT/'exact-replay/input/evidence').exists()
assert reg['status']=='PASS' and reg['tests_run']==70 and not reg['skipped']
assert ind['passed']==26 and ind['failed']==0 and ind['all_children_reaped']
identities={};groups=[]
def add(identity):identities[(identity['pid'],identity['creation_filetime'])]={'pid':identity['pid'],'creation_filetime':identity['creation_filetime']}
for p in [OUT/'initial/process-results.json',OUT/'independent/process-results.json']:
    g=read(p);add(g['runner_identity']);assert g['all_reaped']
    for job in g['jobs']:add(job['identity']);assert job['reaped'] and job['returncode']==0 and not job['timed_out']
    groups.append({'path':p.relative_to(OUT).as_posix(),'data':g})
guards=[]
for p in (OUT/'guard-records').glob('*.json'):
    g=read(p);assert not g['blocked_events'] and g['exit_hook_reached'];add(g)
    guards.append({'path':p.relative_to(OUT).as_posix(),'pid':g['pid'],'creation_filetime':g['creation_filetime'],'local_python_starts':len(g['local_python_starts'])})
for g in ind['children']:add(g['identity']);assert g['reaped']
observations=[probe(identities[key]) for key in sorted(identities)]
assert all(x['original_process_exited'] for x in observations)
save(OUT/'self-release.json',{'at':datetime.now(timezone.utc).isoformat(),'scope':'Only recorded own PID+creation-time identities; no enumeration/profile scan',
 'observations':observations,'all_original_workers_exited':True,'recorded_identities':len(observations),'guard_exit_records':guards,
 'groups':groups,'browser_network_platform_login_profile_credentials_model_book_actions':0,
 'PID_reuse_policy':'Later creation time is recorded as different process; never stopped, cleaned or treated as original worker',
 'actual_authorized_profile_current_state':'NOT_INSPECTED'})
sys.path.insert(0,str(F/'src'))
from annotation.source.usense import parser,png_pixels as gate
from annotation.contracts import load_bundle
paths={'source_parser':parser.__file__,'png_gate':gate.__file__,'public_loader':load_bundle.__code__.co_filename}
for path in paths.values():Path(path).resolve().relative_to(F.resolve())
save(OUT/'environment.json',{'python':sys.version,'executable':sys.executable,'Pillow':importlib.metadata.version('Pillow'),
 'Pydantic':importlib.metadata.version('pydantic'),'actual_import_paths':paths,'dependencies_installed_or_changed':False,
 'PNG_limits':{n:getattr(gate,n) for n in ['MAX_PNG_BYTES','MAX_PNG_PIXELS','MAX_PNG_DIMENSION','MAX_PNG_SCANLINE_BYTES','MAX_PNG_CHUNKS']}})
save(OUT/'review-verdict.json',{'target_commit':'6c8137a4fadddc01a47906d564ab3460277c8958',
 'implementation_commit':'81d62255b545b88f344849d08011a2a859c49c5e','review_workflow_commit':'d834bf531f95abac7ed30b89b3ca55105fa6f491',
 'reasoning_effort_requested':'xhigh','OFFLINE_R3':'ACCEPTED','A04_OVERALL':'BLOCKED','findings':[],
 'accepted_scope':'Fixed R3 PNG scanline completeness repair, public source/prepublication gates, representative static layouts, existing JPEG/PGM and bounded resource behavior only',
 'exact_unchanged_reproducer':'Wrapper0 / public CLI2 / no output or source history / SHA-bound original 180byte case',
 'independent_cases':26,'independent_failures':0,'independent_representative_layouts':7,'scoped_regression_tests':70,
 'public_positive_packages':8,'public_runtime_children':len(ind['children']),
 'not_run':['Node deadline','Windows junction','whole previous test matrix','full configured 64/128MiB resource stress','real R01-R06','D01 installation revalidation'],
 'compatibility_tightening':['APNG explicitly unsupported','Trailing PNG content rejected','Unknown critical/chunk/stream/invalid palette states fail closed as documented'],
 'non_assertions':['All PNG ancillary semantics','Universal decoder equivalence','Content correctness','Whole-book source completeness','Current real coordinates or counts','B confirmation','Save/OCR/recovery/cost acceptance'],
 'handoff_clauses':[{'clause':1,'status':'PASS','evidence':['exact-replay/result.json','initial/process-results.json']},
 {'clause':2,'status':'PASS_WITH_DECLARED_LIMITS','evidence':['independent-cases/results.json','environment.json']},
 {'clause':3,'status':'PASS','evidence':['independent-cases/U-same-size-swap/result.json','independent-cases/U-public-copy-swap/result.json','independent-cases/results.json']},
 {'clause':4,'status':'PASS_WITH_EXCLUSIONS','evidence':['initial/regression-result.json','independent-cases/results.json']},
 {'clause':5,'status':'COMPLETE_BOUNDED_REVIEW','evidence':['review-verdict.json']}],
 'real_scenarios':{f'R{i:02d}':'BLOCKED_NOT_RUN' for i in range(1,7)},'release_downstream_or_integrate':False,
 'all_prior_evidence_retained':True,'paid_model_calls':0,'paid_model_cost':0})
print(json.dumps({'OFFLINE_R3':'ACCEPTED','A04_OVERALL':'BLOCKED','independent':26,'regression':70,
 'own_process_identities_exited':len(observations),'guard_records':len(guards),'PID_reuse_observations':sum(x['observation']=='PID_REUSED_LATER_NO_ACTION' for x in observations)}))
