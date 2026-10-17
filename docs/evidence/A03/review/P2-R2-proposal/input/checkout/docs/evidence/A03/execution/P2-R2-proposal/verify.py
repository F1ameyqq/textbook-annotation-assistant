"""Raw bytes/scope/links/process receipts only. --check is read-only."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
EX=ROOT/'examples/a03/P2-R2-proposal'
REPORT=ROOT/'docs/tasks/A03-P2-R2-proposal-delivery.md'
BASE='7fdbde8f16569fd3bc399013115e13269d5d33fa'
def sha(v):return hashlib.sha256(v).hexdigest()
def load(p):return json.loads(p.read_bytes())
def git(*args):return subprocess.check_output(['git','-c','core.longpaths=true',*args],cwd=ROOT)
def allfiles():return sorted([REPORT]+[p for root in (OUT,EX)for p in root.rglob('*')if p.is_file()])
def allowed(s):return s==REPORT.relative_to(ROOT).as_posix() or any(s.startswith(p.relative_to(ROOT).as_posix()+'/')for p in(OUT,EX))

if __name__=='__main__':
    check=sys.argv[1:]==['--check'];assert check or len(sys.argv)==1
    old=load(OUT/'old-baseline.json')['files']
    for v in old:
        p=ROOT/v['path'];assert p.is_file() and p.stat().st_size==v['bytes'] and sha(p.read_bytes())==v['sha256'],v['path']
    for v in load(OUT/'input-index.json')['inputs']:
        raw=(ROOT/v['copy']).read_bytes();assert sha(raw)==v['sha256'] and len(raw)==v['bytes']
    for item in git('status','--porcelain=v1','-uall','-z').split(b'\0'):
        if item:assert item[:2]in(b'??',b'A ')and allowed(item[3:].decode('utf8')),item[:200]
    for name in git('diff','--name-only',BASE,'--').decode('utf8').splitlines():assert allowed(name),name
    deferred=[];links=0
    outputs={OUT/'sha256-manifest.json',OUT/'delivery-verification.json',OUT/'process-release.json'}
    for doc in (REPORT,EX/'SPEC.md'):
        for target in re.findall(r'\[[^\]\n]+\]\(([^)]+)\)',doc.read_text(encoding='utf8')):
            assert not target.startswith(('https:','http:'));p=(doc.parent/target.split('#')[0]).resolve();assert p.is_relative_to(ROOT)
            if not p.exists():assert not check and p in outputs,target;deferred.append(p.relative_to(ROOT).as_posix())
            links+=1
    current=load(OUT/'static-results.json')
    assert current['checker_sha256']==sha((EX/'check.py').read_bytes())
    assert current['schema_interpreter_sha256']==sha((EX/'schema_check.py').read_bytes())
    assert current['profile_sha256']==sha((EX/'candidate-final/profile.json').read_bytes())
    assert len(current['records'])==36 and current['native_sessions']==current['product_runs']==current['database_queries']==0
    finished=[]
    for run in sorted((OUT/'runs').iterdir()):
        if (run/'exit.json').exists():
            v=load(run/'exit.json');assert v['owned_child_alive']is False and v['native_sessions']==0;finished.append(run.name)
            assert (run/'stdout.txt').is_file()and(run/'stderr.txt').is_file()and(run/'registration.json').is_file()
    for p in allfiles():
        assert '__pycache__'not in p.parts and '.local'not in p.parts and p.suffix!='.pyc'
        if p.suffix=='.json':load(p)
    manifest=OUT/'sha256-manifest.json';entries=None
    if manifest.exists():
        m=load(manifest);expected={p.relative_to(ROOT).as_posix()for p in allfiles()if p!=manifest};assert expected=={v['path']for v in m['files']}
        for v in m['files']:
            raw=(ROOT/v['path']).read_bytes();assert sha(raw)==v['sha256']and len(raw)==v['bytes'],v['path']
        entries=len(m['files'])
    elif check:raise AssertionError('manifest absent')
    result={'status':'REVIEW_STATIC_ONLY_NOT_ACCEPTANCE','base':BASE,'unchanged_old_files':len(old),'changed_old_files':0,
        'scope_only_three_new_locations':True,'document_links':links,'deferred_before_seal_only':deferred,
        'static_records':36,'finished_prior_owned_runs':finished,'manifest_entries_if_sealed':entries,
        'native_sessions':0,'product_runs':0,'database_queries':0,'network_or_model_calls':0,
        'residuals':['R17 native version bridge not approved/proven','registration-derived scope branch lacks independent positive fixture','all real lock/DB/read/CAS/quality/conversion fault evidence NOT_EXECUTED'],
        'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    if not check:
        with (OUT/'delivery-verification.json').open('xb')as f:f.write(json.dumps(result,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
    print(json.dumps(result))
