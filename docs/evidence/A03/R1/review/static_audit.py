"""Read only fixed raw files and Git identities; no product import or SQL."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('D:/1800-worktrees/a03-r1-review-54e86adf')
OUT = Path(__file__).resolve().parent
FINAL = '54e86adfaf144093a688b62fe0dad5190ceb2fa6'
CANDIDATE = '6097a06de937fee8876feccedf46920510850b83'
BASE = 'd5f777590e72eb070af0497afdb144d60c61b95d'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads((ROOT/path).read_bytes())
def git(*args):
    return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(ROOT),*args])
def blob(rev,path): return git('show',rev+':'+path)
def functions(raw):
    tree=ast.parse(raw)
    return {cls.name+'.'+fn.name: ast.dump(fn,include_attributes=False)
            for cls in tree.body if isinstance(cls,ast.ClassDef)
            for fn in cls.body if isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef))}

def main():
    execution='docs/evidence/A03/R1/execution/'
    manifest=load(execution+'manifest.json')
    mismatches=[]
    for row in manifest['members']:
        raw=(ROOT/row['path']).read_bytes()
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']: mismatches.append(row['path'])
    changed=git('diff','--name-only',BASE,FINAL).decode().splitlines()
    def allowed(path):
        return path.startswith(('src/annotation/runtime/storage/','src/annotation/runtime/recovery/',
            'src/annotation/contracts/a03_native/','src/annotation/contracts/a03_bridge/',
            'examples/a03/R1/','tests/fixtures/a03/R1/',execution)) or path in (
            'src/annotation/contracts/recovery.py','examples/a03/T3-closure/run.py',
            'tests/test_a03_t3_closure.py','docs/tasks/A03-R1-execution-report.md') or (
            path.startswith('tests/test_a03_r1') and path.endswith('.py'))
    protected=[p for p in changed if not allowed(p)]
    audit=dict(final=FINAL,candidate=CANDIDATE,base=BASE,changed_paths=changed,
        out_of_scope=protected,manifest_members=len(manifest['members']),
        manifest_bytes=sum(x['bytes'] for x in manifest['members']),manifest_mismatches=mismatches,
        report_sha256=sha(blob(FINAL,'docs/tasks/A03-R1-execution-report.md')),
        manifest_sha256=sha(blob(FINAL,execution+'manifest.json')),
        candidate_to_final_src_changes=git('diff','--name-only',CANDIDATE,FINAL,'--','src').decode().splitlines())
    guards={
        'src/annotation/runtime/storage/__init__.py': ['RuntimeStore._lease','RuntimeStore.commit_intent',
            'RuntimeStore.issue_first_dispatch','RuntimeStore.consume_first_dispatch',
            'RuntimeStore.verify_target_authorization','RuntimeStore._guard_target_effect'],
        'src/annotation/runtime/storage/native.py':['NativeRegistry._current','NativeRegistry._dispatch',
            'NativeRuntimeStore._pre_lease','NativeRuntimeStore.commit_unattempted_absence']}
    audit['guards']=[]
    for path,names in guards.items():
        old,new=functions(blob(BASE,path)),functions(blob(FINAL,path))
        for name in names:
            audit['guards'].append(dict(path=path,method=name,ast_identical=old[name]==new[name]))
    audit['unchanged_public_and_runtime']={p:blob(BASE,p)==blob(FINAL,p) for p in (
        'src/annotation/runtime/storage/holds.py','src/annotation/runtime/recovery/__init__.py',
        'src/annotation/runtime/recovery/native_quality.py','src/annotation/delivery/mock/persistent.py',
        'src/annotation/delivery/reconciler/__init__.py','src/annotation/contracts/a03_native/data/api.json',
        'src/annotation/contracts/a03_native/data/oracle.json','src/annotation/contracts/a03_native/data/schemas/exchange.json',
        'src/annotation/contracts/a03_native/data/schemas/prefix.json','src/annotation/contracts/a03_native/data/schemas/fact.json',
        'src/annotation/contracts/a03_native/data/schemas/basis.json')}
    native=ROOT/'src/annotation/contracts/a03_native'
    profile=json.loads((native/'data/profile.json').read_bytes())
    pins=[]
    for path,expected in profile['implementation_pins']:
        f=ROOT/('src/'+path[1:]) if path.startswith('@') else native/path
        pins.append(dict(path=path,expected=expected,actual=sha(f.read_bytes())))
    for path,expected in profile['schema_pins']:
        pins.append(dict(path=path,expected=expected,actual=sha((native/'data'/path).read_bytes())))
    audit['pins']=pins
    audit['capture_sha256']=sha((ROOT/'examples/a03/T1-capture/capture.py').read_bytes())
    bad=(ROOT/execution/'deltas-correction/B/input/assets/page-1.pgm').read_bytes()
    good=(ROOT/'examples/a03/T3-closure/inputs/single/assets/page-1.pgm').read_bytes()
    audit['L2_input']=dict(raw_sha256=sha(good),raw_bytes=len(good),failed_sha256=sha(bad),
        failed_bytes=len(bad),crlf_to_lf_is_raw=bad.replace(b'\r\n',b'\n')==good,
        registration_not_reached=True,driver='examples/a03/R1/deltas.py::setup')
    commits=git('log','--format=%H',BASE+'..'+FINAL).decode().splitlines()
    audit['commit_src_trees']=[dict(commit=c,src_tree=git('rev-parse',c+':src').decode().strip()) for c in commits]
    audit['matrices']={p:load(execution+p) for p in ('candidate-1/business/matrix.json',
        'deltas/matrix.json','deltas-correction/matrix.json')}
    audit['T1_T2_inheritance']=[dict(report=p,workflow='07708f34',sha256=sha(blob('07708f34',p))) for p in (
        'docs/tasks/A03-T1-coordinator-acceptance.md','docs/tasks/A03-T2-coordinator-acceptance.md',
        'docs/tasks/A03-T2-static-archive-review-report.md')]
    (OUT/'static-audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    assert not mismatches and not protected and not audit['candidate_to_final_src_changes']
    assert all(r['expected']==r['actual'] for r in pins)
    assert all(r['ast_identical'] for r in audit['guards'])
    assert all(audit['unchanged_public_and_runtime'].values())
    print(json.dumps(dict(status='STATIC_AUDIT_COMPLETE',members=len(manifest['members']),
        changed=len(changed),pins=len(pins),L2_CRLF=audit['L2_input']['crlf_to_lf_is_raw'],
        unique_product_src=len({r['src_tree'] for r in audit['commit_src_trees']}))))

if __name__=='__main__': main()
