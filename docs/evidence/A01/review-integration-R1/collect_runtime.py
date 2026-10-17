import hashlib,json,re
from pathlib import Path
out=Path(__file__).resolve().parent;info=json.loads((out/'bootstrap.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(path,data):
 with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
summaries=[]
for label in ('checkout','raw'):
 folder=out/'runtime'/label;result=json.loads((folder/'entry/results.json').read_text(encoding='utf-8'))
 observations=[]
 for trace in sorted((folder/'imports').glob('[0-9][0-9].json')):
  content=json.loads(trace.read_text(encoding='utf-8'))
  for item in content['executed_modules']+content['loaded_annotation_modules']:
   assert not item['relative'].startswith('OUTSIDE:');assert sha(Path(item['resolved_path']))==item['sha256']
   observations.append(dict(trace=str(trace.relative_to(out)),**item))
 required=('src/annotation/source/static/importer.py','src/annotation/source/static/consistency.py','src/annotation/geometry/__init__.py','src/annotation/contracts/models.py','tests/test_a01_rework_r3.py','tests/test_a01_integration_r1.py')
 for path in required:assert any(item['relative']==path for item in observations)
 index=json.loads((out/('checkout-input-index.json' if label=='checkout' else 'raw-input-index.json')).read_text(encoding='utf-8'))
 changes=[x['path'] for x in index if not (Path(info[label])/x['path']).is_file() or sha(Path(info[label])/x['path'])!=x.get('disk_sha256',x.get('sha256'))]
 assert not changes
 commands=[]
 for c in result['commands']:
  match=re.search(r'Ran (\d+) tests?',c['stderr'])
  commands.append(dict(label=c['label'],exit_code=c['exit_code'],tests=int(match[1]) if match else None,permission_skips=c['stderr'].count("skipped 'host cannot create file symlinks; WinError=1314'")))
 command=json.loads((folder/'command.json').read_text(encoding='utf-8'))
 summary=dict(label=label,entry_exit_code=command['exit_code'],entry_passed=result['passed'],commands=commands,actual_import_observations=len(observations),required_actual_files=list(required),input_files=len(index),disk_changes=changes,git_available=command['git_available'])
 if not (folder/'actual-imports.json').exists():dump(folder/'actual-imports.json',dict(observations=observations))
 if not (folder/'summary.json').exists():dump(folder/'summary.json',summary)
 summaries.append(summary)
dump(out/'runtime-observed-summary.json',summaries)
dump(out/'run_forms-launch.json',dict(argv=['python','-B',str(out/'run_forms.py')],cwd='D:/1800',exit_code=1,reason='Wrapper asserted all top-level entries exit zero; raw entry actually exited 1 due one A02 missing-Git error. All original child outputs and import traces retained. Checkout entry exited 0.'))
print(json.dumps(summaries,ensure_ascii=False))
