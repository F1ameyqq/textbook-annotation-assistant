"""Pre-business M static compile, exact inputs/schema refs and staged raw pins."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/evidence/A03/T3/execution/M/preflight'
K='62a023a1c88c20d884a61f38d1ad995b0908b74c'
PRODUCTS=[
'src/annotation/quality/synthetic_precheck.py',
'src/annotation/runtime/storage/__init__.py','src/annotation/runtime/storage/native.py','src/annotation/runtime/storage/holds.py',
'src/annotation/contracts/a03_native/__init__.py','src/annotation/contracts/a03_native/_closure.py',
'src/annotation/contracts/a03_native/data/oracle.json','src/annotation/contracts/a03_native/data/api.json',
'src/annotation/contracts/a03_native/data/profile.json','src/annotation/contracts/a03_native/data/adoption.json',
'src/annotation/contracts/a03_native/data/schemas/prefix.json','src/annotation/contracts/a03_native/data/schemas/basis.json',
'src/annotation/contracts/a03_native/data/schemas/fact.json','src/annotation/contracts/recovery.py']


def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def git(*args):return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(ROOT),*args],cwd=str(ROOT))
def raw(path):return git('show',':'+path)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    changed=git('diff','--cached','--name-only',K).decode().splitlines()
    assert all(p in PRODUCTS or p.startswith(('examples/a03/T3-closure/','docs/evidence/A03/T3/execution/M/'))
        or p in ('tests/test_a03_t3_closure.py','docs/tasks/A03-T3-M-adoption.md') for p in changed),changed
    paths=git('ls-files','src/annotation','examples/a03/T3-closure','examples/a03/T1-capture/capture.py',
        'tests/test_a03_t3_closure.py').decode().splitlines()
    identities=[]
    for path in paths:
        b=raw(path)
        if path.endswith('.py'):ast.parse(b.decode('utf-8'),filename=path);compile(b.decode('utf-8'),path,'exec')
        if path.endswith('.json'):json.loads(b)
        identities.append({'path':path,'bytes':len(b),'raw_sha256':sha(b),
            'checkout_sha256':sha((ROOT/path).read_bytes()),'checkout_equal_raw':(ROOT/path).read_bytes()==b})
    data='src/annotation/contracts/a03_native/data/'
    profile=json.loads(raw(data+'profile.json'))
    for path,expected in profile['implementation_pins']:
        full='src/'+path[1:] if path.startswith('@') else 'src/annotation/contracts/a03_native/'+path
        assert sha(raw(full))==expected,full
    for path,expected in profile['schema_pins']:assert sha(raw(data+path))==expected,path
    for key,name in [('api_sha256','api.json'),('oracle_sha256','oracle.json')]:assert profile[key]==sha(raw(data+name))
    assert json.loads(raw(data+'adoption.json'))['profile_sha256']==sha(raw(data+'profile.json'))
    schema_summary=[]
    for filename in ['basis.json','prefix.json','fact.json']:
        doc=json.loads(raw(data+'schemas/'+filename))
        def walk(v):
            if isinstance(v,dict):
                if '$ref'in v:
                    assert v['$ref'].startswith('#/')
                    t=doc
                    for token in v['$ref'][2:].split('/'):t=t[token.replace('~1','/').replace('~0','~')]
                if 'required'in v:assert len(v['required'])==len(set(v['required']))
                for x in v.values():walk(x)
            elif isinstance(v,list):
                for x in v:walk(x)
        walk(doc)
        schema_summary.append({'path':filename,'local_schema_refs':'RESOLVED','required_keys_unique':True})
    fixtures=[]
    for tag,count in [('single',1),('three',3)]:
        path='examples/a03/T3-closure/inputs/'+tag+'/initial.json'
        doc=json.loads(raw(path));index={(a['artifact_id'],a['revision']):a for a in doc['artifacts']}
        for a in doc['artifacts']:
            assert a['content_hash']==sha(canon({k:v for k,v in a.items() if k!='content_hash'}))
            for ref in a['input_refs']:
                actual=index[(ref['artifact_id'],ref['revision'])]
                assert ref=={k:actual[k]for k in ('artifact_id','revision','kind','content_hash')}
        source=next(a for a in doc['artifacts']if a['kind']=='SourceBundle')
        graph=next(a for a in doc['artifacts']if a['kind']=='QuestionGraph')
        assert len(source['payload']['assets'])==len(graph['payload']['questions'])==count
        for asset in source['payload']['assets']:
            b=raw('examples/a03/T3-closure/inputs/'+tag+'/'+asset['path'])
            assert sha(b)==asset['sha256']
            tokens=b' '.join(l.split(b'#',1)[0]for l in b.splitlines()).split()
            assert tokens[:4]==[b'P2',b'32',b'32',b'255']and len(tokens[4:])==1024
        inv=source['payload']['scope_integrity']['proof']
        assert sha(raw('examples/a03/T3-closure/inputs/'+tag+'/'+inv['path']))==inv['sha256']
        fixtures.append({'path':path,'sha256':sha(raw(path)),'question_count':count,'assets_and_refs':'STATIC_MATCH'})
    assert sha(raw('examples/a03/T1-capture/capture.py'))=='3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b'
    native=ast.parse(raw('src/annotation/runtime/storage/native.py').decode('utf-8'))
    klass=next(n for n in native.body if isinstance(n,ast.ClassDef)and n.name=='NativeRuntimeStore')
    methods={n.name for n in klass.body if isinstance(n,ast.FunctionDef)}
    assert {'commit_unattempted_absence','record_hold_candidate','_check_readonly_entry','_pending'}<=methods
    assert not git('diff','--cached',K,'--','src/annotation/delivery','src/annotation/quality/targetcheck',
        'src/annotation/runtime/recovery','src/annotation/runtime/storage/native_target.py',
        'examples/a03/T1-capture/capture.py','pyproject.toml')
    assert not git('diff','--cached','--check')
    result={'status':'PASS_STATIC_ONLY_NOT_FUNCTIONAL','base_K':K,'changed':changed,
        'files':identities,'fixtures':fixtures,'schemas':schema_summary,'pins':'ALL_STAGED_RAW_MATCH',
        'product_imports':0,'business_runs':0,'sqlite_connections':0,
        'preparation_failure_preserved':'preparation-failure-01','business_correction_budget_used':0,
        'cases':['M1','M2-sufficient','M2-insufficient','M3-new-plan','M3-final-drift']}
    (OUT/'static-and-input-index.json').write_bytes((json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'status':result['status'],'files':len(paths),'fixtures':fixtures,'business_runs':0},ensure_ascii=False))


if __name__=='__main__':main()
