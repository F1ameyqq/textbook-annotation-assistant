"""Errors shared by the explicit read-only A03 codec."""
from ..validation import ContractError


class StaticCodecError(ContractError):
    """A code/path error; never an execution or retry instruction."""

    def __init__(self, code, path, message=None):
        self.code = code
        self.path = path
        super().__init__([{"code": code, "path": path, "message": message or code}])


def need(condition, code, path, message=None):
    if not condition:
        raise StaticCodecError(code, path, message)
