"""Exclusive profile lease with redacted real-process and Chromium-lock checks.

Existing locks are evidence of a conflict, including stale locks.  This module
never deletes them or terminates browser processes.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
import secrets
import stat
import subprocess
from typing import Callable, Optional

from .guard import BrowserSafetyError


CHROMIUM_LOCKS = ("SingletonLock", "SingletonCookie", "lockfile")
LEASE_NAME = ".a04-readonly.lease"


def windows_profile_process_count(profile: Path) -> int:
    """CIM returns only a count, never a process command line or profile path.

    The profile is passed through a private child environment.  It is never
    interpolated into executable shell code or subprocess diagnostics.
    """
    if os.name != "nt":
        raise BrowserSafetyError("PROCESS_CHECK_UNAVAILABLE", "process_check")
    script = r'''
$ErrorActionPreference = 'Stop'
$profileForA04 = [IO.Path]::GetFullPath($env:USENSE_A04_PROFILE).TrimEnd('\').Replace('/', '\')
$escapedProfileForA04 = [regex]::Escape($profileForA04)
$patternForA04 = '(?i)(?:^|\s)"?--user-data-dir(?:=|\s+)"?' + $escapedProfileForA04 + '(?:"|\s|$)'
$browsersForA04 = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.Name -in @('msedge.exe', 'chrome.exe', 'chromium.exe', 'headless_shell.exe')
})
if (@($browsersForA04 | Where-Object { -not $_.CommandLine }).Count) {
    throw 'A04_PROCESS_INSPECTION_INCOMPLETE'
}
$matchedForA04 = @($browsersForA04 | Where-Object {
    $_.CommandLine.Replace('/', '\') -match $patternForA04
})
[Console]::Write($matchedForA04.Count)
'''
    child_env = dict(os.environ)
    child_env["USENSE_A04_PROFILE"] = str(profile.resolve())
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            env=child_env, capture_output=True, text=True, timeout=20, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        count = int(result.stdout.strip())
        if result.returncode != 0 or count < 0:
            raise ValueError
        return count
    except (OSError, ValueError, subprocess.SubprocessError):
        raise BrowserSafetyError("PROCESS_CHECK_FAILED", "process_check") from None


class ProfileLease:
    """One A04 owner per profile, with injected process checks for offline tests.

    ``process_checker(profile)`` returns a nonnegative process count.  Callers
    close their own browser before release; release never stops a process.
    """

    def __init__(self, profile, process_checker: Optional[Callable] = None):
        self._profile = Path(profile)
        self._checker = process_checker or windows_profile_process_count
        self._lease = self._profile / LEASE_NAME
        self._token = secrets.token_hex(24)
        self._identity = None
        self._creation_pending = False
        self._held = False
        self._report = {"acquired": False, "released": False,
                        "owned_lease_present": False, "pre": None, "post": None}

    @property
    def held(self) -> bool:
        return self._held

    def _snapshot(self) -> dict:
        try:
            count = self._checker(self._profile)
            if type(count) is not int or count < 0:
                raise ValueError
            return {"process_count": count,
                    "chromium_lock_count": sum(os.path.lexists(self._profile / name)
                                               for name in CHROMIUM_LOCKS),
                    "lease_present": os.path.lexists(self._lease)}
        except BrowserSafetyError:
            raise
        except Exception:
            raise BrowserSafetyError("PROCESS_CHECK_FAILED", "process_check") from None

    def _capture_post(self) -> None:
        """Keep cleanup evidence even when a second process check itself fails."""
        try:
            after = self._snapshot()
            self._report["post"] = after
            self._report.pop("post_error", None)
            self._report["released"] = not any((after["process_count"],
                                                   after["chromium_lock_count"],
                                                   after["lease_present"]))
        except BrowserSafetyError as exc:
            self._report["post"] = None
            self._report["post_error"] = {"code": exc.code, "stage": exc.stage}
            self._report["released"] = False

    def _owns_current_lease(self) -> bool:
        if self._identity is None:
            return False
        try:
            info = self._lease.lstat()
            if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != self._identity:
                return False
            return (self._creation_pending
                    or self._lease.read_text(encoding="ascii") == self._token)
        except (OSError, UnicodeError):
            return False

    def _remove_owned_lease(self) -> None:
        if not self._owns_current_lease():
            if self._identity is not None:
                raise BrowserSafetyError("LEASE_OWNERSHIP_LOST", "release")
            return
        try:
            self._lease.unlink()
        except OSError:
            raise BrowserSafetyError("LEASE_RELEASE_FAILED", "release") from None
        self._held = False
        self._identity = None
        self._creation_pending = False
        self._report["owned_lease_present"] = False

    @staticmethod
    def _require_idle(snapshot: dict, stage: str) -> None:
        if snapshot["process_count"]:
            raise BrowserSafetyError("PROFILE_IN_USE", stage)
        if snapshot["chromium_lock_count"]:
            raise BrowserSafetyError("PROFILE_LOCK_CONFLICT", stage)

    def acquire(self):
        if self._held:
            raise BrowserSafetyError("PROFILE_LEASE_CONFLICT", "acquire")
        try:
            self._profile.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise BrowserSafetyError("PROFILE_PATH_UNAVAILABLE", "acquire") from None
        before = self._snapshot()
        self._report["pre"] = before
        try:
            self._require_idle(before, "preflight")
        except BrowserSafetyError:
            self._capture_post()
            raise
        try:
            descriptor = os.open(self._lease, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            self._capture_post()
            raise BrowserSafetyError("PROFILE_LEASE_CONFLICT", "acquire") from None
        except OSError:
            raise BrowserSafetyError("LEASE_WRITE_FAILED", "acquire") from None
        try:
            info = os.fstat(descriptor)
            self._identity = (info.st_dev, info.st_ino)
            self._creation_pending = True
            with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                stream.write(self._token)
                stream.flush()
                os.fsync(stream.fileno())
            self._creation_pending = False
            self._held = True
            self._report["owned_lease_present"] = True
            # Recheck after the atomic lease so a newly visible foreign process
            # or Chromium lock cannot pass the first preflight observation.
            self._require_idle(self._snapshot(), "acquire")
        except Exception as exc:
            try:
                self._remove_owned_lease()
            except BrowserSafetyError:
                self._capture_post()
                raise
            self._capture_post()
            if isinstance(exc, BrowserSafetyError):
                raise exc from None
            raise BrowserSafetyError("LEASE_WRITE_FAILED", "acquire") from None
        self._report.update(acquired=True, released=False, post=None)
        return self

    def release(self) -> dict:
        try:
            self._remove_owned_lease()
        except BrowserSafetyError as exc:
            self._capture_post()
            self._report["release_error"] = {"code": exc.code, "stage": exc.stage}
            self._report["released"] = False
            raise
        self._capture_post()
        if "post_error" in self._report:
            error = self._report["post_error"]
            raise BrowserSafetyError(error["code"], error["stage"])
        if not self._report["released"]:
            raise BrowserSafetyError("PROFILE_NOT_RELEASED", "release")
        return self.report()

    def report(self) -> dict:
        result = copy.deepcopy(self._report)
        result["owned_lease_present"] = self._owns_current_lease()
        return result

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.release()
