"""Seal only new review files as raw Git blobs; no suite/product execution."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path('D:/1800-worktrees/a11-r')
E=ROOT/'docs/evidence/A11/review'
BASE='c580ca63ada9e452fd5ee71e5272cf0d047d4574'
AUTHOR_BASE='87f55ff636e463053f0b3c3ec97b0692511a06d0'
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1')
def git(*args,input=None):
    return subprocess.check_output(['git','-c','core.longpaths=true',*args],cwd=ROOT,env=ENV,input=input)
def tree(ref):
    result={}
    for row in git('ls-tree','-r','-z',ref).split(b'\0'):
        if row:
            info,path=row.split(b'\t',1)
            result[path.decode('utf-8')]=info.decode('ascii')
    return result
def save(name,value):
    (E/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
baseline=tree(BASE)
old=tree(AUTHOR_BASE)
added=set(baseline)-set(old)
allowed_exact={'src/annotation/quality/live_pilot.py','tests/test_live_pilot_admission.py',
    'tests/test_live_pilot_journal.py','tests/test_live_pilot_readback.py','docs/live-pilot-runbook.md',
    'docs/tasks/A11-limited-live-runner-execution-report.md'}
allowed_prefix=('src/annotation/delivery/live_pilot/','src/annotation/runtime/live_pilot/',
    'tests/fixtures/live_pilot/','docs/evidence/A11/execution/')
assert all(p in allowed_exact or p.startswith(allowed_prefix) for p in added)
assert all(baseline.get(p)==identity for p,identity in old.items())
changed_product=git('diff','--name-only','f5e3d63e6e31a87eb2b45789dbebadf89b4ac81e',
    'ea5b62fd593041c29c00831ddb0eb453b0230307','--','src','tests').decode().splitlines()
assert changed_product==['src/annotation/delivery/live_pilot/plan.py']
fixture_catalog=json.loads((ROOT/'tests/fixtures/live_pilot/fixture-catalog.json').read_bytes())
report=ROOT/'docs/tasks/A11-limited-live-runner-independent-report.md'
links=[]
for target in re.findall(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8')):
    if '://' in target: continue
    path=(report.parent/target.split('#')[0]).resolve()
    if path==E/'review-raw-manifest.json': continue
    assert path.exists(),target
    links.append(target)
save('scope-and-document-check.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'author_added_paths':len(added),'all_author_additions_in_allowlist':True,
    'author_old_members_preserved':len(old),'only_candidate_product_change':changed_product,
    'report_links_checked':links,'missing_links':[],
    'review_allowed_additions':['docs/evidence/A11/review/','docs/tasks/A11-limited-live-runner-independent-report.md'],
    'product_or_test_calls':0,'review_scope':'static raw packaging only'})
paths=sorted([p for p in E.rglob('*') if p.is_file() and p.name!='review-raw-manifest.json']+[report])
manifest=[]
for path in paths:
    relative=path.relative_to(ROOT).as_posix()
    assert relative not in baseline
    raw=path.read_bytes()
    manifest.append({'path':relative,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                     'mode':'100644','type':'blob',
                     'blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()})
save('review-raw-manifest.json',{'author_final':BASE,'product_commit':'ea5b62fd593041c29c00831ddb0eb453b0230307',
    'review_branch':'codex/a11-live-pilot-review','decision':'REWORK_STATIC_GAPS_WITH_FIXED_SUITE_PASS',
    'suite_runs':1,'suite_successes':1,'raw_member_count_excluding_this_manifest':len(manifest),
    'raw_member_bytes_excluding_this_manifest':sum(x['bytes'] for x in manifest),
    'members':manifest})
paths.append(E/'review-raw-manifest.json')
relatives=[p.relative_to(ROOT).as_posix() for p in paths]
objects=git('hash-object','-w','--no-filters','--stdin-paths',input=('\n'.join(relatives)+'\n').encode('utf-8')).decode().splitlines()
assert len(objects)==len(paths)
index_data=b''.join(('100644 '+obj+'\t'+path+'\0').encode('utf-8') for obj,path in zip(objects,relatives))
git('update-index','-z','--index-info',input=index_data)
index_tree=git('write-tree').decode().strip()
staged=tree(index_tree)
assert all(staged.get(p)==value for p,value in baseline.items())
assert set(staged)-set(baseline)==set(relatives)
for p,obj in zip(paths,objects):
    assert git('cat-file','blob',obj)==p.read_bytes()
raw=(E/'review-raw-manifest.json').read_bytes()
print(json.dumps({'review_raw_members_excluding_manifest':len(manifest),
    'review_raw_bytes_excluding_manifest':sum(x['bytes'] for x in manifest),
    'review_manifest_sha256':hashlib.sha256(raw).hexdigest(),'new_paths_in_index':len(relatives),
    'author_final_paths_preserved':len(baseline),'staged_tree':index_tree}))
