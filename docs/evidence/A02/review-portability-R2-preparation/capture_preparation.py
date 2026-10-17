"""Preparation metadata and document checks only; never import or run A02 code."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('D:/1800')
OUT = Path(__file__).resolve().parent
REPORT = ROOT / 'docs/tasks/A02-portability-R2-review-preparation.md'
BASE = '38aca9dcc8d027409b95193e9cc142c2336b76d3'
WORKFLOW = '6b77c436742cf2826083b109d8ed86b85539cba6'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

def git(*args):
    result = subprocess.run(['git', '-C', str(ROOT), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
    return result.stdout

def main():
    for name in ('preparation-observation.json', 'preparation-validation.json', 'sha256-manifest.json'):
        assert not (OUT / name).exists(), 'Preparation has already been recorded; do not repeat or overwrite.'
    state_path = ROOT / 'docs/coordination-state.json'
    state_raw = state_path.read_bytes()
    state = json.loads(state_raw.decode('utf-8-sig'))
    a02 = state['tasks']['A02']
    paths = ['AGENTS.md', 'docs/coordination.md', 'docs/tasks/A02-portability-R2-dispatch.md',
             'docs/tasks/A01-integration-R1-review-report.md',
             'docs/evidence/A01/coordinator/integration-R2-preflight/coordinator-check.json',
             'docs/tasks/A02-review-R1-report.md', 'docs/architecture.md', 'docs/contracts-v1.md']
    sources = [{'path': p, 'sha256': sha((ROOT / p).read_bytes())} for p in paths]
    identity = git('show', BASE + ':examples/a02/R1/identity.py')
    old_test = git('show', BASE + ':tests/test_a02_r1.py')
    checkpoints = ['docs/tasks/A02-review-report.md', 'docs/tasks/A02-review-final-report.md', 'docs/tasks/A02-review-R1-report.md',
                   'docs/evidence/A02/review/sha256-manifest.json', 'docs/evidence/A02/review/formal/sha256-manifest.json',
                   'docs/evidence/A02/review-R1/sha256-manifest.json']
    preserved = {p: sha((ROOT / p).read_bytes()) for p in checkpoints}
    observation = {
        'phase': 'WAITING_EXECUTION', 'observed_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'task': 'A02 portability-R2 independent-review preparation', 'base_commit': BASE, 'workflow_commit': WORKFLOW,
        'formal_target_commit': None, 'formal_delivery_received': False, 'acceptance_decision': None,
        'execution_thread_id': '01a144cc-23e9-7c80-9a90-02162ef99b64',
        'review_thread_id': '01a144cc-2eae-7a23-b299-03f533e30951',
        'main_head_observed': git('rev-parse', 'HEAD').decode().strip(),
        'workflow_identity': git('show', '-s', '--format=%H %s', WORKFLOW).decode().strip(),
        'coordination_state_updated_at': state.get('updated_at'), 'coordination_state_sha256': sha(state_raw),
        'state_excerpt': {k: a02.get(k) for k in ('status', 'phase', 'operational_status', 'portability_repair', 'execution', 'review', 'integration')},
        'source_documents': sources,
        'fixed_baseline_reads': [{'commit': BASE, 'path': 'examples/a02/R1/identity.py', 'sha256': sha(identity)},
                                 {'commit': BASE, 'path': 'tests/test_a02_r1.py', 'sha256': sha(old_test)}],
        'old_review_checkpoint_sha256': preserved,
        'preservation_note': 'Preparation hashes reports and existing manifest bytes only; does not claim a new full historical-manifest audit.',
        'actual_preparation_read_commands': [
            'Get-Content AGENTS.md', 'Get-Content docs/tasks/A02-portability-R2-dispatch.md',
            'Get-Content docs/coordination.md -TotalCount 30', 'Get-Content docs/coordination-state.json',
            'Get-Content docs/tasks/A01-integration-R1-review-report.md -TotalCount 100',
            'Get-Content docs/evidence/A01/coordinator/integration-R2-preflight/coordinator-check.json',
            'git show ' + BASE + ':examples/a02/R1/identity.py',
            'git show ' + BASE + ':tests/test_a02_r1.py',
            'git rev-parse HEAD', 'git show -s --format=%H %s ' + WORKFLOW],
        'implementation_imports': 0, 'implementation_calls': 0, 'functional_tests_run': 0,
        'floating_worktree_read_or_run': False, 'browser_platform_network_credential_ocr_model_calls': 0,
        'external_model_cost': 0, 'other_codex_chats_messaged': 0,
        'permission_boundary': 'Only preparation report and reviewer-owned preparation evidence. No implementation/state/old-evidence modifications or stage release.',
        'resume_condition': 'Coordinator explicitly supplies frozen R2 patch/final commit, report and evidence manifest to this existing review chat.'}
    save(OUT / 'preparation-observation.json', observation)
    # Place actual targets before checking document links; finalize their bytes before sealing.
    validation_path = OUT / 'preparation-validation.json'
    manifest_path = OUT / 'sha256-manifest.json'
    save(validation_path, {'phase': 'PREPARATION_DOCUMENT_CHECK_IN_PROGRESS'})
    save(manifest_path, {'phase': 'PREPARATION_DOCUMENT_CHECK_IN_PROGRESS'})
    links = []
    whitespace = []
    for path in (REPORT, OUT / 'scenario-matrix.md'):
        text = path.read_text(encoding='utf-8')
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
            if target.startswith(('https:', 'http:', '#')):
                continue
            exists = (path.parent / target.split('#', 1)[0]).resolve().exists()
            links.append({'source': path.relative_to(ROOT).as_posix(), 'target': target, 'exists': exists})
        for n, line in enumerate(text.splitlines(), 1):
            if re.search(r'[ \t]+$', line):
                whitespace.append({'path': path.relative_to(ROOT).as_posix(), 'line': n})
    ids = re.findall(r'^\| (P\d{2}) \|', (OUT / 'scenario-matrix.md').read_text(encoding='utf-8'), re.M)
    assert ids == ['P' + str(i).zfill(2) for i in range(1, 15)], ids
    assert not whitespace and all(item['exists'] for item in links)
    assert all(sha((ROOT / p).read_bytes()) == digest for p, digest in preserved.items())
    validation = {'phase': 'WAITING_EXECUTION', 'scope': 'Preparation documents only; not candidate tests.',
                  'scenario_count': 14, 'scenario_ids': ids, 'all_scenario_execution_status': 'NOT_RUN',
                  'links': links, 'missing_links': [], 'trailing_whitespace': whitespace,
                  'old_report_manifest_checkpoint_count': len(preserved), 'checkpoint_mismatches': [],
                  'functional_tests_run': 0, 'acceptance_decision': None}
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    files = [REPORT] + sorted(p for p in OUT.rglob('*') if p.is_file() and p != manifest_path)
    manifest = {'schema_version': 1, 'phase': 'WAITING_EXECUTION', 'workflow_commit': WORKFLOW, 'base_commit': BASE,
                'formal_target_commit': None, 'acceptance_decision': None, 'self_excluded': True,
                'files': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size} for p in files]}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert all(sha((ROOT / item['path']).read_bytes()) == item['sha256'] for item in manifest['files'])
    print(json.dumps({'phase': 'WAITING_EXECUTION', 'scenarios_not_run': len(ids), 'document_links_checked': len(links),
                      'manifest_files': len(files), 'old_checkpoints_preserved': len(preserved), 'functional_tests_run': 0,
                      'report_sha256': sha(REPORT.read_bytes()), 'manifest_sha256': sha(manifest_path.read_bytes())}))

if __name__ == '__main__':
    main()
