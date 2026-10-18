"""Verify exact scoped merge bytes; no business invocation."""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('D:/1800')
WORKFLOW = 'ca1fb902c2228579cd2d0c84d81fc72cd0643796'
CANDIDATE = '3d22524ff626fc7b0376b7312be6fe75f2e73aab'
AUTHOR = '6f8f1d6fa4c8db9678738673a54fa862df9a666e'
EDITS = {'src/annotation/source/b_q1/reader.py', 'src/annotation/quality/q1_offline.py'}
os.environ['GIT_NO_LAZY_FETCH'] = '1'


def tree(rev):
    data = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'ls-tree', '-rz', rev], cwd=ROOT)
    return {part.split(b'\t', 1)[1].decode(): tuple(part.split(b'\t', 1)[0].decode().split())
            for part in data.split(b'\0') if part}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', required=True)
    p.add_argument('--integrated', required=True)
    p.add_argument('--review', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    old, current, workflow, candidate, author, review = [tree(r) for r in
        (args.base, args.integrated, WORKFLOW, CANDIDATE, AUTHOR, args.review)]
    a_paths = {path for path in author if workflow.get(path) != author[path]}
    r_paths = {path for path in review if candidate.get(path) != review[path]}
    assert all(path in author for path in workflow)
    assert all(review.get(path) == value for path, value in candidate.items())
    assert a_paths & set(workflow) == EDITS
    assert not a_paths & r_paths
    expected = dict(old)
    for paths, source in ((a_paths, author), (r_paths, review)):
        for path in paths:
            if path in old and path not in EDITS:
                assert old[path] == source[path]
            expected[path] = source[path]
    assert current == expected
    assert all(current.get(path) == value for path, value in old.items() if path not in EDITS)
    assert all(current.get(path) == value for path, value in candidate.items() if path.startswith('src/'))
    result = {'result': 'PASS_SCOPED_LOCAL_INTEGRATION', 'base': args.base,
              'integration_commit': args.integrated, 'candidate': CANDIDATE,
              'author_delivery': AUTHOR, 'review_delivery': args.review,
              'modified_old_paths': sorted(EDITS), 'all_other_old_paths_raw_preserved': True,
              'old_paths_preserved': len(old) - len(EDITS),
              'added_paths': len(set(current) - set(old)), 'deleted_paths': 0,
              'all_candidate_source_bytes_equal': True, 'all_frozen_evidence_bytes_equal': True,
              'author_paths': sorted(a_paths), 'review_paths': sorted(r_paths),
              'new_business_attempts': 0, 'new_dispatches': 0, 'platform_actions': 0, 'pushed': False}
    output = Path(args.output)
    assert not output.exists()
    output.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({k: v for k, v in result.items() if k not in ('author_paths', 'review_paths')}))


if __name__ == '__main__':
    main()
