"""Replay cached formula canvases, or explicitly collect with local models.

The frozen mathematical layout and legacy formula observations are independently
audited first. Cached replay never initializes a model or downloads anything.
An accepted check covers source and candidate integrity only; every result is
HOLD, unverified, and separate from the question graph and annotation platform.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]

from replay_formula_b import local_path, reference


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _upstream(fixture, layout_path, crop_path, legacy_path):
    """Audit saved source geometry and the unchanged legacy observations."""
    from annotation.recognition.math_layout import audit_math_layout
    from annotation.recognition.baseline import digest
    from replay_formula_b import replay as replay_legacy

    fixture = Path(fixture)
    layout = _load(layout_path or fixture / "formula-layout.json")
    recovery = _load(fixture / "recovery-evidence.json")
    source = _load(fixture / "source-descriptor.json")
    probes = [p for p in recovery["payload"]["probes"] if p["probe_id"] == layout["payload"]["probe_id"]]
    assets = [a for a in source["assets"] if a["asset_id"] == layout["payload"]["asset_id"]]
    if len(probes) != 1 or len(assets) != 1:
        raise ValueError("saved layout source probe or asset is missing or duplicated")
    if crop_path is None:
        crop = (fixture / probes[0]["crop_path"]).resolve()
        if not crop.is_relative_to(fixture.resolve()):
            raise ValueError("saved layout crop escapes the fixture")
    else:
        crop = Path(crop_path)
    layout_check = audit_math_layout(layout, assets[0], recovery, crop)
    if layout_check.get("geometry_and_token_coverage_valid") is not True:
        raise ValueError("saved mathematical layout failed its independent geometry/token audit")
    legacy_file = Path(legacy_path or fixture / "formula-observations.json")
    _, legacy, _, legacy_check, legacy_summary = replay_legacy(fixture,
        observations_path=legacy_file, layout_path=layout_path or fixture / "formula-layout.json", crop_path=crop)
    if (legacy_check["payload"].get("accepted") is not True
            or legacy_summary["recognition_failures"] or legacy_summary["exit_code"] != 0):
        raise ValueError("legacy formula observations failed their independent audit or contain recognition failures")
    upstream = {"layout_check_sha256": digest(layout_check), "legacy_observation_ref": reference(legacy),
                "legacy_check_ref": reference(legacy_check), "legacy_integrity_accepted": True}
    return layout, crop, legacy, upstream


def replay(fixture=FIXTURE, *, observations_path=None, legacy_path=None,
           layout_path=None, crop_path=None, collect=False, model_dir=None, collector=None):
    """Return layout, canvas observations, candidates, independent check, summary.

    The optional collector is a synthetic test seam, never a production backend
    selector. The CLI uses the local tensor collector only under --collect.
    Source descriptor/recovery metadata always comes from --fixture, including
    when a custom saved layout and bound source crop are supplied.
    """
    if (layout_path is None) != (crop_path is None):
        raise ValueError("--layout and --crop must be supplied together")
    if collect and (layout_path is None or crop_path is None or model_dir is None):
        raise ValueError("--collect requires explicit --layout, --crop and --models")
    if collect and observations_path is not None:
        raise ValueError("--collect cannot consume --observations")
    if not collect and (model_dir is not None or collector is not None):
        raise ValueError("local model/collector inputs require explicit --collect")
    layout, crop, legacy, upstream = _upstream(fixture, layout_path, crop_path, legacy_path)
    if collect:
        injected_collector = collector is not None
        if collector is None:
            from annotation.recognition.formula_canvas import collect_canvas_observations
            collector = collect_canvas_observations
        observations = collector(layout, crop, model_dir=Path(model_dir))
        if injected_collector and observations.get("producer", {}).get("execution_kind") != "SYNTHETIC_TEST":
            raise ValueError("an injected test collector must remain SYNTHETIC_TEST")
    else:
        observations = _load(observations_path or Path(fixture) / "formula-canvas-observations.json")
    from annotation.recognition.formula_canvas import build_canvas_candidates
    from annotation.recognition.formula_canvas_quality import audit_canvas_candidates

    candidates = build_canvas_candidates(layout, observations, crop, legacy)
    check = audit_canvas_candidates(layout, observations, candidates, crop, legacy)
    checked = check["payload"]
    if (check["schema_version"] != "b-formula-canvas-check-trial/0.1"
            or type(checked.get("accepted")) is not bool or checked.get("decision") != "HOLD"
            or checked.get("business_acceptance") is not False or checked.get("transcription_verified") is not False
            or checked.get("platform_actions") != []):
        raise ValueError("canvas audit must preserve explicit HOLD and unverified transcription/business status")
    failures = sum(v["recognition_error"] is not None
        for unit in observations["payload"]["units"] for v in unit["variants"])
    summary = {**checked["summary"], "schema_version": "b-formula-canvas-cli-summary-trial/0.1",
        "replay_mode": "EXPLICIT_LOCAL_COLLECTION" if collect else "CACHED_REPLAY",
        "execution_kind": observations["producer"]["execution_kind"], "integrity_accepted": checked["accepted"],
        "verification_scope": "FORMULA_CANVAS_SOURCE_AND_CANDIDATE_INTEGRITY_ONLY",
        "decision": "HOLD", "transcription_verified": False, "business_acceptance": False,
        "graph_modified": False, "entire_answer_reconstructed": False,
        "paid_model_calls": 0, "website_requests": 0, "platform_actions": [],
        "recognition_failures": failures, "upstream": upstream,
        "artifacts": {"math-layout.json": reference(layout), "canvas-observations.json": reference(observations),
                      "canvas-candidates.json": reference(candidates), "canvas-check.json": reference(check)},
        "exit_code": 0 if checked["accepted"] and not failures else 1}
    return layout, observations, candidates, check, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=local_path, default=FIXTURE,
                        help="source/recovery metadata and default saved artifacts")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--observations", type=local_path, help="custom cached canvas observations")
    mode.add_argument("--collect", action="store_true", help="explicitly run the current interpreter's local tensor backend")
    parser.add_argument("--legacy", type=local_path, help="unchanged cached legacy formula observations")
    parser.add_argument("--layout", type=local_path, help="saved source-bound layout; requires --crop")
    parser.add_argument("--crop", type=local_path, help="source crop bound to the saved layout; requires --layout")
    parser.add_argument("--models", type=local_path, help="existing local models only; requires --collect")
    parser.add_argument("--out", type=local_path, required=True, help="new directory for the five replay artifacts")
    args = parser.parse_args(argv)
    if args.out.exists(): parser.error("--out must be a new directory")
    if (args.layout is None) != (args.crop is None): parser.error("--layout and --crop must be supplied together")
    if args.collect and (args.layout is None or args.crop is None or args.models is None):
        parser.error("--collect requires explicit --layout, --crop and --models")
    if args.models is not None and not args.collect: parser.error("--models requires explicit --collect")
    try:
        layout, observations, candidates, check, summary = replay(args.fixture,
            observations_path=args.observations, legacy_path=args.legacy, layout_path=args.layout,
            crop_path=args.crop, collect=args.collect, model_dir=args.models)
        args.out.mkdir(parents=True, exist_ok=False)
        for name, value in (("math-layout.json", layout), ("canvas-observations.json", observations),
                ("canvas-candidates.json", candidates), ("canvas-check.json", check), ("summary.json", summary)):
            (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        parser.exit(1, f"Formula canvas replay failed: {type(exc).__name__}: {exc}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return summary["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
