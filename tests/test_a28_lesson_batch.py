"""A28 evidence/once-send/process-order controls; synthetic files, no network.

The pure insertion contract has its own tests. These tests retain the real
batch/evidence/intent/release boundaries and replace only the child process or
pure plan/comparison operations needed to exercise their orchestration.
"""
import asyncio
import base64
import copy
from contextlib import redirect_stdout
import io
import importlib.util
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from annotation.runtime.usense_live import lesson_batch as batch
from annotation.runtime.usense_live import insertion_writer as writer
from annotation.runtime.usense_live.core import sha


def dump(path, value):
    path.write_bytes(json.dumps(value, ensure_ascii=False).encode('utf-8'))
    return {'path': str(path), 'sha256': sha(path.read_bytes())}


class FrozenFixture:
    """Four distinct candidate/reference sets and exactly fourteen crop proofs."""
    def __init__(self, root):
        self.root = root
        self.baseline = root / 'baseline'; self.baseline.mkdir()
        self.profile = root / 'profile'; self.profile.mkdir()
        self.ledger = root / 'usense-existing-ledger'; self.ledger.mkdir()
        self.old_ledger = self.ledger / 'old-accepted-fixed.json'
        self.old_ledger.write_bytes(b'{"historical":"unchanged"}')
        self.old_bytes = self.old_ledger.read_bytes()
        self.candidates, self.candidate_paths, self.proof_rows = [], [], []
        self.source = root / 'synthetic-source.bin'
        self.source.write_bytes(b'SYNTHETIC_SOURCE_BYTES_NOT_PLATFORM_CONTENT')
        source_ref = {'path': str(self.source), 'sha256': sha(self.source.read_bytes())}
        for index, key in enumerate(batch.KEYS):
            review = root / (key + '-review.json')
            review_ref = dump(review, {'fixture': key, 'independent_acceptance': 'NOT_CLAIMED'})
            frames = []
            for n in range(4 if index < 2 else 3):
                crop = root / (key + '-crop-' + str(n) + '.bin')
                crop.write_bytes(('SYNTHETIC_CROP:' + key + ':' + str(n)).encode())
                frame = {'key': key + '-frame-' + str(n), 'source': source_ref,
                         'bbox': [0, 0, 1, 1], 'image_path': 'https://fixture.invalid/' + key + '/' + str(n),
                         'planned_rect_id': str(uuid.uuid5(uuid.NAMESPACE_URL, key + ':' + str(n)))}
                frames.append(frame)
                self.proof_rows.append({'logical_key': key, 'key': frame['key'],
                    'url': frame['image_path'], 'http_status': 200, 'bbox': frame['bbox'],
                    'dimensions': [1, 1], 'source_sha256': source_ref['sha256'],
                    'full_pixel_decode': True, 'file': str(crop), 'sha256': sha(crop.read_bytes())})
            candidate = {'schema': 'A28LessonQuestionCandidate/v1', 'logical_key': key,
                         'book_id': '46007447', 'review': review_ref, 'frames': frames}
            path = root / (key + '-candidate.json')
            dump(path, candidate)
            self.candidates.append(candidate); self.candidate_paths.append(path)
        self.proof = root / 'crop-proof.json'
        self.manifest = root / 'manifest.json'
        names = batch.ins.full_endpoints(tail_order=23)
        captures, files = {}, {}
        for name in names:
            digest = dump(self.baseline / (name + '.json'), {'synthetic_endpoint': name})['sha256']
            files[name] = digest
            captures[name] = {'sha256': digest, 'status': 200, 'request_counts': {'context': 1, 'native': 1}}
        summary_ref = dump(self.baseline / 'capture-summary.json', {
            'status': 'NATIVE_GETS_CAPTURED', 'save_attempts': 0,
            'release': {'context_runtime_release_confirmed': True},
            'transport': {'mode': 'DIRECT', 'proxy_server': None}, 'captures': captures})
        self.manifest_value = {'schema': batch.SCHEMA, 'book_id': '46007447',
            'baseline': {'capture_summary_sha256': summary_ref['sha256'], 'files': files}, 'targets': []}
        self.refresh()

    def refresh(self):
        self.manifest_value['crop_evidence'] = dump(self.proof, {
            'schema': 'A28CropProof/v1', 'status': 'ALL_CROPS_CAPTURED', 'images': self.proof_rows})
        self.manifest_value['targets'] = [
            {'candidate': dump(path, candidate)} for path, candidate in zip(self.candidate_paths, self.candidates)]
        self.manifest_sha = dump(self.manifest, self.manifest_value)['sha256']

    def approved(self, index=0):
        candidate = copy.deepcopy(self.candidates[index])
        review = candidate['review']; crop = self.manifest_value['crop_evidence']
        return {'candidate_ref': str(self.candidate_paths[index]),
            'candidate_sha256': sha(self.candidate_paths[index].read_bytes()),
            'review_ref': review['path'], 'review_sha256': review['sha256'],
            'crop_evidence_ref': crop['path'], 'crop_evidence_sha256': crop['sha256'],
            'source_evidence': [candidate['frames'][0]['source']], 'candidate': candidate}

    def prepare(self):
        with patch.object(batch.ins, 'validate_candidate'), patch.object(batch.ins, 'make_insert_plan', return_value={'fixture_plan': True}):
            return batch.prepare(self.manifest, self.manifest_sha, self.baseline, self.profile, 'synthetic-authority')


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = FrozenFixture(Path(self.temp.name))

    def test_all_four_candidates_and_fourteen_crops_bound_before_runtime(self):
        prepared = self.f.prepare()
        self.assertEqual([row['logical_key'] for row in prepared['targets']], list(batch.KEYS))
        for row in prepared['targets']:
            self.assertTrue(batch.verify_evidence({'approved_new_content': row['approved_new_content']}))
        self.assertEqual(len(self.f.proof_rows), 14)
        self.assertEqual(self.f.old_ledger.read_bytes(), self.f.old_bytes)

    def test_candidate_mutation_rejected(self):
        self.f.candidate_paths[3].write_bytes(self.f.candidate_paths[3].read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'A28_FILE_CHANGED'):
            self.f.prepare()

    def test_manifest_digest_change_rejected_before_candidate_processing(self):
        self.f.manifest.write_bytes(self.f.manifest.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'A28_MANIFEST_CHANGED'):
            self.f.prepare()

    def test_review_source_and_remote_crop_raw_hashes_are_live_bound(self):
        paths = [Path(self.f.candidates[0]['review']['path']), self.f.source,
                 Path(self.f.proof_rows[0]['file'])]
        for path in paths:
            with self.subTest(path=path.name):
                before = path.read_bytes(); path.write_bytes(before + b'CHANGED')
                with self.assertRaisesRegex(ValueError, 'A28_FILE_CHANGED'):
                    batch.verify_evidence({'approved_new_content': self.f.approved()})
                path.write_bytes(before)

    def test_candidate_embedded_copy_must_equal_frozen_file(self):
        approved = self.f.approved(); approved['candidate']['book_id'] = 'wrong-book'
        with self.assertRaisesRegex(ValueError, 'A28_CANDIDATE_NOT_EXACT'):
            batch.verify_evidence({'approved_new_content': approved})

    def test_cross_question_uuid_collision_rejected_before_plan_creation(self):
        self.f.candidates[3]['frames'][0]['planned_rect_id'] = self.f.candidates[0]['frames'][0]['planned_rect_id']
        self.f.refresh()
        with patch.object(batch.ins, 'make_insert_plan') as make:
            with self.assertRaisesRegex(ValueError, 'A28_CROSS_TARGET_RECT_DUPLICATE'):
                batch.prepare(self.f.manifest, self.f.manifest_sha, self.f.baseline, self.f.profile, 'authority')
            make.assert_not_called()

    def test_duplicate_remote_crop_or_mismatched_url_rejected(self):
        original = copy.deepcopy(self.f.proof_rows)
        for kind in ('duplicate', 'url'):
            with self.subTest(kind=kind):
                self.f.proof_rows = copy.deepcopy(original)
                if kind == 'duplicate':
                    self.f.proof_rows[-1] = self.f.proof_rows[0]
                else:
                    self.f.proof_rows[0]['url'] += '/wrong'
                self.f.refresh()
                with self.assertRaisesRegex(ValueError, 'A28_EXACT_FOURTEEN_CROPS|A28_CROP_BINDING'):
                    batch.verify_evidence({'approved_new_content': self.f.approved()})

    def test_existing_q8_variant_intent_blocks_batch_before_runtime(self):
        (self.f.ledger / 'book46007447-lesson2-q8-variant-existing.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'A28_EXISTING_INTENT_NO_RETRY'):
            self.f.prepare()

    def test_recheck_detects_old_ledger_change_without_rewriting_it(self):
        prepared = self.f.prepare()
        self.f.old_ledger.write_bytes(b'SYNTHETIC_EXTERNAL_CHANGE')
        with self.assertRaisesRegex(ValueError, 'A28_EXISTING_LEDGER_CHANGED'):
            batch.recheck(prepared)
        self.assertEqual(self.f.old_ledger.read_bytes(), b'SYNTHETIC_EXTERNAL_CHANGE')


class FakeBinding:
    def check(self, **kwargs):
        return self


class SendTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, timeout=False):
        with tempfile.TemporaryDirectory() as temp:
            f = FrozenFixture(Path(temp)); run = f.root / 'writer-run'; run.mkdir()
            claim = f.ledger / 'book46007447-lesson2-q6-once.json'
            policy = writer.InsertPolicy(FakeBinding(), [])
            plan = {'schema': 'A28LessonInsertPlan/v1', 'operation': 'A28_LESSON_INSERT',
                'payload_candidate': {'annotations_upsert': [{}, {}, {}, {}]},
                'approved_new_content': f.approved(), 'ledger_key': claim.stem, 'plan_sha256': 'a' * 64}
            events = []
            test = self

            class Page:
                async def evaluate(self, script, value):
                    if script == writer.PREPARE_LESSON:
                        events.append('prepare')
                        return {'sha256': sha(b'{}'), 'created_by_bound': True, 'seven_row_user_ids_bound': True,
                            'runtime_actor_sha256': sha(b'synthetic-actor'), 'runtime_user_id_sha256': sha(b'synthetic-id')}
                    test.assertEqual(script, writer.SEND)
                    test.assertTrue(claim.exists())
                    test.assertTrue((run / 'send-intent.json').exists())
                    test.assertFalse(batch.read(claim)['automatic_retry_allowed'])
                    test.assertTrue(policy.armed)
                    for layer in ('context', 'native'):
                        test.assertTrue(policy.allow(layer, 'POST', writer.POST, '{}'))
                    events.append('send')
                    if timeout:
                        raise TimeoutError('synthetic-send-unknown')
                    return {'status': 200, 'body_base64': base64.b64encode(b'{"fixture":"receipt"}').decode()}

            result = {'post_attempts': 0}
            decoder = SimpleNamespace(decode_receipt=lambda *_: {'ok': True})
            with patch.object(writer, 'comparator', return_value=decoder):
                if timeout:
                    with self.assertRaisesRegex(TimeoutError, 'synthetic-send-unknown'):
                        await writer.record_and_send(page=Page(), policy=policy, plan=plan, claim=claim, run=run, result=result)
                else:
                    await writer.record_and_send(page=Page(), policy=policy, plan=plan, claim=claim, run=run, result=result)
            self.assertEqual(events, ['prepare', 'send'])
            self.assertFalse(policy.armed); self.assertTrue(policy.sealed)
            self.assertEqual(result['post_attempts'], 1)
            original_intent = claim.read_bytes()
            with self.assertRaises(FileExistsError):
                await writer.record_and_send(page=Page(), policy=policy, plan=plan, claim=claim, run=run, result={})
            self.assertEqual(events.count('send'), 1)
            self.assertEqual(claim.read_bytes(), original_intent)
            self.assertEqual(f.old_ledger.read_bytes(), f.old_bytes)
            return result

    async def test_durable_intent_precedes_single_send_and_receipt_is_not_readback(self):
        result = await self.exercise()
        self.assertTrue(result['receipt_exact_success'])
        self.assertNotEqual(result['status'], 'ACCEPTED_LESSON_INSERT')

    async def test_unknown_send_retains_intent_and_never_resends(self):
        result = await self.exercise(timeout=True)
        self.assertNotIn('receipt_exact_success', result)


