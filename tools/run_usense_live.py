"""Run the checked-out Usense package without installing this repository.

Use an existing Python environment with the runtime dependencies installed.
This entry point does not install packages, select an account, or grant writes.
"""
from importlib import import_module
from pathlib import Path
import sys


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    source = Path(__file__).resolve().parents[1] / "src"
    package = source / "annotation" / "runtime" / "usense_live"
    if not (package / "cli.py").is_file():
        print("SOURCE_PACKAGE_MISSING: put this tool in the repository tools directory.", file=sys.stderr)
        return 2
    # Source discovery is relative to the tool, never the caller's directory.
    sys.path.insert(0, str(source))
    insertion = bool(args and args[0] in ("--insert-writer", "insert-writer"))
    finalization = bool(args and args[0] in ("--finalize-writer", "finalize-writer"))
    writer = finalization or insertion or bool(args and args[0] in ("--writer", "writer"))
    if writer:
        args.pop(0)
        module_file = "finalize_writer.py" if finalization else "insertion_writer.py" if insertion else "writer.py"
        if not (package / module_file).is_file():
            print("WRITER_NOT_INTEGRATED: integrate the reviewed writer and update modules first.", file=sys.stderr)
            return 2
        module_name = "annotation.runtime.usense_live." + module_file.removesuffix(".py")
    else:
        module_name = "annotation.runtime.usense_live.cli"
    module = import_module(module_name)
    previous = sys.argv
    try:
        # The writer exposes main() while the read/login CLI accepts main(argv).
        sys.argv = [str(Path(__file__).resolve())] + args
        return module.main() if writer else module.main(args)
    finally:
        sys.argv = previous


if __name__ == "__main__":
    raise SystemExit(main())
