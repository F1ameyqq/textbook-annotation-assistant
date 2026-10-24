# Local OCR before native question binding

`tools/run_source_region_ocr.py` handles explicitly declared source regions when
a saved image has no native question ID or frame yet. It does not invent either
identity, import a browser/runtime writer, or grant platform approval.

```powershell
python tools/run_source_region_ocr.py collect --spec PRIVATE/spec.json --out PRIVATE/new-run
python tools/run_source_region_ocr.py check --run PRIVATE/new-run/run.json
```

The output directory must not exist. The collector preflights installed local
RapidOCR models, uses CPU recognition only on regions with `ocr=true`, and keeps
both scale-3 and scale-4 observations. Other regions retain original source
pixels without model inference. The CLI blocks socket connections. Importing
the module does not patch global sockets or initialize a model.

The private input has schema `SourceRegionOCRSpec/v1`:

- `book_id`: the expected source book string.
- `sources`: each source has `viewer_page`, `image`, `dimensions`,
  `native_metadata`, `page_inventory`, `download_manifest`, and `allowed_roles`.
  File references contain absolute `path`, raw `bytes`, and lowercase `sha256`.
- `regions`: each region has `region_id`, `viewer_page`, `role`, `bbox`, and an
  explicit boolean `ocr`. IDs are local proposal identities, never server IDs.
  Bboxes are XYXY pixels on the original image; minima round down and maxima up.

The reader checks the observed download manifest's image hash and URL against
the native page metadata and page inventory. It checks the expected book, one
native page per response, source image index equal to viewer page minus one,
dimensions, allowed role, finite coordinates, and bounds. A page declared only
for a section boundary cannot be used as an answer page. Both existing source
manifest URL keys (`url` and `source_url`) are supported without changing the
stored bytes. The source inputs are trusted evidence anchors, not generated
from the image bytes just to make a check pass.

`check` reopens the original image and compares crop pixels, validates the full
source binding and role, reconstructs primary text from retained raw rows, and
checks observation scope and inference counts without running OCR. This is a
deterministic producer-side integrity check, not a transcription correctness
score or independent human review. Candidate text revisions remain a separate
private source-review artifact. Raw OCR must never be overwritten by a cleaned
transcript. A worked solution absent from the source must remain unknown.

The shared OCR capture JSON loader also rejects duplicate object keys at every
depth, non-finite constants and overflowing floats. Business success requires
`type(code) is int and code == 0`; booleans and floating-point zero are not an
integer success code. Valid object key order, finite numbers, strings and large
integer IDs are preserved.

Synthetic verification (no real business content, models, browser or account):

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s tests -p test_source_region_ocr.py -v
python -m unittest discover -s tests -p test_usense_ocr_candidates.py -v
```

Real sources, source text, source review, figures, native responses and candidate
bundles stay outside Git. This is an OCR-layer facility, not a public contract,
new-question write plan, directory migration, or business acceptance.
