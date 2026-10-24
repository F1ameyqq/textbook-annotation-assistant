"""Assemble/check private OCR candidates without browsers, network, or writers."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from annotation.recognition.usense_candidates import assemble, check


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("assemble")
    build.add_argument("--ocr-root", type=Path, required=True)
    build.add_argument("--review", type=Path)
    build.add_argument("--out", type=Path, required=True)
    verify = commands.add_parser("check")
    verify.add_argument("--package", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "assemble":
        package = assemble(args.ocr_root, args.review, args.out)
        result = {"status": package["status"], "items": len(package["items"]), "write_allowed": False}
    else:
        result = check(args.package)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
