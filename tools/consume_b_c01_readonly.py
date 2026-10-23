"""Read an existing C01 bundle through pinned A24 code; no conversion/dispatch."""
import argparse
import hashlib
import importlib.abc
import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

A_COMMIT = 'c5aefbc8e995c410b3babf74a251f05a7724a1c2'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def forbidden(*args, **kwargs):
    raise RuntimeError('LOCAL_C01_READ_ONLY_NO_NETWORK_OR_SUBPROCESS')


class LocalImportsOnly(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('annotation.delivery', 'annotation.runtime', 'annotation.quality.target', 'playwright', 'requests', 'httpx')):
            raise ImportError('C01_READ_ONLY_BLOCKED_IMPORT:' + fullname)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('a-source', 'pins', 'pins-sha256', 'bundle', 'out'):
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--expected-questions', type=int)
    args = parser.parse_args()
    pins_raw = Path(args.pins).read_bytes()
    if sha(pins_raw) != args.pins_sha256:
        raise ValueError('A24_PINS_FILE_CHANGED')
    pins = json.loads(pins_raw)
    if pins['a_commit'] != A_COMMIT or len(pins['members']) != 50:
        raise ValueError('FIXED_A24_C01_CLOSURE_REQUIRED')
    source = Path(args.a_source).resolve()
    for member in pins['members']:
        rel = member['path']
        if not (rel == 'src/annotation/__init__.py' or rel.startswith(('src/annotation/contracts/', 'src/annotation/geometry/'))) or '..' in Path(rel).parts:
            raise ValueError('ONLY_CONTRACTS_GEOMETRY_SOURCE_ALLOWED')
        raw = (source / rel).read_bytes()
        if len(raw) != member['bytes'] or sha(raw) != member['sha256']:
            raise ValueError('A24_SOURCE_BYTES_CHANGED:' + rel)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source / 'src'))
    sys.meta_path.insert(0, LocalImportsOnly())
    socket.create_connection = socket.socket.connect = socket.socket.connect_ex = forbidden
    urllib.request.urlopen = subprocess.Popen = forbidden
    from annotation.contracts import load_bundle
    if not Path(inspect.getfile(load_bundle)).resolve().is_relative_to(source / 'src'):
        raise ValueError('WRONG_CONSUMER_IMPORT_LOCATION')
    path = Path(args.bundle).resolve()
    original = json.loads(path.read_bytes())
    if original.get('format_version') != 'c01-exchange-1':
        raise ValueError('EXPECTED_EXISTING_C01_NOT_PRIVATE_CANDIDATE_SCHEMA')
    actual = load_bundle(path, verify_assets=True).model_dump(mode='json')
    if canonical(original) != canonical(actual):
        raise ValueError('COMPLETE_OBJECT_READBACK_DIFFERS')
    graphs = [a for a in actual['artifacts'] if a['kind'] == 'QuestionGraph']
    if len(graphs) != 1:
        raise ValueError('ONE_SCOPE_QUESTION_GRAPH_REQUIRED')
    graph = graphs[0]['payload']
    if args.expected_questions is not None and len(graph['questions']) != args.expected_questions:
        raise ValueError('EXPECTED_QUESTION_SCOPE_COUNT')
    receipt = dict(status='PINNED_A24_C01_READ_AND_COMPLETE_OBJECT_MATCH', a_commit=A_COMMIT,
        source_files_verified=50, bundle_sha256=sha(path.read_bytes()), complete_object_sha256=sha(canonical(actual)),
        complete_object_equal=True, questions=len(graph['questions']), fragments=len(graph['fragments']),
        verify_assets=True, platform_requests=0, planning_or_dispatch=False, a_owner_acceptance=False,
        independent_human_acceptance=False, full_object=actual)
    with Path(args.out).open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({key:value for key,value in receipt.items() if key != 'full_object'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
