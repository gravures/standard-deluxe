"""
This type stub file was generated by pyright.
"""

import contextlib
import functools
import getpass
import os
import re
import stat
import sys
import sysconfig
import time
import types
import unittest
import warnings
from .testresult import get_test_runner
from _testcapi import unicode_legacy_string

"""Supporting definitions for the Python regression tests."""
if __name__ != 'test.support':
    ...
__all__ = ["PIPE_MAX_SIZE", "verbose", "max_memuse", "use_resources", "failfast", "Error", "TestFailed", "TestDidNotRun", "ResourceDenied", "record_original_stdout", "get_original_stdout", "captured_stdout", "captured_stdin", "captured_stderr", "is_resource_enabled", "requires", "requires_freebsd_version", "requires_linux_version", "requires_mac_ver", "check_syntax_error", "BasicTestRunner", "run_unittest", "run_doctest", "requires_gzip", "requires_bz2", "requires_lzma", "bigmemtest", "bigaddrspacetest", "cpython_only", "get_attribute", "requires_IEEE_754", "requires_zlib", "has_fork_support", "requires_fork", "has_subprocess_support", "requires_subprocess", "has_socket_support", "requires_working_socket", "anticipate_failure", "load_package_tests", "detect_api_mismatch", "check__all__", "skip_if_buggy_ucrt_strfptime", "check_disallow_instantiation", "check_sanitizer", "skip_if_sanitizer", "is_jython", "is_android", "is_emscripten", "is_wasi", "check_impl_detail", "unix_shell", "setswitchinterval", "open_urlresource", "reap_children", "run_with_locale", "swap_item", "findfile", "infinite_recursion", "swap_attr", "Matcher", "set_memlimit", "SuppressCrashReport", "sortdict", "run_with_tz", "PGO", "missing_compiler_executable", "ALWAYS_EQ", "NEVER_EQ", "LARGEST", "SMALLEST", "LOOPBACK_TIMEOUT", "INTERNET_TIMEOUT", "SHORT_TIMEOUT", "LONG_TIMEOUT"]
LOOPBACK_TIMEOUT = ...
if sys.platform == 'win32' and ' 32 bit (ARM)' in sys.version:
    LOOPBACK_TIMEOUT = ...
else:
    LOOPBACK_TIMEOUT = ...
INTERNET_TIMEOUT = ...
SHORT_TIMEOUT = ...
LONG_TIMEOUT = ...
TEST_SUPPORT_DIR = ...
TEST_HOME_DIR = ...
STDLIB_DIR = ...
REPO_ROOT = ...
class Error(Exception):
    """Base class for regression test exceptions."""
    ...


class TestFailed(Error):
    """Test failed."""
    ...


class TestFailedWithDetails(TestFailed):
    """Test failed."""
    def __init__(self, msg, errors, failures) -> None:
        ...

    def __str__(self) -> str:
        ...



class TestDidNotRun(Error):
    """Test did not run any subtests."""
    ...


class ResourceDenied(unittest.SkipTest):
    """Test skipped because it requested a disallowed resource.

    This is raised when a test calls requires() for a resource that
    has not be enabled.  It is used to distinguish between expected
    and unexpected skips.
    """
    ...


def anticipate_failure(condition): # -> Callable[..., _FT] | Callable[..., Any]:
    """Decorator to mark a test that is known to be broken in some cases

       Any use of this decorator should have a comment identifying the
       associated tracker issue.
    """
    ...

def load_package_tests(pkg_dir, loader, standard_tests, pattern):
    """Generic load_tests implementation for simple test packages.

    Most packages can implement load_tests using this function as follows:

       def load_tests(*args):
           return load_package_tests(os.path.dirname(__file__), *args)
    """
    ...

def get_attribute(obj, name): # -> Any:
    """Get an attribute, raising SkipTest if AttributeError is raised."""
    ...

verbose = ...
use_resources = ...
max_memuse = ...
real_max_memuse = ...
junit_xml_list = ...
failfast = ...
_original_stdout = ...
def record_original_stdout(stdout): # -> None:
    ...

def get_original_stdout(): # -> TextIO:
    ...

