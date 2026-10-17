import hashlib,json,subprocess,sys
from pathlib import Path
out=Path(__file__).resolve().parent;folder=out/'collector-runtime';folder.mkdir(exist_ok=False)
script=out/'run_forms.py';before=hashlib.sha256(script.read_bytes()).hexdigest()
args=[sys.executable,'-B',str(script)]
p=subprocess.run(args,cwd='D:/1800',capture_output=True)
(folder/'stdout.log').write_bytes(p.stdout);(folder/'stderr.log').write_bytes(p.stderr)
record=dict(argv=args,cwd='D:/1800',exit_code=p.returncode,script_sha256_before=before,script_sha256_after=hashlib.sha256(script.read_bytes()).hexdigest(),stdout='stdout.log',stderr='stderr.log',capture='Original subprocess stdout/stderr bytes, captured at startup by this external launcher.')
with (folder/'command.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record))
if p.returncode:print(p.stderr.decode('utf-8','replace'))
raise SystemExit(p.returncode)
