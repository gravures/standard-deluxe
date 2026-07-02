from __future__ import annotations


import inspect
import sys
import pytest
from deluxe.availability import availability, hints, supported, AvailabilityError
from hypothesis import given, settings  # noqa: F401
from hypothesis import strategies as st  # noqa: F401


def test_hints_returns_correct_platform_hints(monkeypatch: pytest.MonkeyPatch):
    impl = sys.implementation.name

    # Test Windows platform
    monkeypatch.setattr(sys, "platform", "win32")
    assert hints() == ("nt", "win32", "windows", impl)

    # Test Darwin (macOS) platform
    monkeypatch.setattr(sys, "platform", "darwin")
    assert hints() == ("posix", "darwin", "macos", impl)

    # Test Linux platform
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("platform.freedesktop_os_release", lambda: {"ID": "ubuntu"})
    assert hints() == ("posix", "unix", "linux", "ubuntu", impl)

    # Test iOS platform
    monkeypatch.setattr(sys, "platform", "ios")
    assert hints() == ("posix", "darwin", "ios", impl, "mobile")

    # Test Android platform
    monkeypatch.setattr(sys, "platform", "android")
    assert hints() == ("posix", "linux", "android", impl, "mobile")

    # Test WASI platform
    monkeypatch.setattr(sys, "platform", "wasi")
    assert hints() == ("posix", "vm", "wasi", "wasi", impl)

    # Test Cygwin platform
    monkeypatch.setattr(sys, "platform", "cygwin")
    assert hints() == ("posix", "windows", "cygwin", impl)

    # Test generic Unix platform
    monkeypatch.setattr(sys, "platform", "freebsd")
    assert hints() == ("posix", "unix", "freebsd", impl)


def test_hints_handles_unknown_platforms(monkeypatch: pytest.MonkeyPatch):
    # Test with an unknown platform
    monkeypatch.setattr(sys, "platform", "unknown_platform")
    result = hints()

    # Check that the result follows the expected structure for unknown platforms
    assert isinstance(result, tuple)
    assert len(result) >= 3
    assert result[0] == "posix"
    assert result[1] == "unix"
    assert result[2] == "unknown_platform"

    # Test with a made-up platform name
    monkeypatch.setattr(sys, "platform", "fictional_os123")
    result = hints()
    assert result[0] == "posix"
    assert result[1] == "unix"
    assert result[2] == "fictional_os"  # Should strip numbers

    # Test with a platform name that doesn't match any specific case
    monkeypatch.setattr(sys, "platform", "solaris10")
    result = hints()
    assert result[0] == "posix"
    assert result[1] == "unix"
    assert result[2] == "solaris"
    assert sys.implementation.name in result


def test_supported_evaluates_platform_compatibility(monkeypatch: pytest.MonkeyPatch):
    # Test with various platform configurations

    # Test case 1: Platform is in 'only' list
    monkeypatch.setattr(
        "deluxe.availability.hints", lambda: ("posix", "linux", "ubuntu", "cpython")
    )
    assert supported(only="linux") is True
    assert supported(only=("linux",), but=()) is True

    # Test case 2: Platform is not in 'only' list
    assert supported(only=("darwin",), but=()) is False

    # Test case 3: Platform is in 'but' list
    assert supported(only=(), but=("linux",)) is False

    # Test case 4: Platform is not in 'but' list
    assert supported(only=None, but="darwin") is True
    assert supported(only=(), but=("darwin",)) is True

    # Test case 5: Platform is in both 'only' and 'but' lists
    assert supported(only=("linux",), but=("linux",)) is False

    # Test case 6: Empty 'only' and 'but' lists
    assert supported(only=(), but=()) is True

    # Test case 7: Case insensitivity
    assert supported(only=("LINUX",), but=()) is True
    assert supported(only=(), but=("LINUX",)) is False

    # Test case 8: Multiple hints in 'only' list (any match should return True)
    assert supported(only=("darwin", "linux", "windows"), but=()) is True

    # Test case 9: Multiple hints in 'but' list (any match should return False)
    assert supported(only=(), but=("darwin", "linux", "windows")) is False

    # Test case 10: Complex scenario with both lists
    assert supported(only=("posix", "unix"), but=("darwin",)) is True


