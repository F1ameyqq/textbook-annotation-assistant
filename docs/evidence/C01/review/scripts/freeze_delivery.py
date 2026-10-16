"""Export only C01 delivery paths at an explicit clean commit, without checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--worktree', type=Path, required=True)
    p.add_argument('--base', required=True)
    p.add_argument('--commit', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()

    def git(*args):
        return subprocess.check_output(['git', '-C', str(a.worktree), *args], text=True, encoding='utf-8').strip()

    head = git('rev-parse', 'HEAD')
    status = git('status', '--porcelain=v1', '--untracked-files=all')
    if head != a.commit or status:
        raise RuntimeError('delivery not frozen at explicit clean commit: ' + repr((head, status)))
    paths = git('diff', '--name-only', a.base + '..' + a.commit).splitlines()
    prefixes = ('src/annotation/', 'tests/fixtures/contracts/', 'examples/contracts/', 'config/policies/')
    single = {'pyproject.toml', 'docs/contracts-implementation-v1.md', 'docs/tasks/C01-execution-report.md'}
    outside = [x for x in paths if x not in single and not x.startswith(prefixes)
               and not (x.startswith('tests/test_contracts') and x.endswith('.py'))]
    if outside:
        raise RuntimeError('out of C01 scope: ' + repr(outside))
    a.output.mkdir(parents=True, exist_ok=True)
    archive = a.output / 'delivery.zip'
    subprocess.run(['git', '-C', str(a.worktree), 'archive', '--format=zip', '-o', str(archive),
                    a.commit, '--', *paths], check=True)
    tree = a.output / 'tree'
    tree.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        z.extractall(tree)
    manifest = []
    for name in paths:
        local = tree / name
        manifest.append(dict(path=name, bytes=local.stat().st_size,
                             sha256=hashlib.sha256(local.read_bytes()).hexdigest()))
    result = dict(base=a.base, commit=head, branch=git('branch', '--show-current'),
                  execution_status=status, changed_paths=paths, files=manifest,
                  archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  diff_stat=git('diff', '--stat', a.base + '..' + a.commit),
                  commit_log=git('log', '--format=%H %s', a.base + '..' + a.commit))
    (a.output / 'delivery-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(commit=head, changed_files=len(paths), tree=str(tree)), ensure_ascii=False))


if __name__ == '__main__':
    main()
