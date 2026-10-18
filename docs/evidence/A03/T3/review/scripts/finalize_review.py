"""Seal this static review only; no product imports, tests, or database access."""
import ast
import hashlib
import json
import posixpath
from pathlib import Path
import re
import subprocess
import sys

REPO = Path('D:/1800')
ROOT = REPO / '.local/A03-T3-independent-review'
OUT = REPO / 'docs/evidence/A03/T3/review'
REPORT = REPO / 'docs/tasks/A03-T3-review-report.md'
TARGET = '3fcdb73416142a0a85dfb951a7f839849871c549'
P = '1330047dd29890dea0e433ff01b991f615bf78f4'
commands = []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args):
    argv = ['git', '-c', 'core.longpaths=true', *args]
    result = subprocess.run(argv, cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    commands.append({'argv': argv, 'exit_code': result.returncode, 'cwd': str(REPO),
                     'completed_and_reaped': True, 'stdout_sha256': sha(result.stdout),
                     'stderr': result.stderr.decode('utf-8', 'replace')})
    if result.returncode:
        raise RuntimeError(repr(argv))
    return result.stdout

def write(name, obj):
    (OUT / name).write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

def main():
    index = json.loads((ROOT / 'frozen-target/docs/evidence/A03/T3/execution/reference-index.json').read_bytes())
    basepath = 'src/annotation/contracts/a03_native/'
    profile_raw = git('show', P + ':' + basepath + 'data/profile.json')
    profile = json.loads(profile_raw)
    adoption = json.loads(git('show', P + ':' + basepath + 'data/adoption.json'))
    assert adoption['profile_sha256'] == sha(profile_raw)
    pins = []
    for relative, expected in profile['implementation_pins']:
        path = 'src/' + relative[1:] if relative.startswith('@') else basepath + relative
        data = git('show', P + ':' + path)
        assert sha(data) == expected, path
        pins.append({'path': path, 'raw_sha256': sha(data), 'matches': True, 'kind': 'implementation'})
    for relative, expected in profile['schema_pins']:
        path = basepath + 'data/' + relative
        data = git('show', P + ':' + path)
        assert sha(data) == expected, path
        pins.append({'path': path, 'raw_sha256': sha(data), 'matches': True, 'kind': 'schema'})
    impacts = []
    for item in index['historical_product_impact']:
        actual = git('diff', '--name-only', item['historical_target'], P, '--', 'src').decode('utf-8').splitlines()
        assert actual == item['changed_product_paths'], item['historical_target']
        impacts.append({'historical_target': item['historical_target'], 'source_commit': P,
                        'paths_match_author_index': True, 'changed_path_count': len(actual),
                        'scope': 'STATIC_IMPACT_INDEX_ONLY_NOT_CURRENT_ACCEPTANCE'})
    write('additional-pin-and-impact-checks.json', {'source_commit': P, 'profile_raw_sha256': sha(profile_raw),
        'adoption_profile_matches': True, 'pins': pins, 'historical_impact_checks': impacts,
        'commands': commands, 'product_imports': 0, 'business_runs': 0, 'database_connections': 0})

    body = REPORT.read_text(encoding='utf-8')
    assert all(line == line.rstrip() for line in body.splitlines())
    links = []
    for dest in re.findall(r'\[[^\]]+\]\(([^)]+)\)', body):
        path = posixpath.normpath('docs/tasks/' + dest)
        if path in {'docs/tasks/A03-T3-remaining-matrix.md', 'docs/tasks/A03-T3-integration-plan.md'}:
            git('cat-file', '-e', TARGET + ':' + path)
            method = 'exact-target-git-tree'
        else:
            resolved = (REPO / path).resolve()
            assert resolved.is_file() or path == 'docs/evidence/A03/T3/review/manifest.json', path
            assert resolved == OUT / 'manifest.json' or OUT.resolve() in resolved.parents, path
            method = 'review-owned-output'
        links.append({'document': 'docs/tasks/A03-T3-review-report.md', 'destination': dest, 'verified_at': method})
    semantic = json.loads((OUT / 'semantic-28-review.json').read_bytes())
    assert len(semantic['requirements']) == 28
    compiled = []
    for path in sorted((OUT / 'scripts').glob('*.py')):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        compiled.append(path.relative_to(REPO).as_posix())
    write('reviewer-correction.json', {
        'classification': 'REVIEWER_STATIC_EXCERPT_RANGE_ERROR_NOT_PRODUCT_FAILURE',
        'first_script': 'docs/evidence/A03/T3/review/reviewer-tool-failure-01/review_semantics.failed.py',
        'first_observed_exit_code': 1,
        'first_output_provenance': 'Observed combined tool output transcribed; no separately registered PID or raw stream files claimed.',
        'single_correction': 'Converter excerpt end line 1282 -> 1279, start unchanged 1273.',
        'rerun': 'Only static review_semantics.py; exit0. No business or source mutation.',
        'historical_failure_files_changed': False})
    write('process-release.json', {
        'scope': 'OWNED_STATIC_REVIEW_COMMANDS_ONLY_NOT_GLOBAL_PID_SCAN',
        'identity_audit': {'reported_exit_code': 0, 'recorded_git_commands_completed_and_reaped': 119},
        'semantic_first_attempt': {'reported_exit_code': 1, 'classification': 'static excerpt bounds error',
                                   'pid_or_raw_split_streams_claimed': False},
        'semantic_corrected_attempt': {'reported_exit_code': 0, 'recorded_git_commands_completed_and_reaped': 15},
        'final_static_git_commands': commands,
        'product_imports': 0, 'business_processes_started': 0, 'database_connections': 0,
        'background_processes_started': 0, 'browser_or_profile_sessions': 0,
        'unreleased_owned_sessions': [], 'unreleased_owned_business_processes': [],
        'statement': 'All launched static shell/Python/Git calls returned synchronously. No business owner or background session created.',
        'main_git_index_or_commit_operations': 0,
        'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
    write('final-verification.json', {
        'target': TARGET, 'report': REPORT.relative_to(REPO).as_posix(), 'report_sha256': sha(REPORT.read_bytes()),
        'report_links': links, 'scripts_ast_syntax_only': compiled,
        'independent_manifest_members_verified': 5, 'independent_reference_entries_verified': 70,
        'independent_linked_indexes_verified': 44, 'independent_requirement_mappings': 28,
        'implementation_pin_count': sum(item['kind'] == 'implementation' for item in pins),
        'schema_pin_count': sum(item['kind'] == 'schema' for item in pins),
        'historical_impact_index_count': len(impacts),
        'matrix_result': 'ACCEPTED_LIMITED',
        'plan': 'PENDING_ONE_CONSOLIDATED_REVISION_AND_COORDINATOR_DECISIONS_C1_C4',
        'functional_tests': 'NOT_RUN', 'a03': 'REWORK', 'i01': 'NOT_RELEASED',
        'no_t1_t2_new_results_used_to_update_old_frozen_matrix': True})
    members = []
    for path in [REPORT] + sorted(OUT.rglob('*')):
        if not path.is_file() or path == OUT / 'manifest.json':
            continue
        data = path.read_bytes()
        members.append({'path': path.relative_to(REPO).as_posix(), 'bytes': len(data), 'sha256': sha(data)})
    write('manifest.json', {'scope': 'A03_T3_PHASE1_INDEPENDENT_STATIC_REVIEW_ONLY',
                            'target': TARGET, 'members': members,
                            'self_excluded': 'docs/evidence/A03/T3/review/manifest.json',
                            'old_evidence_not_rewritten': True})
    for item in members:
        data = (REPO / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256']
    actual = {path.relative_to(REPO).as_posix() for path in OUT.rglob('*') if path.is_file() and path.name != 'manifest.json'}
    assert actual | {REPORT.relative_to(REPO).as_posix()} == {item['path'] for item in members}
    print(json.dumps({'report_sha256': sha(REPORT.read_bytes()),
                      'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()),
                      'manifest_members': len(members), 'implementation_pins': 23,
                      'schema_pins': len(profile['schema_pins']), 'impact_entries': len(impacts),
                      'unreleased_owned_sessions': [], 'product_imports': 0,
                      'database_connections': 0}, ensure_ascii=False))

if __name__ == '__main__':
    main()
