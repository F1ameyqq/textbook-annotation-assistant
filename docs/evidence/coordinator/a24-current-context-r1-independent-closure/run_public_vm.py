"""Execute only PUBLIC_JSON in an isolated local VM with fake fetch."""
import ast
import hashlib
import json
import subprocess
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
tree = ast.parse((ROOT / 'tools/a16_current_state_probe.py').read_text(encoding='utf-8'))
programs = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == 'PUBLIC_JSON' for target in node.targets)]
assert len(programs) == 1
program = programs[0]
payload = {'program': program,
    'url': 'https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images/46007447/independent13.json'}
started = time.monotonic()
run = subprocess.run(['node', str(OUT / 'public_vm.cjs')], input=json.dumps(payload).encode('utf-8'),
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, creationflags=0x08000000)
for name, raw in (('public-vm-stdout.txt', run.stdout), ('public-vm-stderr.txt', run.stderr)):
    with (OUT / name).open('xb') as stream:
        stream.write(raw)
rows = json.loads(run.stdout)['results'] if run.returncode == 0 else []
success = run.returncode == 0 and len(rows) == 3 and all(row['success'] for row in rows)
result = {'result': 'PASS' if success else 'FAIL', 'mode': 'OFFLINE_PUBLIC_JSON_VM_FAKE_FETCH',
    'cases': rows, 'node_returncode': run.returncode, 'duration_ms': round((time.monotonic() - started) * 1000),
    'exact_PUBLIC_JSON_sha256': hashlib.sha256(program.encode('utf-8')).hexdigest(),
    'product_imports': 0, 'runtime_account_context_reads': 0, 'real_resources': 0, 'local_fake_Node_processes': 1}
with (OUT / 'public-vm-result.json').open('xb') as stream:
    stream.write((json.dumps(result, indent=2) + '\n').encode('utf-8'))
print(json.dumps({'result': result['result'], 'cases': len(rows), 'duration_ms': result['duration_ms']}))
raise SystemExit(0 if success else 1)
