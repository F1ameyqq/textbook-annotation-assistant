"""Read-only API example; stdout is UTF-8 JSON. Does not write artifacts."""

import json
import sys

from annotation.source.b_batch import BatchReceptionError, receive_package


if __name__ == "__main__":
    try:
        result, code = receive_package(sys.argv[1]), 0
    except BatchReceptionError as exc:
        result, code = exc.as_dict(), 2
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    sys.exit(code)
