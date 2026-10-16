"""Consolidate actual command receipts, matrix coverage and immutable-source checks."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path('D:/1800')
OUT=Path(__file__).resolve().parent
STAGE=ROOT/'.local/stages/A02-review/frozen-5c928572'
COMMIT='5c9285720c8628c5198bedeadfc9f6bc7826a914'

def load(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

export=load(OUT/'frozen-export.json')
mismatches=[e['path'] for e in export['files'] if sha(STAGE/e['path'])!=e['sha256']]
preparation=load(OUT.parent/'sha256-manifest.json')
preparation_mismatches=[e['path'] for e in preparation['files'] if sha(ROOT/e['path'])!=e['sha256']]
imports={}
for folder in ('delivery/mock','delivery/planner','quality/targetcheck'):
    path=STAGE/'src/annotation'/folder/'__init__.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    imports[str(path.relative_to(STAGE))]=[{'module':node.module,'names':[n.name for n in node.names]} if isinstance(node,ast.ImportFrom) else {'module':None,'names':[n.name for n in node.names]} for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom))]
    assert not any(isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('annotation.contracts.') for n in ast.walk(tree))
report_sha=sha(STAGE/'docs/tasks/A02-execution-report.md')
assert report_sha=='d8c0cfc961a0ac7a1d78a4ca8cfa235bb26a20ee1c3af5c0bbedc6ab492eddda'
assert not mismatches and not preparation_mismatches
save(OUT/'source-integrity.json',{'frozen_commit':COMMIT,'exported_files_reverified':len(export['files']),'source_mismatches':mismatches,
    'preparation_files_preserved':len(preparation['files']),'preparation_mismatches':preparation_mismatches,'frozen_execution_report_sha256':report_sha,
    'changed_paths':len(export['changed_paths']),'out_of_scope':export['out_of_scope'],'imports':imports,
    'scope_note':'All original exported Git blob bytes reverified after tests. Review scripts are separate; no changes to implementation, contracts, task state or preparation artifacts.'})
original=load(OUT/'independent/results.json')
supp=load(OUT/'independent/supplement-results.json')
last=load(OUT/'independent/final-supplement-results.json')
allresults=original['results']+supp['results']+last['results']
coverage={}
for r in allresults:
    if r['status']=='PASS':
        for matrix in r['matrix_ids']:
            coverage.setdefault(matrix,[]).append('independent/cases/'+r['name']+'/observation.json')
for matrix,evidence in [('F01','frozen-export.json'),('F02','source-integrity.json'),('U11','source-integrity.json'),('B05','reproduction/manifest.json')]: coverage.setdefault(matrix,[]).append(evidence)
rows=[]
for group,count in [('F',5),('G',20),('I',9),('S',8),('E',9),('U',11),('B',5)]:
    for num in range(1,count+1):
        matrix=group+str(num).zfill(2)
        assert matrix in coverage,matrix
        status='FAIL' if matrix=='U05' else 'PASS_STATIC' if matrix in ('F01','F02','U11') else 'PASS_WITH_BOUNDARY_NOTE' if matrix=='B05' else 'PASS'
        evidence=coverage[matrix]
        if matrix=='U05': evidence=evidence+['counterexamples/crossbook/observations.json']
        rows.append({'matrix_id':matrix,'status':status,'evidence':evidence,'note':'Separate-package isolation passes; legal multibook history bundle incorrectly pauses unrelated book (R1).' if matrix=='U05' else 'Only declared synthetic inputs exercised; OBSERVED registry label admission is a separate boundary observation N2.' if matrix=='B05' else ''})
save(OUT/'matrix-results.json',{'commit':COMMIT,'matrix_rows':rows,'matrix_count':len(rows),'formal_decision':'REWORK',
    'independent_scenario_invocations':len(allresults),'independent_passed_invocations':sum(r['status']=='PASS' for r in allresults),
    'review_harness_error_invocations':[{'name':r['name'],'error':r['error'],'superseded_by':'independent/cases/stale-policy-rechecked/observation.json'} for r in allresults if r['status']!='PASS'],
    'product_failure':'R1 cross-book history contamination; probes exit 0 means defect reproduced, not acceptance'})
reproduced=load(OUT/'reproduction/manifest.json')
save(OUT/'reproduction-bindings.json',{'frozen_commit':COMMIT,'actual_source_integrity':'source-integrity.json',
    'author_reproducer_manifest_code_commit':reproduced['code_commit'],'author_manifest_code_commit_trusted':False,
    'explanation':'The exported tree has no .git. The author verify.py git rev-parse walks to the concurrently maintained D:/1800 parent repository. Its code_commit field is not used as source identity; every imported source file is bound to the fixed Git blob export instead.',
    'author_commands':reproduced['commands'],'author_test_totals':{'a02':44,'c01':70,'demos':10},'all_author_command_exits_zero':all(r['exit_code']==0 for r in reproduced['commands'])})
save(OUT/'independent-command-receipts.json',{
    'frozen_commit':COMMIT,'cwd':'D:/1800','environment':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(STAGE/'src')},
    'commands':[
      {'command':'python docs/evidence/A02/review/formal/export_frozen.py','exit_code':0,'evidence':'frozen-export.json'},
      {'command':'python docs/evidence/A02/review/formal/run_commands.py','exit_code':0,'evidence':'commands.json'},
      {'command':'python docs/evidence/A02/review/formal/independent_review.py','exit_code':1,'evidence':'independent/results.json','reason':'60 pass, 1 reviewer shallow-copy input bug; no product failure counted here.'},
      {'command':'python -B docs/evidence/A02/review/formal/independent_review.py --supplement','exit_code':0,'evidence':'independent/supplement-results.json','reason':'9 pass including corrected stale-policy case; original error evidence preserved.'},
      {'command':'python -B docs/evidence/A02/review/formal/probe_crossbook.py','exit_code':0,'evidence':'counterexamples/crossbook/observations.json','reason':'Asserts and reproduces product defect R1.'},
      {'command':'python -B docs/evidence/A02/review/formal/probe_coverage_labels.py','exit_code':0,'evidence':'counterexamples/coverage-labels/summary.json','reason':'Asserts two supplementary boundary observations; no executor invoked.'},
      {'command':'python -B docs/evidence/A02/review/formal/supplement_final.py','exit_code':0,'evidence':'independent/final-supplement-results.json','reason':'2 targeted checks pass.'},
      {'command':'python -B docs/evidence/A02/review/formal/consolidate.py','exit_code':0,'evidence':'matrix-results.json'}],
    'script_revision_note':'The reviewer shallow-copy bug was corrected and only the affected policy check plus previously uncovered scenarios were run. Scripts now accept new output directories where applicable; original observations are retained.',
    'platform_actions':0,'browser_actions':0,'credential_access':0,'external_model_calls':0,'external_model_cost':0})
print(json.dumps({'source_files_verified':len(export['files']),'matrix_count':len(rows),'independent_passes':sum(r['status']=='PASS' for r in allresults),'review_harness_errors':sum(r['status']!='PASS' for r in allresults),'formal_decision':'REWORK'}))
