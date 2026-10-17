# A04 source parser fixture

Every value and image here is **SYNTHETIC**. This is an offline response-shape and reference fixture, not a current platform observation, not copied book content, and not geometry or content acceptance.

`capture.json` distinguishes viewer pages 14/15/173 from source indices 13/14/172. Two directories each contain printed question 1 and platform order 1, with different stable question-node identities. Four annotation records include one unacquired page; only three originals exist. Metadata reports 214 pages and must never become an acquired-page count.

Run from the repository root:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_a04_source*.py' -v
```

Tests explicitly use the fixture observation timestamp as their comparison clock. Real callers use the current clock and the default 300-second maximum age. All error messages omit response values, URLs and credentials. A source history resource is generated in a temporary output bundle, never into this immutable fixture directory.
