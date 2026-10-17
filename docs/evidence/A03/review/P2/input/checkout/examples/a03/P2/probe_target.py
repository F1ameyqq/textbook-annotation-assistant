"""Reopen the target through its public API without importing runtime storage.

This reader still works when the runtime database is deliberately damaged by a
separate author fault case; target effects cannot be reconstructed from receipts.
"""
import argparse
import json
from pathlib import Path
import sys


def probe(request):
    from annotation.delivery.mock import PersistentMockSession
    import annotation.delivery.mock.persistent as imported
    session = PersistentMockSession.open(
        request["target_dir"], expected_store_id=request["expected_store_id"],
        expected_target_session_id=request["expected_target_session_id"],
        expected_target_key=request["expected_target_key"],
        expected_scope_id=request["expected_scope_id"],
        expected_source_ref=request["expected_source_ref"],
    )
    result = session.export_book_context(request["expected_target_key"])
    result = dict(result)
    result["actual_import"] = str(Path(imported.__file__).resolve())
    result["python_executable"] = sys.executable
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    probe(json.loads(args.request.read_text(encoding="utf-8")))
