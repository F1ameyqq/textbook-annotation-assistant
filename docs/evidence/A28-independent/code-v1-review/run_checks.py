import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

PRIVATE = Path('D:/1800/.local/stages/a28-independent-20261023/code-v1-review')
PUBLIC = Path('D:/1800/docs/evidence/A28-independent/code-v1-review')
PYTHON = Path('D:/1800/.local/stages/a25-lesson2-expansion-20261023/runtime-py312/venv/Scripts/python.exe')
assert hashlib.sha256(PYTHON.read_bytes()).hexdigest() == 'd59c9a894b319828d023f3aa83d9a3488d2339f9e27e60e49b02abb0d53cf538'
out = PRIVATE / 'author-new-checks'
out.mkdir()
code = '''import sys,unittest
def audit(event,args):
 if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'): raise RuntimeError('INDEPENDENT_OFFLINE_DENIAL:'+event)
 if event=='open' and isinstance(args[0],str) and ('browser-profiles' in args[0].lower() or 'worktrees/b-latest' in args[0].replace(chr(92),'/').lower()): raise RuntimeError('INDEPENDENT_ACTIVE_RESOURCE_READ_DENIED')
sys.addaudithook(audit)
sys.path.insert(0,'src');sys.path.insert(0,'tests')
suite=unittest.defaultTestLoader.loadTestsFromNames(['test_a28_lesson_insert','test_a28_lesson_batch'])
result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
sys.exit(not result.wasSuccessful())
'''
cmd = [str(PYTHON), '-I', '-B', '-c', code]
start = datetime.now(timezone.utc).isoformat()
process = subprocess.run(cmd, cwd=PRIVATE / 'workspace', capture_output=True, timeout=60,
                         env=dict(os.environ, PYTHONUTF8='1'))
for name, data in [('stdout.txt', process.stdout), ('stderr.txt', process.stderr)]:
    with (out / name).open('xb') as stream:
        stream.write(data)
record = {'schema': 'A28IndependentNewSuiteRun/v1', 'argv': cmd, 'cwd': str(PRIVATE / 'workspace'),
          'started_at': start, 'finished_at': datetime.now(timezone.utc).isoformat(),
          'exit_code': process.returncode, 'stdout_sha256': hashlib.sha256(process.stdout).hexdigest(),
          'stderr_sha256': hashlib.sha256(process.stderr).hexdigest(),
          'stdout': str(out / 'stdout.txt'), 'stderr': str(out / 'stderr.txt'),
          'scope': 'Only two new A28 suites; audit denies network, subprocess and active profile/workspace reads.'}
with (PUBLIC / 'new-suite-process.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2)
print(process.stderr.decode('utf-8')[-1200:])
print(json.dumps({'exit_code': process.returncode}))
