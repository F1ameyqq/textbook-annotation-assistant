"""python -m annotation.source.b_handoff PACKAGE --sha256 EXPECTED_SHA256"""
import argparse
import json
import sys

from . import HandoffError, receive_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--documents", action="store_true", help="include every unchanged native JSON document")
    args = parser.parse_args()
    try:
        received = receive_package(args.package, expected_sha256=args.sha256,
                                   expected_manifest_sha256=args.manifest_sha256)
        output = received.receipt
        if args.documents:
            output = {"receipt": output, "documents": received.documents}
        code = 0
    except HandoffError as exc:
        output, code = exc.as_dict(), 2
    except (KeyError, TypeError, IndexError, AttributeError, ValueError) as exc:
        # Invalid unregistered shapes must also produce a refusal, never a permissive fallback.
        output = HandoffError("UNSUPPORTED_ENTRY_SHAPE", "$", str(exc), "SHAPE").as_dict()
        code = 2
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
