"""Passive import provenance at normal Python exit; no business hooks."""
import atexit
import hashlib
import json
import os
from pathlib import Path
import sys


def record_imports():
    folder = os.environ.get('A03_R12_R1_IMPORT_AUDIT')
    if not folder:
        return
    result = {}
    for name, module in sorted(sys.modules.items()):
        source = getattr(module, '__file__', None)
        if source and (name.startswith('annotation') or name in ('__main__', 'support', 'sitecustomize', 'r8_fixed_helper')):
            path = Path(source).resolve()
            if path.is_file():
                result[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    output = Path(folder)
    output.mkdir(parents=True, exist_ok=True)
    with (output / (str(os.getpid()) + '.json')).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump({'pid': os.getpid(), 'imports': result}, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')


atexit.register(record_imports)
