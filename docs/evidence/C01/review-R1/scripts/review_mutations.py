"""Independent C01 adversarial cases from the contract, prepared before delivery.

Each mutation is applied to a complete delivered fixture. The review runner must
recompute artifact hashes and update only dependent digest references, so that
semantic failures do not pass merely because an unrelated hash is stale.
"""
import copy


def artifact(bundle, kind, stage=None):
    candidates = [a for a in bundle['artifacts'] if a['kind'] == kind]
    if stage is not None:
        candidates = [a for a in candidates if a['payload']['stage'] == stage]
    if not candidates:
        raise AssertionError('fixture lacks ' + kind + ' ' + str(stage))
    return candidates[0]


def payload(bundle, kind, stage=None):
    return artifact(bundle, kind, stage)['payload']


def first_box(bundle):
    return payload(bundle, 'EvidenceBundle')['regions'][0]['box']


def modify_box(field, value):
    def mutate(bundle):
        first_box(bundle)[field] = copy.deepcopy(value)
    return mutate


def modify_binding(field, value):
    def mutate(bundle):
        first_box(bundle)['image'][field] = value
    return mutate


def modify_payload(kind, field, value, stage=None):
    def mutate(bundle):
        payload(bundle, kind, stage)[field] = copy.deepcopy(value)
    return mutate


def invalid_fragment_reference(bundle):
    payload(bundle, 'QuestionGraph')['fragments'][0]['region_ids'] = ['region-not-present']


def one_pass_twice(bundle):
    p = payload(bundle, 'ApplyPlan')
    p['targetcheck'] = copy.deepcopy(p['precheck'])


def missing_target_report(bundle):
    target_id = artifact(bundle, 'CheckReport', 'TARGET')['artifact_id']
    bundle['artifacts'] = [a for a in bundle['artifacts'] if a['artifact_id'] != target_id]


def missing_required_check(bundle):
    p = payload(bundle, 'CheckReport', 'PRE_APPLY')
    p['checks'] = [c for c in p['checks'] if c['check_id'] != 'coverage']


def failed_check_with_pass(bundle):
    payload(bundle, 'CheckReport', 'PRE_APPLY')['checks'][0]['outcome'] = 'FAIL'


def dangling_check_evidence(bundle):
    payload(bundle, 'CheckReport', 'PRE_APPLY')['checks'][0]['evidence_refs'] = ['proof-not-present']


def incomplete_coverage(bundle):
    payload(bundle, 'CheckReport', 'PRE_APPLY')['coverage']['pages_checked'] = []


def forged_coverage(bundle):
    p = payload(bundle, 'CheckReport', 'PRE_APPLY')['coverage']
    p['pages_expected'] = ['page-not-present']
    p['pages_checked'] = ['page-not-present']


def duplicate_artifact_revision(bundle):
    a = copy.deepcopy(artifact(bundle, 'QuestionGraph'))
    a['payload']['identity_notes'] += ' conflicting same-revision copy'
    bundle['artifacts'].append(a)


def mismatched_graph_version(bundle):
    payload(bundle, 'CheckReport', 'TARGET')['graph']['revision'] += 1


def wrong_ref_kind(bundle):
    payload(bundle, 'ApplyPlan')['graph']['kind'] = 'SourceBundle'


def graph_policy_conflict(bundle):
    payload(bundle, 'CheckReport', 'TARGET')['policy']['revision'] += 1


def capability_unknown(bundle):
    required = payload(bundle, 'ApplyPlan')['required_capabilities'][0]
    for capability in payload(bundle, 'PlatformSnapshot')['capabilities']:
        if capability['name'] == required:
            capability['status'] = 'UNKNOWN'
            return
    raise AssertionError('required capability not found in normal fixture')


def capability_no_proof(bundle):
    for capability in payload(bundle, 'PlatformSnapshot')['capabilities']:
        if capability['status'] == 'VERIFIED':
            capability['evidence_refs'] = []
            return
    raise AssertionError('no verified capability in normal fixture')


def capability_wrong_version(bundle):
    required = payload(bundle, 'ApplyPlan')['required_capabilities'][0]
    for capability in payload(bundle, 'PlatformSnapshot')['capabilities']:
        if capability['name'] == required:
            capability['platform_version'] = 'different-platform-version'
            return
    raise AssertionError('required capability not found')


def action_missing_entity(bundle):
    payload(bundle, 'ApplyPlan')['actions'][0]['source_entity_ids'] = ['entity-not-present']


