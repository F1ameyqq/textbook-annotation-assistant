"""Reconcile observed results and inspect only this review's recorded PIDs."""
import ctypes,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
OUT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
initial=read(OUT/'independent-cases/results.json');targeted=read(OUT/'pixel-diagnostics-cases/results.json')
minimum=read(OUT/'minimal-repro/result.json');observed=read(OUT/'pixel-diagnostics-cases/short-row-observation.json')
assert minimum['defect_reproduced'] and observed['public_cli_returncode']==0 and observed['public_loader_accepted']
assert observed['independent_row_check']['actual_scanline_bytes']==112 and observed['independent_row_check']['expected_scanline_bytes']==3248
assert observed['decoders']=={'pillow_structure':'PASS','pillow_full_load':'PASS','opencv_full_decode':'REJECTED'}
assert initial['passed']==11 and initial['failed']==4 and targeted['passed']==3 and targeted['failed']==1
regression=read(OUT/'regression/a04-unittest.json');contracts=read(OUT/'regression/contracts-unittest.json')
fix1=read(OUT/'guard-correction/affected-four-unittest.json');fix2=read(OUT/'guard-correction-remaining/remaining-three-unittest.json')
assert regression['tests_run']==152 and regression['errors']==2 and len(regression['skipped'])==1
assert contracts['tests_run']==70 and contracts['errors']==8
assert fix1['status']=='PASS' and fix1['tests_run']==4
assert fix2['status']=='PASS' and fix2['tests_run']==3 and len(fix2['skipped'])==1
pidset=set();group_records=[]
for p in OUT.glob('*/process-results.json'):
    group=read(p);pidset.add(group['runner_pid']);assert group['all_reaped']
    for child in group['children']:pidset.add(child['pid']);assert child['wait_complete'] and not child['timed_out']
    group_records.append({'path':p.relative_to(OUT).as_posix(),'data':group})
guards=[]
for folder in [OUT/'guard-records',OUT/'minimal-repro/guard-records']:
    for p in folder.glob('*.json'):
        g=read(p);assert not g['blocked_events'] and g['exit_hook_reached'];pidset.add(g['pid'])
        guards.append({'path':p.relative_to(OUT).as_posix(),'pid':g['pid'],'allowed_local_python_starts':len(g['local_python_starts'])})
for source in [initial,targeted]:
    assert source['all_recorded_children_reaped']
    for child in source['children']:pidset.add(child['pid']);assert child['reaped']
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];kernel.OpenProcess.restype=ctypes.c_void_p
kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)];kernel.GetExitCodeProcess.restype=ctypes.c_int
kernel.CloseHandle.argtypes=[ctypes.c_void_p];kernel.CloseHandle.restype=ctypes.c_int
pidchecks=[]
for pid in sorted(pidset):
    assert pid!=os.getpid()
    handle=kernel.OpenProcess(0x1000,False,pid)
    if handle:
        code=ctypes.c_uint32();ok=kernel.GetExitCodeProcess(handle,ctypes.byref(code));kernel.CloseHandle(handle)
        assert ok;running=code.value==259;record={'pid':pid,'running':running,'exit_code':code.value}
    else:
        error=ctypes.get_last_error();assert error==87,(pid,error)
        record={'pid':pid,'running':False,'open_process_result':'NO_SUCH_PROCESS'}
    assert not record['running'],record
    pidchecks.append(record)
save(OUT/'self-release.json',{'at':datetime.now(timezone.utc).isoformat(),
 'inspection_scope':'Only PIDs recorded by this review runtime/guard/children; no OS-wide scan',
 'worker_pid_observations':pidchecks,'all_recorded_workers_exited':True,
 'process_groups':group_records,'guard_exit_records':guards,
 'browser_started':False,'login_or_book_actions':0,'actual_authorized_profile_opened_or_inspected':False,
 'authorized_credentials_read':False,'network_or_platform_requests':0,'model_calls':0,'paid_cost':0,
 'scope_note':'Initial guard TypeError happened before process creation; Node probe and cmd junction fallback excluded. Git object reads are metadata tooling, not platform actions.'})
