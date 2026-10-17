# -*- coding: utf-8 -*-
"""Bounded normal control plus one independent no-intent ABSENT positive path.

Never invokes the prohibited authorization field-reset probe or author test suite.
"""
from pathlib import Path
import ctypes,json,os,subprocess,sys,time,traceback
from ctypes import wintypes as W
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2';STAGE=OUT/'input/checkout'
OWN=[];RESULTS=[]
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
class Job:
 """Confine this one owned worker and descendants; no process enumeration."""
 def __init__(self,process):
  k=ctypes.WinDLL('kernel32',use_last_error=True);self.k=k
  k.CreateJobObjectW.argtypes=[W.LPVOID,W.LPCWSTR];k.CreateJobObjectW.restype=W.HANDLE
  k.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,W.LPVOID,W.DWORD];k.SetInformationJobObject.restype=W.BOOL
  k.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE];k.AssignProcessToJobObject.restype=W.BOOL
  k.QueryInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,W.LPVOID,W.DWORD,W.LPVOID];k.QueryInformationJobObject.restype=W.BOOL
  k.CloseHandle.argtypes=[W.HANDLE];k.CloseHandle.restype=W.BOOL
  class Basic(ctypes.Structure):
   _fields_=[('per_process',ctypes.c_longlong),('per_job',ctypes.c_longlong),('flags',W.DWORD),('minimum',ctypes.c_size_t),('maximum',ctypes.c_size_t),('active',W.DWORD),('affinity',ctypes.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]
  class IO(ctypes.Structure):_fields_=[(x,ctypes.c_ulonglong) for x in ('r_ops','w_ops','o_ops','r_bytes','w_bytes','o_bytes')]
  class Extended(ctypes.Structure):_fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
  self.handle=k.CreateJobObjectW(None,None);assert self.handle,ctypes.get_last_error()
  info=Extended();info.basic.flags=0x2000
  assert k.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)),ctypes.get_last_error()
  assert k.AssignProcessToJobObject(self.handle,W.HANDLE(int(process._handle))),ctypes.get_last_error()
 def accounting(self):
  class Account(ctypes.Structure):_fields_=[(x,ctypes.c_longlong) for x in ('user','kernel','period_user','period_kernel')]+[(x,W.DWORD) for x in ('faults','total','active','terminated')]
  a=Account();assert self.k.QueryInformationJobObject(self.handle,1,ctypes.byref(a),ctypes.sizeof(a),None),ctypes.get_last_error()
  return {'total_processes':a.total,'active_processes':a.active,'terminated_processes':a.terminated}
 def close(self):
  assert self.k.CloseHandle(self.handle),ctypes.get_last_error();self.handle=None
def command(case,name,argv,request=None,timeout=65):
 folder=case/'commands'/name;folder.mkdir(parents=True,exist_ok=False)
 if request is not None:write(folder/'request.json',request)
 env=dict(os.environ,PYTHONPATH=str(STAGE/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
 started=time.monotonic();p=subprocess.Popen([str(x) for x in argv],cwd=STAGE,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000)
 OWN.append(p);job=None;timed_out=False
 try:
  job=Job(p)
  write(folder/'launch.json',{'pid':p.pid,'argv':[str(x) for x in argv],'cwd':str(STAGE),'pythonpath':env['PYTHONPATH'],'timeout_seconds':timeout,'windows_job_assigned':True})
  try:stdout,stderr=p.communicate(timeout=timeout)
  except subprocess.TimeoutExpired:
   timed_out=True;job.close();p.kill();stdout,stderr=p.communicate(timeout=10)
  (folder/'stdout.log').write_bytes(stdout);(folder/'stderr.log').write_bytes(stderr)
  accounting=job.accounting() if job and job.handle else {'active_processes':'terminated_on_timeout'}
  immediate=dict(accounting);join_deadline=time.monotonic()+2
  while not timed_out and accounting['active_processes'] and time.monotonic()<join_deadline:
   time.sleep(0.01);accounting=job.accounting()
  lines=[]
  for line in stdout.decode('utf-8','replace').splitlines():
   try:lines.append(json.loads(line))
   except ValueError:pass
  record={'pid':p.pid,'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-started,'timed_out':timed_out,'alive':p.poll() is None,
   'job_accounting_immediate':immediate,'job_accounting_before_close':accounting,'parsed_json':lines,'request':request}
  write(folder/'completion.json',record)
  assert not timed_out and accounting['active_processes']==0,record
  return record
 finally:
  if job and job.handle:job.close()
  if p.poll() is None:p.kill();p.wait(timeout=10)
def last(record):
 assert record['parsed_json'],record
 return record['parsed_json'][-1]
def make(case_name):
 case=OUT/'cases'/case_name;case.mkdir(parents=True,exist_ok=False)
 prepared=command(case,'01-prepare',[sys.executable,'-B',STAGE/'examples/a03/P2/prepare.py','--root',STAGE,'--output',case/'fixtures'])
 assert prepared['exit_code']==0 and last(prepared)['ok'];inputs=last(prepared)
 common={'anchor_path':str(case/'anchor.json'),'expected_ledger_id':'independent-'+case_name,'expected_target_store_id':'independent-target-'+case_name}
 init={**common,'operation':'init','state_dir':str(case/'runtime'),'target_dir':str(case/'target'),'target_session_id':'independent-session',
  'bundle_path':inputs['bundle_path'],'asset_root':inputs['asset_root'],'config_path':inputs['config_path'],'source_ref':inputs['source_ref'],'snapshot_ref':inputs['snapshot_ref'],'platform_namespace':'a03-mock'}
 rec=cli(case,'02-init',init);assert rec['exit_code']==0 and last(rec)['ok'];data=last(rec)['result']
 common['registration_id']=data['registration_id']
 return case,common,data
def cli(case,name,request):
 path=case/'commands'/name/'request.json'
 return command(case,name,[sys.executable,'-B','-m','annotation.runtime.recovery.cli','--request',path],request)
def inspect(case,name):
 r=command(case,name,[sys.executable,'-B',OUT/'scripts/sql_probe.py',case],timeout=15)
 assert r['exit_code']==0;return last(r)