def is_resource_enabled(resource): # -> Literal[True]:
    """Test whether a resource is enabled.

    Known resources are set by regrtest.py.  If not running under regrtest.py,
    all resources are assumed enabled unless use_resources has been set.
    """
    ...

def requires(resource, msg=...): # -> None:
    """Raise ResourceDenied if the specified resource is not available."""
    ...

def requires_freebsd_version(*min_version): # -> Callable[[_FT], _FT]:
    """Decorator raising SkipTest if the OS is FreeBSD and the FreeBSD version is
    less than `min_version`.

    For example, @requires_freebsd_version(7, 2) raises SkipTest if the FreeBSD
    version is less than 7.2.
    """
    ...

def requires_linux_version(*min_version): # -> Callable[[_FT], _FT]:
    """Decorator raising SkipTest if the OS is Linux and the Linux version is
    less than `min_version`.

    For example, @requires_linux_version(2, 6, 32) raises SkipTest if the Linux
    version is less than 2.6.32.
    """
    ...

def requires_mac_ver(*min_version): # -> Callable[..., _Wrapped[Callable[..., Any], Any, Callable[..., Any], Any]]:
    """Decorator raising SkipTest if the OS is Mac OS X and the OS X
    version if less than min_version.

    For example, @requires_mac_ver(10, 5) raises SkipTest if the OS X version
    is lesser than 10.5.
    """
    ...

def skip_if_buildbot(reason=...): # -> Callable[[_FT], _FT]:
    """Decorator raising SkipTest if running on a buildbot."""
    ...

def check_sanitizer(*, address=..., memory=..., ub=...): # -> bool:
    """Returns True if Python is compiled with sanitizer support"""
    ...

def skip_if_sanitizer(reason=..., *, address=..., memory=..., ub=...): # -> Callable[[_FT], _FT]:
    """Decorator raising SkipTest if running with a sanitizer active."""
    ...

def system_must_validate_cert(f): # -> _Wrapped[Callable[..., Any], Any, Callable[..., Any], None]:
    """Skip the test on TLS certificate validation failures."""
    ...

PIPE_MAX_SIZE = ...
SOCK_MAX_SIZE = ...
requires_IEEE_754 = ...
def requires_zlib(reason=...): # -> Callable[[_FT], _FT]:
    ...

def requires_gzip(reason=...): # -> Callable[[_FT], _FT]:
    ...

def requires_bz2(reason=...): # -> Callable[[_FT], _FT]:
    ...

def requires_lzma(reason=...): # -> Callable[[_FT], _FT]:
    ...

def has_no_debug_ranges(): # -> bool:
    ...

def requires_debug_ranges(reason=...): # -> Callable[[_FT], _FT]:
    ...

requires_legacy_unicode_capi = ...
is_jython = ...
is_android = ...
if sys.platform not in ('win32', 'vxworks'):
    unix_shell = ...
else:
    unix_shell = ...
is_emscripten = ...
is_wasi = ...
has_fork_support = ...
def requires_fork(): # -> Callable[[_FT], _FT]:
    ...

has_subprocess_support = ...
def requires_subprocess(): # -> Callable[[_FT], _FT]:
    """Used for subprocess, os.spawn calls, fd inheritance"""
    ...

has_socket_support = ...
def requires_working_socket(*, module=...): # -> Callable[[_FT], _FT] | None:
    """Skip tests or modules that require working sockets

    Can be used as a function/class decorator or to skip an entire module.
    """
    ...

has_strftime_extensions = ...
if sys.platform != "win32":
    has_strftime_extensions = ...
TEST_HTTP_URL = ...
PGO = ...
PGO_EXTENDED = ...
TEST_DATA_DIR = ...
def darwin_malloc_err_warning(test_name): # -> None:
    """Assure user that loud errors generated by macOS libc's malloc are
    expected."""
    ...

def findfile(filename, subdir=...): # -> str:
    """Try to find a file on sys.path or in the test directory.  If it is not
    found the argument passed to the function is returned (this does not
    necessarily signal failure; could still be the legitimate path).

    Setting *subdir* indicates a relative path to use to find the file
    rather than looking directly in the path directories.
    """
    ...

def sortdict(dict): # -> LiteralString:
    "Like repr(dict), but in sorted order."
    ...

