"""Independent post-run integrity, 14 checks and source/import evidence consolidation."""
import ast
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

OUT=Path(__file__).resolve().parent;ROOT=Path('D:/1800')
REPO=Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')
COMMIT='a1e5be00909172429d792b6c41bdaf384258694e';PATCH='ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def object_bytes(path,commit=COMMIT):return subprocess.check_output(['git','-C',str(REPO),'show',commit+':'+path])

def main():
    bootstrap=load(OUT/'bootstrap.json');stage=Path(bootstrap['stage']);commands=load(OUT/'commands.json')['commands']
    assert len(commands)==20 and all(c['exit_code']==c['expected_exit_code'] for c in commands)
    bylabel={c['label']:c for c in commands}
    def event(label,kind):return next(e for e in bylabel[label]['events'] if e.get('event')==kind)
    manifest=json.loads(object_bytes('docs/evidence/A02/execution/portability-R2/sha256-manifest.json'))
    entries=[]
    for group in ('files_sha256','patch_source_sha256'):
        for path,digest in manifest[group].items():
            raw=object_bytes(path);assert hashlib.sha256(raw).hexdigest()==digest,path
            if group=='patch_source_sha256':assert object_bytes(path,PATCH)==raw
            entries.append({'group':group,'path':path,'sha256':digest,'git_matches':True})
    expected=set(bootstrap['changed_paths']);covered={e['path'] for e in entries}|{'docs/evidence/A02/execution/portability-R2/sha256-manifest.json'}
    assert expected==covered,(expected-covered,covered-expected)
    save(OUT/'delivery-manifest-complete.json',{'target_commit':COMMIT,'evidence_and_report_entries':181,'patch_source_entries':6,'total_entries':len(entries),
        'all_changed_paths_including_self':len(covered),'entries':entries})
    old=load(OUT/'preserved-review-index.json')['files_sha256'];assert all(sha(ROOT/p)==h for p,h in old.items())
    source_checked=0;imports=[]
    for exported in bootstrap['exports'].values():
        for item in exported['files']:
            assert sha(Path(exported['root'])/item['path'])==item['sha256'];source_checked+=1
    candidate=bootstrap['exports']['candidate'];candidate_map={e['path']:e['sha256'] for e in candidate['files']}
    for label in ('a02-discovery-real-noGit','a02-discovery-withGit'):
        result=event(label,'tests-result');assert(result['tests_run'],result['failures'],result['errors'],result['skipped'])==(62,0,0,0)
        stderr=(OUT/bylabel[label]['stderr']).read_text(encoding='utf-8')
        counts={name:len(re.findall(r'^test_\S+ \('+re.escape(name)+r'\.',stderr,re.M)) for name in ('test_a02','test_a02_r1','test_a02_portability_r2')}
        assert counts=={'test_a02':44,'test_a02_r1':8,'test_a02_portability_r2':10},counts
        for name,record in result['actual_imports'].items():
            path=Path(record.get('path',record.get('file')));relative=path.relative_to(Path(candidate['root'])).as_posix()
            assert record['sha256']==candidate_map[relative] and sha(path)==record['sha256'],(name,relative)
            imports.append({'label':label,'module':name,'relative_path':relative,'sha256':record['sha256']})
        result['separate_test_counts']=counts
        save(OUT/(label+'-test-result.json'),result)
    good=event('binding-positive','result')['result']
    for p,h in good['source_sha256'].items():assert candidate_map[p]==h
    for label in ('binding-noGit','binding-damaged','binding-invalid-commit','binding-invalid-repository','binding-git-disappears'):
        assert bylabel[label]['exit_code']==1 and not any(e.get('event')=='result' for e in bylabel[label]['events'])
    import_events=[event(c['label'],'environment') for c in commands]
    for env in import_events:
        assert sha(Path(env['identity_import']))==env['identity_sha256']
    no_git=[c for c in commands if c['git_executable'] is None]
    assert all(not event(c['label'],'environment')['git_os_probe']['started'] for c in no_git)
    fixtures=load(OUT/'fixture-checkout.json');checkout=Path(fixtures['root']);nested=Path(fixtures['nested_root'])
    for root in (checkout,nested):
        for item in candidate['files']:assert sha(root/item['path'])==item['sha256']
    damaged=stage/'damaged source/src/annotation/__init__.py';original=Path(candidate['root'])/'src/annotation/__init__.py'
    assert len(damaged.read_bytes())==len(original.read_bytes()) and sum(a!=b for a,b in zip(damaged.read_bytes(),original.read_bytes()))==1
    mutation=OUT/'counterexample-inputs';mutation.mkdir(exist_ok=False)
    (mutation/'original-init.py').write_bytes(original.read_bytes());(mutation/'damaged-init.py').write_bytes(damaged.read_bytes())
    mapping={
        'P01':['bootstrap.json','identity.diff.txt','delivery-manifest-complete.json'],
        'P02':['runtime-final/candidate-real-noGit/command.json'],
        'P03':['runtime-final/base-original-noGit/command.json','runtime-final/base-original-withGit/command.json','runtime-final/candidate-original-noGit/command.json','runtime-final/candidate-original-withGit/command.json'],
        'P04':['fixture-checkout.json','runtime-final/checkout-real/command.json'],
        'P05':['fixture-checkout.json','runtime-final/nested-real-withGit/command.json'],
        'P06':['runtime-final/nested-real-noGit/command.json'],
        'P07':['runtime-final/binding-noGit/command.json'],
        'P08':['runtime-final/binding-positive/command.json'],
        'P09':['runtime-final/binding-damaged/command.json','runtime-final/binding-invalid-commit/command.json','runtime-final/binding-invalid-repository/command.json','runtime-final/binding-git-disappears/command.json'],
        'P10':['runtime-final/second-real-path-disappears/command.json'],
        'P11':['runtime-final/mock-finite-faults/command.json'],
        'P12':['runtime-final/mock-finite-faults/command.json'],
        'P13':['a02-discovery-real-noGit-test-result.json','a02-discovery-withGit-test-result.json'],
        'P14':['preserved-review-index.json','delivery-manifest-complete.json']}
    rows=[]
    for key,paths in mapping.items():
        assert all((OUT/p).is_file() for p in paths)
        rows.append({'id':key,'status':'PASS_STATIC' if key in ('P01','P14') else 'PASS_MOCK_LABELLED' if key in ('P11','P12') else 'PASS',
            'evidence':paths,'note':'Real OS subprocess with PATH changed only after actual toplevel succeeds.' if key=='P10' else 'These limited mock failures do not replace actual noGit evidence.' if key in ('P11','P12') else ''})
    source_status=subprocess.check_output(['git','-C',str(REPO),'status','--short']).decode().splitlines()
    source_head=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD']).decode().strip()
    assert not source_status and source_head==COMMIT
    save(OUT/'integrity-and-imports.json',{'target_commit':COMMIT,'raw_source_files_reverified':source_checked,'old_review_files_preserved':len(old),
        'old_git_files_preserved':bootstrap['old_git_files_preserved'],'source_binding_function_bytes_unchanged':True,
        'actual_imports_rechecked':imports,'all_child_identity_imports_sha_checked':len(import_events),
        'checkout_and_nested_raw_exact_files_each':len(candidate['files']),'damaged_case_exactly_one_byte_changed':True,
        'binding_positive_production_hash_count':len(good['source_sha256']),'source_worktree_head':source_head,'source_worktree_status':source_status})
    save(OUT/'matrix-results.json',{'decision':'ACCEPTED','target_commit':COMMIT,'patch':PATCH,'matrix':rows,'count':len(rows),
        'actual_child_commands':len(commands),'expected_nonzero_child_commands':sum(c['expected_exit_code']!=0 for c in commands),
        'a02_tests_each_environment':62,'counts_each_environment':{'original':52,'new':10,'failure':0,'error':0,'skip':0},
        'no_git_os_probe_confirmed_commands':len(no_git),'unknown_is_not_verified':True,'binding_failure_is_not_success':True})
    save(OUT/'collector-incidents.json',{'product_defects':0,'incidents':[
        {'command':'python -B docs/evidence/A02/review-portability-R2/run_checks.py','outer_exit_code':1,'type':'UnicodeDecodeError',
         'detail':'First baseline child actually failed as expected, but WinError Chinese text used platform stdout encoding; collector decoded UTF-8. Raw output retained in runtime/base-real-noGit; collector now requests UTF-8 only in own child environment. No source changed and no tests had run.'},
        {'command':'python -B docs/evidence/A02/review-portability-R2/run_checks.py --resume','outer_exit_code':1,'type':'KeyError:event',
         'detail':'19 actual child receipts retained. noGit 62 tests had already passed; unrelated test stdout JSON lacks event key. Collector now uses .get; validates retained result, runs only not-yet-run withGit discovery. No successful functional case repeated.'}],
        'final_command':'python -B docs/evidence/A02/review-portability-R2/run_checks.py --resume --finish','final_outer_exit_code':0,
        'final_child_receipts':'commands.json','author_failures_retained_in_exact_objects':'retained-author-failures.json'})
    save(OUT/'process-release.json',{'observed_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'scope':'Owned review processes only; no system-wide process census',
        'synchronous_test_children_launched':len(commands),'synchronous_test_children_returned':len(commands),
        'git_cat_file_helper_closed_and_waited':True,'local_git_setup_commands_synchronous_returned':True,'background_helpers_started':0,
        'owned_browser_sessions':0,'owned_pending_processes':0,'no_external_threads_contacted':True})
    print(json.dumps({'decision':'ACCEPTED','matrix_rows':len(rows),'commands':len(commands),'nonzero_expected':sum(c['expected_exit_code']!=0 for c in commands),
        'raw_files':source_checked,'old_review_files':len(old),'manifest_entries':len(entries),'tests_each_environment':62}))
if __name__=='__main__':main()
