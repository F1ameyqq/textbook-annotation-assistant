"""Run the dependency-free local editor protocol regression when Node is present."""
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReviewUIDOMTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the local DOM protocol check")
    def test_candidate_editor_and_restore_guard(self):
        result = subprocess.run(
            ["node", str(ROOT / "tests" / "review_ui_dom.cjs"), str(ROOT)],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)


if __name__ == "__main__":
    unittest.main()