class BatchExecutionTests(unittest.TestCase):
    def run_batch(self, *, stop_writer=None, unreleased=False, same_pid=False, alter_final_ledger=False,
                  alter_prior_content=False, duplicate_new_info=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); out = root / 'out'; out.mkdir()
            ledger = root / 'usense-existing-ledger'; ledger.mkdir()
            old = ledger / 'old-accepted.json'; old.write_bytes(b'{"old":"fixed"}')
            prepared = {'before': {'fixture_before': 'initial'}, 'evidence_file_sha256': {},
                'ledger_root': str(ledger), 'ledger_files': {str(old): sha(old.read_bytes())},
                'targets': [{'logical_key': key, 'candidate': {'logical_key': key},
                             'approved_new_content': {'candidate_sha256': sha(key.encode())}} for key in batch.KEYS]}
            events, before_values = [], []
            active_order = [None]

            def make_plan(before, candidate, approved):
                order = 23 + batch.KEYS.index(candidate['logical_key'])
                active_order[0] = order; before_values.append(copy.deepcopy(before))
                return {'new_order': order, 'plan_sha256': sha(candidate['logical_key'].encode()),
                        'ledger_key': 'book46007447-lesson2-' + candidate['logical_key']}

            def child(args, result_path):
                order = active_order[0]
                command = args[0]; events.append((order, command, str(result_path)))
                if command == 'configure':
                    orders = args[args.index('--orders') + 1:args.index('--pages')]
                    expected = list(range(23, order + 2)) if 'independent-reader' in str(result_path) else [order]
                    self.assertEqual(orders, expected)
                    return {'exit_code': 0, 'result': {'sha256': 'b' * 64}}
                if command == '--insert-writer':
                    if order == stop_writer:
                        return {'exit_code': 2, 'result': {'status': 'UNKNOWN_DO_NOT_RETRY', 'post_attempts': 1}}
                    writer_dir = out / ('writer-' + str(order)); writer_dir.mkdir()
                    receipt_ref = dump(writer_dir / 'native-receipt.json', {'synthetic_receipt': order})
                    key = 'book46007447-lesson2-' + batch.KEYS[order - 23]
                    dump(ledger / (key + '.json'), {'once_intent': order})
                    return {'exit_code': 0, 'pid': 100 + order, 'finished_at': '2026-10-23T00:00:02+00:00',
                        'result': {'run_id': writer_dir.name, 'receipt_exact_success': True,
                            'release': {'context_runtime_release_confirmed': not unreleased}, 'post_attempts': 1,
                            'post_layers': {'context': 1, 'native': 1}, 'runtime_actor_hashes': {},
                            'send_intent_at': '2026-10-23T00:00:00+00:00', 'finished_at': '2026-10-23T00:00:01+00:00',
                            'receipt_sha256': receipt_ref['sha256']}}
                self.assertEqual(command, 'capture')
                reader_dir = out / ('reader-' + str(order)); reader_dir.mkdir()
                names = batch.endpoints(range(23, order + 2), batch.PAGES, source=True)
                self.assertEqual(len(names), [20, 27, 34, 41][order - 23])
                captures = {}
                for name in names:
                    number = int(name.split('_')[0][1:]) if name.startswith('q') else None
                    value = {'from_actual_reader': min(number, order) if number else order, 'endpoint': name}
                    if name.endswith('_info'):
                        value['data'] = {'id': 'synthetic-info-' + str(number)}
                    if alter_prior_content and order == 24 and name == 'q23_question':
                        value['changed_after_acceptance'] = True
                    if duplicate_new_info and order == 24 and name == 'q24_info':
                        value['data']['id'] = 'synthetic-info-23'
                    ref = dump(reader_dir / (name + '.json'), value)
                    captures[name] = {'sha256': ref['sha256'], 'status': 200,
                        'request_counts': {'context': 1, 'native': 1}, 'observed_at': '2026-10-23T00:00:04+00:00'}
                if alter_final_ledger and order == 26:
                    old.write_bytes(b'SYNTHETIC_READER_SIDE_CHANGE')
                return {'exit_code': 0, 'pid': 100 + order if same_pid else 200 + order,
                    'started_at': '2026-10-23T00:00:03+00:00', 'result': {
                        'status': 'NATIVE_GETS_CAPTURED', 'run_id': reader_dir.name, 'save_attempts': 0,
                        'release': {'context_runtime_release_confirmed': True}, 'captures': captures}}

            with patch.object(batch.ins, 'make_insert_plan', side_effect=make_plan), \
                 patch.object(batch.ins, 'validate_insert_plan'), \
                 patch.object(batch.ins, 'compare_insert_readback', return_value={'ok': True}):
                result = batch.execute(prepared, out, root, root / 'profile', 'authority', 'tls', child, None)
            self.assertEqual(batch.read(out / 'batch-summary.json'), result)
            return result, events, before_values, old.read_bytes()

    def test_writer_release_then_separate_reader_and_actual_predecessor(self):
        result, events, before, old = self.run_batch()
        self.assertEqual(result['status'], 'ALL_FOUR_ACCEPTED')
        self.assertEqual(result['lesson_cumulative_count'], 9)
        for order in range(23, 27):
            calls = [event[1] for event in events if event[0] == order]
            self.assertEqual(calls, ['configure', '--insert-writer', 'configure', 'capture'])
        self.assertTrue(all(value['from_actual_reader'] == 23 for value in before[1].values()))
        self.assertEqual(old, b'{"old":"fixed"}')

    def test_unknown_second_writer_blocks_reader_and_all_successors(self):
        result, events, _, old = self.run_batch(stop_writer=24)
        self.assertEqual(result['status'], 'STOPPED_NO_RETRY')
        self.assertEqual(result['new_completed_count'], 1)
        self.assertEqual([row['status'] for row in result['results']],
                         ['ACCEPTED_LESSON_INSERT', 'STOPPED_NO_RETRY', 'NOT_RUN', 'NOT_RUN'])
        self.assertFalse(any(order >= 25 or (order == 24 and command == 'capture') for order, command, _ in events))
        self.assertEqual(old, b'{"old":"fixed"}')

    def test_unreleased_writer_blocks_even_reader_configuration(self):
        result, events, _, _ = self.run_batch(unreleased=True)
        self.assertEqual(result['new_completed_count'], 0)
        self.assertEqual([e[1] for e in events], ['configure', '--insert-writer'])
        self.assertIn('A28_WRITER_UNKNOWN_OR_UNRELEASED', result['error_code'])

    def test_reused_writer_pid_is_not_independent_readback(self):
        result, _, _, _ = self.run_batch(same_pid=True)
        self.assertEqual(result['status'], 'STOPPED_NO_RETRY')
        self.assertFalse(result['results'][0]['checks']['different_processes'])

    def test_later_readback_must_preserve_previous_new_question_content(self):
        result, _, _, _ = self.run_batch(alter_prior_content=True)
        self.assertEqual(result['new_completed_count'], 1)
        self.assertFalse(result['results'][1]['checks']['all_prior_new_native_content_unchanged'])
        self.assertEqual(result['results'][2]['status'], 'NOT_RUN')

    def test_new_info_identity_cannot_reuse_previous_insert_identity(self):
        result, _, _, _ = self.run_batch(duplicate_new_info=True)
        self.assertEqual(result['new_completed_count'], 1)
        self.assertFalse(result['results'][1]['checks']['new_info_distinct_from_prior_new'])
        self.assertEqual(result['results'][2]['status'], 'NOT_RUN')

    def test_final_reader_old_ledger_mutation_cannot_report_all_four_accepted(self):
        result, _, _, old = self.run_batch(alter_final_ledger=True)
        self.assertEqual(result['status'], 'STOPPED_NO_RETRY')
        self.assertEqual(result['new_completed_count'], 3)
        self.assertIn('A28_EXISTING_LEDGER_CHANGED', result['error_code'])
        self.assertEqual(old, b'SYNTHETIC_READER_SIDE_CHANGE')


class WriterReleaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_persists_release_on_inert_preresource_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); profile = root / 'profile'; profile.mkdir()
            ledger = root / 'usense-existing-ledger'; ledger.mkdir()
            plan_path = root / 'plan.json'
            plan = {'schema': 'A28LessonInsertPlan/v1', 'operation': 'A28_LESSON_INSERT',
                    'plan_sha256': 'a' * 64, 'ledger_key': 'book46007447-lesson2-q6-test'}
            plan_ref = dump(plan_path, plan)
            binding = FakeBinding(); binding.output = root / 'writer-run'
            binding.data = {'profile': {'directory': str(profile)}, 'static_get': {'mode': 'DISABLED', 'max_requests': 0}, 'allowed_get': []}
            fake_api = ModuleType('playwright.async_api')
            fake_api.async_playwright = lambda: self.fail('BROWSER_RUNTIME_MUST_NOT_START')
            with patch.dict(sys.modules, {'playwright.async_api': fake_api}), \
                 patch.object(writer, 'load_binding', return_value=binding), \
                 patch.object(writer, 'validate_inputs', return_value=({}, {}, ledger / 'claim.json')), \
                 patch.object(writer, 'tls_launch_arguments', side_effect=ValueError('synthetic-preresource-stop')):
                result = await writer.execute(config_path='unused', config_sha256='b' * 64,
                    plan_path=plan_path, plan_sha256=plan_ref['sha256'], baseline=root,
                    ledger_root=ledger, authorization_reference='synthetic-authority')
            self.assertEqual(result['status'], 'BLOCKED_BEFORE_SEND')
            self.assertEqual(result['post_attempts'], 0)
            self.assertTrue(result['release']['context_runtime_release_confirmed'])
            self.assertEqual(batch.read(binding.output / 'execution-result.json')['release'], result['release'])


