"""Replay cached formula observations, or explicitly collect from local models.

The default path never initializes a formula runtime. --collect uses the current
Python interpreter and requires a saved layout, source crop and local models;
it never installs or downloads a backend. Every candidate set is independently
audited and remains HOLD for transcription and business acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path.insert(0, str(ROOT / "src"))


def local_path(value):
    if (value.startswith(("\\\\", "//")) or "://" in value
            or (re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value)
                and not re.match(r"^[A-Za-z]:[\\/]", value))):
        raise argparse.ArgumentTypeError("local paths required; URLs and network shares are unsupported")
    return Path(value)


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def replay(fixture=FIXTURE, *, observations_path=None, layout_path=None, crop_path=None,
           collect=False, model_dir=None, collector=None):
    """Return layout, raw observations, candidates, independent check, summary.

    ``collector`` is for injected synthetic tests only. The production CLI uses
    collect_formula_observations in this same interpreter when --collect is set.
    """
    if (layout_path is None) != (crop_path is None):
        raise ValueError("--layout and --crop must be supplied together")
    if collect and (layout_path is None or crop_path is None or model_dir is None):
        raise ValueError("--collect requires explicit --layout, --crop and --models")
    if collect and observations_path is not None:
        raise ValueError("--collect cannot consume --observations")
    if not collect and (model_dir is not None or collector is not None):
        raise ValueError("local model/collector inputs require explicit --collect")
    if layout_path is None:
        fixture = Path(fixture)
        closed_layout = fixture / "formula-layout.json"
        if closed_layout.is_file():
            # A cached model observation names an exact upstream artifact.
            # Rebuilding it under different NumPy/OpenCV versions changes its
            # identity even if the geometry is identical. Re-audit the frozen
            # source artifact rather than silently replacing that input.
            from annotation.recognition.math_layout import audit_math_layout
            layout = json.loads(closed_layout.read_text(encoding="utf-8"))
            recovery = json.loads((fixture / "recovery-evidence.json").read_text(encoding="utf-8"))
            source = json.loads((fixture / "source-descriptor.json").read_text(encoding="utf-8"))
            matches = [p for p in recovery["payload"]["probes"] if p["probe_id"] == layout["payload"]["probe_id"]]
            if len(matches) != 1:
                raise ValueError("frozen layout source probe is missing or duplicated")
            crop = (fixture / matches[0]["crop_path"]).resolve()
            if not crop.is_relative_to(fixture.resolve()):
                raise ValueError("frozen source crop escapes fixture")
            asset = next(a for a in source["assets"] if a["asset_id"] == layout["payload"]["asset_id"])
            layout_check = audit_math_layout(layout, asset, recovery, crop)
        else:
            from replay_math_b import replay as replay_layout
            layout, layout_check, crop = replay_layout(fixture)
        if not layout_check["geometry_and_token_coverage_valid"]:
            raise ValueError("source mathematical layout failed its geometry/token audit")
    else:
        layout = json.loads(Path(layout_path).read_text(encoding="utf-8"))
        crop = Path(crop_path)
    if collect:
        injected_collector = collector is not None
        if collector is None:
            from annotation.recognition.formula_backend import collect_formula_observations
            collector = collect_formula_observations
        observations = collector(layout, crop, model_dir=Path(model_dir))
        if injected_collector and observations.get("producer", {}).get("execution_kind") != "SYNTHETIC_TEST":
            raise ValueError("an injected test collector must remain SYNTHETIC_TEST")
    else:
        observations = json.loads(Path(observations_path or Path(fixture) / "formula-observations.json").read_text(encoding="utf-8"))
    from annotation.recognition.formula_candidates import build_formula_candidates
    from annotation.recognition.formula_quality import audit_formula_candidates
    candidates = build_formula_candidates(layout, observations, crop)
    check = audit_formula_candidates(layout, observations, candidates, crop)
    checked = check["payload"]
    if (check["schema_version"] != "b-formula-check-trial/0.1"
            or type(checked["accepted"]) is not bool or checked["decision"] != "HOLD"
            or checked["business_acceptance"] is not False or checked["transcription_verified"] is not False
            or checked["platform_actions"] != []):
        raise ValueError("formula audit must preserve explicit HOLD and unverified transcription/business status")
    recognition_failures = sum(v["recognition_error"] is not None
        for unit in observations["payload"]["units"] for v in unit["variants"])
    summary = dict(schema_version="b-formula-cli-summary-trial/0.1",
        replay_mode="EXPLICIT_LOCAL_COLLECTION" if collect else "CACHED_REPLAY",
        execution_kind=observations["producer"]["execution_kind"], integrity_accepted=checked["accepted"],
        verification_scope="FORMULA_SOURCE_AND_CANDIDATE_INTEGRITY_ONLY", decision="HOLD",
        transcription_verified=False, business_acceptance=False, graph_modified=False,
        entire_answer_reconstructed=False, paid_model_calls=0, website_requests=0, platform_actions=[],
        recognition_failures=recognition_failures, **checked["summary"],
        artifacts={"math-layout.json": reference(layout), "formula-observations.json": reference(observations),
            "formula-candidates.json": reference(candidates), "formula-check.json": reference(check)},
        exit_code=0 if checked["accepted"] and not recognition_failures else 1)
    return layout, observations, candidates, check, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=local_path, default=FIXTURE)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--observations", type=local_path, help="read a custom cached observation artifact")
    mode.add_argument("--collect", action="store_true", help="explicitly run the current interpreter's local formula CPU backend")
    parser.add_argument("--layout", type=local_path, help="saved global-version mathematical layout; requires --crop")
    parser.add_argument("--crop", type=local_path, help="source image crop bound to the saved layout; requires --layout")
    parser.add_argument("--models", type=local_path, help="existing local model directory; requires --collect")
    parser.add_argument("--out", type=local_path, required=True, help="new directory for the five replay artifacts")
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error("--out must be a new directory")
    if (args.layout is None) != (args.crop is None):
        parser.error("--layout and --crop must be supplied together")
    if args.collect and (args.layout is None or args.crop is None or args.models is None):
        parser.error("--collect requires explicit --layout, --crop and --models")
    if args.models is not None and not args.collect:
        parser.error("--models requires explicit --collect")
    try:
        layout, observations, candidates, check, summary = replay(args.fixture,
            observations_path=args.observations, layout_path=args.layout, crop_path=args.crop,
            collect=args.collect, model_dir=args.models)
        args.out.mkdir(parents=True, exist_ok=False)
        for name, value in (("math-layout.json", layout), ("formula-observations.json", observations),
                ("formula-candidates.json", candidates), ("formula-check.json", check), ("summary.json", summary)):
            (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        parser.exit(1, f"Formula replay failed: {type(exc).__name__}: {exc}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return summary["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
