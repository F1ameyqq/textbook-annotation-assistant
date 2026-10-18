"""One ordered author run. Never retries or proceeds after a first failure."""
import argparse
import json
from pathlib import Path
import sys
import traceback
from support import ROOT, HERE, OUT, GROUPS, process, write, check_frozen


def run(root):
    assert root.is_relative_to(OUT)
    root.mkdir(parents=True, exist_ok=False)
    check_frozen()
    statuses = {name: 'NOT_RUN' for name in GROUPS}
    for name in GROUPS:
        try:
            process(root / 'watchdogs' / name, [sys.executable, '-X', 'utf8', '-B',
                str(HERE / 'support.py'), name, str(root)], 90)
        except BaseException:
            statuses[name] = 'FAILED'
            write(root / 'first-failure.txt', traceback.format_exc().encode('utf-8'))
            write(root / 'matrix.json', statuses)
            raise
        statuses[name] = 'PASS_AUTHOR_ONLY'
        print(json.dumps({'group': name, 'status': statuses[name]}), flush=True)
    write(root / 'matrix.json', statuses)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT / 'validation/author-01')
    args = parser.parse_args()
    run(args.output.resolve())
