"""R1 source identity: never treat an enclosing repository as the source checkout."""
import hashlib
from pathlib import Path
import subprocess


def git_identity(source_root):
    root = Path(source_root).resolve()
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root, capture_output=True, text=True)
    except OSError:
        return {"checkout_commit": None, "status": "unknown; Git could not be started"}
    if result.returncode or Path(result.stdout.strip()).resolve() != root:
        return {"checkout_commit": None, "status": "unknown; source is not the Git top-level"}
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return {"checkout_commit": None, "status": "unknown; Git HEAD lookup unavailable"}
    if not head:
        return {"checkout_commit": None, "status": "unknown; Git HEAD lookup was empty"}
    return {"checkout_commit": head, "status": "source Git top-level verified"}


def source_binding(source_root, declared_commit, identity_repo):
    """Verify all production Python files against explicitly specified Git blobs.

    A raw export can be verified using an external identity repository. Its own
    checkout_commit stays unknown; a parent HEAD is never adopted as its identity.
    """
    root, repo = Path(source_root).resolve(), Path(identity_repo).resolve()
    assert git_identity(repo)["checkout_commit"] is not None, "identity repository must be an actual Git top-level"
    files = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", declared_commit, "src/annotation"], cwd=repo, text=True).splitlines()
    hashes = {}
    for relative in files:
        blob = subprocess.check_output(["git", "show", declared_commit + ":" + relative], cwd=repo)
        actual = (root / relative).read_bytes()
        assert actual == blob, "source differs from declared raw Git blob: " + relative
        hashes[relative] = hashlib.sha256(actual).hexdigest()
    assert hashes, "no production source blobs found"
    return dict(git_identity(root), declared_commit=declared_commit,
                binding_method="explicit declared commit plus raw Git blob verification",
                source_root=str(root), identity_repo=str(repo), source_sha256=hashes)
