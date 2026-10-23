import datetime, hashlib, json, os, subprocess, sys
from pathlib import Path

PYTHON = Path('C:/Users/ASUS/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
PUBLIC = Path(__file__).resolve().parent
PRIVATE = Path('D:/1800/.local/stages/a27-independent-20261023')
PRODUCT = PRIVATE/'candidate-23591811/product'
label, script, *args = sys.argv[1:]
assert label.replace('-', '').isalnum()
run = PUBLIC/'commands'/label
run.mkdir(parents=True, exist_ok=False)
temp = PRIVATE/'test-output'/label
temp.mkdir(parents=True, exist_ok=False)
env=dict(os.environ, A27_OUTPUT=str(temp), TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
argv=[str(PYTHON), '-I', '-B', str(Path(script).resolve()), *args]
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
start=now()
timeout=False
try:
    p=subprocess.run(argv,cwd=PRODUCT,env=env,capture_output=True,timeout=60)
    stdout,stderr,code=p.stdout,p.stderr,p.returncode
except subprocess.TimeoutExpired as exc:
    timeout=True; stdout=exc.stdout or b''; stderr=exc.stderr or b''; code=None
sha=lambda b:hashlib.sha256(b).hexdigest()
(run/'stdout').write_bytes(stdout); (run/'stderr').write_bytes(stderr)
record={'argv':argv,'cwd':str(PRODUCT),'started_at':start,'finished_at':now(),'exit_code':code,'timeout':timeout,
        'python_sha256':sha(PYTHON.read_bytes()),'script_sha256':sha(Path(script).read_bytes()),'stdout_sha256':sha(stdout),
        'stderr_sha256':sha(stderr),'temporary_root':str(temp)}
(run/'process.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record))
print(stdout.decode('utf-8',errors='backslashreplace'))
print(stderr.decode('utf-8',errors='backslashreplace'))
raise SystemExit(code if code is not None else 124)
