"""One compatibility group with binary nested-process evidence."""
import json
import locale
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

from audit import EVIDENCE, ROOT, write, sha


def main(label, pattern):
    original = subprocess.Popen
    directory = EVIDENCE / 'nested-processes' / label
    directory.mkdir(parents=True, exist_ok=False)
    records = []

    class RecordedPopen(original):
        def __init__(self, args, *positional, **kwargs):
            self.audit_dir = directory / ('child-%02d' % (len(records) + 1))
            self.audit_dir.mkdir()
            self.text_requested = bool(kwargs.pop('text', False) or kwargs.pop('universal_newlines', False) or kwargs.get('encoding') or kwargs.get('errors'))
            self.audit_encoding = kwargs.pop('encoding', None) or locale.getpreferredencoding(False)
            self.audit_errors = kwargs.pop('errors', None) or 'strict'
            self.audit_streams = [(self.audit_dir / name).open('xb') for name in ('stdout.txt', 'stderr.txt')]
            write(self.audit_dir / 'preregistered.json', {'argv': args, 'cwd': str(kwargs.get('cwd') or ROOT), 'timeout_seconds': 30,
                'parent_source_index_sha256': sha((EVIDENCE / 'runs' / label / 'product-source-index.json').read_bytes()),
                'script_sha256': sha(Path(__file__).read_bytes()), 'environment': 'not serialized'})
            self.tick = time.monotonic()
            super().__init__(args, *positional, **kwargs)
            write(self.audit_dir / 'started.json', {'pid': self.pid, 'parent_pid': os.getpid()})
            records.append(self)

        def communicate(self, input=None, timeout=None):
            if isinstance(input, str):
                input = input.encode(self.audit_encoding, self.audit_errors)
            timed_out = False
            try:
                result = super().communicate(input=input, timeout=30 if timeout is None else min(timeout, 30))
            except subprocess.TimeoutExpired:
                timed_out = True
                self.kill()
                result = super().communicate()
            for stream, body in zip(self.audit_streams, result):
                if body is not None:
                    stream.write(body)
                stream.close()
            write(self.audit_dir / 'completed.json', {'pid': self.pid, 'exit_code': self.returncode,
                'alive': self.poll() is None, 'timed_out': timed_out, 'elapsed_seconds': time.monotonic() - self.tick})
            if self.text_requested:
                return tuple(body.decode(self.audit_encoding, self.audit_errors).replace('\r\n', '\n').replace('\r', '\n') if body is not None else None for body in result)
            return result

    subprocess.Popen = RecordedPopen
    try:
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern=pattern)
        outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        subprocess.Popen = original
        for process in records:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    return 0 if outcome.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
