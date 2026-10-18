"""Bounded R1 invocation. Reuses the adopted M driver and T1 capture."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('m_driver', ROOT/'examples/a03/T3-closure/run.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('preflight', 'business'), required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    m.write(root/'invocation.json', dict(argv=sys.argv, cwd=str(Path.cwd()), candidate=args.candidate,
        mode=args.mode, child_seconds=m.CHILD_SECONDS, parent_seconds=m.PARENT_SECONDS,
        no_network=True, field_reset='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'))
    if args.mode == 'preflight':
        view = m.raw_view(args.candidate, root)
        env = dict(os.environ, PYTHONPATH=str(view/'src'), PYTHONDONTWRITEBYTECODE='1',
            A03_R1_CONTROLS=str(root/'controls'), A03_R1_DISPOSABLE=str(view))
        commands = [
            [sys.executable, '-X', 'utf8', '-B', str(view/'tests/test_a03_t3_closure.py'), '--validation-controls'],
            [sys.executable, '-X', 'utf8', '-B', str(view/'tests/test_a03_r1_validation.py')]]
        for index, argv in enumerate(commands):
            result = m.run_child(root/('process-'+str(index)), argv, cwd=ROOT, env=env, timeout=60)
            if result['exit_code'] != 0 or result['timeout']:
                raise RuntimeError('control failed; inspect preserved raw streams')
        print('PREFLIGHT_ENDED; no DB/target/dispatch')
        return
    assert root.parent == ROOT/'docs/evidence/A03/R1/execution'
    assert root.name in ('candidate-1', 'candidate-2')
    args.output = root/'business'
    try:
        m.batch(args)
    except BaseException as error:
        m.write(root/'first-business-failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        matrix = json.loads((args.output/'matrix.json').read_bytes())
        failed = matrix['actual'][-1]['case'] if matrix['actual'] else None
        if failed and (args.output/'cases'/failed/'anchor.json').exists():
            view = args.output/'runtime-view'
            env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(view/'src'), str(view/'examples/a03/T1-capture')]),
                A03_R1_ROOT=str(root), PYTHONDONTWRITEBYTECODE='1')
            result = m.run_child(root/'release-process', [sys.executable, '-X', 'utf8', '-B',
                str(view/'examples/a03/T3-closure/run.py'), '--validation-r1-release',
                '--state', str(args.output/'cases'/failed), '--output', str(root/'release'/failed)],
                cwd=ROOT, env=env, timeout=60)
            m.write(root/'release-result.json', result)
        raise


if __name__ == '__main__':
    main()
