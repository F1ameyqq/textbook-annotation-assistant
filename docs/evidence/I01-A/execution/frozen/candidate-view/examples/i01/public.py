"""Record actual imports around one unchanged public entry point."""
import argparse
import os
from pathlib import Path
import runpy
import sys
from support import EVIDENCE, imports, write

parser=argparse.ArgumentParser()
parser.add_argument('--mode',choices=('C01','A01'),required=True)
parser.add_argument('--input',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
try:
    if args.mode=='C01':
        sys.argv=['annotation.contracts.cli','validate',str(args.input)]
        runpy.run_module('annotation.contracts.cli',run_name='__main__')
    else:
        script=EVIDENCE/'preparation/raw-view/examples/a01/consume.py'
        sys.argv=[str(script),str(args.input),'--book-id','46007447']
        runpy.run_path(str(script),run_name='__main__')
finally:
    write(args.output,dict(pid=os.getpid(),argv=sys.argv,imports=imports(),entry=args.mode))
