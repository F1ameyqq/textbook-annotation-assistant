"""One synthetic malformed-enum edge; never runs a product launcher or suite."""
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests/a24_first_save_wire_r1'))
sys.path.insert(0, str(ROOT / 'tests/a24_bootstrap_exclusion'))


def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
        raise AssertionError('REVIEW_REAL_IO_FORBIDDEN')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).resolve()
        low = str(path).lower()
        if low.startswith('d:\\1800-worktrees\\a24-first-save\\') or any(p in low for p in (
            '\\microsoft\\edge\\user data\\', '\\google\\chrome\\user data\\', '\\.credentials', '\\secrets\\')):
            raise AssertionError('REVIEW_ACTIVE_OR_PRIVATE_PATH_FORBIDDEN')
        mode, flags = args[1], args[2]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and OUT not in path.parents:
            raise AssertionError('REVIEW_WRITE_OUTSIDE_OUTPUT')


sys.addaudithook(audit)
from test_integration import make_guard, owner

observation = {}


class ProjectionEnumEdge(unittest.TestCase):
    def test_directly_injected_non_enum_decision_is_incomplete(self):
        guard, _ = make_guard()
        guard.audit('GET', owner.TARGET, 'Document', 'NAVIGATION', True, 'FETCH_REQUEST_STAGE')
        original = guard.events[0]['decision']
        guard.events[0]['decision'] = 'FORMAT_ONLY_NONENUM'
        snapshot = owner.guard_evidence(guard)
        observation.update(original_decision=original, direct_mutation=True,
                           synthetic_non_sensitive_value='FORMAT_ONLY_NONENUM', snapshot=snapshot)
        self.assertEqual(snapshot['status'], 'PROJECTION_ERROR',
                         'Shape-only validation accepted a decision outside ALLOW/BLOCK')
        self.assertFalse(snapshot['complete'])


if __name__ == '__main__':
    target = OUT / 'independent-control-result.json'
    assert not target.exists(), 'NO_CONTROL_RERUN'
    stream = io.StringIO()
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, failfast=True).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ProjectionEnumEdge))
    value = dict(schema='A24BootstrapIndependentProjectionEdge/v1', tests=result.testsRun,
                 failures=len(result.failures), errors=len(result.errors), passed=result.wasSuccessful(),
                 duration_ms=round((time.monotonic()-started)*1000), raw_output=stream.getvalue(),
                 observation=observation, subsequent_controls='NOT_RUN_FIRST_FAILURE' if not result.wasSuccessful() else 'NONE_PLANNED',
                 actual_resources=0, old_suites_run=0, model_or_content_review=0,
                 product_input_edits=0, run_count=1)
    with target.open('xb') as handle:
        handle.write((json.dumps(value, indent=2)+'\n').encode('utf-8'))
    print(stream.getvalue())
    print(json.dumps({key: value[key] for key in ('tests','failures','errors','passed','duration_ms','subsequent_controls')}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
