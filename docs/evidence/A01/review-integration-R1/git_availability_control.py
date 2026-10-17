import concurrent.futures,json,os,shutil,subprocess,sys
from pathlib import Path
out=Path(__file__).resolve().parent;info=json.loads((out/'bootstrap.json').read_text(encoding='utf-8'));tree=Path(info['raw'])
base=out/'git-availability';base.mkdir(exist_ok=False)
def run(label,available,full):
 folder=base/label;folder.mkdir();temp=Path(info['temporary'])/label;temp.mkdir()
 env=dict(os.environ,PYTHONPATH=str(tree/'src'),PYTHONDONTWRITEBYTECODE='1',TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp))
 if not available:env['PATH']=r'C:\Windows\System32;C:\Windows'
 if full:args=[sys.executable,'-B',str(tree/'examples/a01/integration-R1/verify.py'),str(folder/'entry')];cwd=temp
 else:args=[sys.executable,'-B','-m','unittest','test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head','-v'];cwd=tree/'tests'
 p=subprocess.run(args,cwd=cwd,env=env,capture_output=True)
 (folder/'stdout.txt').write_bytes(p.stdout);(folder/'stderr.txt').write_bytes(p.stderr)
 data=dict(argv=args,cwd=str(cwd),exit_code=p.returncode,git_executable=shutil.which('git',path=env['PATH']),has_dot_git=(tree/'.git').exists(),PATH=env['PATH'],PYTHONPATH=env['PYTHONPATH'],stdout='stdout.txt',stderr='stderr.txt',observer='none; direct original Python command')
 with (folder/'command.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 expected=0 if available else 1
 assert p.returncode==expected,(data,p.stderr.decode('utf-8','replace'))
 if not available:assert b'FileNotFoundError' in p.stderr and b'WinError 2' in p.stderr
 return data
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 futures=[pool.submit(run,'raw-full-with-git',True,True),pool.submit(run,'minimal-without-git',False,False),pool.submit(run,'minimal-with-git',True,False)]
 results=[f.result() for f in futures]
with (base/'summary.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False))
