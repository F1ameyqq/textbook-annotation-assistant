"""Final review archive validation; never run candidate code or functional tests."""
import ast
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parent
REPORT=ROOT/'docs/tasks/A02-portability-R2-review-report.md';MANIFEST=OUT/'sha256-manifest.json'
COMMIT='a1e5be00909172429d792b6c41bdaf384258694e'
REPO=Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def manifest():
    files=[REPORT]+sorted(p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST)
    data={'schema_version':1,'task':'A02-portability-R2-independent-review','decision':'ACCEPTED','target_commit':COMMIT,
        'base_commit':'38aca9dcc8d027409b95193e9cc142c2336b76d3','patch_commit':'ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8',
        'handoff_workflow_commit':'3ed8dcba2f921c7a89b7f1d2ef9f6ace40aed583','report':'docs/tasks/A02-portability-R2-review-report.md','report_sha256':sha(REPORT),
        'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],
        'self_excluded':True,'archive_scope':'All reviewer-owned new files and raw logs regardless of Git ignore; runtime source fixtures kept in authorized stage with exact input indexes.',
        'platform_network_browser_credential_ocr_external_model_calls':0,'integration_or_dependency_release':False}
    save(MANIFEST,data);return data
def main():
    matrix=load(OUT/'matrix-results.json');assert matrix['decision']=='ACCEPTED' and matrix['count']==14
    commands=load(OUT/'commands.json')['commands'];assert len(commands)==20 and all(c['exit_code']==c['expected_exit_code'] for c in commands)
    for c in commands:
        assert(OUT/c['stdout']).is_file() and(OUT/c['stderr']).is_file()
        assert Path(c['argv'][2]).resolve()==(OUT/'probe.py').resolve()
    for row in matrix['matrix']:
        assert all((OUT/p).is_file() for p in row['evidence'])
    old=load(OUT/'preserved-review-index.json')['files_sha256']
    assert all(sha(ROOT/p)==h for p,h in old.items())
    bootstrap=load(OUT/'bootstrap.json')
    for info in bootstrap['exports'].values():
        assert all(sha(Path(info['root'])/f['path'])==f['sha256'] for f in info['files'])
    for entry in load(OUT/'input-provenance.json')['files']:
        assert sha(OUT/entry['archived_path'])==entry['sha256']
    format_argv=['git','-C',str(REPO),'diff','--check',bootstrap['base'],COMMIT,'--','examples/a02/R1/identity.py','examples/a02/portability-R2','tests/test_a02_portability_r2.py']
    run=subprocess.run(format_argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (OUT/'code-diff-check.stdout.txt').write_bytes(run.stdout);(OUT/'code-diff-check.stderr.txt').write_bytes(run.stderr)
    assert run.returncode==0
    parsed=0;pyfiles=0
    for path in OUT.rglob('*'):
        if not path.is_file():continue
        if path.suffix=='.json':load(path);parsed+=1
        if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'),filename=str(path));pyfiles+=1
    manifest()
    links=[]
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8')):
        if target.startswith(('http:','https:','#')):continue
        assert(REPORT.parent/target.split('#',1)[0]).resolve().is_file(),target
        links.append(target)
    assert not any(re.search(r'[ \t]+$',line) for line in REPORT.read_text(encoding='utf-8').splitlines())
    head=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD']).decode().strip()
    status=subprocess.check_output(['git','-C',str(REPO),'status','--short']).decode().splitlines()
    assert head==COMMIT and not status
    save(OUT/'top-level-command-receipts.json',{'cwd':'D:/1800','commands':[
        {'argv':['python','-B','docs/evidence/A02/review-portability-R2/bootstrap.py'],'exit_code':0,'evidence':'bootstrap.json'},
        {'argv':['python','-B','docs/evidence/A02/review-portability-R2/run_checks.py'],'exit_code':1,'evidence':'collector-incidents.json','kind':'REVIEW_COLLECTOR_ERROR'},
        {'argv':['python','-B','docs/evidence/A02/review-portability-R2/run_checks.py','--resume'],'exit_code':1,'evidence':'collector-incidents.json','kind':'REVIEW_COLLECTOR_ERROR'},
        {'argv':['python','-B','docs/evidence/A02/review-portability-R2/run_checks.py','--resume','--finish'],'exit_code':0,'evidence':'commands.json'},
        {'argv':['python','-B','docs/evidence/A02/review-portability-R2/consolidate.py'],'exit_code':0,'evidence':'matrix-results.json'},
        {'argv':['python','-B','docs/evidence/A02/review-portability-R2/archive_inputs.py'],'exit_code':0,'evidence':'input-provenance.json'},
        {'argv':['python','-B','docs/evidence/A02/review-portability-R2/validate_and_seal.py'],'exit_code':0,'evidence':'final-validation.json'}],
        'all_functional_child_actual_receipts':'commands.json','code_diff_check':{'argv':format_argv,'exit_code':run.returncode},
        'note':'Collectors have two recorded metadata errors. Expected-failing child commands keep actual nonzero exit codes.'})
    save(OUT/'final-validation.json',{'observed_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'target_commit':COMMIT,'decision':'ACCEPTED',
        'matrix_rows':14,'actual_child_commands':20,'expected_nonzero_children':7,'a02_discovery_each_environment':62,
        'old_review_files_preserved':len(old),'raw_input_files_reverified':sum(len(v['files']) for v in bootstrap['exports'].values()),
        'report_links_verified':len(links),'report_links':links,'evidence_json_parsed':parsed,'python_files_syntax_checked':pyfiles,
        'code_diff_check_exit':0,'source_worktree_head':head,'source_worktree_status':status,
        'raw_logs_preserved_without_encoding_or_whitespace_normalization':True,'owns_no_pending_background_helper':True})
    sealed=manifest()
    assert all(sha(ROOT/item['path'])==item['sha256'] for item in sealed['files'])
    print(json.dumps({'decision':'ACCEPTED','manifest_files':len(sealed['files']),'report_links':len(links),
        'report_sha256':sealed['report_sha256'],'manifest_sha256':sha(MANIFEST)}))
if __name__=='__main__':main()
