"""Read/roundtrip copied C01 fixtures using only the public contracts API."""
import argparse
import json
import shutil
from pathlib import Path

from annotation.contracts import load_bundle, write_bundle
from build_fixtures import summary


def consume(fixture_directory, roundtrip=None):
    folder = Path(fixture_directory).resolve()
    bundle = load_bundle(folder / "input.json", verify_assets=True)
    observed = summary(bundle)
    expected = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
    if observed != expected:
        raise ValueError("expected.json: exact public-API summary mismatch")
    if roundtrip is not None:
        destination = Path(roundtrip).resolve()
        if destination == folder / "input.json":
            raise ValueError("roundtrip destination must preserve the original input.json")
        if destination.exists():
            raise ValueError("roundtrip destination already exists; preserve the old exchange")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if (destination.parent / "assets").resolve() != (folder / "assets").resolve():
            shutil.copytree(str(folder / "assets"), str(destination.parent / "assets"))
        write_bundle(bundle, destination)
        reloaded = load_bundle(destination, verify_assets=True)
        if summary(reloaded) != expected:
            raise ValueError("roundtrip: public-API summary mismatch")
        (destination.parent / "expected.json").write_text(
            json.dumps(expected, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return {"fixture": folder.name, "comparison": "EXACT_MATCH", "roundtrip": roundtrip is not None,
            "kind_counts": observed["kind_counts"], "plan": observed["plan"], "batch_state": observed["batch"]["state"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture_directory")
    parser.add_argument("--roundtrip", type=Path)
    args = parser.parse_args()
    print(json.dumps(consume(args.fixture_directory, args.roundtrip), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
