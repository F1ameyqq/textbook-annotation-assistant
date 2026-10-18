"""Seal D01 with Git bytes and explicitly enumerated checkout representations.

One-time correction after the first inventory/index comparison. The original
inventory and changed helper/report bytes are retained in index-byte-first-attempt.
This does not alter original evidence or A01 representation policies.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    root = Path(__file__).resolve().parents[2]
    evidence = root / "docs/evidence/D01/execution"
    manifest = evidence / "SHA256SUMS.json"
    first = evidence / "index-byte-first-attempt/SHA256SUMS.json"
    assert sha(first.read_bytes()) == "6f1a0451900e6b8f9607782d98cbf43e3b153de32b3bb501deb25c13729055ba"
    assert manifest.read_bytes() == first.read_bytes(), "do not overwrite a later seal"
    data = json.loads(first.read_text(encoding="utf-8"))
    allowed = {"pyproject.toml"} | {
        p.relative_to(root).as_posix() for p in (root / "examples/d01").iterdir()
        if p.suffix in (".py", ".ps1")}
    audit = {"first_manifest_sha256": sha(first.read_bytes()),
             "first_index_comparison": {"files": 182, "git_matches": 181, "mismatches": ["pyproject.toml"],
                  "tool_session": 45917, "exit_code": 1, "terminal": "AssertionError: ['pyproject.toml']"},
             "scope": "Only pyproject.toml and enumerated D01 Python/PowerShell helper text; no raw evidence or A01 policy changes",
             "files": []}
    paths = {root / "pyproject.toml", root / "docs/tasks/D01-execution-report.md"}
    for prefix in ("examples/d01", "docs/evidence/D01/execution"):
        paths.update(p for p in (root / prefix).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    paths.discard(manifest)
    primary = {}
    for relative in sorted(allowed):
        raw = subprocess.check_output(["git", "-C", str(root), "show", ":" + relative])
        assert b"\r" not in raw, "fixed Git text must use LF"
        disk = (root / relative).read_bytes()
        crlf = raw.replace(b"\n", b"\r\n")
        assert disk in (raw, crlf), relative
        ast.parse(raw.decode("utf-8"), filename=relative, feature_version=9) if relative.endswith(".py") else None
        primary[relative] = raw
        audit["files"].append({"path": relative, "git_bytes": len(raw), "git_sha256": sha(raw),
            "checkout_bytes": len(disk), "checkout_sha256": sha(disk),
            "exact_crlf_bytes": len(crlf), "exact_crlf_sha256": sha(crlf)})
    audit_path = evidence / "checkout-byte-audit.json"
    assert not audit_path.exists()
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    paths.add(audit_path)
    entries = []
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        raw = primary[relative] if relative in primary else path.read_bytes()
        entry = {"path": relative, "bytes": len(raw), "sha256": sha(raw)}
        if relative in allowed:
            other = raw.replace(b"\n", b"\r\n")
            entry["representations"] = [{"kind": "EXACT_LF_TO_CRLF_FOR_THIS_FILE",
                                          "bytes": len(other), "sha256": sha(other)}]
        entries.append(entry)
    data.update(format="d01-execution-sha256-2", files=entries,
        byte_policy="Primary is exact Git bytes; only explicitly enumerated pyproject/D01 helper entries have one fixed CRLF hash. Raw evidence has no alternatives.")
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(entries), "explicit_checkout_alternatives": len(allowed),
                      "manifest_sha256": sha(manifest.read_bytes())}, indent=2))


if __name__ == "__main__":
    main()
