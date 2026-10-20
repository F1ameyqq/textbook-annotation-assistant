"""Freeze revision review. File/AST/Git reads only, no product execution."""
import ast
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path('D:/1800-worktrees/a16-r1-review').resolve()
REPO=Path('D:/1800')
OUT=ROOT/'docs/evidence/A16/independent-r1-review'
E=ROOT/'docs/evidence/A16/current-readonly/revisions/frame-binding-r1'
OLD='4fe417d5246f20fbbbedc577495c7ca400d4ded8'
CANDIDATE='071340237c76a7159bd90485e17a774c2f870114baef0199172a2fc5f9547efc'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def save(name,data):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n')

inputs=load(OUT/'input-raw-manifest.independent.json')['members']
for item in inputs:
    raw=(ROOT/item['path']).read_bytes()
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],item['path']
freeze=load(OUT/'independent-input-freeze.json')['members']
for item in freeze:
    raw=(OUT/item['path']).read_bytes()
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
for item in load(OUT/'revision-suite-copy-manifest.json')['members']:
    raw=(OUT/item['path']).read_bytes()
    assert sha(raw)==item['sha256'] and len(raw)==item['bytes']
    assert raw==(E/'test-runs/independent-r1-01'/Path(item['path']).name).read_bytes()

def definition(text,name):
    node=ast.parse(text)
    for part in name.split('.'):
        node=next(n for n in node.body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==part)
    return ast.get_source_segment(text,node)

reuse={
    'src/annotation/source/usense/current_readonly/policy.py':['parts','key','diagnostic','ReadPolicy.decide','ReadPolicy.register_original'],
    'src/annotation/source/usense/current_readonly/decode.py':['content_state','bound_content','source_page','sample_order','validate_draft'],
    'src/annotation/source/usense/current_readonly/gate.py':['fixed_fields','validate_activation','context_options','marker'],
    'tools/a16_current_state_probe.py':['CurrentGuard','get_once','visible_mapping','original_once']}
same=[]
for path,names in reuse.items():
    raw=subprocess.check_output(['git','-c','core.longpaths=true','show',OLD+':'+path],
        cwd=str(REPO),env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
    old_text=raw.decode();new_text=(ROOT/path).read_text(encoding='utf-8')
    for name in names:
        before,after=definition(old_text,name),definition(new_text,name)
        assert before==after,(path,name)
        same.append({'path':path,'definition':name,'source_sha256':sha(after.encode()),
            'previous_final':OLD,'meaning':'Unchanged source only; changed globals/callees tested separately and not certified by this equality'})
save('unchanged-source-evidence.json',{'task':'A16','definitions_byte_equal':same,
    'gate_workflow_changed':'New workflow retested by revision75; source equality alone is not activation acceptance',
    'original_info_changed_callee':'Full image decode independently tested',
    'parser_and_sample_binding_changed':'New suite and independent controls; parser reserved-word finding remains REWORK'})

archive=E/'authority/independent-fixed'
old_manifest=(archive/'raw-manifest.json').read_bytes()
assert sha(old_manifest)=='922217dbcc59faea36efbcc30382784676442b2752fbbbcfd759344e0bad9e7f'
old_members=load(archive/'raw-manifest.json')['members']
for item in old_members:
    raw=(archive/item['path']).read_bytes()
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],item['path']
assert len(old_members)==31

result=load(OUT/'review-result.json')
assert result['task']=='A16' and result['result']=='REWORK' and result['candidate_manifest_sha256']==CANDIDATE
controls=load(OUT/'independent-controls-result.json')
assert len(controls['cases'])==13 and controls['resource_attempts']==[]
assert sum(c['status']=='PASS' for c in controls['cases'])==12
report=(OUT/'REPORT.md').read_text(encoding='utf-8')
deferred={'release.json','raw-manifest.json','final-preservation.json'}
links=re.findall(r'\]\(([^)]+)\)',report)
for link in links:
    path=(OUT/link).resolve();assert ROOT in path.parents and '://' not in link
    if link not in deferred:assert path.is_file(),link
for path in OUT.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
now=datetime.now(timezone(timedelta(hours=8))).isoformat()
save('final-preservation.json',{'task':'A16','at':now,'result':'PASS_EVIDENCE_PRESERVATION_ONLY',
    'fixed_raw111_unchanged':True,'independent_inputs_frozen_and_unchanged':True,
    'revision_suite_raw_copies_equal':True,'original_independent31_members_archive_preserved':True,
    'unchanged_source_definitions_verified':len(same),'report_links_verified':len(links),
    'base31259_and_old39':'Independent raw preflight PASS; no Git mutation or product write occurred',
    'review_script_AST_parse':'PASS','product_retested_by_finalizer':False,'acceptance':'REWORK'})
child_records=load(OUT/'revision-command-results.json')['commands']+load(OUT/'independent-command-results.json')['commands']
save('release.json',{'task':'A16','revision':'same-stage-R01-R04','candidate_manifest_sha256':CANDIDATE,
    'result':'REWORK','state':'REWORK_RELEASED','at':now,
    'review_thread_id':'01a15841-0d44-7272-9740-40d013839869',
    'resources':{'real_browser':0,'network':0,'profile_credentials':0,'real_native_API':0,
        'occupancy_scan':0,'login':0,'upload_OCR':0,'business':0,'old_suites':0,'B_or_other_chat_messages':0},
    'resource_attempts':[],'children':[{'name':c['name'],'pid':c['pid'],'wait_completed':c['wait_completed'],
        'exit_code':c['exit_code']} for c in child_records],
    'OS_creation_identity':'NOT_HELD_NOT_CLAIMED; no own-process OS exit or machine-wide process absence assertion',
    'pending_real_resources':0,'JS_checks':'Syntax-only; no JS source execution',
    'first_unexpected_failure':'R2_RESERVED_GETTER_SYNTAX; no later product rerun/repair',
    'live_activated':False,'TLS_approved':False,'first_save_content_refresh_reopen':'NOT_RUN',
    'author_product_modified':False,'root_tasks_or_JSON_written':False,
    'outputs':['D:/1800-worktrees/a16-r1-review/docs/evidence/A16/independent-r1-review/',
        'D:/1800-worktrees/a16-r1-review/docs/evidence/A16/current-readonly/revisions/frame-binding-r1/test-runs/independent-r1-01/'],
    'next_dependency':'Coordinator handles R02 same-stage correction/new frozen delivery; no reviewer activation or product repair'})

members=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw=path.read_bytes()
        if path.suffix=='.json':json.loads(raw)
        members.append({'path':path.relative_to(OUT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
save('raw-manifest.json',{'schema':'A16-independent-r1-review/v1','task':'A16','result':'REWORK',
    'candidate_manifest_sha256':CANDIDATE,'at':now,'member_count':len(members),'self_excluded':True,'members':members})
for item in members:
    assert sha((OUT/item['path']).read_bytes())==item['sha256']
print(json.dumps({'result':'REWORK','release':'REWORK_RELEASED','members':len(members),
    'manifest_sha256':sha((OUT/'raw-manifest.json').read_bytes()),
    'report_sha256':sha((OUT/'REPORT.md').read_bytes()),'result_json_sha256':sha((OUT/'review-result.json').read_bytes()),
    'raw111_preserved':True,'old_review31_preserved':True,'unchanged_definitions':len(same)}))
