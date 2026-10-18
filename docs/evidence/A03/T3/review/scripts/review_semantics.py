"""Static source anchors and manually reviewed requirement classifications."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

REPO = Path('D:/1800')
ROOT = REPO / '.local/A03-T3-independent-review'
OUT = REPO / 'docs/evidence/A03/T3/review'
P = '1330047dd29890dea0e433ff01b991f615bf78f4'
W = 'f7084b2e8f2e9a1fcf758f9cba56ec9c9fb1f304'
T = '3fcdb73416142a0a85dfb951a7f839849871c549'
commands = []
cache = {}

def read(commit, path):
    key = (commit, path)
    if key not in cache:
        argv = ['git', '-c', 'core.longpaths=true', 'show', commit + ':' + path]
        result = subprocess.run(argv, cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        commands.append({'argv': argv, 'cwd': str(REPO), 'exit_code': result.returncode,
                         'completed_and_reaped': True, 'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                         'stderr': result.stderr.decode('utf-8', 'replace')})
        if result.returncode:
            raise RuntimeError(repr(argv))
        cache[key] = result.stdout
    return cache[key]

def save(name, value):
    (OUT / name).write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

def anchor(label, commit, path, start, end):
    raw = read(commit, path)
    lines = raw.decode('utf-8').splitlines()
    assert 1 <= start <= end <= len(lines)
    return {'label': label, 'commit': commit, 'path': path, 'raw_sha256': hashlib.sha256(raw).hexdigest(),
            'start': start, 'end': end, 'text': '\n'.join(lines[start - 1:end]),
            'type': 'STATIC_SOURCE_OR_DOCUMENT_EXCERPT_NOT_RUNTIME_RESULT'}

def matched(label, commit, path, terms):
    raw = read(commit, path)
    lines = raw.decode('utf-8').splitlines()
    return {'label': label, 'commit': commit, 'path': path, 'raw_sha256': hashlib.sha256(raw).hexdigest(),
            'matched_lines': [{'line': i, 'text': line} for i, line in enumerate(lines, 1)
                              if any(term in line for term in terms)],
            'type': 'STATIC_SOURCE_OR_DOCUMENT_EXCERPT_NOT_RUNTIME_RESULT'}

def main():
    prefix = 'src/annotation/'
    anchors = [
        anchor('UNATTEMPTED_STUB', P, prefix + 'runtime/storage/__init__.py', 1045, 1048),
        anchor('ONE_QUESTION_LANGUAGE', P, prefix + 'quality/synthetic_precheck.py', 48, 85),
        anchor('PLANNER_ACTION_PER_QUESTION', P, prefix + 'delivery/planner/__init__.py', 265, 290),
        anchor('NATIVE_PLAN_WHILE_HOLD', P, prefix + 'runtime/storage/native.py', 415, 432),
        anchor('ORDINARY_LEASE_HOLD_GUARD', P, prefix + 'runtime/storage/__init__.py', 340, 354),
        anchor('POST_HOLD_PROOF_REQUIRES_CURRENT_HOLD', P, prefix + 'runtime/storage/native.py', 258, 284),
        anchor('ASSERT_PRE_USES_CURRENT_PROOF', P, prefix + 'runtime/storage/native.py', 160, 174),
        anchor('CLEAR_REQUIRES_INDEXED_CANDIDATE', P, prefix + 'runtime/storage/holds.py', 291, 337),
        anchor('CLEAR_LOCAL_CURRENTNESS_AND_EVENT', P, prefix + 'runtime/storage/holds.py', 341, 365),
        anchor('INDEXED_ARTIFACT_ONLY', P, prefix + 'runtime/storage/holds.py', 63, 75),
        anchor('ARCHIVE_IMPORT_CLASSIFICATION', P, prefix + 'runtime/storage/__init__.py', 906, 922),
        anchor('RECONCILE_BUDGET', P, prefix + 'runtime/recovery/__init__.py', 135, 170),
        anchor('PERSISTED_ATTEMPT_LIMIT', P, prefix + 'runtime/storage/__init__.py', 936, 958),
        anchor('CONVERTER_LEGACY_COMPLETION', P, prefix + 'contracts/recovery.py', 1273, 1279),
        anchor('NATIVE_FRESH_META', P, prefix + 'runtime/storage/native.py', 435, 455),
        matched('CLI_LEGACY', P, prefix + 'runtime/recovery/cli.py',
                ['from annotation.runtime.storage import', 'store = init_state', 'store = open_state',
                 'operation == "replan"', 'def _build_current_plan_locked', 'pre = next']),
        matched('R1_DECISIONS', W, 'docs/tasks/A03-P2-R1-proposal-coordinator-decision.md',
                ['| 未尝试只读预算', '| 排他与 CAS', '| 已知 DB 接纳', '| 转换接纳点', '| R17', '| 证据保全']),
        matched('R2_STATIC_ONLY', W, 'docs/tasks/A03-P2-R2-proposal-coordinator-decision.md',
                ['SESSION-02', 'CONVERSION-07', '不批准', '未执行']),
        matched('R8_FIXED_LANGUAGE_FRESH_ONLY', W, 'docs/tasks/A03-P2-R8-native-bridge-implementation.md',
                ['固定合成 oracle', '未知库、既有旧库', '| N7', '原 P2 V01', '固定单题']),
        matched('R8R3_POST_HOLD_LIMIT', W, 'docs/tasks/A03-P2-R8-R3-post-hold-coordinator-decision.md',
                ['hold 未清除', '不同 hold', 'N7', '不重跑这个失败路径']),
        matched('R8R4_MULTI_PENDING', W, 'docs/tasks/A03-P2-R8-R4-remaining-coordinator-decision.md',
                ['正常多动作', '有限实现与采用范围', 'before_completion']),
        matched('R10_LIMITED_ACCEPTANCE', W, 'docs/tasks/A03-P2-R10-owner-fencing-coordinator-decision.md',
                ['有限 ACCEPTED', 'effects均0', '多动作仍需明确采用范围']),
        matched('R11_FOUR_CUTS_ONLY', W, 'docs/tasks/A03-P2-R11-crash-cuts-coordinator-decision.md',
                ['范围仅为', '| BEFORE_', '| AFTER_', 'F2/F3', '不重跑已接受']),
    ]
    native = ast.parse(read(P, prefix + 'runtime/storage/native.py').decode('utf-8'))
    native_class = next(node for node in native.body if isinstance(node, ast.ClassDef) and node.name == 'NativeRuntimeStore')
    methods = [node.name for node in native_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert 'commit_unattempted_absence' not in methods
    assert any(isinstance(node, ast.Name) and node.id == 'RuntimeStore' for node in native_class.bases)
    body = read(P, prefix + 'runtime/storage/__init__.py').decode('utf-8')
    base = next(node for node in ast.parse(body).body if isinstance(node, ast.ClassDef) and node.name == 'RuntimeStore')
    stub = next(node for node in base.body if isinstance(node, ast.FunctionDef) and node.name == 'commit_unattempted_absence')
    assert len(stub.body) == 1 and isinstance(stub.body[0], ast.Expr) and isinstance(stub.body[0].value, ast.Call)
    converter = next(node for node in ast.parse(read(P, prefix + 'contracts/recovery.py').decode('utf-8')).body
                     if isinstance(node, ast.FunctionDef) and node.name == 'convert_synthetic_fixture')
    source_lines = read(P, prefix + 'contracts/recovery.py').decode('utf-8').splitlines()
    converter_text = '\n'.join(source_lines[converter.lineno - 1:converter.end_lineno])
    assert 'COMPLETED_NEW_FIXTURE' in converter_text and 'COMMITTED' not in converter_text

    meanings = {
        'V01': ('M1', 'Multi-action requirement retained; existing normal single-action/old three-action observations remain version-limited.'),
        'V02': ('F', 'Six named single-action crash categories covered by historical accepted subscopes; no new full crash matrix.'),
        'V03': ('T1/T2/M3', 'Abnormal comparisons and existing-receipt terminal chain are outstanding; ABSENT new planning remains distinct.'),
        'V04': ('M2', 'Unattempted sufficient/insufficient ABSENT and prefix distinction correctly retained; unconditional inherited stub is static gap.'),
        'V05': ('L1/L2', 'Full same-book scope/run scan, one resolved/one outstanding, other book and legal multi-book remain required.'),
        'V06': ('L3/F', 'Accepted controlled owner examples preserved; new UNKNOWN and stale proof remain. Field reset excluded.'),
        'V07': ('T2/L4/G1', 'Identity/chain/version guard distinctions retained; new counts are proposed caps, not original standards.'),
        'V08': ('G2/G3', 'Storage/format failure requirements preserved; fixture conversion and old-DB adoption require separate scope decision.'),
        'V09': ('G3/G4', 'Archive versus current eligibility, legacy no-intent UNKNOWN and real-source refusal retained; no implicit DB migration authority.'),
        'V10': ('T2/G5/G6', 'Denominator/content/submission/budget requirements retained; diagnostic progress allowed where complete report not justified.'),
        'R01': ('F', 'Exact scope, raw identity, report/manifest/release requirements retained without remaking historical missing artifacts.'),
        'R02': ('T2/G1', 'Load/value validation and current runtime qualification remain distinct; early rejection cannot prove later guard.'),
        'R03': ('F', 'Historical named crash cuts retained, not extrapolated to arbitrary schedules; no mandatory historical rerun.'),
        'R04': ('T1/T2/M/F', 'Independent runtime and target evidence retained; sequential copies not called atomic snapshots.'),
        'R05': ('T1/T2/M2', 'Sufficient MATCH/ABSENT preserved; inconclusive inputs stay pending, reconciliation adds no target effect.'),
        'R06': ('T2/L3/L4', 'Immutable original receipt and new UNKNOWN priority retained; runtime chain controls are separate from old static DAG proof.'),
        'R07': ('L1', 'Local package and caller empty ledger do not substitute for controlled full-book current scan.'),
        'R08': ('G1/G2/L1/L3', 'Supported identity/state replacement and pending bypass guards retained; field-reset variants excluded.'),
        'R09': ('F', 'Accepted two controlled owner examples preserved; only actual changed guard justifies a new differential check.'),
        'R10': ('L2', 'Other-book single/multi-book forms and multiple same-book histories retained; choose exact archive family before running.'),
        'R11': ('M1/M2', 'APPLIED/UNKNOWN/NOT_ATTEMPTED and adequate/inadequate absence retained; D2 MAY_HAVE_BEEN_ATTEMPTED is not unattempted.'),
        'R12': ('M3/G1/L1', 'Real fresh checks/plan plus full-book pending check remain mandatory; optional CLI wording needs executable command contract.'),
        'R13': ('M3/G1', 'Target/version drift and fresh hold proof retained; listed current POST_HOLD plan/clear/use chain has static seams.'),
        'R14': ('G2/G3', 'Identifiable fail-closed storage/format/conversion interruption retained; no exact outer error-symbol expansion.'),
        'R15': ('G3', 'Old immutable reads/conversion and no-intent UNKNOWN block retained; COMMITTED fixture point not old-DB migration mandate.'),
        'R16': ('G4', 'Deep source/evidence synthetic-only refusal retained; seven slots are proposed finite coverage, S01/B remain separate.'),
        'R17': ('T2/G5', 'Current exact recovery refs/fresh report and PENDING/NOT_SUBMITTED retained; multi-head different snapshots remain value-level.'),
        'R18': ('G5/G6/M2', 'Denominator and persisted three-read bounds retained; no-intent entry counter is separate from intent reconciliation.'),
    }
    rows = [{'id': key, 'mapping_result': 'ACCURATE_REQUIREMENT_AND_REMAINING_SCOPE_LIMITED',
             'proposed_packages': value[0], 'independent_note': value[1],
             'functional_result': 'NOT_RUN_IN_THIS_REVIEW'} for key, value in meanings.items()]
    save('source-and-decision-anchors.json', {
        'target': T, 'source_commit': P, 'decision_workflow': W,
        'scope': 'STATIC_PATH_REASONING_ONLY_NO_PRODUCT_IMPORT_OR_DATABASE',
        'anchors': anchors, 'ast_checks': {'unattempted_inherited_unconditional_stub': True,
                                         'legacy_converter_has_no_committed_record': True},
        'manual_static_path_findings': [
            {'id': 'M3-SEAM-REGISTER', 'path': 'POST_HOLD ADMITTED -> create_plan -> record_native_plan',
             'finding': 'record_native_plan calls ordinary _lease while hold is active; its candidate cannot be persisted by this listed path before clear.',
             'anchors': ['NATIVE_PLAN_WHILE_HOLD', 'ORDINARY_LEASE_HOLD_GUARD', 'CLEAR_REQUIRES_INDEXED_CANDIDATE', 'INDEXED_ARTIFACT_ONLY'],
             'result_kind': 'STATIC_COMPOSITION_GAP_NOT_DYNAMIC_FAILURE'},
            {'id': 'M3-SEAM-CONSUME', 'path': 'clear_target_drift_hold -> run_plan -> assert_pre -> _current -> _pre_lease(POST_HOLD)',
             'finding': 'POST_HOLD proof validation still requires an active exact hold; a clear/use transition is not specified by the listed sequence.',
             'anchors': ['POST_HOLD_PROOF_REQUIRES_CURRENT_HOLD', 'ASSERT_PRE_USES_CURRENT_PROOF', 'CLEAR_LOCAL_CURRENTNESS_AND_EVENT'],
             'result_kind': 'STATIC_COMPOSITION_GAP_NOT_DYNAMIC_FAILURE'},
            {'id': 'CONVERSION-SCOPE', 'finding': 'R1 static COMMITTED fixture rule and known-DB adoption are separate. R8 explicitly keeps old DB adoption blocked; current converter is legacy initial fixture only.',
             'result_kind': 'COORDINATOR_ADOPTION_DECISION_PENDING_NOT_IMPLICIT_MIGRATION_REQUIREMENT'}],
        'commands': commands, 'business_runs': 0, 'product_imports': 0, 'database_connections': 0})
    save('semantic-28-review.json', {'target': T, 'scope': 'LIMITED_MATRIX_MAPPING_REVIEW',
                                    'requirements': rows, 'count': len(rows),
                                    'overall_matrix_result': 'ACCEPTED_LIMITED',
                                    'plan_status': 'PENDING_ONE_CONSOLIDATED_REVISION_AND_COORDINATOR_DECISIONS',
                                    'a03': 'REWORK', 'i01': 'NOT_RELEASED'})
    print(json.dumps({'source_decision_anchors': len(anchors), 'reviewed_requirements': len(rows),
                      'static_git_commands_reaped': len(commands), 'business_runs': 0,
                      'database_connections': 0}, ensure_ascii=False))

if __name__ == '__main__':
    main()
