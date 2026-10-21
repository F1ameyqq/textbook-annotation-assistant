"""python -m annotation.source.b_batch PACKAGE --priority-case q4-first-lesson --report REPORT.json"""

import argparse
import json
import sys
from pathlib import Path

from . import BatchReceptionError, receive_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help="exact fixed a76e5a9 stage ZIP; no extraction or code execution")
    parser.add_argument("--priority-case", default="q4-first-lesson")
    parser.add_argument("--report", help="new JSON report; existing differing output is refused")
    args = parser.parse_args()
    try:
        output = receive_package(args.package, priority_case=args.priority_case)
        code = 0
    except BatchReceptionError as exc:
        output, code = exc.as_dict(), 2
    encoded = (json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    if args.report:
        try:
            report = Path(args.report)
            if report.resolve() == Path(args.package).resolve():
                raise OSError("report must not replace input")
            report.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive create: frozen reports and the input are never overwritten.
            with report.open("xb") as stream:
                stream.write(encoded)
        except OSError as exc:
            error = BatchReceptionError("OUTPUT", "REPORT_WRITE_REFUSED", args.report, str(exc))
            print(json.dumps(error.as_dict(), ensure_ascii=True, sort_keys=True))
            return 3
    # The Windows console's legacy code page cannot represent every source glyph.
    # CLI JSON is always UTF-8, including when stdout is redirected.
    sys.stdout.buffer.write(encoded)
    return code


if __name__ == "__main__":
    sys.exit(main())
