"""Explicit-root resource reads; no repository paths or override channel."""
from pathlib import Path, PurePosixPath, PureWindowsPath

from ._errors import StaticCodecError, need
from ._json import parse_json, sha


class ResourceReader:
    def __init__(self, root):
        self.root = root
        self._raw = {}
        self.consumed = {}

    def read(self, resource):
        logical = resource["path"]
        need(type(logical) is str and logical and "\x00" not in logical, "RESOURCE_PATH", str(logical))
        # Interpret both path syntaxes on every host; drive/UNC and backslash
        # ambiguity must not turn a Windows absolute path into a POSIX name.
        posix = PurePosixPath(logical)
        windows = PureWindowsPath(logical)
        need(not posix.is_absolute() and not windows.is_absolute() and not windows.drive and "\\" not in logical and ":" not in logical, "RESOURCE_PATH", logical)
        need(all(part not in ("", ".", "..") for part in logical.split("/")), "RESOURCE_PATH", logical)
        try:
            target = (self.root / logical).resolve(strict=True)
            need(target.is_relative_to(self.root) and target.is_file(), "RESOURCE_ESCAPE", logical)
            if logical not in self._raw:
                self._raw[logical] = target.read_bytes()
        except OSError as error:
            raise StaticCodecError("RESOURCE_READ", logical, str(error)) from error
        raw = self._raw[logical]
        actual = sha(raw)
        need(actual == resource["sha256"], "RESOURCE_HASH", logical)
        self.consumed[logical] = actual
        # Parse independently for every consumer. Raw bytes alone are cached;
        # no found/declared/scope or validation result is shared.
        return parse_json(raw, logical) if resource["media_type"] == "application/json" else None
