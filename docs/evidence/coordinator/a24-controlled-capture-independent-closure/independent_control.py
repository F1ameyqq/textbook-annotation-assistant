"""One new post-binding reparse edge through the scheduled response chain."""
import asyncio
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
TEMP=OUT/'independent-temporary';TEMP.mkdir(exist_ok=False)
os.environ['TEMP']=os.environ['TMP']=str(TEMP);tempfile.tempdir=str(TEMP)


def audit(event,args):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system'):
        raise AssertionError('REVIEW_REAL_IO_FORBIDDEN')
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        path=Path(os.fsdecode(args[0])).resolve();low=str(path).lower()
        if low.startswith('d:\\1800-worktrees\\a24-first-save\\') or any(p in low for p in (
                '\\microsoft\\edge\\user data\\','\\google\\chrome\\user data\\','\\.credentials','\\secrets\\')):
            raise AssertionError('REVIEW_ACTIVE_OR_PRIVATE_PATH_FORBIDDEN')
        mode,flags=args[1],args[2]
        writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and OUT not in path.parents:raise AssertionError('REVIEW_WRITE_OUTSIDE_OUTPUT')


sys.addaudithook(audit)
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests/a24_first_save_wire_r1'))
sys.path.insert(0,str(ROOT/'tests/a24_controlled_capture'))
from noio_loop import MemoryPolicy
from test_integration import capability,framework,guard_for,Response,SCRIPT,RAW,owner
asyncio.set_event_loop_policy(MemoryPolicy())
observation={}


class PostBindingReparse(unittest.TestCase):
    def test_reparse_introduced_after_binding_stops_scheduled_capture_before_body(self):
        with tempfile.TemporaryDirectory(prefix='a24-independent-capture-') as directory:
            root=Path(directory);cap=capability(root);fw,old=framework(root)
            guard,context,page=guard_for(cap,fw);owner.bind_capture_owner(cap,fw,guard)
            marker=(guard.output/'capture-owner.json').read_bytes()
            request=SimpleNamespace(url=SCRIPT,method='GET',resource_type='script',frame=guard.auth_frame)
            response=Response(request,RAW);original=Path.lstat
            def reparse_lstat(path):
                info=original(path)
                if path==guard.output:
                    return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=getattr(info,'st_file_attributes',0)|0x400)
                return info
            async def dispatch():
                guard.response(response)
                return await fw.settle_callbacks(guard,seconds=1)
            with patch.object(Path,'lstat',new=reparse_lstat):
                settled=asyncio.run(dispatch())
            observation.update(settled=settled,response_body_reads=response.reads,stopped=guard.stopped,
                first_failure=guard.failure,pending_tasks=len(guard.tasks),pending_callbacks=len(guard.callbacks),
                assets=len(guard.scripts),static_assets_directory_created=(guard.output/'static-assets').exists(),
                marker_unchanged=(guard.output/'capture-owner.json').read_bytes()==marker,
                old_output_member_names=sorted(p.name for p in old.iterdir()))
            self.assertTrue(settled);self.assertTrue(guard.stopped);self.assertIsNotNone(guard.failure)
            self.assertEqual(response.reads,0);self.assertFalse(guard.scripts)
            self.assertFalse(guard.tasks);self.assertFalse(guard.callbacks)
            self.assertFalse((guard.output/'static-assets').exists())
            self.assertEqual((guard.output/'capture-owner.json').read_bytes(),marker)
            self.assertEqual(sorted(p.name for p in old.iterdir()),['claimed.json'])
            self.assertEqual((old/'claimed.json').read_bytes(),b'SYNTHETIC_OLD_CLAIM_UNCHANGED')


if __name__=='__main__':
    target=OUT/'independent-control-result.json';assert not target.exists(),'NO_CONTROL_RERUN'
    started=time.monotonic();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2,failfast=True).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(PostBindingReparse))
    value=dict(schema='A24ControlledCaptureIndependentPostBindingEdge/v1',tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
        duration_ms=round((time.monotonic()-started)*1000),raw_output=stream.getvalue(),observation=observation,
        run_count=1,reruns=0,successors='NONE_PLANNED' if result.wasSuccessful() else 'NOT_RUN_FIRST_FAILURE',
        actual_resources=0,old_suites_run=0,model_or_content_review=0)
    with target.open('xb') as handle:handle.write((json.dumps(value,indent=2)+'\n').encode())
    print(stream.getvalue());print(json.dumps({k:value[k] for k in ('tests','failures','errors','passed','duration_ms')}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
