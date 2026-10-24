#!/usr/bin/env python3
"""Q15 revision-9 plan-specific assertions.

This does not replace the generic content-revision consumer. It closes two
Q15-specific semantic checks that the reusable API intentionally does not
derive: the printed number must remain metadata, and the source-inspected
one-quarter must remain an explicitly typed LaTeX run.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path


ANSWER_ID = "a-17f4ef3ee25046f8e3f583a2"
LEFT_ID = "rebuild-page7-q15-left-start-source-region"
RIGHT_ID = "rebuild-page7-q15-right-continuation-source-region"
FRACTION = r"\frac{1}{4}"


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def audit(plan: dict, graph: dict) -> dict:
    errors: list[str] = []
    operations = plan.get("payload", {}).get("operations", [])
    q15 = [op for op in operations if op.get("operation_id") in {LEFT_ID, RIGHT_ID}]
    by_id = {op.get("operation_id"): op for op in q15}
    if len(q15) != 2 or set(by_id) != {LEFT_ID, RIGHT_ID}:
        errors.append("plan must contain exactly the two named Q15 operations")
    if len(operations) != 16 or [op.get("operation_id") for op in operations[-2:]] != [LEFT_ID, RIGHT_ID]:
        errors.append("Q15 operations must be the final two operations of the 16-operation plan")

    answers = [a for a in graph.get("payload", {}).get("answers", []) if a.get("answer_id") == ANSWER_ID]
    if len(answers) != 1:
        errors.append("graph must contain exactly one bound Q15 answer")
        return {"accepted": False, "errors": errors}
    answer = answers[0]
    if answer.get("printed_number") != "15":
        errors.append("Q15 printed_number metadata must remain exactly '15'")
    active = answer.get("text")
    if not isinstance(active, str):
        errors.append("Q15 active text must be a string")
        active = ""
    if re.match(r"^\s*15\s*[.．、]", active):
        errors.append("Q15 active text duplicates its printed-number metadata")

    plan_blocks = [block for op_id in (LEFT_ID, RIGHT_ID) for block in by_id.get(op_id, {}).get("blocks", [])]
    expected_text = "\n".join("".join(run.get("text", "") for run in block.get("runs", [])) for block in plan_blocks)
    if active != expected_text:
        errors.append("Q15 active text is not the exact ordered projection of the four plan blocks")

    plan_runs = [run for block in plan_blocks for run in block.get("runs", [])]
    fraction_runs = [run for run in plan_runs if run.get("text") == FRACTION]
    if fraction_runs != [{"format": "latex", "text": FRACTION}]:
        errors.append("Q15 one-quarter must occur exactly once as an explicit LaTeX run")
    if any(run.get("format") == "plain" and (FRACTION in run.get("text", "") or "1/4" in run.get("text", "")) for run in plan_runs):
        errors.append("Q15 one-quarter is hidden in a plain-text run")

    content = answer.get("content_fragments", [])
    graph_blocks = [item for item in content if item.get("operation_id") in {LEFT_ID, RIGHT_ID}]
    if [item.get("block_id") for item in graph_blocks] != [block.get("block_id") for block in plan_blocks]:
        errors.append("materialized Q15 block order differs from the plan")
    for item, block in zip(graph_blocks, plan_blocks):
        if item.get("runs") != block.get("runs"):
            errors.append(f"materialized runs differ for block {block.get('block_id')}")
        if (item.get("verification_status") != "UNVERIFIED" or item.get("complete") is not False
                or item.get("transcription_verified") is not False or item.get("business_acceptance") is not False):
            errors.append(f"block {block.get('block_id')} promotes an unverified draft")

    region_ops = answer.get("content_projection", {}).get("region_operations")
    if region_ops != [LEFT_ID, RIGHT_ID]:
        errors.append("materialized Q15 region-operation order differs")
    return {"accepted": not errors, "errors": errors}


def self_test(plan: dict, graph: dict) -> dict:
    honest = audit(plan, graph)

    duplicate = copy.deepcopy(graph)
    answer = next(a for a in duplicate["payload"]["answers"] if a["answer_id"] == ANSWER_ID)
    answer["text"] = "15. " + answer["text"]
    duplicate_result = audit(plan, duplicate)

    plain_plan = copy.deepcopy(plan)
    right = next(op for op in plain_plan["payload"]["operations"] if op["operation_id"] == RIGHT_ID)
    fraction = next(run for block in right["blocks"] for run in block["runs"] if run["text"] == FRACTION)
    fraction["format"] = "plain"
    plain_graph = copy.deepcopy(graph)
    answer = next(a for a in plain_graph["payload"]["answers"] if a["answer_id"] == ANSWER_ID)
    graph_fraction = next(run for item in answer["content_fragments"] for run in item.get("runs", []) if run["text"] == FRACTION)
    graph_fraction["format"] = "plain"
    plain_result = audit(plain_plan, plain_graph)

    accepted = honest["accepted"] and not duplicate_result["accepted"] and not plain_result["accepted"]
    return {
        "accepted": accepted,
        "honest": honest,
        "negative_printed_number_duplicate": duplicate_result,
        "negative_fraction_plain_run": plain_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    parser.add_argument("graph")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    plan, graph = load(args.plan), load(args.graph)
    result = self_test(plan, graph) if args.self_test else audit(plan, graph)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