def check_syntax_error(testcase, statement, errtext=..., *, lineno=..., offset=...): # -> None:
    ...

def open_urlresource(url, *args, **kw):
    ...

@contextlib.contextmanager
def captured_output(stream_name): # -> Generator[Any, Any, None]:
    """Return a context manager used by captured_stdout/stdin/stderr
    that temporarily replaces the sys stream *stream_name* with a StringIO."""
    ...

def captured_stdout(): # -> _GeneratorContextManager[Any]:
    """Capture the output of sys.stdout:

       with captured_stdout() as stdout:
           print("hello")
       self.assertEqual(stdout.getvalue(), "hello\\n")
    """
    ...

def captured_stderr(): # -> _GeneratorContextManager[Any]:
    """Capture the output of sys.stderr:

       with captured_stderr() as stderr:
           print("hello", file=sys.stderr)
       self.assertEqual(stderr.getvalue(), "hello\\n")
    """
    ...

def captured_stdin(): # -> _GeneratorContextManager[Any]:
    """Capture the input to sys.stdin:

       with captured_stdin() as stdin:
           stdin.write('hello\\n')
           stdin.seek(0)
           # call test code that consumes from sys.stdin
           captured = input()
       self.assertEqual(captured, "hello")
    """
    ...

def gc_collect(): # -> None:
    """Force as many objects as possible to be collected.

    In non-CPython implementations of Python, this is needed because timely
    deallocation is not guaranteed by the garbage collector.  (Even in CPython
    this can be the case in case of reference cycles.)  This means that __del__
    methods may be called later than expected and weakrefs may remain alive for
    longer than expected.  This function tries its best to force all garbage
    objects to disappear.
    """
    ...

@contextlib.contextmanager
def disable_gc(): # -> Generator[None, Any, None]:
    ...

def python_is_optimized(): # -> bool:
    """Find if Python was built with optimizations."""
    ...

_header = ...
_align = ...
if hasattr(sys, "getobjects"):
    _header = ...
    _align = ...
_vheader = ...
def calcobjsize(fmt): # -> int:
    ...

def calcvobjsize(fmt): # -> int:
    ...

_TPFLAGS_HAVE_GC = ...
_TPFLAGS_HEAPTYPE = ...
def check_sizeof(test, o, size): # -> None:
    ...

@contextlib.contextmanager
def run_with_locale(catstr, *locales): # -> Generator[None, Any, None]:
    ...

def run_with_tz(tz): # -> Callable[..., Callable[..., Any]]:
    ...

_1M = ...
_1G = ...
_2G = ...
_4G = ...
MAX_Py_ssize_t = ...
def set_memlimit(limit): # -> None:
    ...

class _MemoryWatchdog:
    """An object which periodically watches the process' memory consumption
    and prints it out.
    """
    def __init__(self) -> None:
        ...

    def start(self): # -> None:
        ...

    def stop(self): # -> None:
        ...



def bigmemtest(size, memuse, dry_run=...): # -> Callable[..., Callable[..., Any]]:
    """Decorator for bigmem tests.

    'size' is a requested size for the test (in arbitrary, test-interpreted
    units.) 'memuse' is the number of bytes per unit for the test, or a good
    estimate of it. For example, a test that needs two byte buffers, of 4 GiB
    each, could be decorated with @bigmemtest(size=_4G, memuse=2).

    The 'size' argument is normally passed to the decorated test method as an
    extra argument. If 'dry_run' is true, the value passed to the test method
    may be less than the requested value. If 'dry_run' is false, it means the
    test doesn't support dummy runs when -M is not specified.
    """
    ...

def bigaddrspacetest(f): # -> Callable[..., Any]:
    """Decorator for tests that fill the address space."""
    ...

class BasicTestRunner:
    def run(self, test): # -> TestResult:
        ...



def requires_resource(resource): # -> Callable[[_FT], _FT] | Callable[..., Any]:
    ...

def cpython_only(test):
    """
    Decorator for tests only applicable on CPython.
    """
    ...

def impl_detail(msg=..., **guards): # -> Callable[..., Any] | Callable[[_FT], _FT]:
    ...

