"""A03-P1 packaging audit only. No recovery implementation or semantic admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
EVIDENCE = ROOT / 'docs/evidence/A03/execution/P1'
WORKFLOW = 'a354f95f1d0b40a8f0847b57fa3978cac999e7a2'
BASE = 'ec1b4defbfa3ec0f181d291106fb53313983e493'
ALLOWED = ('examples/a03/P1/', 'docs/evidence/A03/execution/P1/')
EXACT = ('docs/a03-recovery-contract-v1-proposal.md', 'docs/tasks/A03-P1-execution-report.md')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=str(ROOT)).decode('utf-8').strip()

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

def allowed(path):
    return path in EXACT or path.startswith(ALLOWED)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['baseline', 'audit', 'manifest', 'verify-manifest'])
    args = parser.parse_args()
    os.chdir(str(ROOT))
    baseline_path = EVIDENCE / 'baseline-files.json'
    manifest_path = EVIDENCE / 'sha256-manifest.json'
    if args.mode == 'baseline':
        paths = git('ls-tree', '-r', '--name-only', WORKFLOW).splitlines()
        if git('diff', '--name-only', WORKFLOW):
            raise RuntimeError('Tracked baseline modified before baseline capture')
        files = [{'path': name, 'bytes': (ROOT/name).stat().st_size, 'sha256': sha(ROOT/name)} for name in paths]
        write_new(baseline_path, {'design_only': True, 'source_commit': WORKFLOW, 'base_commit': BASE,
                                 'initial_tracked_diff_empty': True, 'files': files})
        print(json.dumps({'baseline_files': len(files), 'source_commit': WORKFLOW}))
        return
    if args.mode == 'audit':
        original = json.loads(baseline_path.read_text(encoding='utf-8'))
        errors = []
        for entry in original['files']:
            path = ROOT/entry['path']
            if not path.is_file() or path.stat().st_size != entry['bytes'] or sha(path) != entry['sha256']:
                errors.append({'baseline_changed': entry['path']})
        changes = set(git('diff', '--name-only', WORKFLOW).splitlines())
        changes.update(git('ls-files', '--others', '--exclude-standard').splitlines())
        for path in sorted(changes):
            if path and not allowed(path):
                errors.append({'outside_allowed_paths': path})
        link_count = 0
        pending_manifest_link = False
        for name in EXACT + ('examples/a03/P1/README.md',):
            path = ROOT/name
            if not path.exists():
                errors.append({'missing_document': name})
                continue
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
                if '://' in target or target.startswith('#'):
                    continue
                local = target.split('#')[0]
                if local:
                    link_count += 1
                    pending_outputs = {manifest_path.resolve(), (EVIDENCE/'delivery-audit.json').resolve()}
                    if (path.parent/local).resolve() in pending_outputs and not (path.parent/local).exists():
                        pending_manifest_link = True
                    elif not (path.parent/local).exists():
                        errors.append({'broken_link': name, 'target': target})
        output = {'check_kind': 'P1_STATIC_PACKAGING_ONLY', 'workflow_commit': WORKFLOW,
                  'base_commit': BASE, 'python': sys.version, 'python_executable': sys.executable,
                  'cwd': str(ROOT), 'baseline_files_checked': len(original['files']),
                  'baseline_mismatches': sum('baseline_changed' in e for e in errors),
                  'new_or_changed_paths': sorted(changes), 'local_links_checked': link_count,
                  'pending_manifest_link_verified_by_final_verify_manifest': pending_manifest_link,
                  'errors': errors, 'passed': not errors,
                  'recovery_semantics_executed': False, 'new_recovery_function_executed': False,
                  'owned_background_processes_started': 0, 'pending_owned_sessions': 0}
        write_new(EVIDENCE/'delivery-audit.json', output)
        print(json.dumps({k:v for k,v in output.items() if k not in ('new_or_changed_paths',)}, ensure_ascii=False))
        sys.exit(0 if not errors else 1)
    if args.mode == 'manifest':
        files = []
        for prefix in ALLOWED:
            files.extend(path for path in (ROOT/prefix).rglob('*') if path.is_file())
        files.extend(ROOT/name for name in EXACT)
        files = sorted(set(files), key=lambda path: path.as_posix())
        rows = [{'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}
                for path in files if path != manifest_path and '__pycache__' not in path.parts]
        write_new(manifest_path, {'kind': 'A03_P1_SHA256_MANIFEST', 'algorithm': 'SHA256',
                                 'excluded_self': manifest_path.relative_to(ROOT).as_posix(),
                                 'excluded_generated_cache': '**/__pycache__/** (none committed)',
                                 'files': rows})
        print(json.dumps({'manifest_files': len(rows), 'manifest_sha256': sha(manifest_path)}))
        return
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    errors = []
    for row in manifest['files']:
        path = ROOT/row['path']
        if not path.is_file() or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            errors.append(row['path'])
    listed = {row['path'] for row in manifest['files']}
    actual = {path.relative_to(ROOT).as_posix() for prefix in ALLOWED
              for path in (ROOT/prefix).rglob('*')
              if path.is_file() and path != manifest_path and '__pycache__' not in path.parts}
    actual.update(EXACT)
    if actual != listed:
        errors.extend(['MANIFEST_FILE_SET:' + name for name in sorted(actual ^ listed)])
    for name in EXACT + ('examples/a03/P1/README.md',):
        path = ROOT/name
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
            if '://' not in target and not target.startswith('#') and not (path.parent/target.split('#')[0]).exists():
                errors.append('BROKEN_LINK:' + name + ':' + target)
    print(json.dumps({'manifest_files_verified': len(manifest['files']), 'errors': errors,
                      'manifest_sha256': sha(manifest_path)}))
    sys.exit(0 if not errors else 1)

if __name__ == '__main__':
    main()
