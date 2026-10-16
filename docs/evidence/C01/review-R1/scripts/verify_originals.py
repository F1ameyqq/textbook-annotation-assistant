import argparse
import hashlib
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('--tree', type=Path, required=True)
a = p.parse_args()
sys.path.insert(0, str(a.tree / 'src'))
from annotation.contracts import ContractError, load_bundle, validate_bundle, assert_plan_ready, artifact_ref

ROOT = Path(r'D:\1800')
results = []
for case, digest, suffix in (
    ('snapshot_question_missing_directory', '91315dde2e4cdefdb0069301047c0e02f35123ca84439c1030ca19a968710101', '.questions[0].directory_id'),
    ('action_missing_platform_question', 'd0bc9967abae687a450975d25043183563f3226676c6c003b46e4ec96e55366d', '.actions[0].target.platform_question_id'),
):
    path = ROOT / 'docs/evidence/C01/review/counterexamples' / case / 'input.json'
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == digest, (case, actual)
    data = json.loads(raw.decode('utf-8'))
    plan = next(x for x in data['artifacts'] if x['kind'] == 'ApplyPlan')
    snapshot = next(x for x in data['artifacts'] if x['kind'] == 'PlatformSnapshot')
    operations = (
        ('validate_bundle', lambda: validate_bundle(data)),
        ('load_bundle_full_resources', lambda: load_bundle(path)),
        ('assert_plan_ready', lambda: assert_plan_ready(data, artifact_ref(plan), artifact_ref(snapshot))),
    )
    for name, call in operations:
        try:
            call()
            results.append(dict(case=case, api=name, passed=False, result='ACCEPTED_INVALID', input_sha256=actual))
        except ContractError as error:
            correct = any(i['code'] == 'MISSING_REFERENCE' and i['path'].endswith(suffix) for i in error.issues)
            results.append(dict(case=case, api=name, passed=correct, result='REJECTED', issues=error.issues, input_sha256=actual))
out = ROOT / '.local/stages/C01-review-R1/original-api-results.json'
out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(results, ensure_ascii=False, indent=2))
sys.exit(1 if any(not x['passed'] for x in results) else 0)
