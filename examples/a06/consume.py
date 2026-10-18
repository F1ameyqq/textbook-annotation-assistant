"""Fixed consumer routes only through the public A06 CLI."""
from annotation.source.b_handoff.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
