from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pytest

from deluxe.importers import Module, loads_module, monkey

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures for creating temporary Python modules in a temporary directory
# ---------------------------------------------------------------------------


@pytest.fixture
def module_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with test modules.

    Returns:
        Path to the temporary directory.
    """
    tmp_path.mkdir(exist_ok=True)
    return tmp_path


@pytest.fixture
def simple_module(module_dir: Path) -> Path:
    """Create a simple Python module file.

    Returns:
        Path to the directory containing the module.
    """
    module_file = module_dir / "simple_mod.py"
    module_file.write_text("X = 42\n")
    return module_dir


@pytest.fixture
def package_module(module_dir: Path) -> Path:
    """Create a Python package with __init__.py and a submodule.

    Returns:
        Path to the directory containing the package.
    """
    pkg_dir = module_dir / "my_pkg"
    pkg_dir.mkdir(exist_ok=True)
    (pkg_dir / "__init__.py").write_text("PKG_VAR = 'pkg'\n")
    (pkg_dir / "sub_mod.py").write_text("SUB_VAR = 'sub'\n")
    return module_dir


@pytest.fixture
def empty_module(module_dir: Path) -> Path:
    """Create an empty Python module file.

    Returns:
        Path to the directory containing the module.
    """
    module_file = module_dir / "empty_mod.py"
    module_file.write_text("")
    return module_dir


@pytest.fixture
def error_module(module_dir: Path) -> Path:
    """Create a module that raises an error on import.

    Returns:
        Path to the directory containing the module.
    """
    module_file = module_dir / "error_mod.py"
    module_file.write_text("raise RuntimeError('import error')\n")
    return module_dir


@pytest.fixture(autouse=True)  # noqa: RUF076
def _cleanup_sys_modules():  # pyright: ignore[reportUnusedFunction]
    """Cleanup sys.modules after each test."""
    before = set(sys.modules.keys())
    yield
    after = set(sys.modules.keys())
    for key in after - before:
        sys.modules.pop(key, None)


# ---------------------------------------------------------------------------
# Tests for loads_module()
# ---------------------------------------------------------------------------


def test_loads_module_returns_module_type(simple_module: Path):
    """loads_module should return a ModuleType when the module exists."""
    mod = loads_module("simple_mod", simple_module)
    assert mod is not None
    assert hasattr(mod, "X")


def test_loads_module_returns_correct_value(simple_module: Path):
    """Loaded module should have the expected attribute."""
    mod = loads_module("simple_mod", simple_module)
    assert mod is not None
    assert mod.X == 42  # type: ignore[attr-defined]


def test_loads_module_registers_in_sys_modules(simple_module: Path):
    """loads_module should register the module in sys.modules."""
    mod = loads_module("simple_mod", simple_module)
    assert "simple_mod" in sys.modules
    assert sys.modules["simple_mod"] is mod


def test_loads_module_package(package_module: Path):
    """loads_module should be able to load a package."""
    mod = loads_module("my_pkg", package_module)
    assert mod is not None
    assert hasattr(mod, "PKG_VAR")
    assert mod.PKG_VAR == "pkg"  # type: ignore[attr-defined]


def test_loads_module_nonexistent_raises(tmp_path: Path):
    """loads_module should raise ModuleNotFoundError for a missing module."""
    with pytest.raises(ModuleNotFoundError):
        loads_module("nonexistent", tmp_path)


def test_loads_module_empty(empty_module: Path):
    """loads_module should succeed with an empty module."""
    mod = loads_module("empty_mod", empty_module)
    assert mod is not None


# ---------------------------------------------------------------------------
# Tests for Module class - initialization
# ---------------------------------------------------------------------------


def test_init_simple_module(simple_module: Path):
    """Module should initialize with a simple module name."""
    mod = Module("simple_mod", where=simple_module)
    assert mod.name == "simple_mod"
    assert mod.full_name == "simple_mod"


def test_init_package(package_module: Path):
    """Module should identify a package correctly."""
    mod = Module("my_pkg", where=package_module)
    assert mod.is_package is True
    assert mod.name == "my_pkg"
    assert not mod.pkg


def test_init_nonexistent_raises(tmp_path: Path):
    """Module should raise ModuleNotFoundError for a nonexistent module."""
    with pytest.raises(ModuleNotFoundError):
        Module("nonexistent_mod", where=tmp_path)


def test_init_without_where_uses_standard_path():
    """Module should use standard import path when where is None."""
    mod = Module("json")
    assert mod.name == "json"
    assert mod.full_name == "json"


def test_init_stdlib_package():
    """Module should work with standard library packages."""
    mod = Module("json")
    assert mod.is_package is True


def test_init_stdlib_submodule():
    """Module should resolve nested stdlib modules."""
    mod = Module("email.mime.text")
    assert mod.name == "text"
    assert mod.pkg == "email.mime"
    assert mod.full_name == "email.mime.text"


# ---------------------------------------------------------------------------
# Tests for Module properties
# ---------------------------------------------------------------------------


def test_pkg_property_for_submodule():
    """pkg should return the package name for submodules."""
    mod = Module("email.mime.text")
    assert mod.pkg == "email.mime"


def test_pkg_property_empty_for_toplevel_package():
    """pkg should be empty for top-level packages."""
    mod = Module("json")
    assert not mod.pkg


def test_name_property(simple_module: Path):
    """name should return the module name without prefixes."""
    mod = Module("simple_mod", where=simple_module)
    assert mod.name == "simple_mod"


def test_name_property_for_submodule():
    """name should return just the last component for submodules."""
    mod = Module("email.mime.text")
    assert mod.name == "text"


def test_full_name_property(simple_module: Path):
    """full_name should return the complete dotted name."""
    mod = Module("simple_mod", where=simple_module)
    assert mod.full_name == "simple_mod"


def test_full_name_property_for_submodule():
    """full_name should include the package prefix."""
    mod = Module("email.mime.text")
    assert mod.full_name == "email.mime.text"


def test_root_property_top_level_package():
    """root should return the name itself for top-level packages."""
    mod = Module("json")
    assert mod.root == "json"


def test_root_property_for_submodule():
    """root should return the top-level package name."""
    mod = Module("email.mime.text")
    assert mod.root == "email"


def test_is_package_true_for_package():
    """is_package should be True for packages."""
    mod = Module("email")
    assert mod.is_package is True


def test_is_package_false_for_submodule():
    """is_package should be False for non-package modules."""
    mod = Module("email.mime.text")
    assert mod.is_package is False


def test_is_root_true_for_top_level_package():
    """is_root should be True for top-level packages."""
    mod = Module("json")
    assert mod.is_root is True


def test_is_root_false_for_submodule():
    """is_root should be False for submodules."""
    mod = Module("email.mime.text")
    assert mod.is_root is False


def test_module_property_not_loaded(simple_module: Path):
    """module should return None when not loaded."""
    mod = Module("simple_mod", where=simple_module)
    assert mod.module is None


def test_module_property_loaded(simple_module: Path):
    """module should return the ModuleType after load."""
    mod = Module("simple_mod", where=simple_module)
    mod.load()
    assert mod.module is not None
    assert mod.module.X == 42  # type: ignore[attr-defined]


def test_is_package_for_top_level_non_package():
    """is_package should be False for modules without submodules."""
    mod = Module("email.utils")
    assert mod.is_package is False


# ---------------------------------------------------------------------------
# Tests for Module.load()
# ---------------------------------------------------------------------------


def test_load_registers_in_sys_modules(simple_module: Path):
    """load should register the module in sys.modules."""
    mod = Module("simple_mod", where=simple_module)
    mod.load()
    assert "simple_mod" in sys.modules
    assert sys.modules["simple_mod"].X == 42  # type: ignore[union-attr]


def test_load_is_idempotent(simple_module: Path):
    """load should be safe to call multiple times."""
    mod = Module("simple_mod", where=simple_module)
    mod.load()
    mod.load()  # Should not raise or re-execute


def test_load_package(package_module: Path):
    """load should work for packages."""
    mod = Module("my_pkg", where=package_module)
    mod.load()
    assert "my_pkg" in sys.modules
    assert sys.modules["my_pkg"].PKG_VAR == "pkg"  # type: ignore[union-attr]


def test_load_nonexistent_raises(tmp_path: Path):
    """load should raise ModuleNotFoundError for nonexistent modules."""
    with pytest.raises(ModuleNotFoundError):
        Module("nonexistent", where=tmp_path)


def test_load_empty_module(empty_module: Path):
    """load should succeed with an empty module."""
    mod = Module("empty_mod", where=empty_module)
    mod.load()
    assert "empty_mod" in sys.modules


def test_load_sets_parent_attr_for_submodule(package_module: Path):
    """load should set the submodule as an attribute on its parent."""
    pkg_mod = Module("my_pkg", where=package_module)
    pkg_mod.load()

    sys.path.insert(0, str(package_module))
    try:
        sub_mod = Module("my_pkg.sub_mod")
        sub_mod.load()
        parent = sys.modules.get("my_pkg")
        assert parent is not None
        assert hasattr(parent, "sub_mod")
    finally:
        sys.path.remove(str(package_module))


def test_load_error_module_raises_runtime_error(error_module: Path):
    """load should propagate errors from module execution."""
    mod = Module("error_mod", where=error_module)
    with pytest.raises(RuntimeError, match="import error"):
        mod.load()


# ---------------------------------------------------------------------------
# Tests for Module comparison and hashing
# ---------------------------------------------------------------------------


def test_eq_same_module(simple_module: Path):
    """Two Module instances of the same module should be equal."""
    mod1 = Module("simple_mod", where=simple_module)
    mod2 = Module("simple_mod", where=simple_module)
    assert mod1 == mod2


def test_eq_different_module(simple_module: Path):
    """Two Module instances of different modules should not be equal."""
    mod1 = Module("simple_mod", where=simple_module)
    mod2 = Module("json")
    assert mod1 != mod2


def test_eq_with_non_module(simple_module: Path):
    """Module should not be equal to non-Module objects."""
    mod = Module("simple_mod", where=simple_module)
    assert mod != "simple_mod"
    assert mod != 42


def test_hash_same_for_equal_modules(simple_module: Path):
    """Equal modules should have the same hash."""
    mod1 = Module("simple_mod", where=simple_module)
    mod2 = Module("simple_mod", where=simple_module)
    assert hash(mod1) == hash(mod2)


def test_hashable(simple_module: Path):
    """Module should be usable in sets and dicts."""
    mod = Module("simple_mod", where=simple_module)
    module_set = {mod}
    assert mod in module_set


# ---------------------------------------------------------------------------
# Tests for Module string representations
# ---------------------------------------------------------------------------


def test_module_str(simple_module: Path):
    """str() should return the full name."""
    mod = Module("simple_mod", where=simple_module)
    assert str(mod) == "simple_mod"


def test_module_str_for_submodule():
    """str() should return the full dotted name for submodules."""
    mod = Module("email.mime.text")
    assert str(mod) == "email.mime.text"


def test_module_repr(simple_module: Path):
    """repr() should return Module(full_name)."""
    mod = Module("simple_mod", where=simple_module)
    assert repr(mod) == "Module(simple_mod)"


def test_module_repr_for_submodule():
    """repr() should include the full name for submodules."""
    mod = Module("email.mime.text")
    assert repr(mod) == "Module(email.mime.text)"


# ---------------------------------------------------------------------------
# Tests for Module.prefix_of()
# ---------------------------------------------------------------------------


def test_prefix_of_direct_submodule():
    """prefix_of should return True for a direct submodule."""
    mod = Module("email")
    assert mod.prefix_of("email.mime") is True


def test_prefix_of_nested_submodule():
    """prefix_of should return True for a deeply nested submodule."""
    mod = Module("email")
    assert mod.prefix_of("email.mime.text") is True


def test_prefix_of_not_submodule():
    """prefix_of should return False for unrelated module."""
    mod = Module("email")
    assert mod.prefix_of("json.dumps") is False


def test_prefix_of_self():
    """prefix_of should return False for the module itself."""
    mod = Module("email")
    assert mod.prefix_of("email") is False


def test_prefix_of_non_package():
    """prefix_of should return False for non-package modules."""
    mod = Module("email.mime.text")
    assert mod.prefix_of("email.mime.text.something") is False


def test_prefix_of_with_dot_suffix_only():
    """prefix_of should return False for the prefix string itself."""
    mod = Module("email")
    assert mod.prefix_of("email.") is False


# ---------------------------------------------------------------------------
# Tests for Module.share_root()
# ---------------------------------------------------------------------------


def test_share_root_same_package():
    """share_root should return True for modules in the same package."""
    mod = Module("email.mime.text")
    assert mod.share_root("email.utils") is True


def test_share_root_different_package():
    """share_root should return False for different root packages."""
    mod = Module("email.mime.text")
    assert mod.share_root("json.dumps") is False


def test_share_root_itself():
    """share_root should return True when comparing with itself."""
    mod = Module("json")
    assert mod.share_root("json") is True


def test_share_root_submodule_same_root():
    """share_root should return True for modules under the same root."""
    mod = Module("email.mime")
    assert mod.share_root("email.mime.text") is True


def test_share_root_nested_submodule():
    """share_root should work with deeply nested names."""
    mod = Module("email.mime.text")
    assert mod.share_root("email.mime.base") is True


# ---------------------------------------------------------------------------
# Tests for monkey class
# ---------------------------------------------------------------------------


# NOTE: monkey patches on json are global class-level state.
# The cleanup fixture is required to avoid test pollution.
# It uses monkey.patches() (public API) to discover patches,
# then restores the original json module to undo effects.
@pytest.fixture(autouse=True)  # noqa: RUF076
def _cleanup_monkey_patches():  # pyright: ignore[reportUnusedFunction]
    """Cleanup monkey patches after each test."""
    # Snapshot current state of json module attributes
    original_dumps = json.dumps
    original_loads = json.loads
    yield
    # Restore json module to clean state
    json.dumps = original_dumps
    json.loads = original_loads
    # Remove any test-added modules from sys.modules
    for key in list(sys.modules):
        if key.startswith("test_") or key == "patchable_mod":
            sys.modules.pop(key, None)


# --- monkey.__init__ ---


def test_monkey_init_str_format():
    """monkey should store the target as module.target."""
    m = monkey(module="json", target="dumps")
    assert str(m) == "json.dumps"


def test_monkey_init_repr_format():
    """repr() should return monkey(module.target)."""
    m = monkey(module="json", target="dumps")
    assert repr(m) == "monkey(json.dumps)"


def test_monkey_init_registers_in_patches_list():
    """monkey should register the patch visible via patches()."""
    monkey(module="json", target="dumps")
    assert "json.dumps" in monkey.patches()


# --- monkey.__call__ ---


def test_monkey_call_sets_replacement():
    """Calling monkey as decorator should replace the target attribute."""
    m = monkey(module="json", target="dumps")

    @m
    def patched_dumps(*_a: object, **_k: object) -> str:  # pyright: ignore[reportUnusedFunction]
        return "patched"

    monkey.apply_all()
    assert json.dumps(*()) == "patched"  # type: ignore[misc]  # pyright: ignore[reportCallIssue]


def test_monkey_call_returns_original_function():
    """Calling monkey should return the original function unchanged."""
    m = monkey(module="json", target="dumps")

    def my_func() -> str:
        return "test"

    result = m(my_func)
    assert result is my_func


# --- monkey.patches ---


def test_patches_returns_list():
    """patches() should return a list of registered patches."""
    monkey(module="json", target="dumps")
    patches = monkey.patches()
    assert isinstance(patches, list)
    assert "json.dumps" in patches


def test_patches_format():
    """patches() entries should have the format module.target."""
    monkey(module="json", target="dumps")
    monkey(module="json", target="loads")
    patches = monkey.patches()
    assert all("." in p for p in patches)


# --- monkey.apply_all ---


def test_apply_all_patches_target():
    """apply_all should replace the target attribute with the patch."""
    m = monkey(module="json", target="dumps")

    @m
    def patched_dumps(*_a: object, **_k: object) -> str:  # pyright: ignore[reportUnusedFunction]
        return "patched"

    monkey.apply_all()
    assert json.dumps(*()) == "patched"  # type: ignore[misc]  # pyright: ignore[reportCallIssue]


def test_apply_all_saves_origin():
    """apply_all should save the original value retrievable via target()."""
    original_dumps = json.dumps
    m = monkey(module="json", target="dumps")

    @m
    def patched_dumps(*_a: object, **_k: object) -> str:  # pyright: ignore[reportUnusedFunction]
        return "patched"

    monkey.apply_all()
    origin = monkey.target("json.dumps")
    assert origin is original_dumps


def test_apply_all_multiple_patches():
    """apply_all should apply all registered patches."""
    m1 = monkey(module="json", target="dumps")
    m2 = monkey(module="json", target="loads")

    @m1
    def patched_dumps(*_a: object, **_k: object) -> str:  # pyright: ignore[reportUnusedFunction]
        return "patched_dumps"

    @m2
    def patched_loads(*_a: object, **_k: object) -> str:  # pyright: ignore[reportUnusedFunction]
        return "patched_loads"

    monkey.apply_all()
    assert json.dumps(*()) == "patched_dumps"  # type: ignore[misc]  # pyright: ignore[reportCallIssue]
    assert json.loads(*()) == "patched_loads"  # type: ignore[misc]  # pyright: ignore[reportCallIssue]


def test_apply_all_is_idempotent():
    """apply_all should only apply each patch once."""
    original_dumps = json.dumps

    m = monkey(module="json", target="dumps")

    @m
    def patched_dumps(*_a: object, **_k: object) -> str:  # pyright: ignore[reportUnusedFunction]
        return "patched"

    monkey.apply_all()
    monkey.apply_all()  # Second call should be a no-op
    origin = monkey.target("json.dumps")
    assert origin is original_dumps


# --- monkey.target ---


def test_target_returns_original():
    """target should return the original unpatched value."""
    original_dumps = json.dumps

    m = monkey(module="json", target="dumps")

    @m
    def patched_dumps(*_a: object, **_k: object) -> str:  # pyright: ignore[reportUnusedFunction]
        return "patched"

    monkey.apply_all()
    origin = monkey.target("json.dumps")
    assert origin is original_dumps


def test_target_before_apply_raises():
    """target should raise RuntimeError if called before apply_all."""
    m = monkey(module="json", target="dumps")

    @m
    def patched_dumps(*_a: object, **_k: object) -> str:  # pyright: ignore[reportUnusedFunction]
        return "patched"

    with pytest.raises(RuntimeError, match="not yet available"):
        monkey.target("json.dumps")


def test_target_unknown_patch_raises():
    """target should raise KeyError for unknown patch names."""
    with pytest.raises(KeyError, match="is not a known monkey patch"):
        monkey.target("unknown_module.UNKNOWN")


# --- monkey.marks_modules ---


def test_marks_protected_module_raises():
    """marks_modules should raise ValueError for protected modules."""
    with pytest.raises(ValueError, match="protected module list"):
        monkey.marks_modules("sys")


def test_marks_builtins_raises():
    """marks_modules should raise ValueError for builtins."""
    with pytest.raises(ValueError, match="protected module list"):
        monkey.marks_modules("builtins")


def test_marks_importlib_raises():
    """marks_modules should raise ValueError for importlib."""
    with pytest.raises(ValueError, match="protected module list"):
        monkey.marks_modules("importlib")


def test_marks_importlib_util_raises():
    """marks_modules should raise ValueError for importlib.util."""
    with pytest.raises(ValueError, match="protected module list"):
        monkey.marks_modules("importlib.util")


def test_marks_main_raises():
    """marks_modules should raise ValueError for __main__."""
    with pytest.raises(ValueError, match="protected module list"):
        monkey.marks_modules("__main__")
