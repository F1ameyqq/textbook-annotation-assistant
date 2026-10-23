"""Execute exact frozen launcher under frozen-file and inert process adapters.
No subprocess, native Job, actual profile metadata, browser or network is used.
The lifecycle checks here concern launcher decisions, not OS cleanup proof.
"""
import sys
sys.path.insert(0,'D:/1800/docs/evidence/A28-independent/code-r1-review')
from control_support import *
import contextlib, io, importlib.util, subprocess
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from annotation.runtime.usense_live import core
ROOT=P/'launcher-controls';ROOT.mkdir()
source=frozen('/launch_production_r1.py').read_bytes()
assert sha(source)=='62088f27c5c2dfc432ecd60497f64d4ca696cb390ac372a7593814c11208f527'
delivery=load('/fixed-delivery-r1.json');fixed_raw=frozen('/fixed-delivery-r1.json').read_bytes()
assert core.implementation_digest()==delivery['implementation_sha256']
profile=Path(delivery['profile']);ledger=profile.parent/'usense-existing-ledger'
real_exists=Path.exists;real_resolve=Path.resolve;real_iterdir=Path.iterdir
cases=[]
def run_case(name,expected_error=None,*,shared=None,release=True):
 base=shared or ROOT/name
 if not shared:base.mkdir()
 stamp=datetime.now(timezone.utc)
 authority={'schema':'A28ProductionAuthority/v1','status':'AUTHORIZED','operation':'A28_COMPLETE_LESSON_PRODUCTION',
  'authority_id':'SYNTHETIC-INDEPENDENT-NO-LIVE-'+name,'fixed_delivery_sha256':sha(fixed_raw),'commit':delivery['commit'],
  'targets_manifest_sha256':delivery['targets_manifest']['sha256'],'limits':delivery['production_limits'],
  'not_before':(stamp-timedelta(seconds=10)).isoformat(),'expires_at':(stamp+timedelta(seconds=600)).isoformat(),
  'profile':delivery['profile'],'profile_fingerprint':delivery['profile_fingerprint'],'transport':delivery['transport'],'tls':delivery['tls']}
 if name=='retry-limit-expanded':authority['limits']={**authority['limits'],'retries':1}
 if name=='expired-window':authority['expires_at']=(stamp-timedelta(seconds=1)).isoformat()
 if name=='profile-mismatch':authority['profile_fingerprint']='0'*64
 ap=base/('authority-'+name+'.json');aref=dump(ap,authority)
 overrides={norm(base/'fixed-delivery-r1.json'):fixed_raw,norm(base/'targets-r1.json'):frozen('/targets-r1.json').read_bytes()}
 if name=='source-byte-change':
  k=norm(member('/known-old-info-r1/q22_info.json')['source_path']);overrides[k]=data[k]+b' '
 if name=='manifest-byte-change':
  k=norm(delivery['raw_manifest']['path']);overrides[k]=data[k]+b' '
 calls=[];commands=[];stdout=io.StringIO();error=None;exit_code=None
 def git_run(cmd,**kwargs):
  commands.append(cmd)
  assert cmd[:3]==['git','-c','core.longpaths=true'] and kwargs['capture_output'] is True
  assert cmd[3:] in (['rev-parse','HEAD'],['status','--porcelain'])
  raw=(delivery['commit']+'\n').encode() if cmd[3]=='rev-parse' else (b' M synthetic\n' if name=='dirty-product' else b'')
  return SimpleNamespace(stdout=raw,returncode=0)
 def holder_run(cmd,cwd,prefix,seconds):
  assert (base/'production-outer-01/launch-once.json').is_file()
  spent=json.loads((base/'production-outer-01/launch-once.json').read_bytes())
  assert spent['attempts_spent']==1 and spent['attempts_remaining']==0
  assert 0<seconds<=900 and '--preflight-only' not in cmd and cmd.count('--manifest')==1
  assert cmd[cmd.index('--manifest')+1]==str(base/'targets-r1.json')
  calls.append({'argv':cmd,'cwd':str(cwd),'prefix':str(prefix),'timeout':seconds,'durable_marker':spent})
  return {'exit_code':0,'owned_os_release_confirmed':release,'SYNTHETIC_NO_PROCESS_STARTED':True}
 loader=SimpleNamespace(exec_module=lambda module:setattr(module,'run',holder_run))
 def spec(name_arg,path):
  assert name_arg=='a28_holder' and norm(path)==norm(delivery['owned_process']['path'])
  return SimpleNamespace(loader=loader)
 def exists(p):
  if norm(p).startswith(norm(profile)):return p==profile
  return real_exists(p)
 def resolve(p,*args,**kwargs):
  if 'browser-profiles' in norm(p) or 'worktrees/b-latest' in norm(p):return p
  return real_resolve(p,*args,**kwargs)
 def iterdir(p):
  if norm(p)==norm(ledger):
   values=[Path(k) for k in delivery['ledger_before']]
   if name=='unexpected-ledger-file':values.append(base/'synthetic-added-ledger.json')
   return iter(values)
  return real_iterdir(p)
 if name=='unexpected-ledger-file':dump(base/'synthetic-added-ledger.json',{'synthetic_extra':True})
 before_sys_path=list(sys.path)
 try:
  with frozen_io(overrides),ExitStack() as stack:
   stack.enter_context(patch.object(Path,'exists',exists));stack.enter_context(patch.object(Path,'resolve',resolve));stack.enter_context(patch.object(Path,'iterdir',iterdir))
   stack.enter_context(patch.object(subprocess,'run',git_run))
   stack.enter_context(patch.object(core,'profile_identity',lambda _: (profile,delivery['profile_fingerprint'])))
   stack.enter_context(patch.object(importlib.util,'spec_from_file_location',spec));stack.enter_context(patch.object(importlib.util,'module_from_spec',lambda _:SimpleNamespace()))
   stack.enter_context(patch.object(sys,'argv',['launch_production_r1.py','--authority',str(ap),'--authority-sha256',aref['sha256']]))
   stack.enter_context(contextlib.redirect_stdout(stdout))
   exec(compile(source,str(frozen('/launch_production_r1.py')),'exec'),{'__file__':str(base/'launch_production_r1.py'),'__name__':'__main__'})
 except SystemExit as e:exit_code=e.code
 except RuntimeError as e:error=str(e)
 finally:sys.path[:]=before_sys_path
 if expected_error:
  assert error==expected_error and not calls,(name,error,exit_code,calls)
  if not shared:assert not (base/'production-outer-01').exists()
 else:assert error is None and exit_code==(0 if release else 2) and len(calls)==1,(name,error,exit_code,calls)
 record={'case':name,'status':'PASS','expected_rejection':expected_error,'observed_error':error,'exit_code':exit_code,'git_adapter_calls':commands,'holder_adapter_calls':calls,
  'stdout':stdout.getvalue(),'exact_launcher_sha256':sha(source),'platform_processes':0,'real_profile_metadata_reads':0}
 dump(ROOT/(name+'-result.json'),record);cases.append({'name':name,'status':'PASS','holder_calls':len(calls),'error':error,'exit_code':exit_code})
 return base
base=run_case('normal')
run_case('replay-existing-output','NO_RETRY_OUTPUT_EXISTS',shared=base)
for name,error in [('retry-limit-expanded','AUTHORITY_LIMITS'),('expired-window','AUTHORITY_WINDOW'),('profile-mismatch','AUTHORITY_PROFILE'),
 ('source-byte-change','SOURCE_BYTES_CHANGED'),('manifest-byte-change','RAW_MANIFEST_HASH'),('dirty-product','CLEAN_FIXED_PRODUCT_REQUIRED'),
 ('unexpected-ledger-file','LEDGER_CHANGED_BEFORE_LAUNCH')]:run_case(name,error)
run_case('holder-release-unconfirmed',release=False)
dump(O/'launcher-controls.json',{'schema':'A28IndependentLauncherControls/v1','status':'PASS','launcher_sha256':sha(source),'cases':cases,
 'exact_source_executed':True,'implementation_digest_actual_isolated_check':True,'OS_profile_and_process_adapters':'SYNTHETIC',
 'real_profile_identity_or_OS_release_proven':False,'platform_requests':0})
print(json.dumps({'status':'PASS','launcher_cases':len(cases)}))
