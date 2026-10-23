"""Explicit reviewed apply/insert writer. Root alone supplies live authorization."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from annotation.runtime.usense_live.structural_writer import main
if __name__=='__main__':raise SystemExit(main())
