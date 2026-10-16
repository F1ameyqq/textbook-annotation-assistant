"""Build the assigned archives into a NEW output directory; offline only."""
import argparse
import json
from pathlib import Path

from annotation.source.static import import_book


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination",type=Path)
    parser.add_argument("--repo-root",type=Path,default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    if args.destination.exists():
        parser.error("destination already exists; choose a new revision directory")
    paths = [import_book(args.repo_root,book,args.destination/book) for book in ("46006966","46007447")]
    print(json.dumps(dict(exchanges=[str(p) for p in paths],model_calls=0,model_cost=0)))


if __name__ == "__main__":
    main()
