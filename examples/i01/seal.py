"""File/Git-only final manifest and staged raw-byte verification."""
import argparse
from pathlib import Path
import re
from support import ROOT, EVIDENCE, BASE, PRODUCT, WORKFLOW, git, load, sha, write

REPORT='docs/tasks/I01-A-execution-report.md'
MANIFEST=EVIDENCE/'manifest.json'


def allowed(path):
    return path==REPORT or path=='tests/test_i01_preflight.py' or path.startswith((
        'examples/i01/','tests/fixtures/i01/','docs/evidence/I01-A/execution/'))


def create():
    changed=git(['diff','--name-only',BASE,'HEAD']).decode().splitlines()
    assert all(allowed(p) for p in changed)
    assert not git(['diff','--name-only',BASE,'HEAD','--','src','pyproject.toml','requirements.txt'])
    paths=[ROOT/'examples/i01', ROOT/'tests/fixtures/i01', ROOT/'tests/test_i01_preflight.py',ROOT/REPORT,EVIDENCE]
    members=sorted({p for item in paths for p in ([item] if item.is_file() else item.rglob('*')) if p.is_file() and p!=MANIFEST})
    rows=[]
    for path in members:
        relative=path.relative_to(ROOT).as_posix()
        assert allowed(relative) and not path.is_symlink()
        rows.append(dict(path=relative,bytes=path.stat().st_size,sha256=sha(path.read_bytes())))
    write(MANIFEST,dict(status='REVIEW',base=BASE,product=PRODUCT,workflow=WORKFLOW,
        first_freeze='3a7b5430659918d015a23fa2da722bfe3cec44af',
        candidate='be68b8d7c645de556d601458d1d493258f063721',
        business_evidence_commit='be6dd893d796e298dda9799ac486a5c27c776f3d',
        evidence_payload_commit='23df362ef88f95fd5998521f24b57fd0fe07a1e9',
        final_delivery_commit='final caller-provided Git HEAD containing this report and manifest; no circular self hash',
        files=rows,excluded=[dict(path=MANIFEST.relative_to(ROOT).as_posix(),reason='self SHA256 cannot be embedded; final tool receipt supplies hash')],
        targets=3,dispatches=3,annotation_effects=3,operator_changes=1,driver_package_corrections=1,
        business_failures=0,business_reruns=0,content_check_status='PENDING',submission_status='NOT_SUBMITTED',
        resource_release='docs/evidence/I01-A/execution/release.json',
        source_boundary='A01 public archive and fixed synthetic native paths separately; no real A01-to-native or B acceptance'))
    print('MANIFEST_CREATED files='+str(len(rows)))


def verify():
    manifest=load(MANIFEST)
    files=manifest['files']
    # A single raw batch avoids text output decoding/EOL normalization.
    packed=git(['cat-file','--batch'],''.join(':'+r['path']+'\n' for r in files).encode('utf-8'))
    offset=0
    for row in files:
        end=packed.index(b'\n',offset)
        _,kind,size=packed[offset:end].split();size=int(size);offset=end+1
        raw=packed[offset:offset+size];offset+=size+1
        assert kind==b'blob' and len(raw)==row['bytes'] and sha(raw)==row['sha256'],row['path']
        assert sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert offset==len(packed)
    assert git(['show',':'+MANIFEST.relative_to(ROOT).as_posix()])==MANIFEST.read_bytes()
    assert not git(['diff','--name-only'])
    changes=git(['diff','--cached','--name-only',BASE]).decode().splitlines()
    assert all(allowed(p) for p in changes)
    text=(ROOT/REPORT).read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://' not in target: assert ((ROOT/REPORT).parent/target.split('#')[0]).exists(),target
    print('STAGED_RAW_MANIFEST_OK files='+str(len(files))+' manifest_sha256='+sha(MANIFEST.read_bytes()))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    verify() if args.verify else create()
