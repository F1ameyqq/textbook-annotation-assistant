"""Validate retained integration results without rerunning product commands."""
import datetime,hashlib,json,re,subprocess
from pathlib import Path
root=Path('D:/1800');out=Path(__file__).resolve().parent
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
merge=json.loads((out/'merge-index-check.json').read_bytes());cmd=json.loads((out/'command.json').read_bytes());r=json.loads((out/'entry/results.json').read_bytes())
parents=subprocess.check_output(['git','show','-s','--format=%P',head],cwd=root,text=True).split()
assert parents==[merge['parent'],'5f872150a237b195f73c78e02e13a91d2f4f46a7']
assert cmd['head']==head and cmd['exit_code']==0 and r['passed'] and len(r['commands'])==11
assert all(row['exit_code']==0 for row in r['commands'])
expected=[('A01 conventional regression',52,1),('C01',70,0),('A02',62,0),('login offline',8,0)]
summaries=[]
for label,count,skip in expected:
 row=next(x for x in r['commands'] if x['label']==label)
 assert re.search(r'^Ran '+str(count)+r' tests in ',row['stderr'],re.M)
 match=re.search(r'^OK(?: \(skipped=(\d+)\))?$',row['stderr'],re.M);assert match
 assert int(match.group(1) or '0')==skip
 summaries.append({'label':label,'run':count,'skip':skip,'actual_unittest_summary':match.group(0)})
for row in merge['files']:assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['disk_sha256']
for path,entry in r['source_files'].items():
 assert Path(entry['path']).resolve()==(root/path).resolve()
 assert hashlib.sha256((root/path).read_bytes()).hexdigest()==entry['disk_sha256']
correction={'first_checker':'run.py','first_checker_exit_code':1,'observed_product_entry_exit_code':cmd['exit_code'],'all_11_child_exit_codes':0,'cause':'Checker searched the substring skipped anywhere in C01 stderr; a passing test is named test_exception_and_skipped_questions_remain_in_denominator. Actual unittest summary is OK without skips.','correction':'Parse anchored unittest terminal summary only; revalidate existing receipts and unchanged input hashes. No product command rerun or source modification.'}
with (out/'checker-correction.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(correction,f,indent=2);f.write('\n')
checks={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'ACTUAL_LOCAL_INTEGRATION_PASS','merge_commit':head,'merge_parents':parents,'argv':cmd['argv'],'exit_code':cmd['exit_code'],'commands':11,'test_summaries':summaries,'URL_cases':5,'consumers':6,'changed_paths_unchanged_after_run':len(merge['files']),'scope':'One conventional full entry on actual merged checkout. Historical frozen R3 release gate and unchanged geometry630 not rerun. Receipt checker correction preserved separately.','all_synchronous_children_returned':True,'sessions_to_release':0,'platform_model_calls':0,'remote_push':False}
with (out/'checks.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(checks,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'result':checks['result'],'merge_commit':head,'commands':11}))