def check_impl_detail(**guards): # -> bool:
    """This function returns True or False depending on the host platform.
       Examples:
          if check_impl_detail():               # only on CPython (default)
          if check_impl_detail(jython=True):    # only on Jython
          if check_impl_detail(cpython=False):  # everywhere except on CPython
    """
    ...

def no_tracing(func): # -> _Wrapped[Callable[..., Any], Any, Callable[..., Any], Any]:
    """Decorator to temporarily turn off tracing for the duration of a test."""
    ...

def refcount_test(test): # -> _Wrapped[Callable[..., Any], Any, Callable[..., Any], Any]:
    """Decorator for tests which involve reference counting.

    To start, the decorator does not run the test if is not run by CPython.
    After that, any trace function is unset during the test to prevent
    unexpected refcounts caused by the trace function.

    """
    ...

_match_test_func = ...
_accept_test_patterns = ...
_ignore_test_patterns = ...
def match_test(test): # -> bool:
    ...

def set_match_tests(accept_patterns=..., ignore_patterns=...): # -> None:
    ...

def run_unittest(*classes): # -> None:
    """Run tests from unittest.TestCase-derived classes."""
    ...

MISSING_C_DOCSTRINGS = ...
HAVE_DOCSTRINGS = ...
requires_docstrings = ...
def run_doctest(module, verbosity=..., optionflags=...): # -> tuple[Literal[0], int]:
    """Run doctest on the given module.  Return (#failures, #tests).

    If optional argument verbosity is not specified (or is None), pass
    support's belief about verbosity on to doctest.  Else doctest's
    usual behavior is used (it searches sys.argv for -v).
    """
    ...

def flush_std_streams(): # -> None:
    ...

def print_warning(msg): # -> None:
    ...

environment_altered = ...
def reap_children(): # -> None:
    """Use this function at the end of test_main() whenever sub-processes
    are started.  This will help ensure that no extra children (zombies)
    stick around to hog resources and create problems when looking
    for refleaks.
    """
    ...

@contextlib.contextmanager
def swap_attr(obj, attr, new_val): # -> Generator[Any | None, Any, None]:
    """Temporary swap out an attribute with a new object.

    Usage:
        with swap_attr(obj, "attr", 5):
            ...

        This will set obj.attr to 5 for the duration of the with: block,
        restoring the old value at the end of the block. If `attr` doesn't
        exist on `obj`, it will be created and then deleted at the end of the
        block.

        The old value (or None if it doesn't exist) will be assigned to the
        target of the "as" clause, if there is one.
    """
    ...

@contextlib.contextmanager
def swap_item(obj, item, new_val): # -> Generator[Any | None, Any, None]:
    """Temporary swap out an item with a new object.

    Usage:
        with swap_item(obj, "item", 5):
            ...

        This will set obj["item"] to 5 for the duration of the with: block,
        restoring the old value at the end of the block. If `item` doesn't
        exist on `obj`, it will be created and then deleted at the end of the
        block.

        The old value (or None if it doesn't exist) will be assigned to the
        target of the "as" clause, if there is one.
    """
    ...

def args_from_interpreter_flags():
    """Return a list of command-line arguments reproducing the current
    settings in sys.flags and sys.warnoptions."""
    ...

def optim_args_from_interpreter_flags():
    """Return a list of command-line arguments reproducing the current
    optimization settings in sys.flags."""
    ...

class Matcher:
    _partial_matches = ...
    def matches(self, d, **kwargs): # -> bool:
        """
        Try to match a single dict with the supplied arguments.

        Keys whose values are strings and which are in self._partial_matches
        will be checked for partial (i.e. substring) matches. You can extend
        this scheme to (for example) do regular expression matching, etc.
        """
        ...

    def match_value(self, k, dv, v): # -> bool:
        """
        Try to match a single stored value (dv) with a supplied value (v).
        """
        ...



_buggy_ucrt = ...
def skip_if_buggy_ucrt_strfptime(test):
    """
    Skip decorator for tests that use buggy strptime/strftime

    If the UCRT bugs are present time.localtime().tm_zone will be
    an empty string, otherwise we assume the UCRT bugs are fixed

    See bpo-37552 [Windows] strptime/strftime return invalid
    results with UCRT version 17763.615
    """
    ...

