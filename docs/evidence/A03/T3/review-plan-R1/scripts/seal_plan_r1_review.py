"""Seal only the new plan-R1 independent review; never touches old review files."""
import ast
import hashlib
import json
from pathlib import Path
import posixpath
import re
import subprocess

REPO = Path('D:/1800')
OUT = REPO / 'docs/evidence/A03/T3/review-plan-R1'
REPORT = REPO / 'docs/tasks/A03-T3-plan-R1-review-report.md'
TARGET = '765aef597a93fe36060fce65e17b22fe1c3408b8'
P = '1330047dd29890dea0e433ff01b991f615bf78f4'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(name, obj):
    (OUT / name).write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

def main():
    audit = json.loads((OUT / 'static-delta-audit.json').read_bytes())
    preserved = []
    for path, expected in audit['old_independent_review_files_unchanged'].items():
        actual = sha((REPO / path).read_bytes())
        assert actual == expected, path
        preserved.append({'path': path, 'sha256': actual, 'unchanged': True})
    plan_path = REPO / '.local/A03-T3-independent-review/plan-R1/frozen-target/docs/tasks/A03-T3-integration-plan.md'
    plan = plan_path.read_bytes()
    lines = plan.decode('utf-8').splitlines()
    assessment = []
    for ident, start, end, note in [
        ('C1', 17, 27, 'Legacy converter, conditional COMMITTED file proposal and blocked DB migration are separate; R15 remains open.'),
        ('C2', 29, 67, 'Clear-only candidate -> final-read/CAS -> fresh INITIAL; complete one-package proposal and session guard obligations remain unadopted.'),
        ('C3', 69, 99, 'Native/legacy identities and 1,2,3,2 pending sequence explicit; B representations and dispatch counts separated.'),
        ('C4', 101, 159, 'Recursive actual consumer bytes govern inheritance/delta; four operations and three bounded F paths explicit.')]:
        assert 1 <= start <= end <= len(lines)
        assessment.append({'id': ident, 'result': 'ACCEPTED_DOCUMENT_REVISION_ONLY',
                           'assessment_kind': 'MANUAL_DOCUMENT_SEMANTIC_REVIEW',
                           'target': TARGET, 'path': 'docs/tasks/A03-T3-integration-plan.md',
                           'raw_sha256': sha(plan), 'start': start, 'end': end, 'note': note,
                           'new_requirement_added': False, 'product_behavior_verified': False})
    write('c1-c4-assessment.json', {
        'target': TARGET, 'result': 'ACCEPTED_LIMITED_TO_C1_C4_PLAN_REVISION',
        'items': assessment, 'necessary_revisions': [],
        'coordinator_decisions_remain': ['D-CONV_CONDITIONAL_VERSION_ADOPTION', 'D-M_ONE_PACKAGE_ADOPTION', 'EXACT_K_AND_SCOPE_DEDUP_SELECTION'],
        'T2_historical_await_delivery_text_is_not_rework_reason': True,
        'old_28_mapping_acceptance_inherited_not_re_reviewed': True,
        'L2_note': 'C01 representation checks plus native B ledger isolation do not by themselves prove mixed-native execution consumption. The plan explicitly retains that unproven boundary.',
        'product_changes_authorized': False, 'business_execution_authorized': False,
        'a03': 'REWORK', 'i01': 'NOT_RELEASED', 'B_confirmation': 'NOT_GRANTED_BY_THIS_REVIEW'})

    argv = ['git', '-c', 'core.longpaths=true', 'show', P + ':src/annotation/delivery/mock/__init__.py']
    proc = subprocess.Popen(argv, cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw, error = proc.communicate(timeout=45)
    assert proc.returncode == 0
    tree = ast.parse(raw.decode('utf-8'))
    mock = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'MockSession')
    execute = next(node for node in mock.body if isinstance(node, ast.FunctionDef) and node.name == 'execute')
    doc = ast.get_docstring(execute)
    assert 'Remaining actions after a non-APPLIED result are read but never dispatched.' in doc
    write('legacy-generator-corroboration.json', {
        'scope': 'ONE_ADDITIONAL_STATIC_CALLEE_REFERENCE_ONLY_NO_EXECUTION',
        'commit': P, 'path': 'src/annotation/delivery/mock/__init__.py', 'raw_sha256': sha(raw),
        'execute_start': execute.lineno, 'execute_end': execute.end_lineno, 'execute_docstring': doc,
        'relation': 'Existing history.generate uses public MockSession.execute with first-action lost_response. This source read does not create history or measure effects.',
        'product_imports': 0, 'business_runs': 0, 'database_connections': 0})
    ast_files = []
    for path in sorted((OUT / 'scripts').glob('*.py')):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        ast_files.append(path.relative_to(REPO).as_posix())
    report = REPORT.read_bytes()
    report_text = report.decode('utf-8')
    assert all(line == line.rstrip() for line in report_text.splitlines())
    links = []
    for destination in re.findall(r'\[[^\]]+\]\(([^)]+)\)', report_text):
        relative = posixpath.normpath('docs/tasks/' + destination)
        absolute = (REPO / relative).resolve()
        if relative == 'docs/tasks/A03-T3-review-report.md':
            assert relative in audit['old_independent_review_files_unchanged']
            kind = 'preserved-prior-review'
        else:
            assert OUT.resolve() in absolute.parents
            assert absolute.is_file() or absolute == OUT / 'manifest.json'
            kind = 'new-review-plan-R1-owned-output'
        links.append({'destination': destination, 'checked': kind})
    write('process-release.json', {
        'scope': 'OWNED_STATIC_COMMANDS_ONLY_NOT_GLOBAL_PROCESS_SCAN',
        'audit_commands_completed_and_reaped': len(audit['review_commands']),
        'supplemental_command': {'argv': argv, 'cwd': str(REPO), 'pid': proc.pid,
                                'exit_code': proc.returncode, 'waited_and_reaped': True,
                                'stderr': error.decode('utf-8', 'replace')},
        'product_imports': 0, 'business_processes_started': 0, 'database_connections': 0,
        'background_processes_started': 0, 'browser_profile_sessions': 0,
        'unreleased_owned_sessions': [], 'unreleased_owned_business_processes': [],
        'main_git_index_or_commit_operations': 0,
        'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
    write('final-verification.json', {
        'target': TARGET, 'review_scope': 'C1_C4_AND_AFFECTED_REFERENCES_ONLY',
        'report_sha256': sha(report), 'manifest_members_independently_verified': 8,
        'affected_index_references_verified': 17, 'old_execution_files_preserved': 4,
        'accepted_28_rows_preserved_not_re_reviewed': 28,
        'old_independent_review_files_preserved': preserved,
        'scripts_AST_syntax_only': ast_files, 'report_links': links,
        'independent_review_tool_failures': [],
        'result': 'ACCEPTED_LIMITED_PLAN_REVISION_ONLY', 'necessary_revisions': [],
        'D_CONV_D_M_adopted_by_reviewer': False,
        'product_K_M_L_G_I01_acceptance': 'NOT_GRANTED', 'business_runs': 0,
        'database_connections': 0, 'unreleased_owned_sessions': []})
    members = []
    for path in [REPORT] + sorted(OUT.rglob('*')):
        if not path.is_file() or path == OUT / 'manifest.json':
            continue
        data = path.read_bytes()
        members.append({'path': path.relative_to(REPO).as_posix(), 'bytes': len(data), 'sha256': sha(data)})
    write('manifest.json', {'scope': 'A03_T3_PLAN_R1_INDEPENDENT_STATIC_REVIEW_ONLY',
                            'target': TARGET, 'members': members,
                            'self_excluded': 'docs/evidence/A03/T3/review-plan-R1/manifest.json',
                            'old_review_not_modified': True})
    for item in members:
        data = (REPO / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256']
    expected_paths = {REPORT.relative_to(REPO).as_posix()} | {
        path.relative_to(REPO).as_posix() for path in OUT.rglob('*')
        if path.is_file() and path != OUT / 'manifest.json'}
    assert expected_paths == {item['path'] for item in members}
    for item in preserved:
        assert sha((REPO / item['path']).read_bytes()) == item['sha256']
    print(json.dumps({'result': 'ACCEPTED_C1_C4_PLAN_REVISION_ONLY',
                      'report_sha256': sha(REPORT.read_bytes()),
                      'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()),
                      'manifest_members': len(members), 'old_review_files_preserved': len(preserved),
                      'business_runs': 0, 'database_connections': 0,
                      'unreleased_owned_sessions': []}, ensure_ascii=False))

if __name__ == '__main__':
    main()
