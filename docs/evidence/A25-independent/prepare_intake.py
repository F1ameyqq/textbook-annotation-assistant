"""A25 reviewer preparation: copy permitted fixed inputs; run no product code."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone, timedelta

REPO = Path('D:/1800')
PUBLIC = REPO / 'docs/evidence/A25-independent'
PRIVATE = REPO / '.local/stages/a25-independent-20261023/preparation'
BASE = 'ee463c800bef1ec5010ee5950662b9726d474e42'
REVIEWER = '01a166e8-3f23-7192-a560-4724adca74b1'
EXPECTED_STDERR = '6cf231091eb51eb51542f57bcb6ea11e15279c696e612688e3ab2d48483fbfed'
BASE_FILES = [
    'tools/run_usense_live.py',
    'tools/run_usense_reviewed_batch.py',
    'src/annotation/runtime/usense_live/__init__.py',
    'src/annotation/runtime/usense_live/cli.py',
    'src/annotation/runtime/usense_live/config.py',
    'src/annotation/runtime/usense_live/core.py',
    'src/annotation/runtime/usense_live/update.py',
    'src/annotation/runtime/usense_live/revision.py',
    'src/annotation/runtime/usense_live/writer.py',
    'tests/usense_live/test_tool_entry.py',
    'docs/usense-live-runtime.md',
    'docs/usense-first-lesson-closure-20261023.md',
]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save_new(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as out:
        out.write(raw)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def item(source, target, raw, kind):
    save_new(target, raw)
    return {'source': str(source).replace('\\', '/'),
            'copy': str(target).replace('\\', '/'),
            'bytes': len(raw), 'sha256': digest(raw), 'kind': kind}


def main():
    if PRIVATE.exists():
        raise RuntimeError('Preparation directory already exists; no overwrite/replay')
    PRIVATE.mkdir(parents=True)
    entries = []
    for name in [
        'AGENTS.md',
        'docs/tasks/A25-lesson2-expansion-20261023.md',
        'docs/tasks/A25-lesson2-expansion-independent-review-20261023.md',
        'docs/coordination-state.json',
    ]:
        source = REPO / name
        entries.append(item(source, PRIVATE / 'instructions' / name,
                            source.read_bytes(), 'instruction_snapshot'))
    state_raw = (PRIVATE / 'instructions/docs/coordination-state.json').read_bytes()
    state = json.loads(state_raw.decode('utf-8-sig'))
    a25 = state['tasks']['A25']
    registration = state['A25_formal_chat_dispatch']
    if registration['review_thread_id'] != REVIEWER:
        raise RuntimeError('Reviewer registration mismatch')
    if a25['base_commit'] != BASE or a25['book_id'] != '46007447':
        raise RuntimeError('Scope identity mismatch')

    initial = REPO / '.local/stages/a25-lesson2-expansion-20261023/evidence'
    failure_entries = []
    for name in ['configure.stdout', 'configure.stderr', 'configure-process.json']:
        source = initial / name
        raw = source.read_bytes()
        if name == 'configure.stderr' and (digest(raw) != EXPECTED_STDERR or len(raw) != 1371):
            raise RuntimeError('Initial failure bytes mismatch')
        record = item(source, PRIVATE / 'initial-configure-failure' / name,
                      raw, 'frozen_initial_failure')
        entries.append(record)
        failure_entries.append(record)
    error = (PRIVATE / 'initial-configure-failure/configure.stderr').read_bytes()
    if b"ModuleNotFoundError: No module named 'annotation.runtime'" not in error:
        raise RuntimeError('Expected initial exception absent')
    process = json.loads((PRIVATE / 'initial-configure-failure/configure-process.json').read_text(encoding='utf-8-sig'))

    env = os.environ.copy()
    env['GIT_NO_LAZY_FETCH'] = '1'
    commands = []

    def git(args):
        argv = ['git', '-c', 'core.longpaths=true'] + args
        result = subprocess.run(argv, cwd=str(REPO), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        n = len(commands) + 1
        prefix = PRIVATE / 'commands' / ('%02d' % n)
        out = item('process stdout', prefix.with_suffix('.stdout'), result.stdout, 'raw_command_output')
        err = item('process stderr', prefix.with_suffix('.stderr'), result.stderr, 'raw_command_output')
        commands.append({'argv': argv, 'cwd': str(REPO).replace('\\', '/'),
                         'env': {'GIT_NO_LAZY_FETCH': '1'}, 'exit_code': result.returncode,
                         'stdout': out, 'stderr': err})
        if result.returncode != 0:
            save_new(PRIVATE / 'git-commands-partial.json', encode(commands))
            raise RuntimeError('Read-only frozen Git intake failed; stop without retry')
        return result.stdout

    resolved = git(['rev-parse', '--verify', BASE + '^{commit}']).decode('ascii').strip()
    if resolved != BASE:
        raise RuntimeError('Frozen baseline commit mismatch')
    for name in BASE_FILES:
        raw = git(['show', BASE + ':' + name])
        entries.append(item(BASE + ':' + name, PRIVATE / 'baseline-raw' / name,
                            raw, 'frozen_baseline_reference_only'))

    save_new(PRIVATE / 'git-commands.json', encode(commands))
    entries.append({'source': 'reviewer helper',
                    'copy': str(PUBLIC / 'prepare_intake.py').replace('\\', '/'),
                    'bytes': (PUBLIC / 'prepare_intake.py').stat().st_size,
                    'sha256': digest((PUBLIC / 'prepare_intake.py').read_bytes()),
                    'kind': 'reviewer_preparation_helper'})
    manifest = {'schema': 'a25-independent-preparation-inputs-v1',
                'created_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
                'status': 'WAITING_EXECUTION', 'base_commit': BASE,
                'reviewer_thread_id': REVIEWER,
                'scope': 'Preparation only; no author active worktree read; no product code imported or executed',
                'inputs': entries, 'commands': commands}
    save_new(PUBLIC / 'preparation-inputs.json', encode(manifest))
    summary = {'status': 'WAITING_EXECUTION', 'formal_product_acceptance': False,
               'reviewer_thread_id': REVIEWER,
               'coordinator_thread_id': registration.get('coordinator_thread_id', state.get('coordinator_thread_id')),
               'executor_thread_id': registration['execution_thread_id'],
               'model': registration['model'], 'thinking': registration['thinking'],
               'base_commit': BASE, 'book_id': a25['book_id'],
               'printed_questions': a25['printed_questions'],
               'reported_native_orders': a25['reported_current_native_orders'],
               'stable_targets': a25['stable_targets'],
               'automation_repository_snapshot_status': state['automation']['status'],
               'state_snapshot': entries[3],
               'initial_failure': {'verified_stderr_bytes': len(error),
                                   'verified_stderr_sha256': digest(error),
                                   'exit_code': process.get('exit_code'),
                                   'process_record_fields': sorted(process.keys()),
                                   'source_evidence': failure_entries,
                                   'classification': 'LOCAL_IMPORT_FAILURE_BEFORE_CONFIGURE',
                                   'platform_failure_claim': False},
               'executed_product_tests': 0, 'product_imports': 0,
               'browser_starts': 0, 'platform_requests': 0,
               'profile_reads_or_mutations': 0, 'OCR_or_model_calls': 0,
               'baseline_raw_reference_files': len(BASE_FILES),
               'frozen_new_delivery_commit': None,
               'preparation_inputs_sha256': digest((PUBLIC / 'preparation-inputs.json').read_bytes())}
    save_new(PUBLIC / 'preparation-observations.json', encode(summary))
    print(json.dumps({'status': summary['status'],
                      'baseline_reference_files': len(BASE_FILES),
                      'git_readonly_commands': len(commands),
                      'initial_stderr_sha256': digest(error),
                      'initial_exit_code': process.get('exit_code'),
                      'product_tests': 0}, ensure_ascii=True))


if __name__ == '__main__':
    main()
