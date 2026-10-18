# -*- coding: utf-8 -*-
"""Class-scoped source/contract and frozen process proof; no candidate calls."""
import ast
import copy
import json
from pathlib import Path
from evidence import OUT,EV,EX,BASE,TARGET,INDEX,MAP,raw,doc,sha,canon,author_key,write,load
checks=[]
def check(name,value):checks.append({'check':name,'passed':bool(value)})
def entity(path,cls,name,rev=TARGET):
    source=raw(path,rev).decode('utf8',errors='strict');tree=ast.parse(source,filename=path);scope=tree
    if cls:scope=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    node=next(n for n in scope.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return node,{'path':path,'class':cls,'method':name,'line':node.lineno,'end_line':node.end_lineno,
      'raw_sha256':sha(raw(path,rev)),'source':ast.get_source_segment(source,node)}
ST='src/annotation/runtime/storage/__init__.py';NA='src/annotation/runtime/storage/native.py'
RE='src/annotation/contracts/recovery.py';VA='src/annotation/contracts/validation.py';NC='src/annotation/contracts/a03_native/__init__.py'
NQ='src/annotation/runtime/recovery/native_quality.py';CL='src/annotation/contracts/a03_native/_closure.py'
methods={};nodes={}
for path,cls,names in [(ST,'RuntimeStore',['commit_action_result','project_plan','_project_plan_locked','_project_unknown_diagnostic_post','_new_artifact','_append','_validate','transaction']),
 (NA,'NativeRuntimeStore',['_project_unknown_diagnostic_post','_append','bridge_for']),
 (NA,'NativeRegistry',['context']),(NC,None,['_issue_context','_validate_value','_reports','validate_native_bundle']),
 (CL,'StaticPackage',['validate']),(RE,None,['_legacy_projection','_receipts_progress']),
 (VA,None,['validate_bundle','_receipt','_check','subset']),(NQ,None,['publish_native_quality'])]:
    for name in names:
        node,value=entity(path,cls,name);key=(cls or 'module')+'.'+name;nodes[key]=node;methods[key]=value
base_projection,_=entity(ST,'RuntimeStore','_project_plan_locked',BASE)
normalized=copy.deepcopy(nodes['RuntimeStore._project_plan_locked'])
hook_conditions=[]
for n in ast.walk(normalized):
    if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and isinstance(n.test.op,ast.And):
        if any(isinstance(v,ast.Call) and isinstance(v.func,ast.Attribute) and v.func.attr=='_project_unknown_diagnostic_post' for v in n.test.values):
            hook_conditions.append(n.lineno);n.test=n.test.values[0]
check('projection unchanged apart from narrow policy condition',ast.dump(normalized,include_attributes=False)==ast.dump(base_projection,include_attributes=False))
for cls,key,expected in [('RuntimeStore','RuntimeStore._project_unknown_diagnostic_post',True),('NativeRuntimeStore','NativeRuntimeStore._project_unknown_diagnostic_post',False)]:
    returns=[n.value.value for n in ast.walk(nodes[key]) if isinstance(n,ast.Return) and isinstance(n.value,ast.Constant)]
    check(cls+' policy literal',returns==[expected])
old_profile=doc('src/annotation/contracts/a03_native/data/profile.json',BASE);new_profile=doc('src/annotation/contracts/a03_native/data/profile.json')
old_pins=dict(old_profile['implementation_pins']);new_pins=dict(new_profile['implementation_pins'])
pin_changes=sorted(p for p in old_pins if old_pins[p]!=new_pins[p])
check('exactly two implementation pin changes',pin_changes==['@annotation/runtime/storage/__init__.py','@annotation/runtime/storage/native.py'])
old_copy=copy.deepcopy(old_profile);old_copy['implementation_pins']=new_profile['implementation_pins']
check('other profile fields unchanged',old_copy==new_profile)
adopt='src/annotation/contracts/a03_native/data/adoption.json';old_a=doc(adopt,BASE);new_a=doc(adopt)
check('adoption only profile binding',dict(old_a,profile_sha256=new_a['profile_sha256'])==new_a and new_a['profile_sha256']==sha(raw('src/annotation/contracts/a03_native/data/profile.json')))
for path,h in new_profile['implementation_pins']:
    p='src/'+path[1:] if path.startswith('@') else 'src/annotation/contracts/a03_native/'+path
    check('implementation pin '+p,sha(raw(p))==h)
for path,h in new_profile['schema_pins']:
    p='src/annotation/contracts/a03_native/data/'+path;check('schema pin '+p,sha(raw(p))==h)
def tree_bytes(path):
    result={}
    for row in path.read_bytes().split(b'\0'):
        if row:
            meta,name=row.split(b'\t',1);result[name.decode()]=meta.decode()
    return result
old_tree=tree_bytes(OUT/'git-processes/01/stdout.bin');target_tree=tree_bytes(OUT/'git-processes/03/stdout.bin')
unchanged=[]
for p in (RE,VA,NC,CL,NQ):
    check('pre-existing unchanged contract/bridge '+p,old_tree[p]==target_tree[p])
    unchanged.append({'path':p,'base_mode_type_blob':old_tree[p],'target_mode_type_blob':target_tree[p],'raw_sha256':sha(raw(p))})
projection=nodes['RuntimeStore._project_plan_locked'];append_receipts=[];issue_nodes=[]
for n in ast.walk(projection):
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='_append' and any(isinstance(a,ast.Name) and a.id=='receipt' for a in n.args):append_receipts.append(n.lineno)
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='issues' for t in n.targets):issue_nodes.append(n)
check('receipt validation precedes policy',len(append_receipts)==1 and len(hook_conditions)==1 and append_receipts[0]<hook_conditions[0])
base_issues=next(n for n in ast.walk(base_projection) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='issues' for t in n.targets))
check('UNKNOWN issue derivation existed before repair',len(issue_nodes)==1 and ast.dump(issue_nodes[0],include_attributes=False)==ast.dump(base_issues,include_attributes=False))
schema=doc('src/annotation/contracts/a03_native/data/schemas/exchange.json')
post_schema=schema['$defs']['AmendedCheckReport']['properties']['payload']['oneOf'][2]
receipt_schema=schema['$defs']['AmendedExecutionReceipt']['properties']['payload']
write(OUT/'reference-chain-review.json',{'status':'FROZEN_EARLIER_RECEIPT_CLOSURE_GAP_CONFIRMED' if all(c['passed'] for c in checks) else 'EVIDENCE_INCONSISTENCY',
 'checks':checks,'failed_checks':[c for c in checks if not c['passed']],'class_scoped_methods':methods,
 'receipt_append_line':append_receipts,'later_report_policy_condition_line':hook_conditions,
 'unchanged_contract_and_bridge_sources':unchanged,'profile_pin_changes':pin_changes,
 'native_receipt_schema':receipt_schema,'native_POST_issues_schema':post_schema['properties']['issues'],
 'native_POST_required':post_schema['required'],'native_root_artifact_registry':schema['properties']['artifacts']['items'],
 'ownership_gap':'Runtime derives SAVE_UNKNOWN issue locally, receipt keeps the ID, no native formal issue owner is present; C01 checks IDs only against CheckReport issues after native POST is excluded and fact/progress detail is stripped.',
 'fix_requires_explicit_issue_ownership_bridge_decision':True,'product_imports_or_calls':0,'SQL_connections_in_this_script':0})

