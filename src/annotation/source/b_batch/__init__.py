"""Fixed A08 stage-package diagnostics. No execution artifacts are constructed."""

from .reader import BatchReceptionError, receive_package

__all__ = ["BatchReceptionError", "receive_package"]
