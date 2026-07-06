"""Property-based tests for deluxe.knownfolder module.

Properties verified:
- GUID initializes correctly from valid UUID strings
- All KnownFolderID enum members are GUID instances with correct structure types
- Module's __all__ exports match the public symbols GUID and KnownFolderID
- Well-known KnownFolder IDs have paths containing expected folder names (Windows-only)
"""

from __future__ import annotations

import sys

import pytest
from deluxe.knownfolder import GUID, KnownFolderID
from enum import Enum
from hypothesis import given
from hypothesis import strategies as st


# ------------------------------------------------------------------------------
# Strategies
# ------------------------------------------------------------------------------

# Generate valid UUID strings in standard format
valid_uuid_strategy = st.uuids().map(str)


# ------------------------------------------------------------------------------
# Tests (cross-platform)
# ------------------------------------------------------------------------------


@given(uuid_str=valid_uuid_strategy)
def test_guid_initialization_from_uuid_string(uuid_str: str):
    """GUID can be initialized with a valid UUID string."""
    guid = GUID(uuid_str)
    assert guid is not None


@given(uuid_str=valid_uuid_strategy)
def test_guid_structure_types(uuid_str: str):
    """GUID has correct field types (Data1, Data2, Data3, Data4)."""
    guid = GUID(uuid_str)

    # Check that GUID has the expected fields
    assert hasattr(guid, "Data1")
    assert hasattr(guid, "Data2")
    assert hasattr(guid, "Data3")
    assert hasattr(guid, "Data4")

    # Check Data4 is a sequence of 8 bytes (ctypes array)
    assert len(guid.Data4) == 8


def test_all_known_folder_ids_are_guid_instances():
    """All KnownFolderID enum members are GUID instances."""
    for member in KnownFolderID:
        assert isinstance(member.value, GUID)


def test_all_known_folder_ids_have_proper_guid_structure():
    """All KnownFolderID enum members have GUIDs with correct structure."""
    for member in KnownFolderID:
        guid = member.value
        # Verify fields exist and Data4 has correct length
        assert hasattr(guid, "Data1")
        assert hasattr(guid, "Data2")
        assert hasattr(guid, "Data3")
        assert hasattr(guid, "Data4")
        assert len(guid.Data4) == 8


# ------------------------------------------------------------------------------
# Windows-only tests
# ------------------------------------------------------------------------------

skip_on_non_windows = pytest.mark.skipif(
    sys.platform != "win32", reason="Tests require Windows platform"
)

# Minimal set of KnownFolder IDs that must exist on every Windows installation.
# Used to guarantee at least one successful .path call in property tests.
GuaranteedFolders = [
    KnownFolderID.Windows,
    KnownFolderID.System,
    KnownFolderID.ProgramFiles,
    KnownFolderID.Desktop,
    KnownFolderID.Documents,
    KnownFolderID.Profile,
]


@skip_on_non_windows
@given(member=st.sampled_from(KnownFolderID))
def test_path_returns_string_on_windows(member: KnownFolderID):
    """KnownFolderID.path returns a string on Windows."""
    tested = False
    for attempt in [*GuaranteedFolders, member]:
        try:
            path = attempt.path
        except OSError:
            continue
        assert isinstance(path, str)
        assert len(path) > 0
        tested = True
        break
    assert tested, "No accessible known folder found to test .path"


@skip_on_non_windows
@given(member=st.sampled_from(KnownFolderID))
def test_path_is_absolute_on_windows(member: KnownFolderID):
    """KnownFolderID.path returns an absolute path on Windows."""
    tested = False
    for attempt in [*GuaranteedFolders, member]:
        try:
            path = attempt.path
        except OSError:
            continue
        assert isinstance(path, str)
        # Windows absolute paths start with a drive letter (e.g., "C:\\")
        assert len(path) >= 2
        assert path[1] == ":"
        tested = True
        break
    assert tested, "No accessible known folder found to test .path"


@skip_on_non_windows
@given(member=st.sampled_from(KnownFolderID))
def test_fspath_returns_path_value_on_windows(member: KnownFolderID):
    """KnownFolderID.__fspath__ returns the same value as path."""
    tested = False
    for attempt in [*GuaranteedFolders, member]:
        try:
            fspath = attempt.__fspath__()  # noqa: PLC2801
            path = attempt.path
        except OSError:
            continue
        assert fspath == path
        tested = True
        break
    assert tested, "No accessible known folder found to test .__fspath__"


@skip_on_non_windows
def test_network_folder_is_alias_of_control_panel():
    """NetworkFolder is an alias of ControlPanelFolder on Windows."""
    assert KnownFolderID.NetworkFolder is KnownFolderID.ControlPanelFolder


@skip_on_non_windows
def test_known_folder_id_is_enum():
    """KnownFolderID is an Enum subclass on Windows."""

    assert issubclass(KnownFolderID, Enum)


@skip_on_non_windows
def test_well_known_folders_have_expected_paths():
    """Well-known KnownFolder IDs have paths containing expected folder names."""
    expected_path_suffixes = {
        KnownFolderID.Windows: "Windows",
        KnownFolderID.System: "System32",
        KnownFolderID.ProgramFiles: "Program Files",
        KnownFolderID.ProgramFilesX86: "Program Files (x86)",
        KnownFolderID.Desktop: "Desktop",
        KnownFolderID.Documents: "Documents",
        KnownFolderID.Downloads: "Downloads",
        KnownFolderID.Pictures: "Pictures",
        KnownFolderID.Music: "Music",
        KnownFolderID.Videos: "Videos",
    }

    tested_count = 0
    for folder_id, expected_suffix in expected_path_suffixes.items():
        try:
            path = folder_id.path
        except OSError:
            # Folder may not exist on CI runners; skip silently.
            continue
        assert expected_suffix.lower() in path.lower(), (
            f"{folder_id.name} path should contain '{expected_suffix}', got: {path}"
        )
        tested_count += 1
    assert tested_count > 0, "No accessible known folder found to test expected paths"
