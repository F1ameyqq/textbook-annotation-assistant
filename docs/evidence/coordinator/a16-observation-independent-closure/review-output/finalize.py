"""Freeze bounded offline observation review. No product execution or live documents created."""
import ast
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path('D:/1800-worktrees/a16-observation-review').resolve();REPO=Path('D:/1800')
OUT=ROOT/'docs/evidence/A16/independent-observation-review'
E=ROOT/'docs/evidence/A16/current-readonly/revisions/observation-only'
PARENT='8ab0944116b5230b8e69c2f129b635435c243d55'
CANDIDATE='e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_bytes())
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def old(path):return subprocess.check_output(['git','-c','core.longpaths=true','show',PARENT+':'+path],
    cwd=str(REPO),env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
def definition(text,name):
    node=ast.parse(text)
    for part in name.split('.'):
        node=next(n for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.name==part)
    return ast.get_source_segment(text,node)
def assignment(text,name):
    def names(node):
        if isinstance(node,ast.Name):return [node.id]
        if isinstance(node,(ast.Tuple,ast.List)):return [x for item in node.elts for x in names(item)]
        return []
    for node in ast.parse(text).body:
        if isinstance(node,ast.Assign) and any(name in names(t) for t in node.targets):return ast.get_source_segment(text,node)
    raise AssertionError('Assignment missing '+name)

inputs=load(OUT/'input-raw-manifest.independent.json')['members']
for item in inputs:
    raw=(ROOT/item['path']).read_bytes();assert len(raw)==item['size'] and sha(raw)==item['sha256']
freeze=load(OUT/'independent-input-freeze.json');raw=(OUT/freeze['script']).read_bytes()
assert len(raw)==freeze['bytes'] and sha(raw)==freeze['sha256']
for item in load(OUT/'suite-copy-manifest.json')['members']:
    raw=(OUT/item['path']).read_bytes()
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
    assert raw==(E/'test-runs/independent-observation-01'/item['source_relative']).read_bytes()

reuse={'tools/a16_current_state_probe.py':['supervise','worker_succeeded','occupancy','open_owned','visible_mapping',
    'original_once','drain','await_existing_response','CurrentGuard.route','CurrentGuard.paused','CurrentGuard.websocket',
    'CurrentGuard.child_target','CurrentGuard.record_failure','CurrentGuard.audit','CurrentGuard.denied','CurrentGuard.response'],
    'src/annotation/source/usense/current_readonly/policy.py':['parts','key','diagnostic','ReadPolicy.register_original'],
    'src/annotation/source/usense/current_readonly/gate.py':['same_typed','unique_json','parse_utc','context_options']}
verified=[]
for path,names in reuse.items():
    before=old(path).decode();after=(ROOT/path).read_text(encoding='utf-8')
    for name in names:
        a,b=definition(before,name),definition(after,name);assert a==b,(path,name)
        verified.append({'path':path,'definition':name,'source_sha256':sha(b.encode()),'parent_final':PARENT})
for path,names in {'src/annotation/source/usense/current_readonly/policy.py':['PREFIX','FIXED','SESSION','STATIC','PASSIVE','OSS'],
    'src/annotation/source/usense/current_readonly/gate.py':['OWNER','COORDINATOR','RUN_ID','BOOK','VIEWERS','ORIGIN','TARGET','OUTPUT','ACTIVATION'],
    'tools/a16_current_state_probe.py':['TOTAL_SECONDS']}.items():
    before=old(path).decode();after=(ROOT/path).read_text(encoding='utf-8')
    for name in names:
        a,b=assignment(before,name),assignment(after,name);assert a==b,(path,name)
        verified.append({'path':path,'assignment':name,'source_sha256':sha(b.encode()),'parent_final':PARENT})
whole=['src/annotation/source/usense/current_readonly/decode.py','src/annotation/source/usense/current_readonly/js_wire.py',
    'tools/a16_current_state_launcher.py']
for path in whole:assert (ROOT/path).read_bytes()==old(path),path
# The remaining decide body is identical after removing only the new hard-deny
# branch. This proves helpers/static permissions were not broadened.
path='src/annotation/source/usense/current_readonly/policy.py'
before=definition(old(path).decode(),'ReadPolicy.decide')
after=definition((ROOT/path).read_text(encoding='utf-8'),'ReadPolicy.decide')
branch="            if any(p.path == prefix or p.path.startswith(prefix + '/') for prefix in SAMPLE_PATHS):\n                return False, 'SAMPLE_DISABLED_OBSERVATION_ONLY'\n"
assert branch in after and after.replace(branch,'',1)==before
save('unchanged-source-evidence.json',{'task':'A16','parent_final':PARENT,'definitions_and_constants':verified,
    'whole_files_byte_equal':whole,'policy_decide_only_added_sample_hard_deny':True,
    'scope':'Source equality only. Retain prior finite pixel/Job/guard conclusions; no old suite rerun or new OS/platform proof.',
    'parser_correctness':'Old parser unchanged and disabled in collect; R02 remains REWORK'})

result=load(OUT/'review-result.json');template=load(E/'independent-report-template-NONEXECUTABLE.json')
for key,value in template.items():
    if key!='result':assert type(result[key]) is type(value) and result[key]==value
assert result['result']=='ACCEPTED_OFFLINE_ONLY' and result['candidate_manifest_sha256']==CANDIDATE
assert result['scope']=='CURRENT_BOOK_SOURCE_INVENTORY_STATIC_OBSERVATION_ONLY' and result['sample_limit']==0
assert result['automatic_schema_confirmation'] is False and not result['live_activated'] and not result['TLS_approved']
controls=load(OUT/'independent-controls-result.json')
assert len(controls['cases'])==9 and all(c['status']=='PASS' for c in controls['cases'])
assert controls['first_failure'] is None and controls['resource_attempts']==[] and controls['parser_qualification_calls']==[]
assert len(load(OUT/'scope-checks.json')['checks'])==7
report=(OUT/'REPORT.md').read_text(encoding='utf-8')
links=re.findall(r'\]\(([^)]+)\)',report);deferred={'release.json','final-preservation.json','raw-manifest.json'}
for link in links:
    target=(OUT/link).resolve();assert ROOT in target.parents and '://' not in link
    if link not in deferred:assert target.is_file(),link
for path in OUT.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
now=datetime.now(timezone(timedelta(hours=8))).isoformat()
save('final-preservation.json',{'task':'A16','at':now,'result':'PASS_FIXED_EVIDENCE_PRESERVATION',
    'raw59_unchanged':True,'input_script_frozen_and_unchanged':True,'suite_raw_copies_equal':True,
    'base31259_and_old_evidence136':'Independent raw preflight verified modes/types/blobs; no Git mutations occurred',
    'unchanged_definitions_constants_count':len(verified),'whole_unchanged_files':whole,
    'policy_helper_whitelist_unexpanded':True,'formal_report_scope_template_match':True,
    'report_links_verified':len(links),'review_scripts_AST_parse':'PASS','product_retested_by_finalizer':False,
    'old_R02':'REWORK_UNCHANGED','acceptance_scope':result['scope']})
children=load(OUT/'fixed-command-results.json')['commands']+[load(OUT/'controls-command-result.json')]
save('release.json',{'task':'A16','candidate_manifest_sha256':CANDIDATE,'result':'ACCEPTED_OFFLINE_ONLY',
    'scope':result['scope'],'sample_limit':0,'automatic_schema_confirmation':False,
    'state':'ACCEPTED_OFFLINE_OBSERVATION_ONLY_RELEASED','at':now,
    'review_thread_id':'01a15841-0d44-7272-9740-40d013839869',
    'protected_resources':{'real_browser':0,'network':0,'profile_credentials':0,'real_native_API':0,
        'occupancy_scan':0,'login':0,'upload_OCR':0,'business':0,'old_suites':0,'B_or_other_chat_messages':0},
    'resource_attempts':[],'parser_qualification_calls':[],'first_unexpected_failure':None,
    'children':[{'name':c.get('name','independent-controls'),'pid':c['pid'],'wait_completed':c['wait_completed'],
        'exit_code':c['exit_code']} for c in children],
    'OS_creation_identity':'NOT_HELD_NOT_CLAIMED; no own OS exit or machine-wide process absence assertion',
    'pending_real_resources':0,'only_synthetic_static_assets_in_package':True,
    'product_modified':False,'root_tasks_JSON_written':False,'live_authorized':False,'live_activated':False,'TLS_approved':False,
    'platform_first_save_refresh_reopen':'NOT_RUN','old_R02':'REWORK_UNCHANGED',
    'outputs':['D:/1800-worktrees/a16-observation-review/docs/evidence/A16/independent-observation-review/',
        'D:/1800-worktrees/a16-observation-review/docs/evidence/A16/current-readonly/revisions/observation-only/test-runs/independent-observation-01/'],
    'next_dependency':'Coordinator verifies this fixed limited report/release, obtains explicit this-run TLS decision, then separately binds/activates any live observation.'})
members=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw=path.read_bytes()
        if path.suffix=='.json':json.loads(raw)
        members.append({'path':path.relative_to(OUT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
save('raw-manifest.json',{'schema':'A16-independent-observation-review/v1','task':'A16','result':'ACCEPTED_OFFLINE_ONLY',
    'scope':result['scope'],'candidate_manifest_sha256':CANDIDATE,'at':now,'member_count':len(members),'self_excluded':True,'members':members})
for item in members:
    raw=(OUT/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
print(json.dumps({'result':'ACCEPTED_OFFLINE_ONLY','scope':result['scope'],
    'state':'ACCEPTED_OFFLINE_OBSERVATION_ONLY_RELEASED','members':len(members),
    'manifest_sha256':sha((OUT/'raw-manifest.json').read_bytes()),'report_sha256':sha((OUT/'REPORT.md').read_bytes()),
    'formal_result_sha256':sha((OUT/'review-result.json').read_bytes()),'raw59_preserved':True,
    'reused_source_definitions_constants':len(verified),'old_R02':'REWORK_UNCHANGED'}))
