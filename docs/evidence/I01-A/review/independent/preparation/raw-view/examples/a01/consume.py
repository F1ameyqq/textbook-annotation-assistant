"""Consume a relocated exchange with public API and full A01 image checks."""
import argparse
import json
from pathlib import Path

from annotation.contracts import load_bundle
from annotation.source.static import load_static_bundle


def consume(path,book_id):
    public = load_bundle(path,verify_assets=True)
    bundle = load_static_bundle(path,expected_book_id=book_id)
    if public != bundle:
        raise ValueError("public/A01 consumers disagree")
    source = bundle.artifacts[0]
    return dict(book_id=source.book_id,revision=source.revision,content_hash=source.content_hash,
                asset_count=len(source.payload.assets),metadata_page_count=source.payload.metadata_page_count,
                reference_records=len(source.payload.scope_manifest),coverage_eligible=False,
                public_resource_validation="OK",full_image_decode="OK",model_calls=0,model_cost=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exchange",type=Path)
    parser.add_argument("--book-id",required=True)
    args = parser.parse_args()
    print(json.dumps(consume(args.exchange,args.book_id),sort_keys=True))


if __name__ == "__main__":
    main()
