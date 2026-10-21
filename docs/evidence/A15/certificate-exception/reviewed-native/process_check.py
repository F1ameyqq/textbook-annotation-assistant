"""A10 v1: pure matching/completeness rules; no OS queries on import."""
import ntpath
import re

BROWSERS = frozenset(('msedge.exe', 'chrome.exe', 'chromium.exe', 'headless_shell.exe'))


class CheckFailure(Exception):
    """Only fixed categories, never OS text, arguments or profile paths."""


def windows_arguments(command):
    if not isinstance(command, str) or not command or '\0' in command or len(command) > 32767:
        raise CheckFailure('COMMANDLINE_INVALID')
    args, i = [], 0
    while i < len(command):
        while i < len(command) and command[i] in ' \t':
            i += 1
        if i == len(command):
            break
        item, quoted = [], False
        while i < len(command) and (quoted or command[i] not in ' \t'):
            slashes = 0
            while i < len(command) and command[i] == '\\':
                slashes += 1
                i += 1
            if i < len(command) and command[i] == '"':
                item.extend('\\' * (slashes // 2))
                if slashes % 2:
                    item.append('"')
                elif quoted and i + 1 < len(command) and command[i + 1] == '"':
                    item.append('"')
                    i += 1
                else:
                    quoted = not quoted
                i += 1
            else:
                item.extend('\\' * slashes)
                if i < len(command) and (quoted or command[i] not in ' \t'):
                    item.append(command[i])
                    i += 1
        if quoted:
            raise CheckFailure('COMMANDLINE_QUOTING')
        args.append(''.join(item))
    if not args or not args[0]:
        raise CheckFailure('COMMANDLINE_INVALID')
    return args


def normalized_profile(value):
    if not isinstance(value, str) or not value or any(ord(x) < 32 for x in value):
        raise CheckFailure('PROFILE_SYNTAX')
    path = value.replace('/', '\\')
    # Device/extended/short/variable paths have alias semantics not proved here.
    if path.startswith(('\\\\?\\', '\\\\.\\')) or re.search(r'~[0-9]', path) or '%' in path:
        raise CheckFailure('PROFILE_ALIAS_UNPROVEN')
    drive, tail = ntpath.splitdrive(path)
    if not drive or not tail.startswith('\\') or '"' in path:
        raise CheckFailure('PROFILE_NOT_ABSOLUTE')
    if any(part.endswith((' ', '.')) for part in tail.split('\\') if part not in ('', '.', '..')):
        raise CheckFailure('PROFILE_ALIAS_UNPROVEN')
    return ntpath.normcase(ntpath.normpath(path))


def matches_profile(command, profile):
    expected = normalized_profile(profile)
    args = windows_arguments(command)
    values, i = [], 1
    while i < len(args):
        arg = args[i].lower()
        if arg == '--user-data-dir':
            i += 1
            if i == len(args) or args[i].startswith('--'):
                raise CheckFailure('PROFILE_ARGUMENT_MISSING')
            values.append(args[i])
        elif arg.startswith('--user-data-dir='):
            values.append(args[i][len('--user-data-dir='):])
        i += 1
    if len(values) > 1:
        raise CheckFailure('PROFILE_ARGUMENT_DUPLICATE')
    return bool(values) and normalized_profile(values[0]) == expected


def candidates(rows):
    result, seen = {}, set()
    for pid, name in rows:
        if type(pid) is not int or pid < 0 or not isinstance(name, str) or not name or pid in seen:
            raise CheckFailure('ENUMERATION_INVALID')
        seen.add(pid)
        if name.lower() in BROWSERS:
            if pid == 0:
                raise CheckFailure('ENUMERATION_INVALID')
            result[pid] = name.lower()
    return result


def count_profile(api, profile):
    """Two complete snapshots plus retained handles; ambiguity never means zero."""
    normalized_profile(profile)
    opened, identities, count = [], {}, 0
    try:
        first = candidates(api.enumerate())
        for pid, name in first.items():
            handle = api.open(pid)
            opened.append(handle)
            identity = api.identity(handle)
            if identity[:2] != (pid, name) or type(identity[2]) is not int or identity[2] <= 0:
                raise CheckFailure('PROCESS_IDENTITY_CHANGED')
            identities[handle] = identity
            count += int(matches_profile(api.commandline(handle), profile))
            if api.identity(handle) != identity:
                raise CheckFailure('PROCESS_IDENTITY_CHANGED')
        if candidates(api.enumerate()) != first:
            raise CheckFailure('ENUMERATION_CHANGED')
        for handle, identity in identities.items():
            if api.identity(handle) != identity:
                raise CheckFailure('PROCESS_IDENTITY_CHANGED')
        return count
    except CheckFailure:
        raise
    except Exception:
        raise CheckFailure('INSPECTION_INCOMPLETE') from None
    finally:
        close_failed = False
        for handle in reversed(opened):
            try:
                api.close(handle)
            except Exception:
                close_failed = True
        if close_failed:
            raise CheckFailure('HANDLE_CLOSE_FAILED') from None
