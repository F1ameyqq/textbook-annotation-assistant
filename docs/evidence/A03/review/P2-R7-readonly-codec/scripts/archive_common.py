# -*- coding: utf-8 -*-
"""Byte-only review archive helpers; no product imports or process scans."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path('D:/1800')
OUT = ROOT / 'docs/evidence/A03/review/P2-R7-readonly-codec'
REPORT = ROOT / 'docs/tasks/A03-P2-R7-readonly-codec-review-report.md'

def load(path):
    return json.loads(path.read_bytes())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    with path.open('x', encoding='utf8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def report_links(allowed_pending=()):
    result = []
    for reference in re.findall(r'\[[^\]]+\]\(([^)]+)\)', REPORT.read_text(encoding='utf8')):
        assert '://' not in reference
        path = (REPORT.parent / reference).resolve()
        assert path.is_relative_to(ROOT)
        assert path.exists() or path in allowed_pending, reference
        result.append({'reference': reference, 'path': path.relative_to(ROOT).as_posix(),
                       'exists': path.exists()})
    return result

def process_records(skip=()):
    parents, children = [], []
    expected_failures = {'c01-compatibility-01', 'author-evidence-audit-01'}
    for directory in sorted((OUT / 'runs').iterdir()):
        if directory.name in skip:
            continue
        registration = load(directory / 'registration.json')
        started = load(directory / 'started.json')
        completion = load(directory / 'completion.json')
        assert registration['argv'] == completion['argv']
        assert registration['cwd'] == completion['cwd']
        assert 0 < registration['timeout_seconds'] <= 60
        assert sha(directory / 'entry-source.py') == registration['entry_sha256']
        assert started['pid'] == completion['pid']
        assert completion['exit_code'] == (1 if directory.name in expected_failures else 0)
        assert not completion['alive_after_wait'] and not completion['timed_out']
        parents.append({'run': directory.name, 'pid': completion['pid'],
                        'exit_code': completion['exit_code'], 'timed_out': False, 'alive': False,
                        'registration_sha256': sha(directory / 'registration.json'),
                        'completion_sha256': sha(directory / 'completion.json'),
                        'script_sha256': registration['entry_sha256'],
                        'stdout_sha256': sha(directory / 'stdout.log'),
                        'stderr_sha256': sha(directory / 'stderr.log')})
    assert {row['run'] for row in parents if row['exit_code']} == expected_failures
    for completion_path in sorted((OUT / 'nested').rglob('completion.json')):
        directory = completion_path.parent
        registration = load(directory / 'registration.json')
        started = load(directory / 'started.json')
        completion = load(completion_path)
        assert registration['argv'] == completion['argv']
        assert registration['cwd'] == completion['cwd']
        assert registration['raw_streams_opened_before_spawn']
        assert registration['parent_input_index_sha256'] == sha(OUT / 'input-index.json')
        assert started['pid'] == completion['pid']
        assert not completion['alive'] and not completion['timed_out']
        assert 0 < completion['effective_timeout_seconds'] <= 30
        children.append({'record': directory.relative_to(OUT).as_posix(), 'pid': completion['pid'],
                         'exit_code': completion['exit_code'], 'timed_out': False, 'alive': False,
                         'registration_sha256': sha(directory / 'registration.json'),
                         'completion_sha256': sha(completion_path),
                         'stdout_sha256': sha(directory / 'stdout.log'),
                         'stderr_sha256': sha(directory / 'stderr.log')})
    assert len(children) == 14
    assert len(list((OUT / 'nested').rglob('registration.json'))) == len(children)
    assert len(list((OUT / 'nested').rglob('started.json'))) == len(children)
    return parents, children
