"""A04 bounded read-only platform view; no platform actions are exposed."""

from .snapshot import SnapshotError, build_snapshot, snapshot_evidence
from .coordinates import ViewerMapping, CoordinateError, binding_from_file, check_reference_points

__all__ = ["SnapshotError", "build_snapshot", "snapshot_evidence", "ViewerMapping",
           "CoordinateError", "binding_from_file", "check_reference_points"]
