"""Verify a sealed portable release, rebuild it and replay its pinned C01 reader."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

sys.dont_write_bytecode = True
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def need(value, code):
    if not value:
        raise ValueError(code)


def safe_member(name):
    need(isinstance(name, str) and name and not any(c in name for c in ("\\", ":", "\x00"))
         and not name.startswith("/") and all(p not in ("", ".", "..") for p in name.split("/")), "UNSAFE_MEMBER")
    return PurePosixPath(name)


def verify_manifest(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_bytes())
    members = manifest["members"]
    expected = {m["path"] for m in members}
    need(len(expected) == len(members) and "manifest.json" not in expected, "DUPLICATE_MANIFEST_MEMBER")
    entries = list(root.rglob("*"))
    need(not any(p.is_symlink() for p in entries), "SYMLINK_NOT_ALLOWED")
    actual = {p.relative_to(root).as_posix() for p in entries if p.is_file()}
    need(actual == expected | {"manifest.json"}, "PACKAGE_MEMBER_SET_CHANGED")
    for member in members:
        raw = (root / safe_member(member["path"])).read_bytes()
        need(len(raw) == member["bytes"] and sha(raw) == member["sha256"], "PACKAGE_MEMBER_CHANGED:" + member["path"])
    return len(members)


def run(root, out):
    root, out = Path(root).resolve(), Path(out).resolve()
    count = verify_manifest(root)
    need(not out.is_relative_to(root) and not root.is_relative_to(out), "OUTPUT_MUST_BE_OUTSIDE_PACKAGE")
    need(not out.exists(), "FRESH_OUTPUT_REQUIRED")
    release = json.loads((root / "release.json").read_bytes())
    producer = release.get('producer_script', 'export_lesson_c01_b.py')
    verifier = release.get('verifier_script', 'verify_lesson_c01_b.py')
    need((producer, verifier) in (
        ('export_lesson_c01_b.py', 'verify_lesson_c01_b.py'),
        ('revise_source_confirmed_c01_b.py', 'verify_source_confirmed_c01_b.py')),
        'UNSUPPORTED_REPLAY_ENTRYPOINTS')
    need(sys.version_info[:2] == (3, 12), "VALIDATED_PYTHON_312_REQUIRED")
    need(sha((root / "delivery/bundle.json").read_bytes()) == release["bundle_sha256"], "RELEASE_BUNDLE_CHANGED")
    out.mkdir(parents=True)

    def command(script, *args):
        completed = subprocess.run([sys.executable, "-B", str(root / "tools" / script), *map(str, args)],
                                   capture_output=True, text=True, encoding="utf-8")
        (out / (script + ".log")).write_text(completed.stdout + completed.stderr, encoding="utf-8")
        need(completed.returncode == 0, "REPLAY_COMMAND_FAILED:" + script)

    rebuilt = out / "rebuilt-delivery"
    command(producer, "--frozen", root / "delivery", "--out", rebuilt)
    reference = {p.relative_to(root / "delivery").as_posix(): p.read_bytes() for p in (root / "delivery").rglob("*") if p.is_file()}
    actual = {p.relative_to(rebuilt).as_posix(): p.read_bytes() for p in rebuilt.rglob("*") if p.is_file()}
    need(actual == reference, "FROZEN_REBUILD_BYTES_DIFFER")
    command(verifier, "--delivery", rebuilt, "--out", out / "b-check.json")
    command("b-c01-readonly-consumer.py", "--a-source", root / "consumer-a", "--pins", root / "consumer-pins.json",
            "--pins-sha256", release["consumer_pins_sha256"], "--bundle", rebuilt / "bundle.json",
            "--expected-questions", release["questions"], "--out", out / "a-readback.json")
    receipt = json.loads((out / "a-readback.json").read_bytes())
    need(receipt["complete_object_equal"] is True and receipt["complete_object_sha256"] == release["complete_object_sha256"]
         and receipt["bundle_sha256"] == release["bundle_sha256"], "FIXED_A24_FULL_READBACK_CHANGED")
    need(verify_manifest(root) == count, "INPUT_PACKAGE_MUTATED")
    result = {"status": "PORTABLE_REBUILD_AND_PINNED_A24_READBACK_PASSED", "manifest_members": count,
              "rebuilt_files": len(actual), "bundle_sha256": receipt["bundle_sha256"],
              "complete_object_sha256": receipt["complete_object_sha256"], "questions": receipt["questions"],
              "fragments": receipt["fragments"], "b_content_ready": release["b_content_ready"],
              "c01_decision": "HOLD", "platform_requests": 0, "planning_or_dispatch": False,
              "a_owner_acceptance": False, "independent_human_acceptance": False}
    (out / "replay-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.package, args.out)))


if __name__ == "__main__":
    main()
