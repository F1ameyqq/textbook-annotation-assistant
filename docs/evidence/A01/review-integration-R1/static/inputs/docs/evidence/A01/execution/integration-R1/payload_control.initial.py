"""Additional bounded negative: corrupt encoded original content, not its hash."""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args(); tree=args.tree.resolve(); out=args.out.resolve()
    original_task=Path(__file__).resolve().parents[5]
    assert tree!=original_task and tree!=Path("D:/1800").resolve()
    out.mkdir(parents=True,exist_ok=False)
    path=tree/"tests/fixtures/a01/integration-R1/reference.json"
    original=path.read_bytes(); value=json.loads(original)
    item=value["files"][0]
    raw=base64.b64decode(item["git_original_base64"],validate=True)
    expected=item["git_sha256"]; assert sha(raw)==expected
    changed=raw+b"\nactual encoded input content damage\n"
    item["git_original_base64"]=base64.b64encode(changed).decode("ascii")
    assert item["git_sha256"]==expected  # The fixed expected digest is untouched.
    modified=(json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    command=[sys.executable,"-B",str(tree/"examples/a01/integration-R1/verify.py"),str(out/"run"),"--focused"]
    try:
        path.write_bytes(modified)
        with tempfile.TemporaryDirectory(prefix="a01-i1-payload-") as tmp:
            env=dict(os.environ,PYTHONPATH=str(tree/"src"),PYTHONDONTWRITEBYTECODE="1",TMP=tmp,TEMP=tmp,TMPDIR=tmp)
            proc=subprocess.run(command,cwd=tree,env=env,capture_output=True,text=True)
    finally:
        path.write_bytes(original)
    record=dict(task="A01-integration-R1",status="REVIEW",command=command,cwd=str(tree),exit_code=proc.returncode,
                stdout=proc.stdout,stderr=proc.stderr,input_path=str(path),fixed_entry=item["path"],
                original_payload_sha256=sha(raw),damaged_payload_sha256=sha(changed),fixed_expected_sha256=expected,
                source_file_before_sha256=sha(original),source_file_damaged_sha256=sha(modified),
                source_file_restored_sha256=sha(path.read_bytes()),
                expected_error="fixed Git original digest mismatch",network_browser_platform_model_calls=0)
    (out/"results.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert proc.returncode==1 and "fixed Git original digest mismatch" in proc.stderr
    assert path.read_bytes()==original
    print(json.dumps(dict(exit_code=proc.returncode,fixed_expected_digest_unchanged=True,payload_corruption_rejected=True,temporary_input_restored=True)))


if __name__=="__main__":
    main()