def test_availability_decorator_allows_execution(monkeypatch: pytest.MonkeyPatch):
    # Setup: Mock the platform to be Linux
    monkeypatch.setattr(
        "deluxe.availability.hints", lambda: ("posix", "linux", "ubuntu", "cpython")
    )

    # Define a function with the availability decorator that should run on Linux
    @availability(only=("linux",), but=())
    def linux_only_function():
        return "Function executed successfully"

    # Test that the function executes normally
    assert linux_only_function() == "Function executed successfully"

    # Define a function that should not run on Linux
    @availability(only=("darwin",), but=())
    def darwin_only_function():
        return "Function executed successfully"

    # Test that the function raises AvailabilityError
    with pytest.raises(AvailabilityError) as excinfo:
        darwin_only_function()
    assert "only supported on" in str(excinfo.value)

    # Define a function that should run on all platforms except Linux
    @availability(only=(), but=("linux",))
    def not_on_linux_function():
        return "Function executed successfully"

    # Test that the function raises AvailabilityError
    with pytest.raises(AvailabilityError) as excinfo:
        not_on_linux_function()
    assert "only supported on all platforms except on" in str(excinfo.value)

    # Test with a class
    @availability(only=("linux",), but=())
    class LinuxOnlyClass:
        def method(self):  # noqa: PLR6301
            return "Method executed successfully"

    # Test that the class can be instantiated and its methods called
    instance = LinuxOnlyClass()
    assert instance.method() == "Method executed successfully"

    # Test with a class that should not be available on Linux
    @availability(only=("darwin",), but=())
    class DarwinOnlyClass:
        def method(self):  # noqa: PLR6301
            return "Method executed successfully"

    # Test that attempting to instantiate the class raises AvailabilityError
    with pytest.raises(AvailabilityError) as excinfo:
        DarwinOnlyClass()
    assert "only supported on" in str(excinfo.value)


def test_availability_decorator_raises_error(monkeypatch: pytest.MonkeyPatch):
    # Mock the platform to be Linux
    monkeypatch.setattr(
        "deluxe.availability.hints", lambda: ("posix", "linux", "ubuntu", "cpython")
    )

    # Test with a function that should only run on Windows
    @availability(only=("windows",), but=())
    def windows_only_function():
        return "Function executed successfully"

    # Test that the function raises AvailabilityError with correct message
    with pytest.raises(AvailabilityError) as excinfo:
        windows_only_function()
    assert "only supported on ('windows',)" in str(excinfo.value)
    assert "platforms" in str(excinfo.value)

    # Test with a function that should run on all platforms except Linux
    @availability(only=(), but=("linux",))
    def not_on_linux_function():
        return "Function executed successfully"

    # Test that the function raises AvailabilityError with correct message
    with pytest.raises(AvailabilityError) as excinfo:
        not_on_linux_function()
    assert "only supported on all platforms except on" in str(excinfo.value)
    assert "('linux',)" in str(excinfo.value)

    # Test with a function that should run on POSIX but not on Linux
    @availability(only=("posix",), but=("linux",))
    def posix_but_not_linux_function():
        return "Function executed successfully"

    # Test that the function raises AvailabilityError with correct message
    with pytest.raises(AvailabilityError) as excinfo:
        posix_but_not_linux_function()
    assert "only supported on ('posix',) platforms except on ('linux',)" in str(excinfo.value)

    # Test with a class that should only run on Windows
    @availability(only=("windows",), but=())
    class WindowsOnlyClass:
        def method(self):  # noqa: PLR6301
            return "Method executed successfully"

    # Test that attempting to instantiate the class raises AvailabilityError
    with pytest.raises(AvailabilityError) as excinfo:
        WindowsOnlyClass()
    assert "only supported on ('windows',)" in str(excinfo.value)