release=doc(EV+'sealing/process-release-proof.json');source_index=doc(EX+'inputs.json');index_hash=sha(raw(EX+'inputs.json'))
raw_to_checkout={r['path']:r for r in load(OUT/'delivery-byte-review.json')['checkout_vs_raw']}
def verify_source(path,digest):
    key=author_key(path);record=raw_to_checkout[key];check('actual imported/source checkout '+key,record['checkout_index_sha256']==digest)
    return {'path':key,'actual_checkout_sha256':digest,'raw_git_sha256':record['raw_sha256'],'representation':record['representation']}
processes=[]
for row in release['processes']:
    start=doc(row['start']);end=doc(row['completion']);directory=row['start'].rsplit('/',1)[0]+'/'
    pre=doc(directory+'preregistered.json');check('historical PID '+str(row['pid']),row['pid']==start['pid']==end['pid'])
    check('historical completion '+str(row['pid']),row['exit_code']==end['exit_code'] and not row['alive'] and not row['timeout'] and not end['alive'] and not end.get('timeout',end.get('timed_out',False)))
    sources=pre['script_sha256'];source_records=[]
    if isinstance(sources,dict):
        source_records=[verify_source(p,h) for p,h in sources.items()]
    elif isinstance(sources,str):
        matches=[p for p,h in source_index['files'].items() if h==sources]
        check('registered script digest belongs to frozen checkout',bool(matches));source_records=[verify_source(p,sources) for p in matches]
    if pre.get('source_index_sha256'):check('historical source index hash',pre['source_index_sha256']==index_hash)
    streams={}
    for stream in ('stdout','stderr'):
        choices=[directory+stream+suffix for suffix in ('.bin','.txt') if (TARGET,directory+stream+suffix) in MAP]
        check('one raw stream '+directory+stream,len(choices)==1)
        body=raw(choices[0]);streams[stream]={'path':choices[0],'sha256':sha(body)}
        if stream+'_sha256' in row:check('release raw stream hash '+choices[0],sha(body)==row[stream+'_sha256'])
        if stream+'_sha256' in end:check('completion raw stream hash '+choices[0],sha(body)==end[stream+'_sha256'])
    processes.append({'record':directory,'pid':row['pid'],'actual_exit':end['exit_code'],'registered_expected_exit':pre.get('expected_exit'),
      'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],'streams':streams,'sources':source_records,'alive_at_wait':False,'timed_out':False})
check('23 actual historical processes',len(processes)==release['count']==23)
check('two actual functional exit1',sum(p['actual_exit']==1 for p in processes)==2)
imports=[]
for r in INDEX:
    if r['commit']==TARGET and r['path'].startswith(EV+'validation/author-01/') and ('/imports/' in r['path'] or '/import-processes/' in r['path']) and r['path'].endswith('.json'):
        data=doc(r['path']);modules=data.get('modules',data.get('imports',data))
        for name,value in modules.items():
            if isinstance(value,dict) and {'path','sha256'}<=set(value):
                imports.append({'record':r['path'],'module':name,**verify_source(value['path'],value['sha256'])})
stderr=raw(EV+'validation/author-01/processes/U1-execute/stderr.txt').decode('utf8',errors='strict')
check('observed exact failure','$.artifacts[10].payload.unresolved_issue_ids[0]: [MISSING_REFERENCE] unknown reference issue-save-unknown-1c539a7e21cad8405cbf61cb958992af' in stderr)
correction=doc(EV+'metadata-correction.json')
write(OUT/'process-source-review.json',{'status':'HISTORICAL_WAIT_SOURCE_AND_STREAMS_RECONCILED' if all(c['passed'] for c in checks) else 'EVIDENCE_INCONSISTENCY',
 'checks':checks,'failed_checks':[c for c in checks if not c['passed']],'historical_processes':processes,'actual_import_records':imports,
 'count':len(processes),'current_PID_scan':False,'source_index_hash':index_hash,'source_index_kind':'EXECUTION_CHECKOUT_BYTES_NOT_UNIFORM_RAW_GIT',
 'author_metadata_correction':correction,'author_first_archive_error_sha256':sha(raw(EV+'first-archive-error.txt')),
 'observed_error':stderr,'product_imports_or_calls':0,'new_functional_scenarios':0})
print(json.dumps({'status':'CHAIN_AND_PROCESS_REVIEW_COMPLETED','checks':len(checks),'failed_checks':sum(not c['passed'] for c in checks),
 'historical_processes':len(processes),'actual_import_records':len(imports),'product_calls':0}))