class PythonSymlink:
    """Creates a symlink for the current Python executable"""
    def __init__(self, link=...) -> None:
        ...

    if sys.platform == "win32":
        ...
    else:
        ...
    def __enter__(self): # -> Self:
        ...

    def __exit__(self, exc_type, exc_value, exc_tb): # -> None:
        ...

    def call_real(self, *args, returncode=...): # -> tuple[bytes, bytes]:
        ...

    def call_link(self, *args, returncode=...): # -> tuple[bytes, bytes]:
        ...



def skip_if_pgo_task(test):
    """Skip decorator for tests not run in (non-extended) PGO task"""
    ...

def detect_api_mismatch(ref_api, other_api, *, ignore=...): # -> set[str]:
    """Returns the set of items in ref_api not in other_api, except for a
    defined list of items to be ignored in this check.

    By default this skips private attributes beginning with '_' but
    includes all magic methods, i.e. those starting and ending in '__'.
    """
    ...

def check__all__(test_case, module, name_of_module=..., extra=..., not_exported=...): # -> None:
    """Assert that the __all__ variable of 'module' contains all public names.

    The module's public names (its API) are detected automatically based on
    whether they match the public name convention and were defined in
    'module'.

    The 'name_of_module' argument can specify (as a string or tuple thereof)
    what module(s) an API could be defined in in order to be detected as a
    public API. One case for this is when 'module' imports part of its public
    API from other modules, possibly a C backend (like 'csv' and its '_csv').

    The 'extra' argument can be a set of names that wouldn't otherwise be
    automatically detected as "public", like objects without a proper
    '__module__' attribute. If provided, it will be added to the
    automatically detected ones.

    The 'not_exported' argument can be a set of names that must not be treated
    as part of the public API even though their names indicate otherwise.

    Usage:
        import bar
        import foo
        import unittest
        from test import support

        class MiscTestCase(unittest.TestCase):
            def test__all__(self):
                support.check__all__(self, foo)

        class OtherTestCase(unittest.TestCase):
            def test__all__(self):
                extra = {'BAR_CONST', 'FOO_CONST'}
                not_exported = {'baz'}  # Undocumented name.
                # bar imports part of its API from _bar.
                support.check__all__(self, bar, ('bar', '_bar'),
                                     extra=extra, not_exported=not_exported)

    """
    ...

def suppress_msvcrt_asserts(verbose=...): # -> None:
    ...

class SuppressCrashReport:
    """Try to prevent a crash report from popping up.

    On Windows, don't display the Windows Error Reporting dialog.  On UNIX,
    disable the creation of coredump file.
    """
    old_value = ...
    old_modes = ...
    def __enter__(self): # -> Self | None:
        """On Windows, disable Windows Error Reporting dialogs using
        SetErrorMode() and CrtSetReportMode().

        On UNIX, try to save the previous core file size limit, then set
        soft limit to 0.
        """
        ...

    def __exit__(self, *ignore_exc): # -> None:
        """Restore Windows ErrorMode or core file behavior to initial value."""
        ...



def patch(test_instance, object_to_patch, attr_name, new_value): # -> None:
    """Override 'object_to_patch'.'attr_name' with 'new_value'.

    Also, add a cleanup procedure to 'test_instance' to restore
    'object_to_patch' value for 'attr_name'.
    The 'attr_name' should be a valid attribute for 'object_to_patch'.

    """
    ...

@contextlib.contextmanager
def patch_list(orig): # -> Generator[None, Any, None]:
    """Like unittest.mock.patch.dict, but for lists."""
    ...

def run_in_subinterp(code):
    """
    Run code in a subinterpreter. Raise unittest.SkipTest if the tracemalloc
    module is enabled.
    """
    ...

def check_free_after_iterating(test, iter, cls, args=...): # -> None:
    class A(cls):
        ...



def missing_compiler_executable(cmd_names=...): # -> Any | Literal['msvc'] | None:
    """Check if the compiler components used to build the interpreter exist.

    Check for the existence of the compiler executables whose names are listed
    in 'cmd_names' or all the compiler executables when 'cmd_names' is empty
    and return the first missing executable or None when none is found
    missing.

    """
    ...

_is_android_emulator = ...
def setswitchinterval(interval): # -> None:
    ...

