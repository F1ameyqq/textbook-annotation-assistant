"""Independent R3-02 fixed Git-reference and actual corruption probes."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode=True
ap=argparse.ArgumentParser()
ap.add_argument('--snapshot',required=True)
ap.add_argument('--git-repo',required=True)
ap.add_argument('--r2-result',required=True)
ap.add_argument('--out',required=True)
ap.add_argument('--temp-root',required=True)
args=ap.parse_args()
ROOT=Path(args.snapshot).resolve();GIT=Path(args.git_repo).resolve();OUT=Path(args.out).resolve();TEMP=Path(args.temp_root).resolve()
OUT.mkdir(parents=True,exist_ok=True);TEMP.mkdir(parents=True,exist_ok=True)
os.environ['TMP']=os.environ['TEMP']=os.environ['TMPDIR']=str(TEMP)
os.environ['PYTHONDONTWRITEBYTECODE']='1';tempfile.tempdir=str(TEMP)
RUN=Path(tempfile.mkdtemp(prefix='preservation-review-',dir=TEMP))
sys.path.insert(0,str(ROOT/'src'))
BASE='c3aff9598b6705ab4122062615a13ae3774698b2'
IMPL='31d715a5f2e6435af3a7e98a6c19b41b72d883bd'
REF_COMMIT='aeb7ca306b3dba9d51740071f96592d8e677ec66'
FINAL='180bb1e86fb2a7eb1546be85af70f466f069daf5'
MUTABLE={'src/annotation/source/static/importer.py','src/annotation/source/static/consistency.py','docs/a01-source-geometry.md'}
CODE_EOL={'src/annotation/source/static/importer.py','src/annotation/source/static/consistency.py','tests/test_a01_rework_r3.py'}

def digest(data):return hashlib.sha256(data).hexdigest()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def tree(commit):
    proc=subprocess.run(['git','ls-tree','-rz','--full-tree',commit],cwd=GIT,capture_output=True,check=True)
    rows={}
    for entry in proc.stdout.split(b'\0'):
        if not entry:continue
        header,path=entry.split(b'\t',1);mode,kind,oid=header.decode().split()
        assert kind=='blob' and mode in ['100644','100755']
        rows[path.decode('utf-8')]={'oid':oid,'mode':mode}
    return rows

trees={c:tree(c) for c in [BASE,IMPL,REF_COMMIT,FINAL]}
old=load(ROOT/'tests/fixtures/a01/R3/preservation-manifest.json')
code=load(ROOT/'tests/fixtures/a01/R3/code-reference.json')
r2=load(args.r2_result)
old_allow={r['path'] for r in r2['author_disk_baseline_EOL_differences']}
assert len(old_allow)==25 and all(r['difference_only_uniform_EOL'] for r in r2['author_disk_baseline_EOL_differences'])
code_paths={p for p in trees[IMPL] if p in MUTABLE or p=='tests/test_a01_rework_r3.py'
            or p.startswith(('examples/a01/R3/','tests/fixtures/a01/R3/'))}
code_paths.discard('tests/fixtures/a01/R3/code-reference.json')
expected_paths={'preservation':set(trees[BASE])-MUTABLE,'code':code_paths}
oids=list(dict.fromkeys(r['git_blob_oid'] for m in [old,code] for r in m['files']))
stream=subprocess.run(['git','cat-file','--batch'],cwd=GIT,input=('\n'.join(oids)+'\n').encode(),capture_output=True,check=True).stdout
blobs={};offset=0
for expected in oids:
    end=stream.index(b'\n',offset);oid,kind,size=stream[offset:end].decode().split();size=int(size)
    raw=stream[end+1:end+1+size];offset=end+size+2
    assert oid==expected and kind=='blob' and len(raw)==size
    assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest()==oid
    blobs[oid]=raw
reference_rows=[]
checks=[]
for name,manifest,commit,allow in [('preservation',old,BASE,old_allow),('code',code,IMPL,CODE_EOL)]:
    paths=[r['path'] for r in manifest['files']]
    checks.append({'id':name+'.exact-path-set','pass':len(paths)==len(set(paths)) and set(paths)==expected_paths[name],
                   'actual_count':len(paths),'expected_count':len(expected_paths[name])})
    checks.append({'id':name+'.fixed-reference-commit','pass':manifest['reference_commit']==commit})
    variants={r['path'] for r in manifest['files'] if len(r['representations'])>1}
    checks.append({'id':name+'.exact-CRLF-allowlist','pass':variants==allow,'actual':sorted(variants),'expected':sorted(allow)})
    for entry in manifest['files']:
        path=entry['path'];raw=blobs[entry['git_blob_oid']]
        expected_reps=[{'kind':'GIT_BLOB','sha256':digest(raw),'bytes':len(raw)}]
        if path in allow:
            assert b'\r' not in raw and b'\n' in raw and b'\0' not in raw
            raw.decode('utf-8')
            converted=raw.replace(b'\n',b'\r\n')
            expected_reps.append({'kind':'FIXED_CRLF_TEXT_REPRESENTATION','sha256':digest(converted),'bytes':len(converted)})
        passed=(trees[commit][path]['oid']==entry['git_blob_oid'] and entry['git_sha256']==digest(raw)
                and entry['representations']==expected_reps)
        identity={c:trees[c].get(path,{}).get('oid')==entry['git_blob_oid'] for c in ([IMPL,REF_COMMIT,FINAL] if name=='code' else [BASE])}
        passed=passed and all(identity.values())
        reference_rows.append({'kind':name,'path':path,'reference_commit':commit,'git_blob_oid':entry['git_blob_oid'],
                               'git_sha256':digest(raw),'representations':expected_reps,'commit_identity':identity,'pass':passed})
save(OUT/'reference-blob-audit.json',{'checks':checks,'records':reference_rows,'r2_source':str(Path(args.r2_result).resolve()),
     'r2_source_sha256':digest(Path(args.r2_result).read_bytes()),'runtime_Git_required':False,
     'pass':all(c['pass'] for c in checks) and all(r['pass'] for r in reference_rows)})

# Import the exact frozen helper, record actual module location; do not run its
# reference builder or use it to compute any expected fixed hashes.
spec=importlib.util.spec_from_file_location('r3_preservation_under_review',ROOT/'examples/a01/R3/preservation.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
assert Path(helper.__file__).resolve()==ROOT/'examples/a01/R3/preservation.py'

allowed_path='tools/coord_reverse.py'
historical_path='examples/a01/bundles/46006966/provenance.json'
jpg_path=next(r['path'] for r in old['files'] if r['path'].startswith('data/raw/images/') and r['path'].endswith('.jpg'))
assert allowed_path in old_allow and historical_path not in old_allow
commands=[]
def run_case(label,changes,expected_code,gate=None,target=None):
    folder=RUN/label/'snapshot';shutil.copytree(ROOT,folder)
    assert not (folder/'.git').exists()
    mutations=[]
    for path,how in changes:
        file=folder/path;before=file.read_bytes()
        if how=='CRLF':
            assert b'\r' not in before and b'\n' in before
            after=before.replace(b'\n',b'\r\n')
        elif how=='mixed-EOL':
            assert b'\r' not in before and before.count(b'\n')>=2
            after=before.replace(b'\n',b'\r\n',1)
        elif how=='real-body':after=before+b'\n# independent real content mutation\n'
        elif how=='binary-byte':
            pos=len(before)//2;changed=bytearray(before);changed[pos]^=1;after=bytes(changed)
        else:raise AssertionError(how)
        file.write_bytes(after)
        mutations.append({'path':path,'kind':how,'before_sha256':digest(before),'after_sha256':digest(after),
                          'before_bytes':len(before),'after_bytes':len(after),'byte_offset':len(before)//2 if how=='binary-byte' else None})
    evidence=OUT/'cases'/label;evidence.mkdir(parents=True,exist_ok=True)
    destination=evidence/'verify-output'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMP=str(TEMP),TEMP=str(TEMP),TMPDIR=str(TEMP),PYTHONPATH=str(folder/'src'))
    # Runtime verification has no .git and no Git directory on PATH. Reference
    # auditing above used Git only to bind expected references independently.
    env['PATH']=str(Path(sys.executable).parent)+os.pathsep+str(Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32')
    command=[sys.executable,'-B',str(folder/'examples/a01/R3/verify.py'),str(destination),'--preservation-only']
    proc=subprocess.run(command,cwd=folder,env=env,capture_output=True,text=True)
    (evidence/'stdout.log').write_text(proc.stdout,encoding='utf-8');(evidence/'stderr.log').write_text(proc.stderr,encoding='utf-8')
    report=json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
    codes=[e.get('code') for e in report.get('errors',[])]
    passed=proc.returncode==expected_code
    if expected_code==0:
        res=load(destination/'results.json');passed=passed and report.get('passed') is True and res['commands']==[] and res['disk_changes']==[]
    else:
        passed=passed and report.get('gate')==gate and any(e.get('code')=='CONTENT_MISMATCH' and e.get('path')==target for e in report.get('errors',[]))
        passed=passed and not (destination/'results.json').exists() and not (destination/'failed-commands.json').exists()
    row={'id':label,'command':command,'cwd':str(folder),'destination':str(destination),'no_git_directory':not(folder/'.git').exists(),
         'runtime_PATH':env['PATH'],'mutations':mutations,'expected_exit_code':expected_code,'actual_exit_code':proc.returncode,
         'expected_gate':gate,'target':target,'stdout':report,'functional_commands_run':0,'pass':passed}
    save(evidence/'command-input-output.json',row);commands.append(row)

run_case('P00-raw-fixed-reference',[],0)
run_case('P01-all-25-fixed-CRLF',[(p,'CRLF') for p in sorted(old_allow)],0)
run_case('N01-real-old-text-body',[(allowed_path,'real-body')],1,'preservation',allowed_path)
run_case('N02-mixed-allowed-text-EOL',[(allowed_path,'mixed-EOL')],1,'preservation',allowed_path)
run_case('N03-unallowed-historical-CRLF',[(historical_path,'CRLF')],1,'preservation',historical_path)
run_case('N04-JPG-binary-byte-damage',[(jpg_path,'binary-byte')],1,'preservation',jpg_path)
run_case('N05-real-current-code-body',[('src/annotation/source/static/consistency.py','real-body')],1,'implementation','src/annotation/source/static/consistency.py')
run_case('N06-unallowed-R3-script-CRLF',[('examples/a01/R3/preservation.py','CRLF')],1,'implementation','examples/a01/R3/preservation.py')

# Independent begin/end transition using an actual, externally Git-audited old
# entry; two allowed representations must not erase an in-run disk change.
transition=RUN/'transition';file=transition/allowed_path;file.parent.mkdir(parents=True,exist_ok=True)
entry=next(r for r in old['files'] if r['path']==allowed_path)
one={'reference_commit':old['reference_commit'],'files':[entry]}
raw=blobs[entry['git_blob_oid']];crlf=raw.replace(b'\n',b'\r\n')
transitions=[]
for label,before,after,expect_change in [('LF-to-CRLF',raw,crlf,True),('CRLF-to-LF',crlf,raw,True),('LF-unchanged',raw,raw,False),('CRLF-unchanged',crlf,crlf,False)]:
    file.write_bytes(before);begin=helper.audit(transition,one)
    file.write_bytes(after);end=helper.audit(transition,one)
    observed=helper.disk_changes(begin,end)
    passed=(begin['passed'] and end['passed'] and bool(observed)==expect_change
            and all(r['code']=='DISK_CHANGED_DURING_RUN' and r['before_sha256']==digest(before) and r['after_sha256']==digest(after) for r in observed))
    transitions.append({'id':label,'fixed_entry':entry,'begin':begin,'end':end,'disk_changes':observed,'pass':passed})
save(OUT/'disk-transition-tests.json',transitions)
save(OUT/'corruption-cases.json',commands)
summary={'delivery_commit':FINAL,'implementation_commit':IMPL,'code_reference_export_commit':REF_COMMIT,'baseline_commit':BASE,
         'snapshot':str(ROOT),'run_root':str(RUN),'TMP':os.environ['TMP'],'TEMP':os.environ['TEMP'],'python':sys.version,
         'executable':sys.executable,'sys_path_0':sys.path[0],'dont_write_bytecode':sys.dont_write_bytecode,
         'helper_module':helper.__file__,'helper_sha256':digest(Path(helper.__file__).read_bytes()),
         'baseline_reference_records':len(old['files']),'code_reference_records':len(code['files']),
         'baseline_CRLF_allowlist':sorted(old_allow),'reference_blob_rows_pass':sum(r['pass'] for r in reference_rows),
         'reference_blob_rows_total':len(reference_rows),'reference_meta_checks_pass':sum(r['pass'] for r in checks),
         'reference_meta_checks_total':len(checks),'verify_cases_pass':sum(r['pass'] for r in commands),'verify_cases_total':len(commands),
         'transition_cases_pass':sum(r['pass'] for r in transitions),'transition_cases_total':len(transitions),
         'full_verify_functional_commands_run':0,'geometry_630_rerun':False,'sessions_to_release':0}
summary['pass']=all(r['pass'] for r in reference_rows+checks+commands+transitions)
summary['conclusion']='ACCEPTED' if summary['pass'] else 'REWORK'
save(OUT/'summary.json',summary)
print(json.dumps(summary,ensure_ascii=False,indent=2))
sys.exit(0 if summary['pass'] else 1)
