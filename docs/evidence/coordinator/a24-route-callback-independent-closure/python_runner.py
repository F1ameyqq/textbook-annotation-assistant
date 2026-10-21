"""One five-control actual-installed-helper group; snapshot private-copy reads."""
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
TEMP = OUT / 'temporary'
TEMP.mkdir(exist_ok=False)
os.environ['TEMP'] = os.environ['TMP'] = str(TEMP)
tempfile.tempdir = str(TEMP)
intake = json.loads((OUT / 'intake-result.json').read_bytes())
redirects = {str(Path(r['declared_private_copy_path']).resolve()).lower(): Path(r['snapshot_path'])
    for r in intake['actual_local_libraries_verified_before_import']}
original_read = Path.read_bytes


def snapshot_read(path):
    target = redirects.get(str(path.resolve()).lower(), path)
    return original_read(target)


def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
        raise AssertionError('REVIEW_REAL_IO_FORBIDDEN')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).resolve()
        low = str(path).lower()
        if low.startswith('d:\\1800-worktrees\\a24-first-save\\') or any(p in low for p in (
            '\\microsoft\\edge\\user data\\', '\\google\\chrome\\user data\\', '\\.credentials', '\\secrets\\')):
            raise AssertionError('REVIEW_ACTIVE_OR_PRIVATE_PATH_FORBIDDEN')
        mode, flags = args[1], args[2]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and OUT not in path.parents:
            raise AssertionError('REVIEW_WRITE_OUTSIDE_OUTPUT')


sys.addaudithook(audit)
sys.argv = [str(ROOT / 'tests/a24_route_callback/run.py'), '--report', str(OUT / 'python-result.json')]
with patch.object(Path, 'read_bytes', snapshot_read):
    runpy.run_path(sys.argv[0], run_name='__main__')
