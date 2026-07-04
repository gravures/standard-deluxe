# Daemon Class — Windows Support Analysis

## Problem Summary

The `Daemon` class in `src/deluxe/process.py` is currently restricted to POSIX
systems only (`@availability(only="posix", but="wasi")`). The implementation
relies entirely on Unix-specific OS primitives (`os.fork()`, `os.setsid()`,
`SIGTERM`/`SIGKILL`, `os.kill(pid, 0)`) that don't exist or behave differently
on Windows. Making it cross-platform requires rearchitecting the daemonization
strategy for a fundamentally different OS model.

## Current Architecture

The Daemon has three components:

- **`_RealDaemon`** — Internal mixin performing Unix double-fork daemonization.
- **`_DaemonMeta`** — Metaclass controlling daemon lifecycle, pidfile, process
  forking via `multiprocessing`.
- **`Daemon`** — Abstract base class with `start()`, `stop()`, `restart()`,
  `run()`.

## What Makes Unix Daemons Work

| Step | Unix API | Windows Equivalent |
|------|----------|-------------------|
| Double fork | `os.fork()` × 2 | Not available — Windows spawns new processes, doesn't fork |
| Detach from terminal | `os.setsid()` | `CREATE_NEW_PROCESS_GROUP` or `DETACHED_PROCESS` flag |
| Redirect stdio to /dev/null | `os.dup2(si.fileno(), ...)` + `os.devnull` | Partially available (same APIs but different semantics) |
| Check process alive | `os.kill(pid, 0)` | Need `OpenProcess()` + `WaitForSingleObject()` via ctypes |
| Send termination signal | `os.kill(pid, SIGTERM)` | `TerminateProcess()` or `GenerateConsoleCtrlEvent()` |
| Force kill | `os.kill(pid, SIGKILL)` | `TerminateProcess()` (no distinction on Windows) |
| Forking via multiprocessing | `mp.get_context("fork")` | Only `"spawn"` available on Windows |

## Additional Windows Complications

1. **No double-fork guarantee**: Unix double-fork ensures the daemon is orphaned
   and can't reacquire a controlling terminal. Windows has no concept of session
   leadership in the same way.

2. **No SIGTERM semantics**: On Windows, `signal.SIGTERM` calls
   `TerminateProcess()` immediately (hard kill). There's no graceful shutdown
   signal like Unix SIGTERM.

3. **Process lifecycle**: Windows processes are tied to the console window or job
   object. A detached process can still be killed when the user logs off unless
   it's a proper Windows Service or uses `SetProcessShutdownParameters()`.

4. **`multiprocessing` context**: The `fork` context is unavailable. Using
   `spawn` means the child process re-imports the module and re-creates state,
   which is slower and requires picklable targets.

## Alternative Approaches

### Approach 1: Detached Subprocess (Simplest)

**Strategy**: Launch the daemon as a detached `subprocess.Popen` with
`DETACHED_PROCESS` flag. The parent returns immediately. The child re-imports
the module, instantiates the real daemon, and runs it.

```python
import subprocess, sys, os
from pathlib import Path

def _spawn_daemon(script_path: Path, pidfile: Path, *args):
    """Spawn a detached daemon process on Windows."""
    creationflags = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NO_WINDOW
    )
    proc = subprocess.Popen(
        [sys.executable, str(script_path), *args],
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    pidfile.write_text(str(proc.pid))
    return proc

def _is_process_alive(pid: int) -> bool:
    """Check if a process is running on Windows."""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return False

def _terminate_process(pid: int, force: bool = False) -> bool:
    """Terminate a process on Windows."""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    PROCESS_TERMINATE = 0x0001
    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        return False
    try:
        result = kernel32.TerminateProcess(handle, 1)
        return bool(result)
    finally:
        kernel32.CloseHandle(handle)
```

**Trade-offs**:

- No `pywin32` dependency (stdlib only)
- Same public API (`Daemon` ABC with `run()`, `start()`, `stop()`, `restart()`)
- Won't survive user logoff (like Unix nohup without `disown`)
- Slightly slower startup (spawn vs fork)
- Different code path than Unix — needs platform branching

### Approach 2: Windows Service (Most Robust)

**Strategy**: Register the daemon as a proper Windows Service using `pywin32`
(`win32serviceutil`, `win32service`, `win32event`). The Service Control Manager
(SCM) handles lifecycle, auto-restart, and logon integration.

