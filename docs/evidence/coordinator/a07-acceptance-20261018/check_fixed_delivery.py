"""Coordinator read-only A07 acceptance; no business execution or mock mutation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path('D:/1800')
REVIEW = 'efe440d07d3600ee9755f1709778a2a742bb2f52'
AUTHOR = 'd2e710c817cf85505ac4fad4919dd51d1062d33a'
CANDIDATE = '6dad9b9a40a10989c102d91cf7b54f19c012015f'
WORKFLOW = 'b1c84db9d1d5603a4fd6aa5487d7c45ec6fca50a'
MAIN = 'c95e62c30e34dc14c2e6ddf05a1a05679eecf64a'
PREFIX = 'docs/evidence/A07/review/candidate-1/'
OUT = ROOT / 'docs/evidence/coordinator/a07-acceptance-20261018'
os.environ['GIT_NO_LAZY_FETCH'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)

def tree(rev):
    result = {}
    for record in git('ls-tree', '-r', '-z', rev).split(b'\0'):
        if record:
            meta, path = record.split(b'\t', 1)
            result[path.decode()] = tuple(meta.decode().split())
    return result

def sha(data):
    return hashlib.sha256(data).hexdigest()

trees = {rev: tree(rev) for rev in (REVIEW, AUTHOR, CANDIDATE, WORKFLOW, MAIN)}
oid_set = set()
for rev, paths in trees.items():
    for path, (_, kind, oid) in paths.items():
        if kind == 'blob' and ((rev == REVIEW and path.startswith('docs/evidence/A07/review/'))
                              or path == 'docs/tasks/A07-Q1-review-report.md'
                              or (rev == MAIN and path.startswith('src/'))):
            oid_set.add(oid)
raw = git('cat-file', '--batch') if not oid_set else subprocess.check_output(
    ['git', '-c', 'core.longpaths=true', 'cat-file', '--batch'], cwd=ROOT,
    input=('\n'.join(sorted(oid_set)) + '\n').encode())
blobs = {}
offset = 0
for oid in sorted(oid_set):
    end = raw.index(b'\n', offset)
    header = raw[offset:end].decode().split()
    assert header[0] == oid and header[1] == 'blob'
    size = int(header[2]); offset = end + 1
    blobs[oid] = raw[offset:offset + size]
    offset += size + 1

def data(path, rev=REVIEW):
    oid = trees[rev][path][2]
    return blobs[oid] if oid in blobs else git('cat-file', 'blob', oid)

def obj(path, rev=REVIEW):
    return json.loads(data(path, rev))

manifest_path = 'docs/evidence/A07/review/review-raw-git-manifest.json'
manifest = obj(manifest_path)
assert manifest['members_count'] == len(manifest['members']) == 54
for item in manifest['members']:
    mode, kind, oid = trees[REVIEW][item['path']]
    body = data(item['path'])
    assert (oid, mode, len(body), sha(body)) == (
        item['blob_oid'], item['mode'], item['bytes'], item['sha256'])
assert sum(item['bytes'] for item in manifest['members']) == 10195346
assert all(trees[REVIEW][p] == v for p, v in trees[CANDIDATE].items())
assert all(trees[AUTHOR][p] == v for p, v in trees[CANDIDATE].items())
assert all(trees[CANDIDATE][p] == v for p, v in trees[WORKFLOW].items())
author_new = set(trees[AUTHOR]) - set(trees[WORKFLOW])
review_new = set(trees[REVIEW]) - set(trees[CANDIDATE])
assert len(author_new) == 64 and len(review_new) == 55
assert not author_new & review_new
assert not (author_new | review_new) & set(trees[MAIN])
assert review_new == {i['path'] for i in manifest['members']} | {manifest_path}

# Export immutable recorded artifacts and accepted C01 source bytes. Do not invoke A07.
stage = ROOT / '.local/stages/coordinator/a07-fixed-artifact-recheck-20261018'
stage.mkdir(parents=True, exist_ok=True)
exported = []
for rev, prefix, destination in ((REVIEW, PREFIX + 'normal/run/', stage / 'run'),
                                 (MAIN, 'src/', stage / 'src')):
    for path in trees[rev]:
        if path.startswith(prefix):
            target = destination / path[len(prefix):]
            target.parent.mkdir(parents=True, exist_ok=True)
            body = data(path, rev)
            if target.exists():
                assert target.read_bytes() == body
            else:
                target.write_bytes(body)
            exported.append({'path': str(target.relative_to(stage)).replace('\\', '/'),
                             'git_commit': rev, 'git_path': path, 'sha256': sha(body)})
sys.dont_write_bytecode = True
sys.path.insert(0, str(stage / 'src'))
from annotation.contracts import load_bundle, assert_plan_ready, artifact_ref

complete = load_bundle(stage / 'run/exchange.json')
pre = load_bundle(stage / 'run/pre-execution.json')
plan = next(a for a in pre.artifacts if a.kind == 'ApplyPlan')
assert_plan_ready(pre, artifact_ref(plan), plan.payload.snapshot)
summary = obj(PREFIX + 'normal/run/summary.json')
receipt = obj(PREFIX + 'normal/run/receipt.json')
before = obj(PREFIX + 'normal/run/assets/before.json')
after = obj(PREFIX + 'normal/run/assets/readback.json')
negative = obj(PREFIX + 'negative-calls.json')
readback_review = obj(PREFIX + 'readback-review.json')
assert summary['complete_attempts'] == summary['dispatches'] == summary['successful_closures'] == 1
assert summary['question_count'] == 1 and summary['frame_count'] == 6
assert summary['execution_mode'] == receipt['payload']['execution_mode'] == 'SIMULATED'
assert summary['platform_calls'] == summary['model_calls'] == 0
assert summary['submission_status'] == 'NOT_SUBMITTED' and summary['content_check_status'] == 'PENDING'
assert before['instance_id'] == after['instance_id']
assert (before['read_sequence'], after['read_sequence']) == (1, 2)
assert len(before['view']['target']['frames']) == 0
frames = after['view']['target']['frames']
expected = [([70, 332, 590, 445], 'viewer-10', 'Q'),
            ([96, 453, 153, 486], 'viewer-10', 'Q'),
            ([207, 453, 262, 486], 'viewer-10', 'Q'),
            ([320, 453, 374, 486], 'viewer-10', 'Q'),
            ([430, 453, 486, 486], 'viewer-10', 'Q'),
            ([72, 239, 88, 258], 'viewer-173', 'A')]
assert len(frames) == 6 and len(after['view']['target']['questions']) == 1
for frame, (bbox, asset, role) in zip(frames, expected):
    assert (frame['box']['bbox'], frame['box']['image']['asset_id'], frame['platform_role']) == (bbox, asset, role)
    assert frame['platform_question_id'] == 'mock-question-1'
assert after['view']['internal_bindings'] == {'q-e92a499995ca1bbd570a2a09': 'mock-question-1'}
assert readback_review['readback_differences'] == []
result = receipt['payload']['results'][0]
assert result['effect_match'] == 'MATCH' and result['outcome'] == 'APPLIED' and not result['replay_allowed']
assert sha(data(PREFIX + 'normal/run/assets/readback.json')) == result['readback']['sha256']
replay = obj(PREFIX + 'normal/run/replay-rejection.json')
assert len(negative['calls']) == 9
assert all(i['zero_target_change'] and i['business_dispatches'] == 0 for i in negative['calls'])
assert replay['code'] == 'PLAN_REPLAY' and replay['zero_target_change'] and replay['business_dispatches'] == 0
expected_originals = {'base.zip': 'b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d',
                      'candidate.zip': '3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac',
                      'history.json': 'a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493',
                      'approval.json': 'cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c'}
assert {k:v['sha256'] for k,v in readback_review['post_run_originals_preserved'].items()} == expected_originals
release = obj(PREFIX + 'process-release.json')
assert release['all_recorded_pids_released']
pid_check = subprocess.check_output(['powershell', '-NoProfile', '-Command',
    "@(41552,59684,73044) | ForEach-Object { $p=Get-Process -Id $_ -ErrorAction SilentlyContinue; [pscustomobject]@{pid=$_;alive=($null -ne $p)} } | ConvertTo-Json -Compress"], text=True)
live_pids = json.loads(pid_check)
assert all(not item['alive'] for item in live_pids)
assert subprocess.check_output(['git','-c','core.longpaths=true','status','--porcelain=v1'],
    cwd='D:/1800-worktrees/a07-q1-review') == b''
report = {'at': datetime.now(timezone.utc).isoformat(),
    'result':'PASS_FIXED_ARTIFACT_RECHECK_NO_NEW_BUSINESS',
    'main_baseline':MAIN, 'candidate':CANDIDATE, 'author_delivery':AUTHOR, 'review_delivery':REVIEW,
    'review_manifest_members':54, 'review_manifest_bytes':10195346,
    'review_manifest_sha256':sha(data(manifest_path)),
    'review_report_sha256':sha(data('docs/tasks/A07-Q1-review-report.md')),
    'all_old_candidate_workflow_paths_preserved':True,
    'integration_new_paths':len(author_new | review_new),
    'C01_exchange_load_with_assets':True, 'C01_pre_execution_load_with_assets':True,
    'C01_assert_plan_ready':True, 'recorded_question_count':1, 'recorded_frame_count':6,
    'six_coordinates_and_relation_match':True, 'recorded_negative_calls':10,
    'recorded_negative_calls_zero_new_mutation':True, 'recorded_readback_differences':[],
    'review_processes_live_rechecked':live_pids, 'review_worktree_clean':True,
    'coordinator_business_attempts':0, 'coordinator_dispatches':0,
    'platform_actions':0, 'network_calls':0, 'new_mock_target_created':False,
    'exported_members':exported, 'plan_ref':summary['plan_ref'], 'receipt_ref':summary['receipt_ref'],
    'scope':'Fixed authorized A-only Q1 offline simulation; no B joint or platform acceptance'}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'fixed-artifact-recheck.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in report.items() if k != 'exported_members'},ensure_ascii=False,indent=2))
