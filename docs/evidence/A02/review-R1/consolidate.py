"""Consolidate actual R1 review results without editing earlier evidence."""
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
COMMIT='38aca9dcc8d027409b95193e9cc142c2336b76d3'
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
results=[]
for name in ('results.json','supplement-results.json','final-supplement-results.json'):
    results.extend(load(OUT/'independent'/name)['results'])
assert len(results)==72 and all(r['status']=='PASS' for r in results)
coverage={}
for result in results:
    for key in result['matrix_ids']:coverage.setdefault(key,[]).append('independent/cases/'+result['name']+'/observation.json')
for key,evidence in [('F01','frozen-export.json'),('F02','production.diff.txt'),('U11','post-run-integrity.json'),('B05','reproduction/source-binding.json')]:coverage.setdefault(key,[]).append(evidence)
coverage['U05'].extend(['independent/mixed-final/forward/observations.json','independent/mixed-final/swapped/observations.json'])
rows=[]
for group,count in [('F',5),('G',20),('I',9),('S',8),('E',9),('U',11),('B',5)]:
    for i in range(1,count+1):
        key=group+str(i).zfill(2);assert key in coverage
        for path in coverage[key]:assert(OUT/path).is_file(),path
        rows.append({'matrix_id':key,'status':'PASS_STATIC' if key in ('F01','F02','U11') else 'PASS_DECLARED_SCOPE_WITH_N2_LIMITATION' if key=='B05' else 'PASS',
            'evidence':coverage[key],'note':'N1/N2, S01 eligibility, real sources, final content and A03 persistence remain outside this acceptance.' if key=='B05' else ''})
history=load(OUT/'independent/history-pair-final/actual.json')
mixed=load(OUT/'independent/mixed-final/results.json')
assert history['all_checks_passed'] and history['mock_intent_count']==0 and len(history['checks'])==29
assert len(mixed['cases'])==5
save(OUT/'matrix-results.json',{'target_commit':COMMIT,'decision':'ACCEPTED','acceptance_scope':'A02 R1 bounded offline book isolation; no integration or A03 release',
    'original_matrix_rows':rows,'original_matrix_count':67,'independent_risk_cases':72,'risk_failed_cases':0,
    'independent_mixed_cases':5,'history_only_pair_checks':29,'history_only_pair_intents':0,
    'original_review_decision_retained':'REWORK on 5c928572; earlier report and observations unchanged',
    'criteria':[
      {'id':'R1-1','status':'PASS','evidence':'author-command.json','observation':'52 A02 + 70 C01 + 16 R1 matrix + 10 demos; exact final commit and null checkout identity.'},
      {'id':'R1-2','status':'PASS','evidence':'independent/mixed-final/results.json','observation':'Both book-role directions retain complete foreign history; diagnostic leaves current unpaused, READY actually produces 3 questions/9 frames.'},
      {'id':'R1-3','status':'PASS','evidence':'independent/history-pair-final/actual.json','observation':'Two books only historical UNKNOWN and no pending/intent; omitted-history READY retries both rejected; 29 independent assertions.'},
      {'id':'R1-4','status':'PASS','evidence':'independent/mixed-final/results.json','observation':'Other book APPLIED/NOT_APPLIED/NOT_EXECUTED preserves actual UNKNOWN book state/history/log; old plans rejected; separate risk replan succeeds after ABSENT.'},
      {'id':'R1-5','status':'PASS','evidence':'production.diff.txt','observation':'Production only adds receipt book filter; no packet filtering, deleted history or single-book-only workaround.'},
      {'id':'R1-6','status':'PASS_WITH_FORMAT_EXCEPTION','evidence':'post-run-integrity.json','observation':'141 exact source files, 382 old delivery files and 2039 old review files preserved; one raw failed-test stderr trailing space retained.'},
      {'id':'R1-7','status':'BOUNDARIES_RETAINED','evidence':'production.diff.txt','observation':'N1/N2, A03, S01, final content and B acceptance not claimed solved.'}],
    'review_harness_corrections':[
      {'command':'run_mixed.py first attempt','exit_code':1,'reason':'Reviewer foreign-artifact comparison keyed only by artifact_id; two immutable revisions require id+revision. Original failure retained, final five cases pass.'},
      {'command':'probe_history_pair.py first attempt','exit_code':1,'reason':'Reviewer clone prefixed check_id enum before reaching mock; protocol enum IDs excluded. Initial script/assets retained, new output passes 29 checks.'}]})
commands=[
 {'argv':['python','-B','docs/evidence/A02/review-R1/prepare.py'],'exit_code':0,'evidence':'frozen-export.json'},
 {'argv':['python','-B','docs/evidence/A02/review-R1/run_author.py'],'exit_code':0,'evidence':'author-command.json'},
 {'argv':['python','-B','docs/evidence/A02/review-R1/run_risk.py'],'exit_code':0,'evidence':'risk-command-receipts.json'},
 {'argv':['python','-B','docs/evidence/A02/review-R1/run_mixed.py'],'exit_code':1,'evidence':'mixed-command.json','kind':'REVIEW_HARNESS_ERROR'},
 {'argv':['python','-B','docs/evidence/A02/review-R1/run_mixed.py','--output','D:/1800/docs/evidence/A02/review-R1/independent/mixed-final'],'exit_code':0,'evidence':'mixed-final-command.json'},
 {'argv':['python','-B','docs/evidence/A02/review-R1/run_final_risk.py'],'exit_code':0,'evidence':'risk-final-command.json'},
 {'argv':['python','-B','docs/evidence/A02/review-R1/probe_history_pair.py','--output','D:/1800/docs/evidence/A02/review-R1/independent/history-pair'],'exit_code':1,'evidence':'probe_history_pair_initial.py','kind':'REVIEW_HARNESS_ERROR','observed':'Pydantic ValidationError: history-a-source_integrity etc are invalid check_id enums; no mock called.'},
 {'argv':['python','-B','docs/evidence/A02/review-R1/probe_history_pair.py','--output','D:/1800/docs/evidence/A02/review-R1/independent/history-pair-final'],'exit_code':0,'evidence':'independent/history-pair-final/actual.json'},
 {'argv':['python','-B','docs/evidence/A02/review-R1/check_integrity.py'],'exit_code':0,'evidence':'post-run-integrity.json'},
 {'argv':['python','-B','docs/evidence/A02/review-R1/consolidate.py'],'exit_code':0,'evidence':'matrix-results.json'}]
save(OUT/'command-receipts.json',{'target_commit':COMMIT,'cwd':'D:/1800','commands':commands,'platform_browser_credential_network_ocr_model_calls':0,
    'environment_binding':'reproduction/source-binding.json','source_root':str(OUT/'source-38aca9dc')})
print(json.dumps({'decision':'ACCEPTED','matrix_rows':len(rows),'risk_cases':len(results),'mixed_cases':len(mixed['cases']),'history_only_checks':len(history['checks'])}))