def action_missing_dependency(bundle):
    payload(bundle, 'ApplyPlan')['actions'][0]['depends_on'] = ['action-not-present']


def action_self_dependency(bundle):
    action = payload(bundle, 'ApplyPlan')['actions'][0]
    action['depends_on'] = [action['action_id']]


def target_outside_scope(bundle):
    payload(bundle, 'PlatformSnapshot')['authorized_scope_id'] = 'scope-not-authorized'


def snapshot_question_missing_directory(bundle):
    snapshot = payload(bundle, 'PlatformSnapshot')
    snapshot['questions'].append(dict(platform_question_id='platform-question-review',
        directory_id='platform-directory-not-present', platform_order=999))


def action_missing_platform_question(bundle):
    payload(bundle, 'ApplyPlan')['actions'][0]['target']['platform_question_id'] = 'platform-question-not-present'


def applied_without_readback(bundle):
    result = payload(bundle, 'ExecutionReceipt')['results'][0]
    result['readback'] = None


def unknown_direct_replay(bundle):
    payload(bundle, 'ExecutionReceipt')['results'][0]['replay_allowed'] = True


def unknown_disguised_as_applied(bundle):
    payload(bundle, 'ExecutionReceipt')['results'][0]['outcome'] = 'APPLIED'


def unknown_retry_disposition(bundle):
    payload(bundle, 'ExecutionReceipt')['write_disposition'] = 'RECHECK_TARGET'


def unknown_batch_without_reconciliation(bundle):
    payload(bundle, 'BatchReport')['state'] = 'NEEDS_REVIEW'


def force_completed(bundle):
    batch = payload(bundle, 'BatchReport')
    batch['state'] = 'COMPLETED'
    batch['submission_status'] = 'CONFIRMED'
    batch['submission_evidence_refs'] = [bundle['evidence'][0]['evidence_id']]
    batch['content_check_status'] = 'VERIFIED'
    batch['frame_check_status'] = 'PASS'
    batch['unresolved_issue_ids'] = []
    for question in batch['questions']:
        question['state'] = 'VERIFIED'


def completed_not_submitted(bundle):
    force_completed(bundle)
    payload(bundle, 'BatchReport')['submission_status'] = 'NOT_SUBMITTED'


def completed_content_pending(bundle):
    force_completed(bundle)
    payload(bundle, 'BatchReport')['content_check_status'] = 'PENDING'


def completed_frames_unavailable(bundle):
    force_completed(bundle)
    payload(bundle, 'BatchReport')['frame_check_status'] = 'UNAVAILABLE'


def patch_bad_baseline_revision(bundle):
    payload(bundle, 'ReviewPatch')['baseline']['revision'] += 1


def patch_bad_baseline_hash(bundle):
    payload(bundle, 'ReviewPatch')['baseline']['content_hash'] = '0' * 64


def patch_same_revision(bundle):
    p = payload(bundle, 'ReviewPatch')
    p['result_revision'] = p['baseline']['revision']


def patch_missing_entity(bundle):
    payload(bundle, 'ReviewPatch')['changes'][0]['entity_id'] = 'entity-not-present'


def patch_wrong_before(bundle):
    payload(bundle, 'ReviewPatch')['changes'][0]['before'] = 'value-not-in-baseline'


def denominator_omission(bundle):
    batch = payload(bundle, 'BatchReport')
    batch['scope_manifest'] = batch['scope_manifest'][:-1]
    batch['questions'] = batch['questions'][:-1]
    batch['total_expected'] = len(batch['scope_manifest'])


def resource_path(value):
    def mutate(bundle):
        payload(bundle, 'SourceBundle')['assets'][0]['path'] = value
    return mutate


