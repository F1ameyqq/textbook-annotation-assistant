"""Read fixed Git artifacts only; no prepare, execute, target mutation or test run."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('D:/1800')
OLD = 'efe440d07d3600ee9755f1709778a2a742bb2f52'
OLD_RUN = 'docs/evidence/A07/review/candidate-1/normal/run/'
EXPECTED = ['Q', 'W', 'W', 'W', 'W', 'A']
AUTH = 'cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c'
os.environ['GIT_NO_LAZY_FETCH'] = '1'
sys.dont_write_bytecode = True


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)


def blob(rev, path):
    return git('cat-file', 'blob', rev + ':' + path)


def obj(rev, path):
    return json.loads(blob(rev, path))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', required=True)
    p.add_argument('--delivery', required=True)
    p.add_argument('--run-prefix', required=True)
    p.add_argument('--stage', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    prefix = args.run_prefix.rstrip('/') + '/'
    stage = Path(args.stage).resolve()
    assert stage.is_relative_to(ROOT / '.local/stages/coordinator')
    stage.mkdir(parents=True, exist_ok=True)
    # Export exact source and archived run bytes, never invoke A07 code paths.
    for rev, source, dest in ((args.candidate, 'src/', stage / 'src'),
                              (args.delivery, prefix, stage / 'run')):
        names = git('ls-tree', '-r', '--name-only', rev, '--', source).decode().splitlines()
        assert names
        for name in names:
            if not name.startswith(source):
                continue
            target = dest / name[len(source):]
            raw = blob(rev, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == raw
            else:
                target.write_bytes(raw)
    sys.path.insert(0, str(stage / 'src'))
    from annotation.contracts import validate_bundle, assert_plan_ready, artifact_ref, content_digest
    run = stage / 'run'
    exchange = json.loads((run / 'exchange.json').read_bytes())
    validated = validate_bundle(exchange, asset_root=run)
    kinds = {a['kind']: a for a in exchange['artifacts'] if a['kind'] != 'CheckReport'}
    old_x = obj(OLD, OLD_RUN + 'exchange.json')
    old_k = {a['kind']: a for a in old_x['artifacts'] if a['kind'] != 'CheckReport'}
    plan, receipt = kinds['ApplyPlan'], kinds['ExecutionReceipt']
    assert_plan_ready(validated, artifact_ref(plan), plan['payload']['snapshot'])
    policy = exchange['policies'][0]
    prior_policy = old_x['policies'][0]
    expected_mapping = dict(prior_policy['role_mapping'], option='W')
    assert policy['role_mapping'] == expected_mapping
    assert policy['confirmation_status'] == 'A_INTERNAL_PROPOSAL'
    assert policy['applicability'] == 'PROPOSAL_ONLY'
    assert policy['content_hash'] != prior_policy['content_hash']
    for artifact in exchange['artifacts'] + exchange['policies']:
        data = dict(artifact)
        data.pop('content_hash')
        assert content_digest(data) == artifact['content_hash']
    graph = kinds['QuestionGraph']['payload']
    old_graph = old_k['QuestionGraph']['payload']
    for key in ('questions', 'fragments', 'answer_relations', 'identity_notes'):
        assert graph[key] == old_graph[key], key
    assert kinds['EvidenceBundle']['payload']['regions'] == old_k['EvidenceBundle']['payload']['regions']
    assert kinds['SourceBundle']['payload']['assets'] == old_k['SourceBundle']['payload']['assets']
    for kind in ('SourceBundle', 'EvidenceBundle', 'QuestionGraph'):
        assert kinds[kind]['producer']['evidence_mode'] == 'OBSERVED'
    for kind in ('PlatformSnapshot', 'ApplyPlan', 'ExecutionReceipt'):
        assert kinds[kind]['producer']['evidence_mode'] == 'SYNTHETIC'
    before, after = [json.loads((run / ('assets/' + n + '.json')).read_bytes()) for n in ('before', 'readback')]
    old_after = obj(OLD, OLD_RUN + 'assets/readback.json')
    assert before['instance_id'] == after['instance_id'] != old_after['instance_id']
    assert [before['read_sequence'], after['read_sequence']] == [1, 2]
    assert before['view']['epoch'] == 0 and after['view']['epoch'] == 1
    assert before['view']['target']['frames'] == []
    assert len(after['view']['target']['questions']) == 1
    frames = after['view']['target']['frames']
    old_frames = old_after['view']['target']['frames']
    assert len(frames) == len(old_frames) == 6
    assert [f['platform_role'] for f in frames] == EXPECTED
    assert [f['platform_role'] for f in old_frames] == ['Q'] * 5 + ['A']
    changed = []
    expected_view = copy.deepcopy(old_after['view'])
    for i, (f, oldf) in enumerate(zip(frames, old_frames)):
        fixed = dict(oldf, platform_role=EXPECTED[i])
        assert f == fixed
        projection = after['view']['frame_projections'][f['platform_frame_id']]
        oldp = old_after['view']['frame_projections'][oldf['platform_frame_id']]
        assert projection == dict(oldp, platform_role=EXPECTED[i])
        expected_view['target']['frames'][i]['platform_role'] = EXPECTED[i]
        expected_view['frame_projections'][f['platform_frame_id']]['platform_role'] = EXPECTED[i]
        if f['platform_role'] != oldf['platform_role']:
            changed.append(i)
    assert changed == [1, 2, 3, 4]
    # The view also carries its canonical digest; it is the only other changed value.
    expected_view.pop('content_hash', None)
    actual_view = dict(after['view'])
    actual_view.pop('content_hash', None)
    assert actual_view == expected_view
    planned = json.loads(plan['payload']['actions'][0]['expected_after']['frames'])
    assert planned == list(after['view']['frame_projections'].values())
    assert [f['platform_role'] for f in planned] == EXPECTED
    reports = {a['payload']['stage']: a for a in exchange['artifacts'] if a['kind'] == 'CheckReport'}
    for stage_name in ('PRE_APPLY', 'TARGET'):
        report = reports[stage_name]['payload']
        assert report['decision'] == 'PASS' and not report['issues']
        checks = json.loads((run / ('assets/calculations/' + stage_name.lower() + '.json')).read_bytes())
        assert all(v is True for part in checks.values() for v in part.values())
    assert len(reports['PRE_APPLY']['payload']['checks']) == 5
    result = receipt['payload']['results']
    assert len(result) == 1 and result[0]['outcome'] == 'APPLIED' and result[0]['effect_match'] == 'MATCH'
    assert result[0]['replay_allowed'] is False and receipt['payload']['unresolved_issue_ids'] == []
    assert receipt['payload']['execution_mode'] == plan['payload']['execution_mode'] == 'SIMULATED'
    summary = json.loads((run / 'summary.json').read_bytes())
    assert summary['complete_attempts'] == summary['dispatches'] == summary['successful_closures'] == 1
    assert summary['submission_status'] == 'NOT_SUBMITTED' and summary['content_check_status'] == 'PENDING'
    assert summary['B_joint_adoption_proven'] is summary['independent_human_visual_review_proven'] is False
    assert all(summary[k] == 0 for k in ('platform_calls', 'model_calls', 'services_started', 'browsers_started', 'process_exit_code'))
    replay = json.loads((run / 'replay-rejection.json').read_bytes())
    assert replay['code'] == 'PLAN_REPLAY' and replay['zero_target_change'] is True and replay['business_dispatches'] == 0
    assert digest((run / 'assets/input/approval.json').read_bytes()) == AUTH
    inputs = list((run / 'assets/input').glob('*'))
    assert inputs
    for input_file in inputs:
        assert input_file.read_bytes() == blob(OLD, OLD_RUN + 'assets/input/' + input_file.name)
    output = {'result': 'PASS_FIXED_RECORDED_DELTA', 'candidate': args.candidate, 'delivery': args.delivery,
              'old_review': OLD, 'expected_roles': EXPECTED, 'changed_frame_indices': changed,
              'old_frame_count': 6, 'new_frame_count': 6, 'content_coordinates_identity_preserved': True,
              'C01_valid': True, 'plan_ready': True, 'input_files_raw_preserved': len(inputs),
              'recorded_attempts': 1, 'recorded_dispatches': 1, 'recorded_successes': 1,
              'recorded_replay_zero_change': True, 'receipt_ref': artifact_ref(receipt),
              'readback_raw_sha256': digest((run / 'assets/readback.json').read_bytes()),
              'new_business_attempts': 0, 'platform_actions': 0}
    Path(args.output).write_bytes((json.dumps(output, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(output, ensure_ascii=True))


if __name__ == '__main__':
    main()
