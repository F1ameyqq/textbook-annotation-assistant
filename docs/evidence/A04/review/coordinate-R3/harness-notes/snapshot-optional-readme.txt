Initial export incorrectly assumed execution/coordinate-R3/README.md existed.
git archive rejected that path before creating the test stage or running product
code. Removed only the unnecessary optional path from the export list; the
fixed report, manifest, release record, code and test inputs remain unchanged.
