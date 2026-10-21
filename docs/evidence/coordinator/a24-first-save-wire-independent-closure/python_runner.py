"""Output-contained wrapper retaining the frozen new suite's no-I/O guards."""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import traceback
import unittest

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
TEMP = OUT / 'temporary'
TEMP.mkdir(exist_ok=False)
os.environ['TMP'] = os.environ['TEMP'] = str(TEMP)
tempfile.tempdir = str(TEMP)


def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = str(args[0]).replace('\\', '/').lower()
        if '/.local/browser-profiles' in path or path.endswith('/.local/usense-login.json'):
            raise AssertionError('PRIVATE_RUNTIME_PATH_FORBIDDEN_INDEPENDENT')
    if event.startswith('socket.') and event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo'):
        raise AssertionError('REAL_SOCKET_FORBIDDEN_INDEPENDENT')


sys.addaudithook(audit)
original_runner = unittest.TextTestRunner


class FirstFailureRunner(original_runner):
    def __init__(self, *args, **kwargs):
        kwargs['failfast'] = True
        super().__init__(*args, **kwargs)


unittest.TextTestRunner = FirstFailureRunner
report = OUT / 'python-result.json'
sys.argv = [str(ROOT / 'tests/a24_first_save_wire/run.py'), '--report', str(report)]
stdout, stderr = io.StringIO(), io.StringIO()
code = 0
try:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        runpy.run_path(sys.argv[0], run_name='__main__')
except SystemExit as error:
    code = error.code if isinstance(error.code, int) else 1
except BaseException:
    traceback.print_exc(file=stderr)
    code = 1
for name, value in (('python-stdout.txt', stdout.getvalue()), ('python-stderr.txt', stderr.getvalue())):
    with (OUT / name).open('xb') as stream:
        stream.write(value.encode('utf-8'))
value = json.loads(report.read_bytes()) if report.exists() else {}
print(json.dumps({'exit_code': code, 'tests': value.get('tests', 0), 'passed': value.get('passed', False),
    'failures': value.get('failures'), 'errors': value.get('errors'), 'duration_ms': value.get('duration_ms'),
    'NOT_RUN': 45 - value.get('tests', 0), 'temporary_output_root': 'temporary/'}))
raise SystemExit(code)
