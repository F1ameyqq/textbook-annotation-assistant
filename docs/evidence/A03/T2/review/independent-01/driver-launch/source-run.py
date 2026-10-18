"""One C12 batch followed by exactly one H1; stop at the first failure."""
import argparse
import json
from pathlib import Path
import sys

from t2_support import HERE, ROOT, TEST, frozen, process, write


def main(root):
    root.relative_to((ROOT / 'docs/evidence/A03/T2/execution').resolve())
    root.mkdir(parents=True, exist_ok=False)
    git_folder = root / 'processes/candidate-Git'
    process(git_folder, ['git', '-c', 'core.longpaths=true', 'rev-parse', 'HEAD'], 30)
    write(root / 'candidate.json', {'candidate': (git_folder / 'stdout.txt').read_text(encoding='ascii').strip(),
        'input_sha256': frozen(), 'frozen_source_index': str(HERE / 'inputs.json')})
    matrix = {'C': 'NOT_RUN', 'H1': 'NOT_RUN', 'status': 'REVIEW'}
    try:
        print('C12 starting', flush=True)
        process(root / 'processes/C', [sys.executable, '-X', 'utf8', '-B', str(TEST), 'contracts', str(root)], 60)
        matrix['C'] = 'PASS_AUTHOR_ONLY'
        print('C12 complete; H1 starting', flush=True)
        process(root / 'processes/H1-watchdog', [sys.executable, '-X', 'utf8', '-B', str(HERE / 't2_support.py'), str(root)], 90)
        matrix['H1'] = 'PASS_AUTHOR_ONLY'
    except BaseException as error:
        matrix.update(status='REWORK', error=repr(error))
        raise
    finally:
        write(root / 'matrix.json', matrix)
    print(json.dumps(matrix))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--root-child', action='store_true')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.relative_to((ROOT / 'docs/evidence/A03/T2/execution').resolve())
    if args.root_child:
        main(output)
    else:
        process(ROOT / 'docs/evidence/A03/T2/execution/launch' / output.name,
            [sys.executable, '-X', 'utf8', '-B', str(Path(__file__).resolve()), '--root-child', '--output', str(output)], 180)
        print((output / 'matrix.json').read_text(encoding='utf-8'), flush=True)
