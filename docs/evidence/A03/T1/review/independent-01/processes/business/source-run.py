"""One six-scene matrix; first unexpected failure stops all successors."""
import argparse
import os
from pathlib import Path
import sys
import traceback
from capture import write
from support_t1 import OUT, ROOT, HERE, GROUPS, process, check_frozen


def run(root, groups):
    assert root.is_relative_to(OUT)
    root.mkdir(parents=True, exist_ok=False)
    check_frozen()
    statuses = {name: 'NOT_RUN' for name in GROUPS}
    write(root / 'invocation.json', {'pid': os.getpid(), 'argv': sys.argv, 'cwd': str(ROOT),
        'groups': groups, 'no_automatic_retries': True})
    for name in groups:
        try:
            process(root / 'watchdogs' / name, [sys.executable, '-X', 'utf8', '-B',
                str(HERE / 'support_t1.py'), name, str(root)], 90)
        except BaseException:
            statuses[name] = 'FAILED'
            write(root / 'first-failure.txt', traceback.format_exc().encode('utf-8'))
            write(root / 'matrix.json', statuses)
            raise
        statuses[name] = 'PASS_AUTHOR_ONLY'
        print(name + ': ' + statuses[name], flush=True)
    write(root / 'matrix.json', statuses)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--groups', nargs='+', choices=GROUPS, default=list(GROUPS))
    args = parser.parse_args()
    assert args.groups == list(GROUPS)[list(GROUPS).index(args.groups[0]):]
    run(args.output.resolve(), args.groups)
