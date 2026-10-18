"""Read-only publication integrity check. Standard library + Git; no product imports."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ref', default='HEAD')
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')

def git(*parts):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *parts], cwd=root, env=env)

ref = git('rev-parse', '--verify', args.ref + '^{tree}').decode().strip()
def blob(path):
    return git('show', ref + ':' + path)

manifest = json.loads(blob('docs/handoff/a07-q1/manifest.json'))
count = 0
for member in manifest['source_members'] + manifest['generated_members']:
    raw = blob(member['path'])
    assert len(raw) == member['bytes'], member['path']
    assert hashlib.sha256(raw).hexdigest() == member['sha256'], member['path']
    count += 1
overrides = {(m['manifest'], m['original_path']): m['published_path'] for m in manifest['historical_overrides']}
historical_members = 0
for path in manifest['frozen_delivery_manifests']:
    original = json.loads(blob(path))
    for member in original['members']:
        target = overrides.get((path, member['path']), member['path'])
        raw = blob(target)
        assert len(raw) == member['bytes'], target
        assert hashlib.sha256(raw).hexdigest() == member['sha256'], target
        historical_members += 1
print(json.dumps({'result': 'PASS_PUBLICATION_INTEGRITY_ONLY', 'tree': ref,
                  'publication_members': count, 'historical_members': historical_members,
                  'normal_business_runs': 0, 'platform_actions': 0}, indent=2))