@contextlib.contextmanager
def disable_faulthandler(): # -> Generator[None, Any, None]:
    ...

class SaveSignals:
    """
    Save and restore signal handlers.

    This class is only able to save/restore signal handlers registered
    by the Python signal module: see bpo-13285 for "external" signal
    handlers.
    """
    def __init__(self) -> None:
        ...

    def save(self): # -> None:
        ...

    def restore(self): # -> None:
        ...



def with_pymalloc():
    ...

class _ALWAYS_EQ:
    """
    Object that is equal to anything.
    """
    def __eq__(self, other) -> bool:
        ...

    def __ne__(self, other) -> bool:
        ...



ALWAYS_EQ = ...
class _NEVER_EQ:
    """
    Object that is not equal to anything.
    """
    def __eq__(self, other) -> bool:
        ...

    def __ne__(self, other) -> bool:
        ...

    def __hash__(self) -> int:
        ...



NEVER_EQ = ...
@functools.total_ordering
class _LARGEST:
    """
    Object that is greater than anything (except itself).
    """
    def __eq__(self, other) -> bool:
        ...

    def __lt__(self, other) -> bool:
        ...



LARGEST = ...
@functools.total_ordering
class _SMALLEST:
    """
    Object that is less than anything (except itself).
    """
    def __eq__(self, other) -> bool:
        ...

    def __gt__(self, other) -> bool:
        ...



SMALLEST = ...
def maybe_get_event_loop_policy():
    """Return the global event loop policy if one is set, else return None."""
    ...

NHASHBITS = ...
def collision_stats(nbins, nballs): # -> tuple[float, float]:
    ...

class catch_unraisable_exception:
    """
    Context manager catching unraisable exception using sys.unraisablehook.

    Storing the exception value (cm.unraisable.exc_value) creates a reference
    cycle. The reference cycle is broken explicitly when the context manager
    exits.

    Storing the object (cm.unraisable.object) can resurrect it if it is set to
    an object which is being finalized. Exiting the context manager clears the
    stored object.

    Usage:

        with support.catch_unraisable_exception() as cm:
            # code creating an "unraisable exception"
            ...

            # check the unraisable exception: use cm.unraisable
            ...

        # cm.unraisable attribute no longer exists at this point
        # (to break a reference cycle)
    """
    def __init__(self) -> None:
        ...

    def __enter__(self): # -> Self:
        ...

    def __exit__(self, *exc_info): # -> None:
        ...



def wait_process(pid, *, exitcode, timeout=...): # -> None:
    """
    Wait until process pid completes and check that the process exit code is
    exitcode.

    Raise an AssertionError if the process exit code is not equal to exitcode.

    If the process runs longer than timeout seconds (LONG_TIMEOUT by default),
    kill the process (if signal.SIGKILL is available) and raise an
    AssertionError. The timeout feature is not available on Windows.
    """
    ...

def skip_if_broken_multiprocessing_synchronize(): # -> None:
    """
    Skip tests if the multiprocessing.synchronize module is missing, if there
    is no available semaphore implementation, or if creating a lock raises an
    OSError (on Linux only).
    """
    ...

def check_disallow_instantiation(testcase, tp, *args, **kwds): # -> None:
    """
    Check that given type cannot be instantiated using *args and **kwds.

    See bpo-43916: Add Py_TPFLAGS_DISALLOW_INSTANTIATION type flag.
    """
    ...

@contextlib.contextmanager
def infinite_recursion(max_depth=...): # -> Generator[None, Any, None]:
    """Set a lower limit for tests that interact with infinite recursions
    (e.g test_ast.ASTHelpers_Test.test_recursion_direct) since on some
    debug windows builds, due to not enough functions being inlined the
    stack size might not handle the default recursion limit (1000). See
    bpo-11105 for details."""
    ...

def ignore_deprecations_from(module: str, *, like: str) -> object:
    ...

def clear_ignored_deprecations(*tokens: object) -> None:
    ...

def requires_venv_with_pip(): # -> Callable[[_FT], _FT]:
    ...

@contextlib.contextmanager
def adjust_int_max_str_digits(max_digits): # -> Generator[None, Any, None]:
    """Temporarily change the integer string conversion length limit."""
    ...
