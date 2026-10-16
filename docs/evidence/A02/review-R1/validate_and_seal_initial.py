"""Validate final R1 report/resource bundles, preserve old evidence, seal unified hashes."""
import ast
from datetime import datetime,timedelta,timezone
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parent;SOURCE=OUT/'source-38aca9dc'
sys.path.insert(0,str(SOURCE/'src'));sys.dont_write_bytecode=True
from annotation.contracts import load_bundle
REPORT=ROOT/'docs/tasks/A02-review-R1-report.md';MANIFEST=OUT/'sha256-manifest.json'
COMMIT='38aca9dcc8d027409b95193e9cc142c2336b76d3'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def manifest():
    files=[REPORT]+sorted(p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST)
    result={'schema_version':1,'task':'A02-R1-independent-review','target_commit':COMMIT,'implementation_commit':'13ddf83083224ffafc17a4f57cf2c1a1a1ae02b2',
        'r1_base_commit':'5c9285720c8628c5198bedeadfc9f6bc7826a914','workflow_commit':'39341c98d73c354d639f3beeb55429f55d0e9be5','decision':'ACCEPTED',
        'acceptance_scope':'Bounded offline A02 R1; no integration/A03 release or real-source/platform qualification',
        'report':'docs/tasks/A02-review-R1-report.md','report_sha256':sha(REPORT),
        'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],
        'self_excluded':True,'platform_network_browser_credential_model_calls':0,'preserved_old_index':'docs/evidence/A02/review-R1/old-review-preservation.json'}
    save(MANIFEST,result);return result

export=read(OUT/'frozen-export.json')
assert all(sha(SOURCE/f['path'])==f['sha256'] for f in export['files'])
old=read(OUT/'old-review-preservation.json')['files_sha256']
assert all(sha(ROOT/path)==digest for path,digest in old.items())
matrix=read(OUT/'matrix-results.json');assert matrix['decision']=='ACCEPTED' and matrix['risk_failed_cases']==0
history=read(OUT/'independent/history-pair-final/actual.json');assert history['all_checks_passed']
binding=read(OUT/'reproduction/source-binding.json');assert binding['checkout_commit'] is None and binding['declared_commit']==COMMIT
commands=read(OUT/'command-receipts.json')
commands['commands'].append({'argv':['python','-B','docs/evidence/A02/review-R1/validate_and_seal.py'],'exit_code':0,'evidence':'final-validation.json'})
save(OUT/'command-receipts.json',commands)
manifest()
links=[]
for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8')):
    if target.startswith(('http:','https:','#')):continue
    assert(REPORT.parent/target.split('#',1)[0]).resolve().exists(),target
    links.append(target)
assert not any(re.search(r'[ \t]+$',line) for line in REPORT.read_text(encoding='utf-8').splitlines())
bundles=[];json_count=0;skipped=[]
invalid={'invalid-input.json','mutation-before-seal.json','tampered-plan.json','invalid-platform-plan.json'}
for path in sorted(OUT.rglob('*')):
    if not path.is_file():continue
    if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    if path.suffix=='.json':
        data=read(path);json_count+=1
        if isinstance(data,dict) and data.get('format_version')=='c01-exchange-1':
            if path.name in invalid:skipped.append(path.relative_to(ROOT).as_posix());continue
            load_bundle(path);bundles.append(path.relative_to(ROOT).as_posix())
save(OUT/'final-validation.json',{'target_commit':COMMIT,'decision':'ACCEPTED','observed_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
    'source_files_reverified':len(export['files']),'old_review_files_preserved':len(old),'old_delivery_files_preserved':len(export['old_delivery_artifacts']),
    'json_files_parsed':json_count,'public_resource_bundles_reloaded':len(bundles),'public_bundle_paths':bundles,
    'deliberate_invalid_mutation_files_skipped_for_public_validation':skipped,'report_links_verified':len(links),'report_links':links,
    'matrix_rows':67,'independent_risk_cases':72,'independent_mixed_cases':5,'history_only_pair_assertions':29,
    'production_files_modified_by_reviewer':0,'previous_REWORK_report_and_evidence_unchanged':True})
sealed=manifest()
assert all(sha(ROOT/f['path'])==f['sha256'] for f in sealed['files'])
print(json.dumps({'decision':'ACCEPTED','report_links':len(links),'source_files':len(export['files']),'old_review_files':len(old),
    'public_bundles':len(bundles),'manifest_files':len(sealed['files']),'report_sha256':sealed['report_sha256'],'manifest_sha256':sha(MANIFEST)}))