def cases():
    # case_id, source fixture, mutation, expected rejection layer
    result = [
        ('missing_region_reference', 'normal', invalid_fragment_reference, 'semantic'),
        ('missing_asset_reference', 'normal', modify_binding('asset_id', 'asset-not-present'), 'semantic'),
        ('asset_dimension_mismatch', 'normal', modify_binding('width', 99999), 'semantic'),
        ('asset_digest_mismatch', 'normal', modify_binding('sha256', '0' * 64), 'semantic'),
        ('bbox_negative', 'normal', modify_box('bbox', [-1.0, 0.0, 1.0, 1.0]), 'structural'),
        ('bbox_zero_area', 'normal', modify_box('bbox', [0.0, 0.0, 0.0, 1.0]), 'structural'),
        ('bbox_reversed', 'normal', modify_box('bbox', [2.0, 0.0, 1.0, 1.0]), 'structural'),
        ('bbox_out_of_bounds', 'normal', modify_box('bbox', [0.0, 0.0, 99999.0, 1.0]), 'structural'),
        ('bbox_nan', 'normal', modify_box('bbox', [float('nan'), 0.0, 1.0, 1.0]), 'structural'),
        ('bbox_infinity', 'normal', modify_box('bbox', [0.0, 0.0, float('inf'), 1.0]), 'structural'),
        ('duplicate_artifact_revision', 'normal', duplicate_artifact_revision, 'semantic'),
        ('one_pass_used_twice', 'normal', one_pass_twice, 'semantic'),
        ('missing_target_pass', 'normal', missing_target_report, 'semantic'),
        ('pass_missing_required_check', 'normal', missing_required_check, 'structural'),
        ('pass_with_failed_check', 'normal', failed_check_with_pass, 'structural'),
        ('check_missing_evidence', 'normal', dangling_check_evidence, 'semantic'),
        ('pass_incomplete_page_coverage', 'normal', incomplete_coverage, 'structural'),
        ('pass_forged_page_coverage', 'normal', forged_coverage, 'semantic'),
        ('target_graph_revision_conflict', 'normal', mismatched_graph_version, 'semantic'),
        ('dependency_kind_conflict', 'normal', wrong_ref_kind, 'semantic'),
        ('target_policy_version_conflict', 'normal', graph_policy_conflict, 'semantic'),
        ('synthetic_policy_cannot_authorize_platform', 'choice-assumption', modify_payload('ApplyPlan', 'execution_mode', 'PLATFORM'), 'semantic'),
        ('required_capability_unknown', 'normal', capability_unknown, 'semantic'),
        ('verified_capability_without_evidence', 'normal', capability_no_proof, 'structural'),
        ('capability_wrong_platform_version', 'normal', capability_wrong_version, 'semantic'),
        ('action_missing_source_entity', 'normal', action_missing_entity, 'semantic'),
        ('action_missing_dependency', 'normal', action_missing_dependency, 'semantic'),
        ('action_dependency_cycle', 'normal', action_self_dependency, 'semantic'),
        ('target_outside_authorized_scope', 'normal', target_outside_scope, 'semantic'),
        ('snapshot_question_missing_directory', 'normal', snapshot_question_missing_directory, 'semantic'),
        ('action_missing_platform_question', 'normal', action_missing_platform_question, 'semantic'),
        ('applied_without_readback', 'normal', applied_without_readback, 'structural'),
        ('unknown_direct_replay', 'unknown', unknown_direct_replay, 'structural'),
        ('unknown_disguised_as_applied', 'unknown', unknown_disguised_as_applied, 'structural'),
        ('unknown_as_regular_retry', 'unknown', unknown_retry_disposition, 'semantic'),
        ('unknown_batch_without_reconciliation', 'unknown', unknown_batch_without_reconciliation, 'semantic'),
        ('unknown_receipt_but_completed_batch', 'unknown', force_completed, 'semantic'),
        ('completed_not_submitted', 'normal', completed_not_submitted, 'structural'),
        ('completed_content_pending', 'normal', completed_content_pending, 'structural'),
        ('completed_frames_unavailable', 'normal', completed_frames_unavailable, 'structural'),
        ('patch_bad_baseline_revision', 'normal', patch_bad_baseline_revision, 'semantic'),
        ('patch_bad_baseline_digest', 'normal', patch_bad_baseline_hash, 'semantic'),
        ('patch_overwrites_old_revision', 'normal', patch_same_revision, 'semantic'),
        ('patch_missing_entity', 'normal', patch_missing_entity, 'semantic'),
        ('patch_wrong_before', 'normal', patch_wrong_before, 'semantic'),
        ('scope_denominator_omits_question', 'normal', denominator_omission, 'semantic'),
    ]
    for name, path in [
        ('drive_absolute', 'C:/private/page.pgm'),
        ('drive_relative', 'C:page.pgm'),
        ('unc', '//server/share/page.pgm'),
        ('posix_absolute', '/private/page.pgm'),
        ('parent_escape', '../page.pgm'),
        ('nested_escape', 'assets/../../page.pgm'),
        ('backslash_escape', 'assets\\..\\page.pgm'),
        ('reserved_device', 'assets/CON.pgm'),
    ]:
        result.append(('resource_path_' + name, 'normal', resource_path(path), 'structural'))
    return result
