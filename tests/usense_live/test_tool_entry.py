import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("usense_tool_entry", ROOT / "tools/run_usense_live.py")
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


class ToolEntryTests(unittest.TestCase):
    def test_read_cli_receives_arguments_and_source_location(self):
        module = Mock()
        module.main.return_value = 7
        previous = sys.argv
        with patch.object(entry, "import_module", return_value=module) as load:
            self.assertEqual(entry.main(["doctor"]), 7)
        load.assert_called_once_with("annotation.runtime.usense_live.cli")
        module.main.assert_called_once_with(["doctor"])
        self.assertEqual(Path(sys.path[0]), ROOT / "src")
        self.assertIs(sys.argv, previous)

    def test_writer_is_explicit_and_restores_argv(self):
        previous = sys.argv
        for flag in ("writer", "--writer"):
            observed = []
            module = Mock()
            module.main.side_effect = lambda: observed.append(sys.argv[1:]) or 0
            with patch.object(entry.Path, "is_file", return_value=True), \
                    patch.object(entry, "import_module", return_value=module) as load:
                self.assertEqual(entry.main([flag, "--help"]), 0)
            load.assert_called_once_with("annotation.runtime.usense_live.writer")
            self.assertEqual(observed, [["--help"]])
            self.assertIs(sys.argv, previous)

    def test_missing_writer_stops_before_import(self):
        with patch.object(entry.Path, "is_file", side_effect=[True, False]), \
                patch.object(entry, "import_module") as load, patch.object(entry, "print", create=True):
            self.assertEqual(entry.main(["--writer", "--help"]), 2)
        load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
