"""A06 bounded, offline B-native diagnostic reader. Never grants execution."""
from .reader import HandoffError, ReceivedHandoff, receive_package, version_policy

__all__ = ["HandoffError", "ReceivedHandoff", "receive_package", "version_policy"]
