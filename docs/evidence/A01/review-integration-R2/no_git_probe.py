import json,os,shutil,subprocess,sys
from pathlib import Path
record=dict(argv=['git','--version'],cwd=os.getcwd(),PATH=os.environ.get('PATH'),which=shutil.which('git'),raw_has_dot_git=(Path(os.getcwd()).parent/'.git').exists())
try:
 p=subprocess.run(['git','--version'],capture_output=True)
 record.update(exit_code=p.returncode,stdout=p.stdout.decode('utf-8','replace'),stderr=p.stderr.decode('utf-8','replace'))
except OSError as e:record.update(exception=type(e).__name__,errno=e.errno,winerror=getattr(e,'winerror',None),actual_OS_spawn_failed=True)
print(json.dumps(record))
raise SystemExit(0 if record.get('actual_OS_spawn_failed') and record['which'] is None else 1)
