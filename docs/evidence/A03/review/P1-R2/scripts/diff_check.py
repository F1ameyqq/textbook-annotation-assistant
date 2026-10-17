"""Record default and single-command CRLF-aware whitespace diagnostics unchanged."""
import json,os,subprocess
from pathlib import Path
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P1-R2'
BASE='ca4fba4f505467228a8164c3999e0cecc54ffc4e';HEAD='940a5de33a24b1a3a9ded6e69ade1dd0609ed83a'
rows=[]
for label,opts in (('default',[]),('crlf-aware',['-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol'])):
 argv=['git',*opts,'diff','--check',BASE,HEAD]
 p=subprocess.run(argv,cwd=ROOT,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'},capture_output=True,timeout=60)
 for stream,b in (('stdout',p.stdout),('stderr',p.stderr)):
  with (OUT/('diff-'+label+'.'+stream+'.log')).open('xb') as f:f.write(b)
 rows.append({'argv':argv,'cwd':str(ROOT),'timeout_seconds':60,'exit_code':p.returncode,'global_config_changed':False})
with (OUT/'diff-check-results.json').open('x',encoding='utf-8',newline='\n') as f:
 json.dump({'commands':rows,'raw_CRLF_bytes_preserved':True,'expected_difference':'default raw evidence CR diagnosed; per-command cr-at-eol recognizes CRLF'},f,indent=2);f.write('\n')
assert [x['exit_code'] for x in rows]==[2,0]
print(json.dumps({'default_exit':rows[0]['exit_code'],'single_command_crlf_aware_exit':rows[1]['exit_code'],'global_config_changed':False}))
