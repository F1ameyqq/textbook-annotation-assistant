"""Publish hashes after finite execution; no product calls or additional SQL."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT=Path('D:/1800')
OUT=ROOT/'docs/evidence/I01-A/review'
REPORT=ROOT/'docs/tasks/I01-A-review-report.md'
os.environ['GIT_NO_LAZY_FETCH']='1'

def sha(b):return hashlib.sha256(b).hexdigest()
def save(path,obj):
    mode='wb' if path in (OUT/'manifest.json',OUT/'final-validation.json') and path.exists() else 'xb'
    with path.open(mode) as f:f.write((json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())

def main():
    audit=json.loads((OUT/'audit.json').read_bytes())
    release=json.loads((OUT/'release.json').read_bytes())
    assert audit['status']=='FINITE_CHECKS_PASSED_PENDING_REPORT' and release['status']=='RELEASED'
    assert audit['targets']==audit['dispatches']==audit['annotation_effects']==3
    assert audit['business_failures']==audit['business_reruns']==0
    assert release['runtime_owner_pid_empty'] and release['runtime_lease']==0
    assert release['registered_processes']==19
    text=REPORT.read_text(encoding='utf8')
    assert not any(line.rstrip()!=line for line in text.splitlines())
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',text):
        p=(REPORT.parent/target).resolve()
        if p==OUT/'manifest.json':continue
        assert p.exists(),target
        links.append(target)
    invocation=json.loads((OUT/'independent-invocation.json').read_bytes())
    candidate_root=Path(invocation['cwd'])
    native=json.loads((candidate_root/'tests/fixtures/i01/N/initial.json').read_bytes())
    assert native['format_version']=='a03-exchange-4-proposal'
    assert {a['schema_version'] for a in native['artifacts']}=={'1.4.0-a03-native-proposal'}
    for p in ('N','E','U-recover'):
        r=json.loads((OUT/'independent/run/cases'/p/'result.json').read_bytes())
        posts=[a for a in r['bundle']['artifacts'] if a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY']
        assert len(posts)==1 and posts[0]['payload']['decision']=='HOLD'
    index_path=Path(subprocess.check_output(['git','-c','core.longpaths=true','-C',str(ROOT),'rev-parse','--path-format=absolute','--git-path','index']).decode().strip())
    validation=dict(status='ACCEPTED_FINITE_I01_A_OFFLINE_ONLY',report_links_checked=len(links),trailing_whitespace=False,native_format=native['format_version'],schema_versions=sorted({a['schema_version'] for a in native['artifacts']}),report_decision='HOLD with frame_structure PASS and content PENDING',main_index_current_sha256=sha(index_path.read_bytes()),reviewer_wrote_main_index=False,business_calls_during_finalization=0,at_ns=time.time_ns())
    save(OUT/'final-validation.json',validation)
    paths=[REPORT]+sorted(p for p in OUT.rglob('*') if p.is_file() and p!=OUT/'manifest.json')
    rows=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in paths]
    assert len({r['path'] for r in rows})==len(rows)
    manifest=dict(status='ACCEPTED',boundary='A01 public offline consumption and N/E/U fixed synthetic paths only; B reception and joint business remain separate',base='a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8',candidate='be68b8d7c645de556d601458d1d493258f063721',delivery='3fdc5d37e221fc73410f197605f5d7b8878182d5',workflow='1534616372e977ddadb2918fbd29044290c263cf',product='6097a06de937fee8876feccedf46920510850b83',independent_targets=3,independent_dispatches=3,independent_annotation_effects=3,independent_operator_changes=1,business_failures=0,business_reruns=0,content_check_status='PENDING',submission_status='NOT_SUBMITTED',author_manifest_members_verified=665,implementation_pins_verified=30,actual_import_records_verified=140,own_quiescent_database_pairs=5,registered_business_processes=19,release='docs/evidence/I01-A/review/release.json',report='docs/tasks/I01-A-review-report.md',files=rows,excluded=[dict(path='docs/evidence/I01-A/review/manifest.json',reason='self hash supplied in final receipt')],main_index_write_performed=False,static_failures_preserved=['static-search-first-tool-failure.json','static-closure/first-audit-tool-failure.json','static-closure/first-publication-tool-failure.json','static-closure/manifest-metadata-edit-first-tool-failure.json'])
    save(OUT/'manifest.json',manifest)
    # Verify the published manifest without modifying evidence or invoking business.
    for row in rows:
        p=ROOT/row['path'];assert p.stat().st_size==row['bytes'] and sha(p.read_bytes())==row['sha256']
    assert {p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and p!=OUT/'manifest.json'} | {REPORT.relative_to(ROOT).as_posix()} == {row['path'] for row in rows}
    for p in (REPORT,OUT/'manifest.json',OUT/'release.json'):
        print(json.dumps(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p.read_bytes())),ensure_ascii=False))
    print(json.dumps(dict(status='ACCEPTED_FINITE_I01_A_OFFLINE_ONLY',manifest_members=len(rows),local_links_checked=len(links),targets=3,dispatches=3,business_reruns=0)))

if __name__=='__main__':main()
