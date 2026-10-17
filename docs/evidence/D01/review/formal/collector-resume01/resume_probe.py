"""Rerun only the one test affected by the reviewer's omitted fixed helper."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

probe_path, root_value, output = sys.argv[1:]
spec = importlib.util.spec_from_file_location("d01_independent_probe", probe_path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
root = Path(root_value)
assert not (root/"src").exists()
before = probe.environment()
sys.path.insert(0, str(root/"tests"))
target = "test_contracts.ContractTests.test_copied_sample_cli_and_public_consumer_work_from_another_cwd"
suite = unittest.defaultTestLoader.loadTestsFromName(target)
result = unittest.TextTestRunner(verbosity=2).run(suite)
probe.write(output,dict(target=target,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                       skipped=result.skipped,successful=result.wasSuccessful(),before=before,after=probe.environment(),
                       sys_path_insertion="fixed tests directory only; no product src directory exists",
                       child_boundary="Original subprocesses set PYTHONPATH to a nonexistent src; not a separate -I installation proof."))
raise SystemExit(0 if result.wasSuccessful() else 1)
