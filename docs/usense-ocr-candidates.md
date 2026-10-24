# Offline OCR review candidates

This B-side trial works on saved source material only. It neither imports a
runtime writer nor grants platform approval. Its JSON format is private to the
OCR/candidate layer, not a change to the public contract or a writer payload.

`tools/run_usense_ocr.py` now accepts either a normal capture directory with its
original `capture-summary.json`, or a merged independent readback directory:

```powershell
python tools/run_usense_ocr.py --repo . --capture PRIVATE/after-full23 --readback-manifest PRIVATE/raw-readback-manifest.json --sources PRIVATE/sources --source-manifest PRIVATE/sources/source-binding.json --orders 18 19 20 21 22 --out PRIVATE/new-ocr-run
```

The merge manifest must be the original list of response names, run IDs and
SHA256 values. Each original run directory must remain alongside that manifest.
The reader checks each original HTTP summary and original entity bytes against
the merged file. Repeated shared responses must all match; a fabricated summary
of merged files is insufficient. No browser is opened and the existing OCR
entrypoint blocks socket connections. An output directory must be new.

Assemble the raw observations without any source revisions:

```powershell
python tools/assemble_usense_candidates.py assemble --ocr-root PRIVATE/new-ocr-run --out PRIVATE/raw-candidates
```

Without review input, semantic mapping stays `null`/`UNKNOWN`. Raw primary text,
all retained OCR variants, existing parser issues and native stable identities
remain available. MCQ parser warnings are retained even when the source item is
a fill-in or worked response; they are not a determination of question type.

To propose explicit source revisions, supply `--review PRIVATE/review.json`.
The review is a JSON object with schema `UsenseOCRSourceReview/v1`, review kind
`MODEL_VISUAL`, a `scope` object whose `complete_lesson_denominator` is null,
and an `items` list. A synthetic item looks like this:

```json
{
  "native_order": 4,
  "revisions": [{
    "field": "answer",
    "before": "raw answer",
    "after": "x² + y²",
    "reason": "Superscripts are visible on the answer source",
    "evidence": [{"viewer_page": 2, "bbox": [12, 12, 75, 75], "purpose": "Answer source"}]
  }],
  "diagrams": [{"viewer_page": 2, "bbox": [12, 12, 75, 75], "purpose": "Original diagram"}],
  "formulas": [{
    "field": "answer", "transcription": "x² + y²",
    "evidence": [{"viewer_page": 2, "bbox": [12, 12, 75, 75], "purpose": "Formula source"}]
  }]
}
```

Allowed revised fields are `question`, `choice`, and `answer`. Each revision
must name the exact original primary OCR string, its proposed replacement,
reason, and source evidence. Evidence must overlap a captured frame of this
question and role on the stated page. This is an association check, not an
automated transcription correctness test. Figures and formulas retain separate
source crops. A model observation cannot be declared a human approval here.

Optional mapping requires explicit `semantic_lesson`, `printed_number`,
`legacy_native_order`, and question `evidence`. It is a source observation only:
the captured directory ID, native order, node ID and question-info ID are kept.
Unknown mappings must not be inferred by arithmetic. Historical global sequence
numbers and local numbers printed within a lesson are different identities.

Read back the package in a new process:

```powershell
python tools/assemble_usense_candidates.py check --package PRIVATE/raw-candidates/candidates.json
```

The checker rebuilds the candidate projection from bound local inputs and
compares source crop pixels against the original image region. It rejects file
changes, stale revision predecessors, missing answer evidence, changed crops,
and attempted package approval. This is deterministic revalidation using the
same implementation, not an independent human content review. It requires the
original absolute file references to remain available on the receiving machine.
The package is not currently relocatable or directly consumable by a writer.

All packages remain `REVIEW_REQUIRED`, with `write_allowed=false` and
`human_confirmation=null`. The layer does not establish a complete lesson
denominator, migrate directories, or submit/save/review platform content.

Verification uses synthetic material only:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s tests -p test_usense_ocr_candidates.py -v
```

Private source images, native responses, real question text and review packages
must stay outside the repository. Only generic code, synthetic tests and
sanitized execution summaries belong in Git.
