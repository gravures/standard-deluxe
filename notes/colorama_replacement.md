# Replacing colorama with a Native `just_fix_windows_console()` Implementation

## Problem Summary

The `deluxe.console.ansi` module currently depends on `colorama` at import time
to enable ANSI escape sequence support on Windows. This creates an optional
dependency that must be conditionally imported and warned about, adding complexity
and a runtime dependency. We can replace this with a self-contained implementation
that uses only `ctypes` (stdlib) to enable Windows' native VT processing.

## What `colorama.just_fix_windows_console()` Actually Does

The function has a single purpose: **make ANSI escape sequences work on Windows
console**. It does this through a two-tier strategy:

### Tier 1: Modern Windows 10+ (Primary Path)

On Windows 10 version 1511 (build 10586) and later, the Windows console has
built-in VT100/ANSI escape sequence support, but it's **disabled by default**.
The fix is a single Win32 API call:

```
SetConsoleMode(handle, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
```

Where `ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004`. This is the flag that
tells the console to interpret ANSI escape sequences natively instead of
printing them as garbage characters.

### Tier 2: Legacy Windows (Fallback Path)

On older Windows versions (pre-10586), VT processing doesn't exist. In this
case, `colorama` wraps `sys.stdout`/`sys.stderr` in proxy objects that:

1. Intercept `.write()` calls
2. Parse ANSI escape sequences via regex
3. Convert them to Win32 API calls (`SetConsoleTextAttribute`, etc.)
4. Write plain text to the original stream

This fallback is complex, heavy, and rarely needed in 2025+.

## The Core Implementation We Need

The entire "modern Windows" fix is ~25 lines of code:

```python
import ctypes
import sys

# Win32 constants
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004


def _enable_vt_processing(fd: int) -> bool:
    """Enable VT100 processing on a Windows console file descriptor.

    Args:
        fd: The file descriptor (e.g., from stream.fileno()).

    Returns:
        True if VT processing was successfully enabled, False otherwise.
    """
    if sys.platform != "win32":
        return True  # Non-Windows doesn't need this

    try:
        # Get the console handle from the file descriptor
        kernel32 = ctypes.windll.kernel32
        handle = kernel32._get_osfhandle(fd)  # msvcrt function
    except (OSError, ValueError, AttributeError):
        return False

    try:
        # Get current mode
        mode = ctypes.wintypes.DWORD()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False

        # Enable VT processing
        new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        if not kernel32.SetConsoleMode(handle, new_mode):
            return False

        # Verify it actually took effect
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False

        return bool(mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except (OSError, AttributeError):
        return False


def fix_windows_console() -> None:
    """Enable ANSI escape sequence support on Windows console.

    On modern Windows (10+), this enables the built-in VT processing.
    On non-Windows platforms, this is a no-op.

    Safe to call multiple times. Safe to call on non-Windows.
    """
    if sys.platform != "win32":
        return

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            fd = stream.fileno()
        except (UnsupportedOperation, ValueError, AttributeError):
            continue
        _enable_vt_processing(fd)
```

## The Full Replacement for Our Import Block

Replace lines 130–139 of `src/deluxe/console/ansi.py`:

```python
# BEFORE (current code):
if sys.platform in {"win32", "cygwin"}:  # pragma: win32 cover
    if importlib.util.find_spec("colorama"):
        colorama = importlib.import_module("colorama")
        colorama.just_fix_windows_console()
    else:
        msg: str = (
            "colorama module is required on windows platform"
            "to make use of ansi escape sequences.\n"
        )
        warn(msg, stacklevel=1)


# AFTER (replacement):
if sys.platform in {"win32", "cygwin"}:  # pragma: win32 cover
    _fix_windows_console()


def _fix_windows_console() -> None:
    """Enable native ANSI/VT100 processing on Windows console.

    On Windows 10+, the console supports ANSI escape sequences natively
    but the feature is disabled by default. This function enables it by
    setting the ENABLE_VIRTUAL_TERMINAL_PROCESSING flag via the Win32 API.

    On older Windows or non-Windows platforms, this is a no-op.

    This eliminates the need for colorama as a dependency.
    """
    try:
        import ctypes
        import ctypes.wintypes
    except ImportError:
        return

    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

    kernel32 = ctypes.windll.kernel32
    msvcrt = ctypes.CDLL("msvcrt")

    for handle_id in (-11, -12):  # STDOUT, STDERR
        try:
            handle = kernel32.GetStdHandle(handle_id)
            if handle == -1:  # INVALID_HANDLE_VALUE
                continue

            mode = ctypes.wintypes.DWORD()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                continue

            if mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING:
                continue  # Already enabled

            if kernel32.SetConsoleMode(
                handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            ):
                # Verify it took effect
                kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                # VT processing is now enabled
        except (OSError, AttributeError):
            continue
```

