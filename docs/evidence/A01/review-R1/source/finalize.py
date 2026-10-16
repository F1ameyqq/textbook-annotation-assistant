"""Freeze new R1 source evidence only; never touches prior review evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')

environment = read(ROOT/'environment.json')
results = read(ROOT/'results.json')
minimal = read(ROOT/'minimal-url/result.json')
assert sha(ROOT/'probe.py') == environment['script_sha256']
assert sha(ROOT/'minimal_url.py') == minimal['script_sha256']
snapshot = Path(environment['PYTHONPATH']).parent
before = read(ROOT/'snapshot-integrity.json')['before']
current = {p.relative_to(snapshot).as_posix():sha(p) for p in sorted(snapshot.rglob('*')) if p.is_file()}
assert before == current
receipt = {'target_commit':results['target_commit'], 'source_subdecision':'REWORK',
           'main': {'argv':[environment['python_executable'],'-B']+environment['command_argv'],
                    'working_directory':'D:/1800','observed_exit_code':0,'stdout_path':'stdout.txt',
                    'stdout_sha256':sha(ROOT/'stdout.txt'),'counts':results['counts'],
                    'case_count':len(results['cases'])},
           'minimal_N17_confirmation': {'argv':[minimal['python_executable'],'-B']+minimal['command_argv'],
                                       'working_directory':'D:/1800','observed_exit_code':0,
                                       'stdout_path':'minimal-url-stdout.txt','stdout_sha256':sha(ROOT/'minimal-url-stdout.txt'),
                                       'expected':minimal['expected'],'actual':minimal['actual']},
           'script_hashes_match_executed_runs':True,
           'frozen_snapshot_unchanged_through_both_runs':True,'frozen_snapshot_file_count':len(current),
           'exit_code_semantics':'0 means evidence collection completed; source feature decision remains REWORK.',
           'original_nine_rejected':results['original_S12_S20_all_rejected_with_expected_code'],
           'normal_old_new_two_books_compatible':results['pristine_samples_all_accepted']}
write(ROOT/'command-receipt.json',receipt)

counterexamples=[]
for identifier in ('N13-acquired-page-declared-missing','N14-selected-page-declared-outside-unacquired',
                   'N16-new-history-image-wrong-book','N17-new-history-image-wrong-index','N18-observation-index-digest'):
    case = next(r for r in results['cases'] if r['id']==identifier)
    assert case['expected']=='REJECT' and case['actual']=='ACCEPT'
    counterexamples.append({'id':identifier,'description':case['description'],
                            'input':str(ROOT/'cases'/identifier/'input.json'),
                            'output':str(ROOT/'cases'/identifier/'result.json'),
                            'expected':'REJECT','actual':'ACCEPT'})
write(ROOT/'minimal-counterexamples.json', {'source_subdecision':'REWORK','target_commit':results['target_commit'],
                                          'blocking_internal_contradictions':counterexamples,
                                          'N17_minimized_output':str(ROOT/'minimal-url/result.json'),
                                          'N15_precision_label':'Supplementary lower-risk observation; not sole REWORK basis.',
                                          'S01_D01':'Known unresolved integration limits, not counted as repaired.'})
manifest = {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(ROOT.rglob('*'))
            if p.is_file() and p != ROOT/'sha256-manifest.json'}
write(ROOT/'sha256-manifest.json',{'files':manifest})
assert all(sha(ROOT/path)==digest for path,digest in manifest.items())
print(json.dumps({'files_verified':len(manifest),'source_subdecision':'REWORK',
                  'report_sha256':sha(ROOT/'REPORT.md'),'results_sha256':sha(ROOT/'results.json'),
                  'manifest_sha256':sha(ROOT/'sha256-manifest.json')},indent=2))
