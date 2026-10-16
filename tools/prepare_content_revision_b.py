"""Create an immutable local draft revision plan from explicit original spans.

Inputs are plain current E/G05/Check05 artifacts and a JSON operation list.
This command creates a plan only; run_pipeline_b.py --content-revision applies
and checks it separately. Draft authorship never certifies transcription.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def local_path(value):
    if (value.startswith(("\\\\", "//")) or "://" in value
            or (re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value)
                and not re.match(r"^[A-Za-z]:[\\/]", value))):
        raise argparse.ArgumentTypeError("a local filesystem path is required")
    return Path(value)


def _read(path):
    raw = Path(path).read_bytes()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key: " + key)
            result[key] = value
        return result
    def finite(value):
        raise ValueError("nonfinite JSON value: " + value)
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=finite)
    return value, hashlib.sha256(raw).hexdigest()


def execute(evidence_path, graph_path, base_check_path, operations_path, out_path, *,
            author_kind, author_id, author_note, previous_path=None, builder=None):
    from annotation.recognition.content_revision import make_revision_plan, reference, validate_revision_plan

    paths = {"evidence": Path(evidence_path), "graph": Path(graph_path),
             "base_check": Path(base_check_path), "operations": Path(operations_path)}
    if previous_path is not None:
        paths["previous_plan"] = Path(previous_path)
    loaded = {name: _read(path) for name, path in paths.items()}
    values = {name: pair[0] for name, pair in loaded.items()}
    if not isinstance(values["operations"], list):
        raise ValueError("operations input must be a complete JSON operation list")
    author = {"kind": author_kind, "id": author_id, "note": author_note}
    plan = (builder or make_revision_plan)(values["evidence"], values["graph"], values["base_check"],
        values["operations"], author, previous_plan=values.get("previous_plan"))
    validate_revision_plan(plan, values["evidence"], values["graph"], values["base_check"])
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != loaded[name][1] for name, path in paths.items()):
        raise ValueError("an input changed while preparing the revision plan")
    encoded = (json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("xb") as stream:
        stream.write(encoded)
    return {"schema_version": "b-content-revision-plan-cli-result-trial/0.1",
        "plan_ref": reference(plan), "revision": plan["revision"], "operations": len(values["operations"]),
        "author_kind": author_kind, "sha256": hashlib.sha256(encoded).hexdigest(),
        "input_sha256": {name: pair[1] for name, pair in loaded.items()},
        "decision": "HOLD", "complete": False, "transcription_verified": False,
        "business_acceptance": False, "platform_actions": [], "new_model_calls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=local_path, required=True)
    parser.add_argument("--graph", type=local_path, required=True, help="plain current G05 artifact")
    parser.add_argument("--base-check", type=local_path, required=True, help="plain current Check05 artifact")
    parser.add_argument("--operations", type=local_path, required=True, help="complete JSON operation list, not a delta")
    parser.add_argument("--previous", type=local_path, help="archive the previous plan when revising its full snapshot")
    parser.add_argument("--author-kind", choices=("MODEL_DRAFT", "HUMAN_DRAFT", "SYNTHETIC_TEST"), required=True)
    parser.add_argument("--author-id", required=True)
    parser.add_argument("--author-note", required=True)
    parser.add_argument("--out", type=local_path, required=True, help="new immutable output JSON file")
    args = parser.parse_args(argv)
    try:
        result = execute(args.evidence, args.graph, args.base_check, args.operations, args.out,
            author_kind=args.author_kind, author_id=args.author_id, author_note=args.author_note,
            previous_path=args.previous)
    except Exception as exc:
        print(json.dumps({"schema_version": "b-content-revision-plan-cli-result-trial/0.1",
            "error": {"type": type(exc).__name__, "message": str(exc)[:800]}, "plan_created": False,
            "decision": "HOLD", "business_acceptance": False, "transcription_verified": False,
            "platform_actions": [], "new_model_calls": 0}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
