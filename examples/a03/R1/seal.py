"""Raw-byte index and static scope/guard comparison, without product imports."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/evidence/A03/R1/execution'
BASE='d5f777590e72eb070af0497afdb144d60c61b95d'
PRODUCT='6097a06de937fee8876feccedf46920510850b83'


def git(*args):
    return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(ROOT),*args])


def write(path,data):
    path.write_bytes((json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8'))


def bodies(raw):
    tree=ast.parse(raw.decode('utf-8-sig'))
    result={}
    def walk(node,prefix=''):
        for child in getattr(node,'body',[]):
            if isinstance(child,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                key=prefix+child.name
                result[key]=ast.dump(child,include_attributes=False)
                walk(child,key+'.')
    walk(tree)
    return result


def main():
    changes=git('diff','--name-only',BASE,'HEAD').decode('utf-8').splitlines()
    assert all(p.startswith(('src/annotation/contracts/a03_native/','src/annotation/contracts/a03_bridge/',
        'src/annotation/runtime/storage/','src/annotation/runtime/recovery/','examples/a03/R1/',
        'docs/evidence/A03/R1/execution/'))or p in ('src/annotation/contracts/recovery.py',
        'examples/a03/T3-closure/run.py','tests/test_a03_r1_validation.py','docs/tasks/A03-R1-execution-report.md')for p in changes)
    guardpaths={
        'src/annotation/runtime/storage/__init__.py':['RuntimeStore._lease','RuntimeStore.commit_intent',
            'RuntimeStore.issue_first_dispatch','RuntimeStore.consume_first_dispatch','RuntimeStore.verify_target_authorization',
            'RuntimeStore._guard_target_effect'],
        'src/annotation/runtime/storage/native.py':['NativeRegistry._current','NativeRegistry._dispatch',
            'NativeRuntimeStore._pre_lease','NativeRuntimeStore.commit_unattempted_absence'],
        'src/annotation/runtime/storage/holds.py':[],
        'src/annotation/runtime/recovery/__init__.py':[],
        'src/annotation/runtime/recovery/native_quality.py':[],
        'src/annotation/delivery/mock/persistent.py':[],
        'src/annotation/delivery/reconciler/__init__.py':[]}
    rows=[]
    for path,names in guardpaths.items():
        old=git('show',BASE+':'+path);current=git('show',PRODUCT+':'+path)
        if not names:
            assert old==current,path
            rows.append(dict(path=path,raw_identical=True,sha256=hashlib.sha256(current).hexdigest()))
        else:
            before,after=bodies(old),bodies(current)
            for name in names:
                assert name in before and name in after,(path,name)
                assert before[name]==after[name],(path,name)
                rows.append(dict(path=path,method=name,ast_identical=True))
    rawsingle=git('show',PRODUCT+':examples/a03/T3-closure/inputs/single/assets/page-1.pgm')
    failed=OUT/'deltas-correction/B/input/assets/page-1.pgm'
    actual=failed.read_bytes()
    expected=json.loads((OUT/'deltas-correction/B/input/initial.json').read_bytes())['artifacts'][0]['payload']['assets'][0]['sha256']
    assert hashlib.sha256(rawsingle).hexdigest()==expected
    assert hashlib.sha256(actual).hexdigest()!=expected
    raw_actual=actual.replace(b'\r\n',b'\n')
    assert raw_actual==rawsingle
    write(OUT/'static-audit.json',dict(base=BASE,product=PRODUCT,audit_source_head=git('rev-parse','HEAD').decode().strip(),changed_paths=changes,guards=rows,
        fixed_B_failure=dict(path=str(failed.relative_to(ROOT)),expected=expected,
            actual_sha256=hashlib.sha256(actual).hexdigest(),expected_bytes=len(rawsingle),actual_bytes=len(actual),
            difference='checkout CRLF conversion only; validation rejected before registration',
            no_product_defect_inferred=True),legacy_conversion='LEGACY_INITIAL_ONLY',migration='NOT_IMPLEMENTED_BLOCKED'))
    members=[]
    for path in sorted(OUT.rglob('*')):
        if not path.is_file()or 'runtime-view'in path.parts or path==OUT/'manifest.json':continue
        raw=path.read_bytes()
        members.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    report=ROOT/'docs/tasks/A03-R1-execution-report.md'
    if report.exists():
        raw=report.read_bytes();members.append(dict(path=report.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    write(OUT/'manifest.json',dict(product=PRODUCT,members=members,
        excluded='reconstructible raw runtime-view exports; manifest self',old_evidence_copied=False))
    print('RAW_INDEX_ENDED',len(members))


if __name__=='__main__':main()
