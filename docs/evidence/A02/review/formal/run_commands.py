"""Run frozen author reproduction with explicit import/temp roots and capture receipts."""
import json
import os
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
STAGE = Path('D:/1800/.local/stages/A02-review/frozen-5c928572')
env = dict(os.environ, PYTHONPATH=str(STAGE / 'src'), PYTHONDONTWRITEBYTECODE='1')
temp = STAGE.parent / 'tmp'
temp.mkdir(exist_ok=True)
env.update(TEMP=str(temp), TMP=str(temp))
commands = [
    ('environment', [sys.executable, '-c', 'import sys,json,pydantic,annotation.contracts,annotation.delivery.mock;print(json.dumps({"python":sys.version,"executable":sys.executable,"pydantic":pydantic.__version__,"contracts":annotation.contracts.__file__,"mock":annotation.delivery.mock.__file__}))'], STAGE),
    ('author-reproduction', [sys.executable, 'examples/a02/verify.py', '--output', str(OUT / 'reproduction')], STAGE),
    ('portable-final-cli', [sys.executable, '-m', 'annotation.contracts', 'validate', str(OUT / 'reproduction/cases/normal/final.json')], temp),
]
results = []
for label, command, cwd in commands:
    result = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (OUT / (label + '.stdout.txt')).write_bytes(result.stdout)
    (OUT / (label + '.stderr.txt')).write_bytes(result.stderr)
    results.append({'label': label, 'command': command, 'cwd': str(cwd), 'exit_code': result.returncode, 'stdout': label + '.stdout.txt', 'stderr': label + '.stderr.txt', 'PYTHONPATH': env['PYTHONPATH'], 'TEMP': str(temp)})
    print(label, result.returncode)
(OUT / 'commands.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
sys.exit(any(r['exit_code'] for r in results))