```python
import win32serviceutil
import win32service
import win32event
import servicemanager

class DaemonService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MyDaemon"
    _svc_display_name_ = "My Daemon Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ''),
        )
        self.main()

    def main(self):
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
```

**Trade-offs**:

- Survives user logoff
- Auto-start on boot
- Proper Windows integration (SCM, Event Log, etc.)
- Requires `pywin32` dependency (C extension)
- Must be *installed* as a service (not just run)
- Different lifecycle model — more complex setup
- Debugging harder (runs in SCM context)

### Approach 3: Platform-Agnostic Abstraction Layer (Cleanest)

**Strategy**: Define a `DaemonBackend` protocol/ABC with platform-specific
implementations. The public `Daemon` class delegates to the appropriate backend
based on the platform. On Unix, it uses the existing double-fork. On Windows,
it uses Approach 1 (detached subprocess).

```python
from abc import ABC, abstractmethod
from typing import Protocol

class DaemonBackend(Protocol):
    """Platform-specific daemon backend."""
    def daemonize(self, target: type, args: tuple, kwargs: dict) -> None: ...
    def is_running(self, pidfile: Path) -> bool: ...
    def stop(self, pid: int, timeout: float) -> None: ...
    def write_pidfile(self, pidfile: Path) -> None: ...
    def cleanup_pidfile(self, pidfile: Path) -> None: ...

class UnixDaemonBackend:
    """Existing double-fork implementation."""
    def daemonize(self, target, args, kwargs):
        # os.fork(), os.setsid(), etc.
        ...

class WindowsDaemonBackend:
    """Detached subprocess implementation."""
    def daemonize(self, target, args, kwargs):
        # subprocess.Popen with DETACHED_PROCESS
        ...

def get_backend() -> DaemonBackend:
    if sys.platform == "win32":
        return WindowsDaemonBackend()
    return UnixDaemonBackend()
```

**Trade-offs**:

- Same public API everywhere
- Clean separation of concerns
- Easy to add new platforms (e.g., macOS launchd, systemd)
- Testable — can mock the backend
- More code / more indirection
- Need to keep both backends in sync feature-wise

## Recommended Approach

**Approach 3** (platform-agnostic abstraction) with **Approach 1** as the
Windows backend. Reasoning:

1. Public API stays identical — users don't need to care about the platform.
2. No hard dependency on `pywin32` — detached subprocess uses only stdlib.
3. Future-proof — easy to swap in a Windows Service backend later if needed.
4. Testable — the backend protocol can be mocked for unit tests.

## Files That Would Need Changes

| File | Change |
|------|--------|
| `src/deluxe/process.py` | Add `_WindowsRealDaemon`, modify `_DaemonMeta.fork()` for Windows, change `@availability` on `Daemon` |
| `tests/process_daemon_test.py` | Add Windows-specific test cases, remove POSIX-only guards where appropriate |

## Implementation Steps

1. **Remove or change `@availability`** on `Daemon` — change to
   `but=("wasi",)` so Windows is allowed.

2. **Create `_WindowsRealDaemon`** class that:
   - Writes a bootstrap script to a temp file.
   - Launches it with `subprocess.Popen(creationflags=DETACHED_PROCESS |
     CREATE_NO_WINDOW)`.
   - The bootstrap re-imports the daemon class and calls `run()`.

3. **Modify `_DaemonMeta.fork()`**:
   ```python
   @staticmethod
   def fork(cls_: type, *args: Any, **kwds: Any) -> None:
       if sys.platform == "win32":
           _WindowsRealDaemon.spawn(cls_, *args, **kwds)
       else:
           ctx = mp.get_context("fork")
           ps = ctx.Process(target=cls_, args=args, kwargs=kwds)
           ps.start()
           ps.join()
   ```

4. **Modify `Daemon.stop()`** for Windows:
   - Replace `os.kill(pid, signal.SIGTERM)` with `TerminateProcess` via ctypes.
   - Replace `os.kill(pid, signal.SIGKILL)` with the same `TerminateProcess`.
   - Replace `os.kill(pid, 0)` with ctypes `OpenProcess` check.

5. **Modify `_RealDaemon.daemonize()`** — guard Unix-specific calls with
   `sys.platform` checks, or split into separate classes.

6. **Update tests** — add Windows-specific tests with appropriate skips.

## Estimated Effort

- Approach 1 (just get it working): ~3-4 hours
- Approach 3 (clean architecture): ~6-8 hours including tests
- Approach 2 (Windows Service): ~8-12 hours (including pywin32 integration)