class WriterEntrypointTests(unittest.TestCase):
    def test_root_cli_insert_writer_routes_to_owned_writer_entry_and_restores_argv(self):
        path = Path(__file__).resolve().parents[1] / 'tools/run_usense_live.py'
        spec = importlib.util.spec_from_file_location('a28_fixture_run_usense_live', path)
        tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
        original = sys.argv
        seen = []

        def inert_main():
            seen.append(sys.argv[:])
            return 17

        with patch.object(tool, 'import_module', return_value=SimpleNamespace(main=inert_main)) as imported:
            result = tool.main(['--insert-writer', '--config', 'synthetic-config'])
        self.assertEqual(result, 17)
        imported.assert_called_once_with('annotation.runtime.usense_live.insertion_writer')
        self.assertEqual(seen[0][1:], ['--config', 'synthetic-config'])
        self.assertIs(sys.argv, original)

    def test_standalone_main_uses_a27_owned_loop_without_asyncio_run(self):
        async def inert_execute(**kwargs):
            return {'status': 'INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK', 'fixture': True}
        args = ['insertion-writer']
        for field in ('config', 'sha256', 'plan', 'plan-sha256', 'baseline', 'ledger-root', 'authorization-reference'):
            args += ['--' + field, 'synthetic']
        stdout = io.StringIO()
        with patch.object(sys, 'argv', args), patch.object(writer, 'execute', side_effect=inert_execute), \
             patch.object(writer, 'run_owned_writer', wraps=writer.run_owned_writer) as owned, \
             patch.object(asyncio, 'run', side_effect=AssertionError('UNBOUNDED_ASYNCIO_RUN_FORBIDDEN')), \
             redirect_stdout(stdout):
            code = writer.main()
        self.assertEqual(code, 0)
        owned.assert_called_once()
        self.assertTrue(json.loads(stdout.getvalue())['fixture'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