## Why Not the Full Colorama Replacement (Tier 2)?

The "legacy Windows" fallback path in colorama is:

1. **~300 lines of code** — Win32 API wrappers, ANSI regex parsing, cursor
   management, screen erasure emulation, title setting via `SetConsoleTitleW`.

2. **Wraps `sys.stdout`/`sys.stderr`** — This is fragile. Multiple libraries
   wrapping the same stream causes "double-wrapping" bugs. Colorama's own
   `just_fix_windows_console()` was created specifically to avoid this.

3. **Unnecessary for modern targets** — Windows 10 build 10586 was released in
   November 2015. Any actively supported Windows version has native VT support.

4. **We only use SGR (m), ED (J), EL (K), and OSC sequences** — Our module
   generates these for styling, clearing, and titles. All are natively supported
   once VT processing is enabled.

**Recommendation**: Drop the legacy fallback entirely. Log a warning if VT
processing can't be enabled (old Windows or piped output), but don't try to
emulate ANSI via Win32 calls.

## Trade-offs

| Aspect | colorama | Our Implementation |
|--------|----------|-------------------|
| Dependencies | `colorama` (optional) | `ctypes` (stdlib only) |
| Lines of code | ~300 (full) / ~20 (just_fix) | ~30 |
| Legacy Windows | Full emulation | Not supported (warning only) |
| Stream wrapping | Yes (can cause double-wrap) | No (modifies console mode directly) |
| Portability | Cross-platform (no-op on Unix) | Cross-platform (no-op on Unix) |
| Maintenance | Upstream dependency | Self-contained |
| `SetConsoleTitle` | Supported via Win32 | Supported natively via OSC |

## What We Lose Without Colorama

The only functionality we'd lose (that we currently use):

1. **`SetConsoleTitle` via Win32** — Not needed. Our `set_title()` uses OSC
   sequences which work natively once VT processing is enabled.

2. **ANSI-to-Win32 conversion for old Windows** — Not needed for any supported
   Windows version.

3. **Stream wrapping / stripping** — We don't want this anyway. It causes
   problems with other libraries.

## Potential Issues to Watch For

1. **Piped output**: When stdout/stderr is redirected to a file or pipe (not a
   console), `GetConsoleMode` will fail. This is expected — ANSI codes will
   appear as raw escape sequences in piped output. This is the same behavior
   as on Linux/macOS.

2. **Cygwin/MSYS2**: These environments may or may not have a real Windows
   console. `GetConsoleMode` will fail on pseudo-terminals. The ANSI codes
   should work anyway since these terminals support VT natively.

3. **IDLE / GUI terminals**: Python's IDLE, Tkinter, or other GUI-based
   terminals may not have a console handle. The function should silently
   skip these.

4. **pytest on Windows CI**: Tests running in CI may not have a real console.
   The function should be a no-op, and tests should mock/patch as needed.

## Implementation Steps

1. Add `_fix_windows_console()` function to `src/deluxe/console/ansi.py`
2. Replace the colorama import block with a call to `_fix_windows_console()`
3. Remove `colorama` from `pyproject.toml` optional dependencies
4. Update the module docstring to reflect no external dependency
5. Add a test that mocks `ctypes.windll` to verify the function works
6. Verify on Windows CI (GitHub Actions `windows-latest`)

## Estimated Effort

- Implementation: ~30 minutes
- Testing / CI verification: ~1-2 hours
- Removing colorama from dependency metadata: ~15 minutes
