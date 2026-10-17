import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from annotation.delivery.usense_readonly.coordinates import DEPENDENCY_COMMIT
from annotation.source.usense import coordinate_run


class CoordinateEntryTests(unittest.TestCase):
    def test_reservation_dependency_and_scope_fail_before_opening_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/'state.json';refs=root/'refs.json'
            good={'platform_session':{'book_id':'46007447','reservation_task':'A04','reservation_stage':'coordinate-R1-execution'},
                  'tasks':{'A04':{'coordinate_resume':{'dependency_commit':DEPENDENCY_COMMIT}}}}
            reference={'book_id':'46007447','pages':{'14':{},'173':{}}}
            args=['--output',str(root/'out'),'--login-root',str(root/'never-read'),
                  '--coordination-state',str(state),'--references',str(refs)]
            for change in ('book','task','stage','dependency','pages'):
                data=json.loads(json.dumps(good));ref=json.loads(json.dumps(reference))
                if change=='book':data['platform_session']['book_id']='46006966'
                elif change=='task':data['platform_session']['reservation_task']='A05'
                elif change=='stage':data['platform_session']['reservation_stage']='execution'
                elif change=='dependency':data['tasks']['A04']['coordinate_resume']['dependency_commit']='wrong'
                else:ref['pages']['15']={}
                state.write_text(json.dumps(data));refs.write_text(json.dumps(ref))
                with patch.object(coordinate_run,'collect_live') as collect,contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(coordinate_run.main(args),2)
                collect.assert_not_called()
                self.assertFalse((root/'out').exists())

    def test_execution_and_review_retain_explicit_tls_boundary_and_no_secret_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/'state.json';refs=root/'refs.json'
            refs.write_text(json.dumps({'book_id':'46007447','pages':{'14':{},'173':{}}}))
            for stage in ('coordinate-R1-execution','coordinate-R1-review'):
                state.write_text(json.dumps({'platform_session':{'book_id':'46007447','reservation_task':'A04','reservation_stage':stage},
                     'tasks':{'A04':{'coordinate_resume':{'dependency_commit':DEPENDENCY_COMMIT}}}}))
                for opt in ([],['--ignore-https-errors']):
                    stream=io.StringIO()
                    with patch.object(coordinate_run,'collect_live',side_effect=RuntimeError('SYNTHETIC_SECRET')) as collect,contextlib.redirect_stdout(stream):
                        result=coordinate_run.main(['--output',str(root/'out'),'--login-root',str(root/'never-read'),
                             '--coordination-state',str(state),'--references',str(refs)]+opt)
                    self.assertEqual(result,2)
                    self.assertEqual(collect.call_args.kwargs['ignore_https_errors'],bool(opt))
                    self.assertNotIn('SYNTHETIC_SECRET',stream.getvalue())


if __name__=='__main__':unittest.main()
