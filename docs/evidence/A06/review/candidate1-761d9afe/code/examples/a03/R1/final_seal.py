"""Post-run immutable-copy audit and additive final evidence index. No product I/O."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/evidence/A03/R1/final-correction'
BASE='54e86adfaf144093a688b62fe0dad5190ceb2fa6'
PRODUCT='6097a06de937fee8876feccedf46920510850b83'
CANDIDATE='9992cd8aba10987d25dd0dc0d0874abec02b27ef'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8'))


def git(*args):return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(ROOT),*args])


def main():
    matrix=json.loads((OUT/'run/matrix.json').read_bytes());assert all(r['status']=='ENDED'for r in matrix)
    assert not git('diff',PRODUCT,CANDIDATE,'--','src')
    capture_path=OUT/'frozen/runtime-view/examples/a03/T1-capture/capture.py'
    assert sha(capture_path)=='3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b'
    spec=importlib.util.spec_from_file_location('final_raw_capture',capture_path)
    capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
    audits=[]
    for path in sorted((OUT/'run/cases').rglob('SQL.json')):
        saved=json.loads(path.read_bytes());row=dict(path=str(path.relative_to(ROOT)),databases=[])
        for kind in ('runtime','target'):
            db=path.parent/(kind+'.sqlite3');before=sha(db)
            actual=capture.sql_copy(db);assert actual==saved[kind],path
            assert sha(db)==before
            row['databases'].append(dict(kind=kind,bytes=db.stat().st_size,sha256=before))
            if kind=='runtime':
                assert all(b['owner']is None and b['pid']is None and b['lease']==0 and b['phase']=='RELEASED'for b in actual['tables']['books'])
        audits.append(row)
    for path in (OUT/'run/cases').glob('*/worker-ended.json'):
        assert json.loads(path.read_bytes())['threads']==['MainThread']
    processes=[]
    for path in (OUT/'run').rglob('completed.json'):
        value=json.loads(path.read_bytes());assert not value['alive'],path
        processes.append(dict(path=str(path.relative_to(ROOT)),value=value))
    # The explicitly authorized source continuation changed at its fixed path.
    # Its old committed source and all old stationary copies remain immutable.
    runtime=ROOT/'docs/evidence/A03/R1/execution/candidate-1/business/cases/M2-sufficient/runtime'
    final_db=OUT/'run/cases/L2/captures/after-release/runtime.sqlite3'
    assert sha(runtime/'runtime.sqlite3')==sha(final_db)
    oldpaths=set(git('ls-tree','-r','--name-only',BASE,'docs/evidence/A03/R1/execution/candidate-1/business/cases/M2-sufficient/runtime').decode().splitlines())
    added=[]
    for path in sorted(runtime.rglob('*')):
        if not path.is_file()or path.relative_to(ROOT).as_posix()in oldpaths:continue
        dest=OUT/'continuation-files'/path.relative_to(runtime);dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copyfile(path,dest)
        assert sha(path)==sha(dest)
        added.append(dict(source=str(path),retained=dest.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
    write(OUT/'continuation-files/index.json',dict(source_directory=str(runtime),old_committed_source=BASE,
        current_database=str(final_db.relative_to(ROOT)),current_database_sha256=sha(final_db),new_live_files=added,
        original_stationary_copies_modified=False,live_source_restored_or_deleted=False))
    l2=json.loads((OUT/'run/cases/L2/result.json').read_bytes())
    l3=json.loads((OUT/'run/cases/L3-second/result.json').read_bytes())
    g6=json.loads((OUT/'run/cases/G6-reopen/result.json').read_bytes())
    assert l2['A_after']['pending_count']==2 and l2['B_status']['pending_count']==0
    assert l3['status']['pending_count']==1 and g6['reconcile']['attempt_count']==0
    first=json.loads((OUT/'run/cases/L3-execute/result.json').read_bytes())
    assert first['plan']['payload']['actions'][0]['action_id']!=l3['plan']['payload']['actions'][0]['action_id']
    first_g6=json.loads((OUT/'run/cases/G6-first/result.json').read_bytes())
    assert first_g6['reconcile']['attempt_count']==3
    attempts=[a for c in g6['export']['recovery_calls']if c['id']=='final-G6-fixed-call'for q in c['intent_queue']for a in q['attempts']]
    assert len(attempts)==3 and all(a['status']=='FAILED_READ'for a in attempts)
    target_changes=[]
    for phase in ('L2','G6-reopen'):
        tables=json.loads((OUT/f'run/cases/{phase}/captures/after-release/SQL.json').read_bytes())['target']['tables']
        state=json.loads(next(r['value']for r in tables['meta']if r['key']=='state'))
        assert len(state['target']['questions'])==1 and len(state['target']['frames'])==2 and state['epoch']==1
        target_changes.append(dict(phase=phase,questions=1,frames=2,actual_changes=1,dispatch_rows=len(tables['effects'])))
    for path in (OUT/'run/cases/L2/input/assets/page-1.pgm',OUT/'run/cases/L3-execute/input/assets/page-1.pgm'):
        assert path.stat().st_size==3579 and sha(path)=='1f82898615c67c676c532b17a8bd8e801c73eb6e7e2ba5a7f685bf1c3582cc7a'
    write(OUT/'post-run-audit.json',dict(product=PRODUCT,candidate=CANDIDATE,src_git_diff='EMPTY',
        sealing_script_sha256=sha(__file__),python=sys.version,executable=sys.executable,target_changes=target_changes,
        immutable_copy_audits=audits,processes=processes,new_targets=2,dispatch=3,
        original_author_counts=dict(M_targets=5,M_dispatch=10,legacy_calls=3,L1_reconcile=1),
        cumulative_author_native_targets=7,cumulative_author_native_dispatch=13,
        independent_prior_counts=dict(M_targets=5,M_dispatch=10,charged_to_author=False),
        A_pending=2,B_pending=0,L3_pending=1,G6_first_reads=3,G6_reopen_reads=0,
        primary_SQL_opened=False,old_material_resealed=False))
    members=[]
    for path in sorted(OUT.rglob('*')):
        if not path.is_file()or 'runtime-view'in path.parts or path==OUT/'manifest.json':continue
        members.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
    report=ROOT/'docs/tasks/A03-R1-final-correction-report.md'
    if report.exists():members.append(dict(path=report.relative_to(ROOT).as_posix(),bytes=report.stat().st_size,sha256=sha(report)))
    write(OUT/'manifest.json',dict(candidate=CANDIDATE,product=PRODUCT,members=members,
        excluded='raw runtime-view exports reconstructible from candidate; manifest self',old_evidence='unchanged Git blobs at 54e86adf'))
    print('FINAL_IMMUTABLE_COPY_AND_SOURCE_AUDIT_OK',len(audits),len(members))


if __name__=='__main__':main()
