"""Repository-relative offline-first batch entry. Legacy --orders is refused."""
from pathlib import Path
import sys


def main(argv=None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from annotation.runtime.usense_live.batch import main as batch_main
    return batch_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
