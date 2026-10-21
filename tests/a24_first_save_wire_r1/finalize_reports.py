"""Record the actual focused results and known helper failures, without reruns."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/"docs/evidence/A24/first-save-wire-r1"
reports = []
for path in sorted(OUT.glob("test-attempt-*.json")):
    report = json.loads(path.read_bytes())
    reports.append({"path": path.relative_to(ROOT).as_posix(), **{k: report[k] for k in
        ("tests", "failures", "errors", "duration_ms", "passed", "real_resources", "old_suites_run")}})
assert reports[-1]["path"].endswith("test-attempt-07-final-author.json") and reports[-1]["passed"]
paths = [ROOT/p for p in ("src/annotation/delivery/live_pilot/plan.py", "src/annotation/delivery/live_pilot/usense.py",
    "src/annotation/delivery/live_pilot/wire.py", "src/annotation/quality/live_pilot.py", "src/annotation/runtime/live_pilot/runner.py",
    "src/annotation/runtime/live_pilot/authority.py", "src/annotation/runtime/live_pilot/owner.py",
    "src/annotation/runtime/live_pilot/private_payload.py", "tools/a24_first_save_launcher.py")]
paths += sorted((ROOT/"tests/a24_first_save_wire_r1").glob("*.py"))
for path in paths: ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
value = {"schema": "A24R1FocusedValidation/v1", "author_result": "PASS_OFFLINE_ONLY", "attempts": reports,
    "syntax_files_checked": len(paths), "first_failures_retained": [
        {"report": "test-attempt-01.json", "cause": "Python3.12 has no pydantic; module load failed, controls NOT_RUN; switched to existing Python3.9 environment"},
        {"report": "test-attempt-05.json", "cause": "New fresh-reopen fake helper omitted parent directory creation; helper error, no platform"},
        {"report": "test-attempt-06-reopen-only.json", "cause": "New fake reader lacked retained fake server payload; native manifest correctly stopped UNKNOWN; helper state fixed"}],
    "preparation_helper_limitations": [
        "Initial source-inspection helper requested quality/targetcheck.py although targetcheck is a package; read failed, source unchanged",
        "PowerShell rg literal wildcard file argument was rejected; exact paths used afterward",
        "One requested old report filename did not exist; this was a read helper error, not a product/test result",
        "Python3.14 dependency availability probe also lacked pydantic; no install or environment mutation",
        "Initial JPEG review sheet preview was too short; six actual JPEGs were individually reviewed and full sheet retained"],
    "product_or_live_failure_reclassified": False, "old_review_REWORK_and_sentinel_failure_preserved": True,
    "model_original_FAILED_HOLD_preserved": True, "actual_model_calls": 0, "actual_platform_calls": 0,
    "real_profile_or_browser_or_native_created": False, "formal_acceptance": "PENDING"}
with (OUT/"failure-inventory.json").open("xb") as handle:
    handle.write((json.dumps(value, indent=2)+"\n").encode())
print(json.dumps({"final_tests": reports[-1]["tests"], "passed": reports[-1]["passed"], "syntax_files": len(paths)}))