def test_availability_with_empty_parameters():
    """Test that the availability decorator works correctly
    with empty inclusion or exclusion tuples."""

    # Test with empty 'only' parameter
    @availability(only=(), but=())
    def all_platforms_function():
        return "Function runs on all platforms"

    # This should run on any platform since both 'only' and 'but' are empty
    assert all_platforms_function() == "Function runs on all platforms"

    # Test with empty 'only' parameter but non-empty 'but' parameter
    current_platform_hints = supported(only=(), but=())  # noqa: F841

    # Create a platform hint that is definitely not in the current platform
    fake_platform = "nonexistent_platform_xyz"

    @availability(only=(), but=(fake_platform,))
    def except_nonexistent_function():
        return "Function runs on all platforms except nonexistent"

    # This should run since the excluded platform doesn't exist
    assert except_nonexistent_function() == "Function runs on all platforms except nonexistent"

    # Test with non-empty 'only' parameter but empty 'but' parameter
    # We'll use a platform hint that is definitely in the current platform
    current_hints = supported(only=("posix",), but=()) or supported(only=("nt",), but=())  # noqa: F841
    platform_to_include = "posix" if supported(only=("posix",), but=()) else "nt"

    @availability(only=(platform_to_include,), but=())
    def only_current_platform_function():
        return f"Function runs only on {platform_to_include}"

    # This should run since we're including the current platform
    assert only_current_platform_function() == f"Function runs only on {platform_to_include}"

    # Test with class and empty parameters
    @availability(only=(), but=())
    class AllPlatformsClass:
        def method(self):  # noqa: PLR6301
            return "Class works on all platforms"

    # Should be able to instantiate and use the class
    instance = AllPlatformsClass()
    assert instance.method() == "Class works on all platforms"


def test_availability_preserves_function_metadata():
    """Test that the availability decorator preserves function metadata."""

    # Define a function with docstring and annotations
    def original_function(param1: str, param2: int = 42) -> str:
        """This is a test function docstring."""  # noqa: DOC201
        return f"{param1} {param2}"

    # Apply the availability decorator
    decorated_function = availability(only=(), but=())(original_function)

    # Check that the name is preserved
    assert decorated_function.__name__ == original_function.__name__

    # Check that the docstring is preserved
    assert decorated_function.__doc__ == original_function.__doc__

    # Check that the signature is preserved
    original_sig = inspect.signature(original_function)
    decorated_sig = inspect.signature(decorated_function)

    assert str(original_sig) == str(decorated_sig)

    # Check that the annotations are preserved
    assert decorated_function.__annotations__ == original_function.__annotations__

    # Check that the default values are preserved
    assert decorated_sig.parameters["param2"].default == original_sig.parameters["param2"].default

    # Check that the function can still be called with the same parameters
    assert decorated_function("test", 10) == "test 10"
    assert decorated_function("test") == "test 42"  # Default parameter works

    # Check that functools.wraps was used (module should be the same)
    assert decorated_function.__module__ == original_function.__module__


def test_availability_with_class_inheritance(monkeypatch: pytest.MonkeyPatch):
    """Test that the availability decorator works correctly with class inheritance."""

    # Mock the platform to be Linux
    monkeypatch.setattr(
        "deluxe.availability.hints", lambda: ("posix", "linux", "ubuntu", "cpython")
    )

    # Define a base class with availability decorator
    @availability(only=("linux",), but=())
    class BaseClass:
        """Docstring"""

        def method(self) -> str:  # noqa: PLR6301
            return "Base method executed"

    # Define a subclass that inherits from the base class
    class SubClass(BaseClass):
        def method(self):  # noqa: PLR6301
            return "Subclass method executed"

        def new_method(self):  # noqa: PLR6301
            return "New method executed"

    # Test that the subclass inherits the platform restrictions and can be instantiated
    instance = SubClass()
    assert instance.method() == "Subclass method executed"
    assert instance.new_method() == "New method executed"

    # Define a base class that should not be available on Linux
    @availability(only=("windows",), but=())
    class WindowsOnlyBaseClass:
        def method(self) -> str:  # noqa: PLR6301
            return "Base method executed"

    # Define a subclass that inherits from the unavailable base class
    class WindowsOnlySubClass(WindowsOnlyBaseClass):
        def method(self):  # noqa: PLR6301
            return "Subclass method executed"

    # Test that attempting to instantiate the subclass raises AvailabilityError
    with pytest.raises(AvailabilityError) as excinfo:
        WindowsOnlySubClass()
    assert "only supported on" in str(excinfo.value)

    # Test with a base class that has no restrictions
    @availability(only=(), but=())
    class UnrestrictedBaseClass:
        def method(self) -> str:  # noqa: PLR6301
            return "Base method executed"

    # Define a subclass with its own restrictions
    @availability(only=("windows",), but=())
    class RestrictedSubClass(UnrestrictedBaseClass):
        def method(self) -> str:  # noqa: PLR6301
            return "Subclass method executed"

    # Test that the subclass has its own restrictions
    with pytest.raises(AvailabilityError) as excinfo:
        RestrictedSubClass()
    assert "only supported on" in str(excinfo.value)
