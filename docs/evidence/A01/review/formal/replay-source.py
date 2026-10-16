"""Replay the source probe in a fresh evidence directory; preserve original evidence."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--snapshot",type=Path,required=True)
parser.add_argument("--out",type=Path,required=True)
parser.add_argument("--stage",type=Path,required=True)
args=parser.parse_args()
formal=Path(__file__).resolve().parent
root=formal.parents[4]
allowed_stage=(root/".local/stages/A01-review").resolve()
out=args.out.resolve()
stage=args.stage.resolve()
out.relative_to(formal.resolve())
stage.relative_to(allowed_stage)
if out.exists() or stage.exists():
    parser.error("output and stage must both be new; preserve existing evidence")
out.mkdir(parents=True,exist_ok=False)
script=out/"probe.py"
shutil.copy2(formal/"source-independent/probe.py",script)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",TMP=str(allowed_stage),TEMP=str(allowed_stage),TMPDIR=str(allowed_stage))
command=[sys.executable,"-B",str(script),"--snapshot",str(args.snapshot.resolve()),"--stage",str(stage)]
proc=subprocess.run(command,env=env,capture_output=True)
(out/"replay.stdout.txt").write_bytes(proc.stdout)
(out/"replay.stderr.txt").write_bytes(proc.stderr)
(out/"replay-command.json").write_text(json.dumps({"command":command,"exit_code":proc.returncode},indent=2)+"\n",encoding="utf-8")
print(json.dumps({"exit_code":proc.returncode,"out":str(out),"note":"Read results.json matches_expectation; exit 0 is collection completion only."}))
raise SystemExit(proc.returncode)
