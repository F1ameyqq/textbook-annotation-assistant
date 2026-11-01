"""Replay pixel-bound mathematical layout from existing CPU OCR; no new OCR."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from annotation.recognition.math_layout import build_math_layout,audit_math_layout,draw_math_layout


def replay(fixture,probe_id="unit2-q16",variant_id=None):
    fixture = Path(fixture)
    recovery = json.loads((fixture/"recovery-evidence.json").read_text(encoding="utf-8"))
    source = json.loads((fixture/"source-descriptor.json").read_text(encoding="utf-8"))
    probe = next(p for p in recovery["payload"]["probes"] if p["probe_id"] == probe_id)
    asset = next(a for a in source["assets"] if a["asset_id"] == probe["asset_id"])
    crop_path = (fixture/probe["crop_path"]).resolve()
    if not crop_path.is_relative_to(fixture.resolve()):raise ValueError("math crop path outside fixture")
    layout = build_math_layout(asset,recovery,probe_id,crop_path,variant_id=variant_id)
    check = audit_math_layout(layout,asset,recovery,crop_path)
    return layout,check,crop_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture",type=Path,default=ROOT/"tests/fixtures/book46007447")
    parser.add_argument("--probe",default="unit2-q16")
    parser.add_argument("--variant")
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    if args.out.exists():parser.error("--out must be a new directory")
    try:
        layout,check,crop = replay(args.fixture,args.probe,args.variant)
    except (ValueError,OSError,KeyError,StopIteration) as exc:
        parser.exit(1,f"Math replay failed: {exc}\n")
    args.out.mkdir(parents=True)
    for name,value in (("math-layout.json",layout),("math-layout-check.json",check)):
        (args.out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    draw_math_layout(layout,crop).save(args.out/"math-layout.png")
    print(json.dumps({"decision":check["decision"],"geometry_and_token_coverage_valid":check["geometry_and_token_coverage_valid"],
                      "fraction_candidates":check["fraction_candidates"],"input_tokens":check["input_tokens"],
                      "transcription_verified":False}))


if __name__ == "__main__":main()
