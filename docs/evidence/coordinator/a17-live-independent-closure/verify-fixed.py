"""Static fixed-evidence consistency check. No product imports or live calls."""
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
P = 'docs/evidence/A17/revisions/first-cause-r1/live-delivery/'
BASE = '8bffd88dacc146fc3f061ed0863b299fa5dabd30'
FINAL = '5aec24575a0e1621f4f22680da3beba581e6cec2'
commands = []


def load(name):
    return json.loads((ROOT / P / name).read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    command = ['git', '-c', 'core.longpaths=true', *args]
    r = subprocess.run(command, cwd='D:/1800', env=dict(os.environ, GIT_NO_LAZY_FETCH='1'),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False, creationflags=0x08000000)
    commands.append({'argv': command, 'exit_code': r.returncode,
                     'stdout_sha256': hashlib.sha256(r.stdout).hexdigest(),
                     'stdout_bytes': len(r.stdout), 'stderr': r.stderr.decode('utf-8', errors='replace')})
    assert r.returncode == 0
    return r.stdout


def tree(raw):
    result = {}
    for row in raw.split(b'\0'):
        if row:
            identity, path = row.split(b'\t', 1)
            result[path.decode('utf-8')] = identity.decode('ascii').split()
    return result


def main():
    c = load('raw/current-state.json')
    act, dec, report, dispatch = [load('authority/' + n + '.json') for n in
                                 ('activation', 'user-decision', 'independent-result', 'dispatch-intent')]
    candidate = load('authority/candidate-manifest.json')
    tool = load('tool-execution.json')
    launch, worker, occupancy = [load('raw/' + n + '.json') for n in
                                ('launcher-release', 'worker-release', 'occupancy')]
    act_sha = sha(ROOT / P / 'authority/activation.json')
    candidate_sha = sha(ROOT / P / 'authority/candidate-manifest.json')
    assert candidate_sha == '4ed38cb1f703c3d0b5e94d601f2f267c05ead871b9a26004e2e44e5d6eeb31dd'
    assert candidate_sha == sha(ROOT / 'docs/evidence/A17/revisions/first-cause-r1/candidate-manifest.json')
    assert act['user_decision_sha256'] == sha(ROOT / P / 'authority/user-decision.json') == dispatch['decision_sha256']
    assert act['independent_report_sha256'] == sha(ROOT / P / 'authority/independent-result.json') == dispatch['report_sha256']
    assert act_sha == dispatch['activation_sha256'] == launch['activation_sha256']
    assert act['candidate_manifest_sha256'] == dispatch['candidate_sha256'] == candidate_sha
    assert dec['user_reply_verbatim'] == '一直批准'
    assert dec['live_authorized'] is True and dec['certificate_exception_authorized'] is True
    assert act['tls_mode'] == dec['tls_mode'] == 'CONTEXT_EXCEPTION'
    assert report['result'] == 'ACCEPTED_OFFLINE_ONLY'
    binding = ['task', 'run_id', 'workflow_commit', 'scope', 'sample_limit',
               'automatic_schema_confirmation', 'fixed_business_get_count', 'original_get_count',
               'executor_thread_id', 'output_directory', 'activation_path', 'decision_path',
               'report_path', 'excluded_static_event_limit']
    for key in binding:
        for document in (act, dec, report):
            assert type(document[key]) is type(candidate[key]) and document[key] == candidate[key]
    assert candidate['workflow_commit'] == 'd137a1bba49550f661b110ee14c9541a1dc4fb19'
    assert act['context_limit'] == act['navigation_limit'] == act['new_live_limit'] == 1
    assert act['total_seconds'] == 900 and act['sample_limit'] == 0
    for name in ('login_submission_limit', 'business_write_limit', 'upload_limit', 'ocr_limit'):
        assert act[name] == 0
    marker = load('raw/launcher-claimed.json')
    for name in ('live-started', 'worker-claimed', 'occupancy-claimed'):
        assert load('raw/' + name + '.json') == marker
    assert marker['activation_sha256'] == act_sha and marker['candidate_sha256'] == candidate_sha
    for key in ('task', 'run_id', 'workflow_commit', 'scope', 'sample_limit', 'profile_fingerprint'):
        assert marker[key] == act[key]
    assert marker['certificate_exception'] is True
    assert load('raw/profile-binding.json')['fingerprint'] == act['profile_fingerprint']
    assert tool['argv'] == dispatch['argv'] and tool['cwd'] == dispatch['cwd']
    assert tool['launcher_call_count'] == 1 and tool['unapproved_restarts_or_retries'] == 0
    assert tool['tool_observed_exit_code'] == 2
    intent = load('raw/launcher-intent.json')
    assert intent['candidate_sha256'] == candidate_sha and intent['activation_sha256'] == act_sha
    assert intent['argv'][3] == '--_launched' and intent['argv'][4:] == tool['argv'][3:]
    start, end = [datetime.fromisoformat(act[k]) for k in ('not_before', 'expires_at')]
    assert (end - start).total_seconds() == 900
    for record in (launch, worker, c):
        assert start <= datetime.fromisoformat(record['started_at']) <= datetime.fromisoformat(record['finished_at']) < end
    audit = c['network_audit']
    assert len(audit) == 11
    assert Counter(a['category'] for a in audit) == {'NAVIGATION': 2, 'STATIC': 4,
        'EXPECTED_EXCLUDED_STATIC_DENIAL': 1, 'PATH_BLOCKED': 1, 'STOPPED': 3}
    times = [datetime.fromisoformat(a['time']) for a in audit]
    assert times == sorted(times)
    excluded = audit[4]
    assert (excluded['hostname'], excluded['port'], excluded['method'], excluded['resource_type'],
            excluded['source'], excluded['decision']) == ('cdn.bootcdn.net', 443, 'GET', 'Script', 'FETCH_REQUEST_STAGE', 'BLOCK')
    fatal = audit[7]
    assert (fatal['hostname'], fatal['port'], fatal['method'], fatal['resource_type'],
            fatal['category'], fatal['source']) == ('www.usense.com', 443, 'GET', 'XHR', 'PATH_BLOCKED', 'FETCH_REQUEST_STAGE')
    assert all(a['category'] == 'STOPPED' and a['decision'] == 'BLOCK' for a in audit[8:])
    assert c['error']['codes'] == ['PATH_BLOCKED'] and c['outcome'] == 'ERROR'
    for name in ('guard_pre_shutdown', 'guard_at_serialization'):
        assert c[name]['failure'] == c['error'] and c[name]['pending_tasks'] == 0
        assert c[name]['terminal_stopped'] is True
    assert c['excluded_static']['combined_guard_events'] == c['excluded_static']['completed_denial_calls'] == 1
    assert c['excluded_static']['pending_callbacks'] == 0 and c['excluded_static']['event_limit'] == 16
    assert c['steps']['navigation'] == 'FAILED'
    assert all(v == 'NOT_RUN' for k, v in c['steps'].items() if k != 'navigation')
    assert not any(a['business_read'] for a in audit) and c['sources'] == []
    assert c['business_writes'] == c['login_submissions'] == c['sample_limit'] == 0
    assert c['production_ready'] is False and c['write_eligible'] is False
    assert c['body_status'] == c['schema_status'] == 'UNKNOWN'
    asset, = c['static_assets']
    assert asset['http_status'] == 200 and asset['size'] == 3065996
    assert asset['sha256'] == 'd0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41'
    assert asset['executed_by_collector'] is False
    assert c['release']['state'] == 'RELEASED' and c['release']['context_closed'] and c['release']['runtime_stopped']
    assert c['release']['errors'] == []
    identities = []
    for name, record, expected_exit in [('product', launch, 2), ('worker', worker, 2), ('occupancy', occupancy, 0)]:
        before, after = record['before'], record['after']
        assert before['pid'] == after['pid'] and before['created_filetime'] == after['created_filetime']
        assert after['exit_observed'] is True and after['exit_code'] == expected_exit
        assert after['exited_filetime'] >= after['created_filetime']
        identities.append({'resource': name, 'pid': after['pid'], 'created_filetime': after['created_filetime'],
                           'exit_observed': True, 'exit_code': after['exit_code']})
    assert launch['product_handle_closed'] and worker['worker_handle_closed'] and occupancy['handle_closed']
    for record in (launch, worker):
        assert record['job_active_final'] == 0 and record['job_closed'] and record['errors'] == [] and record['state'] == 'RELEASED'
    assert not launch['total_deadline_exceeded'] and not worker['hard_deadline_exceeded']
    copies = load('source-copy-manifest.json')['files']
    for member in copies + load('delivery-file-manifest.json')['members']:
        path = ROOT / member['path']
        assert path.stat().st_size == member['size'] and sha(path) == member['sha256']
    parent = git('show', '-s', '--format=%P', FINAL).decode('ascii').strip()
    assert parent == BASE
    base_raw, final_raw = [git('ls-tree', '-r', '-z', '--full-tree', x) for x in (BASE, FINAL)]
    assert base_raw == (ROOT / P / 'base-tree.raw').read_bytes()
    before, after = tree(base_raw), tree(final_raw)
    assert len(before) == 31574 and all(after.get(k) == v for k, v in before.items())
    added = sorted(set(after) - set(before))
    assert len(added) == 25 and all(k.startswith(P) for k in added)
    assert all(k.endswith(('.json', '.md', '.raw')) for k in added)
    assert not any('static-assets/' in k or k.endswith('.source.json') for k in added)
    for m in json.loads((OUT / 'intake.json').read_bytes())['members']:
        assert after[m['path']] == [m['mode'], m['type'], m['blob']]
    for m in candidate['members']:
        path = ROOT / m['path']
        assert path.stat().st_size == m['size'] and sha(path) == m['sha256']
        assert after[m['path']] == [m['mode'], m['type'], m['blob']]
    wall_ms = (datetime.fromisoformat(launch['finished_at']) - datetime.fromisoformat(launch['started_at'])).total_seconds() * 1000
    result = {'result': 'PASS_STATIC_FIXED_FAILURE_AND_PROVEN_OWN_RELEASE_CHECKS',
        'binding_verified': True, 'unique_fixed_launcher_call': 1, 'unapproved_retries_recorded': 0,
        'window_verified': True, 'launcher_started_beijing': '2026-10-20T20:19:44.770667+08:00',
        'launcher_finished_beijing': '2026-10-20T20:19:55.513996+08:00',
        'launcher_wall_interval_ms': round(wall_ms, 3), 'launcher_monotonic_duration_ms': launch['duration_ms'],
        'duration_difference_ms': round(launch['duration_ms'] - wall_ms, 3),
        'duration_limit': 'Different start anchors/clocks: monotonic at function entry, recorded UTC later; exact contribution UNKNOWN. Both within window.',
        'first_fatal': fatal, 'audit_categories': dict(Counter(a['category'] for a in audit)),
        'audit_sources': dict(Counter(a['source'] for a in audit)), 'audit_events_are_requests': False,
        'excluded_static': c['excluded_static'], 'guard_first_cause_and_final_error_equal': True,
        'context_created': 1, 'main_navigation_attempts': 1, 'business_gets_completed': 0,
        'originals_completed': 0, 'sample': 'NOT_RUN', 'authentication': 'NOT_PROVEN',
        'inventory_availability': 'UNKNOWN', 'inventory_coverage': 'UNKNOWN',
        'allowed_script_metadata': asset, 'script_body_or_sidecar_accessed_by_reviewer': False,
        'release_verified': {'context_runtime': c['release'], 'held_identities': identities,
                             'two_jobs_active_final': [0, 0], 'all_three_handles_closed': True,
                             'pending_callbacks': 0, 'launcher_own_OS_identity': 'UNKNOWN',
                             'prelaunch_occupancy_matching': occupancy['matching_processes'],
                             'postrun_occupancy': 'NOT_RUN'},
        'preservation': {'fixed_inputs': 44, 'old_members': 31574, 'old_evidence': sum(k.startswith('docs/evidence/') for k in before),
                         'added': 25, 'modified': 0, 'deleted': 0, 'candidate_dependencies': len(candidate['members']),
                         'source_copy_records_checked': len(copies), 'git_metadata_children': len(commands), 'commands': commands},
        'unknowns': ['XHR path/query/use', 'CDN path/content/necessity', 'auxiliary HTTP sends',
                     'navigation HTTP status', 'DNS/TCP/TLS activity', 'launcher OS creation/exit identity',
                     'exact timing-difference contribution', 'actual captured script body hash not independently recomputed'],
        'reviewer_product_imports_suites_browser_network_profile_native_occupancy_live': 0}
    with (OUT / 'evidence-checks.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('result', 'binding_verified', 'launcher_wall_interval_ms',
          'launcher_monotonic_duration_ms', 'duration_difference_ms', 'audit_categories', 'audit_sources')}))


if __name__ == '__main__':
    main()
