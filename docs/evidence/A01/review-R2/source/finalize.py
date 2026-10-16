"""Freeze only R2 source evidence and verify cumulative read-only boundaries."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def hashes(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
environment=read(ROOT/'environment.json')
results=read(ROOT/'results.json')
preservation=read(ROOT/'preservation.json')
assert sha(ROOT/'probe.py')==environment['script_sha256']
snapshot=Path(environment['PYTHONPATH']).parent
assert hashes(snapshot)==preservation['snapshot_before']==preservation['snapshot_after']
old=Path('D:/1800/docs/evidence/A01/review-R1/primary-source-confirmation')
assert hashes(old)==preservation['R1_formal_inputs_before']==preservation['R1_formal_inputs_after']
assert results['all_public_resource_checks_passed']
assert results['frozen_P01_P04_all_rejected']
assert results['old_R1_R2_two_books_all_accepted']
counterexamples=[]
for identifier in results['unexpected_cases']:
    item=next(r for r in results['cases'] if r['id']==identifier)
    input_data=read(ROOT/'cases'/identifier/'input.json')
    body=input_data['historical_URL_components'][0]
    counterexamples.append({'id':identifier,'expected':'REJECT','actual':item['actual'],
                            'public_resource_validation_passed':item['public_resource_validation_passed'],
                            'field':'history/00-independent-source-page14.json:data.pages[0].image',
                            'raw_file_id':body['file_id'],'raw_page_index':body['page_index'],
                            'image':body['image'],'parsed_components':body['parsed_components'],
                            'complete_temporary_exchange':input_data['exchange'],
                            'changed_input_directory':str(ROOT/'cases'/identifier/'changed-inputs'),
                            'exchange_sha256':input_data['exchange_sha256'],
                            'root_cause':'importer.py:108 applies path suffix regex to whole url rather than parsed.path'})
write(ROOT/'minimal-counterexamples.json',{'target_commit':results['target_commit'],'source_subdecision':'REWORK',
                                          'single_residual_defect':'R2-02 URL path identity is taken from query/fragment suffix.',
                                          'counterexamples':counterexamples,
                                          'R2-03_bounded_decision':'ACCEPTED; P04 and O01-O15 comply with expected behavior.',
                                          'scope_limits':'No host authentication, external authenticity, N15, S01 or D01 expansion.'})
receipt={'target_commit':results['target_commit'],'source_subdecision':'REWORK',
         'argv':[environment['python_executable'],'-B']+environment['command_argv'],
         'working_directory':'D:/1800','observed_exit_code':0,
         'exit_code_semantics':'0 means evidence collection completed, not feature acceptance.',
         'stdout_path':'stdout.txt','stdout_sha256':sha(ROOT/'stdout.txt'),
         'case_count':len(results['cases']),'counts':results['counts'],
         'matching_expectations':sum(r['matches_expectation'] for r in results['cases']),
         'all_public_resource_checks_passed':True,
         'R2-02':'REWORK: one URL-component parsing defect, three minimized variants.',
         'R2-03':'ACCEPTED within the authorized internal identity/digest relationships tested.',
         'snapshot_file_count':len(preservation['snapshot_before']),
         'snapshot_unchanged_through_finalization':True,
         'R1_formal_input_files_unchanged':True,
         'executed_script_hash_verified':True}
write(ROOT/'command-receipt.json',receipt)
manifest={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p!=ROOT/'sha256-manifest.json'}
write(ROOT/'sha256-manifest.json',{'algorithm':'SHA256','self_excluded':'sha256-manifest.json is excluded to avoid self-hash recursion.','files':manifest})
assert all(sha(ROOT/path)==digest for path,digest in manifest.items())
print(json.dumps({'files_verified':len(manifest),'source_subdecision':'REWORK',
                  'report_sha256':sha(ROOT/'REPORT.md'),'results_sha256':sha(ROOT/'results.json'),
                  'manifest_sha256':sha(ROOT/'sha256-manifest.json')},indent=2))