classifications={
 'N02-valid-CRC-zlib-short-pixels':'Original Pillow-reject precondition was wrong. Preserved FAIL; byte-count/OpenCV discrepancy later confirmed real public-gate defect D01.',
 'U01-damaged-after-parse-before-source':'Original strict RESOURCE_INVALID assertion failed; actual RESOURCE_MISMATCH rejected changed bytes. True decode-reject recheck passes with invalid filter in D03.',
 'U03-public-parse-copy-race':'Actual final bundle published from incomplete-row PNG. Same residual decoder gap; retained.',
 'L01-artificial-hash-only-forgery':'Manually resealed counterexample explicitly marked non-A04 output. Source also misses same row gap; not counted as legal product publication.'}
matrix=[
 {'clause':1,'status':'REWORK','detail':'Original 24-byte PNG and bad JPEG/PGM/CRC/filter are rejected; CRC/zlib-valid missing-row PNG is still published and loader-accepted.'},
 {'clause':2,'status':'PASS','detail':'Reviewer PNG, progressive JPEG, ASCII P2 and binary P5: public CLI, relocated public loader, full decode, actual dimensions/hash/path bindings.'},
 {'clause':3,'status':'REWORK','detail':'Invalid-filter decode and valid-byte digest rechecks reject before history; incomplete-row input bypasses pixel gate and public-copy recheck.'},
 {'clause':4,'status':'PASS','detail':'ACCEPTED dependency c6bebdf...; source coordinates NOT_PERFORMED, acceptance NOT_ASSERTED, no network. R1 stale status fixed.'},
 {'clause':5,'status':'PASS_WITH_SCOPE_EXCLUSIONS','detail':'Unique A04 151 passed + 1 Node probe excluded; contracts 69 passed + 1 cmd-junction test excluded. Old R1 unchanged full matrix not rerun.'},
 {'clause':6,'status':'PASS','detail':'158-entry frozen manifest and 148 old execution entries verified, old 5/227 review manifests preserved, raw failures and own-process release retained.'}]
save(OUT/'review-verdict.json',{'target_commit':'76898657e76ac2db071327e90c6ca5031d17571f',
 'review_workflow_commit':'e7ff892776f53636fcddfe136d1659204c4ff738','R2_offline':'REWORK','whole_A04':'BLOCKED',
 'open_finding':'A04-CR2-01','resolved_specific_R1_counterexample':'24-byte PNG rejected; general full-original integrity requirement still incomplete',
 'state_semantics':'R1 stale dependency-waiting text fixed in local CLI',
 'raw_independent_results':{'initial':{'PASS':11,'FAIL':4},'targeted':{'PASS':3,'FAIL':1}},
 'initial_failure_reconciliation':classifications,'handoff_clause_matrix':matrix,
 'regression_unique_results':{'A04':{'PASS':151,'SKIPPED':1},'contracts':{'PASS':69,'SKIPPED':1}},
 'test_guard_correction':'Windows subprocess audit executable=None fixed; only affected Python CLI tests rerun; original 2/8 errors not erased',
 'real_scenarios':{f'R{i:02d}':'BLOCKED_NOT_RUN' for i in range(1,7)},
 'D01_project':'Coordinator separately accepted/integrated c78c8a123437e6c53096e0c48f1dd14aad10c2c3; not reverified here',
 'integration_or_dependency_release':False,'network_browser_profile_or_model_actions':0})
import cv2,numpy
save(OUT/'environment.json',{'python':sys.version,'executable':sys.executable,
 'Pillow':importlib.metadata.version('Pillow'),'Pydantic':importlib.metadata.version('pydantic'),
 'OpenCV':cv2.__version__,'NumPy':numpy.__version__,'dependencies_installed_or_changed':False,
 'additional_decoder_use':'Local cv2.imdecode only; no browser, network or model'})
print(json.dumps({'R2_offline':'REWORK','whole_A04':'BLOCKED','own_pids_exited':len(pidchecks),
 'guard_records':len(guards),'findings':['A04-CR2-01']}))
