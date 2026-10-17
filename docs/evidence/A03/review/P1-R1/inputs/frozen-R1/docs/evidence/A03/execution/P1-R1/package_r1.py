"""A03 P1-R1 static packaging and preservation; no business/runtime imports."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
EVIDENCE = Path(__file__).resolve().parent
BASE = '2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9'
EXACT = ('docs/a03-recovery-contract-v1-r1-proposal.md', 'docs/tasks/A03-P1-R1-execution-report.md')
PREFIXES = ('examples/a03/P1-R1/', 'docs/evidence/A03/execution/P1-R1/')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=str(ROOT)).decode('utf-8').strip()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def current_files():
    result = {ROOT/name for name in EXACT if (ROOT/name).is_file()}
    result.update(p for prefix in PREFIXES for p in (ROOT/prefix).rglob('*') if p.is_file())
    return sorted(result, key=lambda path: path.as_posix())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['baseline', 'audit', 'manifest', 'verify'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    manifest_path = EVIDENCE/'sha256-manifest.json'
    baseline_path = EVIDENCE/'baseline-preservation.json'
    if args.mode == 'baseline':
        if git('rev-parse', 'HEAD') != BASE or git('diff', '--name-only', BASE):
            raise ValueError('Expected exact clean tracked P1 baseline')
        files = [{'path': name, 'bytes': (ROOT/name).stat().st_size, 'sha256': sha(ROOT/name)}
                 for name in git('ls-tree', '-r', '--name-only', BASE).splitlines()]
        dump(baseline_path, {'baseline_commit': BASE, 'worktree': str(ROOT),
                            'tracked_original_diff_empty_at_capture': True, 'files': files})
        print(json.dumps({'baseline_files': len(files), 'baseline_commit': BASE}))
        return 0
    if args.mode == 'audit':
        baseline = load(baseline_path)
        errors = []
        for row in baseline['files']:
            path = ROOT/row['path']
            if not path.is_file() or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
                errors.append({'old_file_changed': row['path']})
        changes = set(git('diff', '--name-only', BASE).splitlines())
        changes.update(git('ls-files', '--others', '--exclude-standard').splitlines())
        for name in changes:
            if name and name not in EXACT and not name.startswith(PREFIXES):
                errors.append({'out_of_scope': name})
        links = 0
        pending_outputs = {manifest_path.resolve()}
        if args.output:
            pending_outputs.add(args.output.resolve())
        for path in [ROOT/name for name in EXACT] + [ROOT/'examples/a03/P1-R1/README.md']:
            if not path.is_file():
                errors.append({'missing_document': str(path)})
                continue
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
                if '://' in target or target.startswith('#'):
                    continue
                local = (path.parent/target.split('#')[0]).resolve()
                links += 1
                if not local.exists() and local not in pending_outputs:
                    errors.append({'broken_link': str(path.relative_to(ROOT)), 'target': target})
        ignored = git('ls-files', '--others', '--ignored', '--exclude-standard',
                      'examples/a03/P1-R1', 'docs/evidence/A03/execution/P1-R1').splitlines()
        result = {'check_kind': 'P1_R1_STATIC_PRESERVATION_ONLY', 'baseline_commit': BASE,
                  'old_files_checked': len(baseline['files']), 'old_files_changed': sum('old_file_changed' in e for e in errors),
                  'changes_checked': len(changes), 'local_links_checked': links,
                  'ignored_new_scope_files': ignored, 'errors': errors, 'passed': not errors,
                  'runtime_function_executed': False, 'owned_background_sessions_started': 0,
                  'pending_owned_sessions': 0}
        if args.output:
            dump(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    if args.mode == 'manifest':
        rows = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                for p in current_files() if p != manifest_path]
        dump(manifest_path, {'kind': 'A03_P1_R1_SHA256_MANIFEST', 'baseline_commit': BASE,
                             'algorithm': 'SHA256', 'excluded_self': manifest_path.relative_to(ROOT).as_posix(),
                             'excluded_scope_files': [], 'files': rows})
        print(json.dumps({'manifest_entries': len(rows), 'sha256': sha(manifest_path)}))
        return 0
    manifest = load(manifest_path)
    errors = []
    expected = {row['path'] for row in manifest['files']}
    actual = {p.relative_to(ROOT).as_posix() for p in current_files() if p != manifest_path}
    if expected != actual:
        errors.append({'manifest_file_set_difference': sorted(expected ^ actual)})
    for row in manifest['files']:
        path = ROOT/row['path']
        if not path.is_file() or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            errors.append({'manifest_mismatch': row['path']})
    for path in [ROOT/name for name in EXACT] + [ROOT/'examples/a03/P1-R1/README.md']:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
            if '://' not in target and not target.startswith('#') and not (path.parent/target.split('#')[0]).exists():
                errors.append({'broken_link': str(path.relative_to(ROOT)), 'target': target})
    print(json.dumps({'manifest_entries_verified': len(manifest['files']), 'errors': errors,
                      'manifest_sha256': sha(manifest_path)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1

if __name__ == '__main__':
    sys.exit(main())
