"""Copy fixed helper definitions only; no historical suite is imported or run."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "a24_first_save_wire"
for name in ("fixture.py", "noio_loop.py"):
    with (HERE/name).open("xb") as handle:
        handle.write((OLD/name).read_bytes())
raw = (OLD/"test_platform.py").read_text(encoding="utf-8")
raw = raw.split("class PlatformTests(", 1)[0]
with (HERE/"browser_helpers.py").open("xb") as handle:
    handle.write(("# Fixed synthetic object definitions only; no old test class.\n"+raw).encode("utf-8"))
raw = (OLD/"run.py").read_text(encoding="utf-8").replace('pattern="test_*.py"', 'pattern="test_r1.py"')
raw = raw.replace("A24NewWire", "A24R1FocusedWire")
with (HERE/"run.py").open("xb") as handle:
    handle.write(raw.encode("utf-8"))
print("copied four helper definition files; historical tests executed: 0")
