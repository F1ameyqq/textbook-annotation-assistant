"""Retain independent ABSENT replan and ordinary separate-book checks on R1."""
import json
import subprocess
import sys
from pathlib import Path

OUT=Path(__file__).resolve().parent
old=OUT.parent/'review/formal/supplement_final.py'
text=old.read_text(encoding='utf-8').replace('import independent_review as review','import risk_review as review').replace(
    '5c9285720c8628c5198bedeadfc9f6bc7826a914','38aca9dcc8d027409b95193e9cc142c2336b76d3')
path=OUT/'risk_final_supplement.py';path.write_text(text,encoding='utf-8')
argv=[sys.executable,'-B',str(path)]
result=subprocess.run(argv,cwd=OUT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(OUT/'risk-final.stdout.txt').write_bytes(result.stdout);(OUT/'risk-final.stderr.txt').write_bytes(result.stderr)
(OUT/'risk-final-command.json').write_text(json.dumps({'argv':argv,'cwd':str(OUT),'exit_code':result.returncode,'derived_from':str(old),
    'changes':'Import new reviewer harness bound to R1; retain independent behavior assertions and new output.'},indent=2)+'\n',encoding='utf-8')
print(result.stdout.decode(errors='replace'))
if result.returncode:print(result.stderr.decode(errors='replace'))
sys.exit(result.returncode)
