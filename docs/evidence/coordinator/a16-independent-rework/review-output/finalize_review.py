"""Freeze reviewer evidence, verify inputs unchanged; no product import or execution."""
import ast
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT=Path('D:/1800-worktrees/a16-independent-fixed').resolve()
OUT=ROOT/'docs/evidence/A16/independent-offline-review'
COMPLETE=Path('D:/1800-worktrees/a16-independent-complete')
PREP=Path('D:/1800-worktrees/a16-review-preparation')


def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_bytes())
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


inputs=load(OUT/'input-raw-manifest.json')['members']
for item in inputs:
    a=(ROOT/item['path']).read_bytes();b=(COMPLETE/item['path']).read_bytes()
    assert a==b and len(a)==item['bytes'] and sha(a)==item['sha256'],item['path']
supplement=(COMPLETE/'src/annotation/__init__.py').read_bytes()
assert sha(supplement)=='a11279a7897a17523423f81c888a410edfb53c74d36435f7ab7c7cfacc67ca2d'
prep_manifest=(PREP/'raw-manifest.json').read_bytes()
assert sha(prep_manifest)=='f5c270c9ddaf53b18425e7e93be84a5b33b0df5474ae684cc2e2f752f3dca2d0'
prep=load(PREP/'raw-manifest.json')['members']
for item in prep:
    raw=(PREP/item['path']).read_bytes()
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256']

for folder,origin in [('initial-suite-raw',ROOT/'docs/evidence/A16/current-readonly/test-runs/independent-01'),
    ('supplemented-suite-raw',COMPLETE/'docs/evidence/A16/current-readonly/test-runs/independent-02')]:
    for path in (OUT/folder).iterdir():
        assert path.read_bytes()==(origin/path.name).read_bytes()

result=load(OUT/'review-result.json')
assert result['task']=='A16' and result['result']=='REWORK'
assert result['candidate_manifest_sha256']=='2579b043d65e665263796d0922f080ad101f4d20c1e9ea500fd7894ba41d966c'
matrix=load(OUT/'requirement-matrix-48.json')
assert len(matrix['requirements'])==48 and len({r['id'] for r in matrix['requirements']})==48
assert {r['id'] for r in matrix['requirements']}=={r['id'] for r in load(PREP/'acceptance-cases.v002.json')['cases']}
controls=load(OUT/'independent-controls-result.json')
assert Counter(r['status'] for r in controls['probes'])=={'PASS':12,'FAIL':1,'NOT_RUN':3}
assert controls['resource_attempts']==[]
for path in OUT.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'),filename=str(path))

report=(OUT/'REPORT.md').read_text(encoding='utf-8')
links=re.findall(r'\]\(([^)]+)\)',report)
deferred={'release.json','raw-manifest.json','final-preservation.json'}
for link in links:
    path=(OUT/link).resolve()
    assert ROOT in path.parents and '://' not in link,link
    if link not in deferred:assert path.is_file(),link
assert 'result=REWORK' in report

now=datetime.now(timezone(timedelta(hours=8))).isoformat()
save('final-preservation.json',{'task':'A16','result':'PASS_INPUT_AND_PACKAGE_CHECKS_ONLY',
    'at':now,'fixed49_members_unchanged':len(inputs),'supplemented50_same_final':True,
    'preparation37_members_unchanged':len(prep),'preparation_manifest_unchanged':True,
    'old31259_mode_type_blob_check':'PASS in initial independent raw preflight; no Git mutations performed',
    'initial_failure_and_supplemented_suite_raw_copies_equal':True,'prepared48_dispositions_complete':True,
    'review_scripts_ast_parse':'PASS','report_local_links_verified':len(links),
    'product_files_modified':False,'product_retested_by_this_finalizer':False,
    'acceptance_result_remains':'REWORK'})
save('release.json',{'task':'A16','role':'FORMAL_INDEPENDENT_OFFLINE_REVIEW',
    'review_thread_id':'01a15841-0d44-7272-9740-40d013839869','at':now,
    'candidate_manifest_sha256':result['candidate_manifest_sha256'],'result':'REWORK',
    'state':'REWORK_RELEASED','live_activated':False,'tls_approved':False,
    'real_resources':{'browser_contexts':0,'network_connections':0,'profile_reads':0,
        'credential_reads':0,'native_real_APIs':0,'real_occupancy_scans':0,'login_submissions':0,
        'business_writes':0,'upload':0,'OCR':0,'old_suites':0,'other_chat_or_B_messages':0},
    'offline_control_resource_attempts':[],
    'child_completion':[{'pid':70728,'wait_completed':True,'exit_code':1,'meaning':'initial loader failure retained'},
        {'pid':53424,'wait_completed':True,'exit_code':0,'meaning':'same-final supplemented suite33/33'}],
    'creation_identity':'NOT_OBSERVED; no OS creation-identity or own-process-exit claim',
    'independent_controls_shell_exit':1,'independent_controls_failure':'A16-R01 semantic counterexample; stopped successors',
    'later_product_probes':'C14 C15 C16 NOT_RUN; only separately authorized packaging-supplement suite ran afterward',
    'local_tooling_scope':'Synchronous file/Git/Python review tooling only; no background helper or real Job created',
    'handles_and_files':'Child pipes completed and tool processes returned; files context-managed; no real browser/native resources to release',
    'write_scope':['D:/1800-worktrees/a16-independent-fixed/docs/evidence/A16/independent-offline-review/',
        'D:/1800-worktrees/a16-independent-fixed/docs/evidence/A16/current-readonly/test-runs/independent-01/',
        'D:/1800-worktrees/a16-independent-complete/docs/evidence/A16/current-readonly/test-runs/independent-02/'],
    'author_product_and_root_tasks_JSON_modified':False,'save_content_refresh_reopen':'NOT_RUN',
    'next_dependency':'Same-stage coordinator disposition and newly frozen correction; no reviewer product repair or live activation.'})

members=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw=path.read_bytes()
        if path.suffix=='.json':json.loads(raw)
        members.append({'path':path.relative_to(OUT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
save('raw-manifest.json',{'schema':'A16-independent-offline-review-manifest/v1','task':'A16',
    'result':'REWORK','candidate_manifest_sha256':result['candidate_manifest_sha256'],
    'at':now,'member_count':len(members),'self_excluded':True,'members':members})
for item in members:
    raw=(OUT/item['path']).read_bytes()
    assert sha(raw)==item['sha256'] and len(raw)==item['bytes']
print(json.dumps({'result':'REWORK','release':'REWORK_RELEASED','members':len(members),
    'manifest_sha256':sha((OUT/'raw-manifest.json').read_bytes()),
    'report_sha256':sha((OUT/'REPORT.md').read_bytes()),
    'result_json_sha256':sha((OUT/'review-result.json').read_bytes()),
    'input49_and_prep37_preserved':True,'supplement_same_final50_verified':True}))
