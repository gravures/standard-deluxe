from __future__ import annotations

import operator
import string
from itertools import chain, combinations
from typing import TYPE_CHECKING

import pytest
from deluxe.version import Release, Version, VersionError
from hypothesis import given
from hypothesis import strategies as st


if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = pytest.mark.slow


def version_string(  # noqa: PLR0917
    major: int,
    minor: int,
    micro: int,
    pre: int | None,
    post: int | None,
    dev: int | None,
    local: str | None,
) -> str:
    return "".join((
        f"{major}.{minor}.{micro}",
        (f"a{pre}" if pre is not None else ""),
        (f".post{post}" if post is not None else ""),
        (f".dev{dev}" if dev is not None else ""),
        (f"+{local}" if local is not None else ""),
    ))


# Strategy for valid version strings
valid_version_strategy = st.builds(
    version_string,
    major=st.integers(min_value=0, max_value=100),
    minor=st.integers(min_value=0, max_value=100),
    micro=st.integers(min_value=0, max_value=100),
    pre=st.one_of(st.none(), st.integers(min_value=0, max_value=100)),
    post=st.one_of(st.none(), st.integers(min_value=0, max_value=100)),
    dev=st.one_of(st.none(), st.integers(min_value=0, max_value=100)),
    local=st.one_of(
        st.none(),
        st.text(alphabet=tuple(string.ascii_letters + string.digits), min_size=2, max_size=10),
    ),
)


# Strategy for invalid version strings
invalid_version_strategy = st.one_of(
    # st.text().filter(lambda s: not s.replace(".", "").isdigit()),
    # Non sensical versions should be invalid
    st.just("a.b.c"),
    st.just("french toast"),
    # Versions with invalid local versions
    st.just("1.0+a+"),
    st.just("1.0++"),
    st.just("1.0+_foobar"),
    st.just("1.0+foo&asd"),
    st.just("1.0+1+1"),
)


@given(version_string=valid_version_strategy)
def test_from_string_parses_valid_versions(version_string: str):
    version = Version.from_string(version_string)
    assert isinstance(version, Version)


@given(version_string=invalid_version_strategy)
def test_from_string_raises_version_error_for_invalid_versions(version_string: str):
    with pytest.raises(VersionError):
        Version.from_string(version_string)


@given(version_string=valid_version_strategy)
def test_version_to_string_and_back(version_string: str):
    try:
        version = Version.from_string(version_string)
        # The string representation might not be identical, but it should be parseable
        # and result in an equal Version object.
        new_version = Version.from_string(str(version))
        assert version == new_version
    except VersionError:
        # Some generated valid strings might be edge cases that are hard to parse back
        # perfectly, but they should still be valid.
        pass


@given(v1_str=valid_version_strategy, v2_str=valid_version_strategy)
def test_version_comparison(v1_str: str, v2_str: str):
    try:  # noqa: PLW0717
        v1 = Version.from_string(v1_str)
        v2 = Version.from_string(v2_str)

        # Test equality
        if v1_str == v2_str:
            assert v1 == v2
        else:
            # This is not always true, e.g. "1.2.3" and "v1.2.3"
            pass

        # Test ordering
        assert (v1 < v2) or (v1 > v2) or (v1 == v2)

    except VersionError:
        pass


def test_specific_version_comparisons():
    assert Version.from_string("1.0.0") < Version.from_string("2.0.0")
    assert Version.from_string("1.0.0") < Version.from_string("1.1.0")
    assert Version.from_string("1.0.0") < Version.from_string("1.0.1")
    assert Version.from_string("1.0.0a1") < Version.from_string("1.0.0")
    assert Version.from_string("1.0.0a1") < Version.from_string("1.0.0a2")
    assert Version.from_string("1.0.0b1") > Version.from_string("1.0.0a2")
    assert Version.from_string("1.0.0.post1") > Version.from_string("1.0.0")
    assert Version.from_string("1.0.0.dev1") < Version.from_string("1.0.0")
    assert Version.from_string("1.0.0+local1") > Version.from_string("1.0.0")
    assert Version.from_string("1.0.0+local1") < Version.from_string("1.0.0+local2")
    assert Version.from_string("1.0.0+local.1") < Version.from_string("1.0.0+local.2")
    assert Version.from_string("1.0.0-alpha") == Version.from_string("1.0.0a0")
    assert Version.from_string("1.0.0-beta") == Version.from_string("1.0.0b0")
    assert Version.from_string("1.0.0-rc") == Version.from_string("1.0.0rc0")
    assert Version.from_string("1.0.0-preview") == Version.from_string("1.0.0c0")
    assert Version.from_string("1.0.0-pre") == Version.from_string("1.0.0c0")
    assert Version.from_string("1.0.0-rev") == Version.from_string("1.0.0.post0")
    assert Version.from_string("1.0.0-r") == Version.from_string("1.0.0.post0")
    assert Version.from_string("1.0.0-dev") == Version.from_string("1.0.0.dev0")


####
# Follow tests are borrowed from packaging library.
#
# This list must be in the correct sorting order
VERSIONS = [
    # Implicit epoch of 0
    "1.0.dev456",
    "1.0a1",
    "1.0a2.dev456",
    "1.0a12.dev456",
    "1.0a12",
    "1.0b1.dev456",
    "1.0b2",
    "1.0b2.post345.dev456",
    "1.0b2.post345",
    "1.0b2-346",
    "1.0c1.dev456",
    "1.0c1",
    "1.0rc2",
    "1.0c3",
    "1.0",
    "1.0.post456.dev34",
    "1.0.post456",
    "1.1.dev1",
    "1.2+123abc",
    "1.2+123abc456",
    "1.2+abc",
    "1.2+abc123",
    "1.2+abc123def",
    "1.2+1234.abc",
    "1.2+123456",
    "1.2.r32+123456",
    "1.2.rev33+123456",
    # Explicit epoch of 1
    "1!1.0.dev456",
    "1!1.0a1",
    "1!1.0a2.dev456",
    "1!1.0a12.dev456",
    "1!1.0a12",
    "1!1.0b1.dev456",
    "1!1.0b2",
    "1!1.0b2.post345.dev456",
    "1!1.0b2.post345",
    "1!1.0b2-346",
    "1!1.0c1.dev456",
    "1!1.0c1",
    "1!1.0rc2",
    "1!1.0c3",
    "1!1.0",
    "1!1.0.post456.dev34",
    "1!1.0.post456",
    "1!1.1.dev1",
    "1!1.2+123abc",
    "1!1.2+123abc456",
    "1!1.2+abc",
    "1!1.2+abc123",
    "1!1.2+abc123def",
    "1!1.2+1234.abc",
    "1!1.2+123456",
    "1!1.2.r32+123456",
    "1!1.2.rev33+123456",
]


@pytest.mark.parametrize(
    ("version1", "version2"),
    combinations(VERSIONS, 2),
)
def test_valid_versions(version1: str, version2: str):
    assert Version.from_string(version1) < Version.from_string(version2)


NORMALIZED = [
    # Various development release incarnations
    ("1.0dev", "1.0.dev0"),
    ("1.0.dev", "1.0.dev0"),
    ("1.0dev1", "1.0.dev1"),
    ("1.0-dev", "1.0.dev0"),
    ("1.0-dev1", "1.0.dev1"),
    ("1.0DEV", "1.0.dev0"),
    ("1.0.DEV", "1.0.dev0"),
    ("1.0DEV1", "1.0.dev1"),
    ("1.0.DEV1", "1.0.dev1"),
    ("1.0-DEV", "1.0.dev0"),
    ("1.0-DEV1", "1.0.dev1"),
    # Various alpha incarnations
    ("1.0a", "1.0a0"),
    ("1.0.a", "1.0a0"),
    ("1.0.a1", "1.0a1"),
    ("1.0-a", "1.0a0"),
    ("1.0-a1", "1.0a1"),
    ("1.0alpha", "1.0a0"),
    ("1.0.alpha", "1.0a0"),
    ("1.0.alpha1", "1.0a1"),
    ("1.0-alpha", "1.0a0"),
    ("1.0-alpha1", "1.0a1"),
    ("1.0A", "1.0a0"),
    ("1.0.A", "1.0a0"),
    ("1.0.A1", "1.0a1"),
    ("1.0-A", "1.0a0"),
    ("1.0-A1", "1.0a1"),
    ("1.0ALPHA", "1.0a0"),
    ("1.0.ALPHA", "1.0a0"),
    ("1.0.ALPHA1", "1.0a1"),
    ("1.0-ALPHA", "1.0a0"),
    ("1.0-ALPHA1", "1.0a1"),
    # Various beta incarnations
    ("1.0b", "1.0b0"),
    ("1.0.b", "1.0b0"),
    ("1.0.b1", "1.0b1"),
    ("1.0-b", "1.0b0"),
    ("1.0-b1", "1.0b1"),
    ("1.0beta", "1.0b0"),
    ("1.0.beta", "1.0b0"),
    ("1.0.beta1", "1.0b1"),
    ("1.0-beta", "1.0b0"),
    ("1.0-beta1", "1.0b1"),
    ("1.0B", "1.0b0"),
    ("1.0.B", "1.0b0"),
    ("1.0.B1", "1.0b1"),
    ("1.0-B", "1.0b0"),
    ("1.0-B1", "1.0b1"),
    ("1.0BETA", "1.0b0"),
    ("1.0.BETA", "1.0b0"),
    ("1.0.BETA1", "1.0b1"),
    ("1.0-BETA", "1.0b0"),
    ("1.0-BETA1", "1.0b1"),
    # Various release candidate incarnations
    ("1.0c", "1.0rc0"),
    ("1.0.c", "1.0rc0"),
    ("1.0.c1", "1.0rc1"),
    ("1.0-c", "1.0rc0"),
    ("1.0-c1", "1.0rc1"),
    ("1.0rc", "1.0rc0"),
    ("1.0.rc", "1.0rc0"),
    ("1.0.rc1", "1.0rc1"),
    ("1.0-rc", "1.0rc0"),
    ("1.0-rc1", "1.0rc1"),
    ("1.0C", "1.0rc0"),
    ("1.0.C", "1.0rc0"),
    ("1.0.C1", "1.0rc1"),
    ("1.0-C", "1.0rc0"),
    ("1.0-C1", "1.0rc1"),
    ("1.0RC", "1.0rc0"),
    ("1.0.RC", "1.0rc0"),
    ("1.0.RC1", "1.0rc1"),
    ("1.0-RC", "1.0rc0"),
    ("1.0-RC1", "1.0rc1"),
    # Various post release incarnations
    ("1.0post", "1.0.post0"),
    ("1.0.post", "1.0.post0"),
    ("1.0post1", "1.0.post1"),
    ("1.0-post", "1.0.post0"),
    ("1.0-post1", "1.0.post1"),
    ("1.0POST", "1.0.post0"),
    ("1.0.POST", "1.0.post0"),
    ("1.0POST1", "1.0.post1"),
    ("1.0r", "1.0.post0"),
    ("1.0rev", "1.0.post0"),
    ("1.0.POST1", "1.0.post1"),
    ("1.0.r1", "1.0.post1"),
    ("1.0.rev1", "1.0.post1"),
    ("1.0-POST", "1.0.post0"),
    ("1.0-POST1", "1.0.post1"),
    ("1.0-5", "1.0.post5"),
    ("1.0-r5", "1.0.post5"),
    ("1.0-rev5", "1.0.post5"),
    # Local version case insensitivity
    ("1.0+AbC", "1.0+abc"),
    # Integer Normalization
    ("1.01", "1.1"),
    ("1.0a05", "1.0a5"),
    ("1.0b07", "1.0b7"),
    ("1.0c056", "1.0rc56"),
    ("1.0rc09", "1.0rc9"),
    ("1.0.post000", "1.0.post0"),
    ("1.1.dev09000", "1.1.dev9000"),
    ("00!1.2", "1.2"),
    ("0100!0.0", "100!0.0"),
    # Various other normalizations
    ("v1.0", "1.0"),
    # ("   v1.0\t\n", "1.0"),
    ("1.0.dev456", "1.0.dev456"),
    ("1.0a1", "1.0a1"),
    ("1.0a2.dev456", "1.0a2.dev456"),
    ("1.0a12.dev456", "1.0a12.dev456"),
    ("1.0a12", "1.0a12"),
    ("1.0b1.dev456", "1.0b1.dev456"),
    ("1.0b2", "1.0b2"),
    ("1.0b2.post345.dev456", "1.0b2.post345.dev456"),
    ("1.0b2.post345", "1.0b2.post345"),
    ("1.0rc1.dev456", "1.0rc1.dev456"),
    ("1.0rc1", "1.0rc1"),
    ("1.0", "1.0"),
    ("1.0.post456.dev34", "1.0.post456.dev34"),
    ("1.0.post456", "1.0.post456"),
    ("1.0.1", "1.0.1"),
    ("0!1.0.2", "1.0.2"),
    ("1.0.3+7", "1.0.3+7"),
    ("0!1.0.4+8.0", "1.0.4+8.0"),
    ("1.0.5+9.5", "1.0.5+9.5"),
    ("1.2+1234.abc", "1.2+1234.abc"),
    ("1.2+123456", "1.2+123456"),
    ("1.2+123abc", "1.2+123abc"),
    ("1.2+123abc456", "1.2+123abc456"),
    ("1.2+abc", "1.2+abc"),
    ("1.2+abc123", "1.2+abc123"),
    ("1.2+abc123def", "1.2+abc123def"),
    ("1.1.dev1", "1.1.dev1"),
    ("7!1.0.dev456", "7!1.0.dev456"),
    ("7!1.0a1", "7!1.0a1"),
    ("7!1.0a2.dev456", "7!1.0a2.dev456"),
    ("7!1.0a12.dev456", "7!1.0a12.dev456"),
    ("7!1.0a12", "7!1.0a12"),
    ("7!1.0b1.dev456", "7!1.0b1.dev456"),
    ("7!1.0b2", "7!1.0b2"),
    ("7!1.0b2.post345.dev456", "7!1.0b2.post345.dev456"),
    ("7!1.0b2.post345", "7!1.0b2.post345"),
    ("7!1.0rc1.dev456", "7!1.0rc1.dev456"),
    ("7!1.0rc1", "7!1.0rc1"),
    ("7!1.0", "7!1.0"),
    ("7!1.0.post456.dev34", "7!1.0.post456.dev34"),
    ("7!1.0.post456", "7!1.0.post456"),
    ("7!1.0.1", "7!1.0.1"),
    ("7!1.0.2", "7!1.0.2"),
    ("7!1.0.3+7", "7!1.0.3+7"),
    ("7!1.0.4+8.0", "7!1.0.4+8.0"),
    ("7!1.0.5+9.5", "7!1.0.5+9.5"),
    ("7!1.1.dev1", "7!1.1.dev1"),
]


@pytest.mark.parametrize(
    ("version", "normalized"),
    NORMALIZED,
)
def test_normalized_versions(version: str, normalized: str):
    assert str(Version.from_string(version)) == normalized


def test_version_rc_and_c_equals():
    assert Version.from_string("1.0rc1") == Version.from_string("1.0c1")


@pytest.mark.parametrize("version", VERSIONS)
def test_version_hash(version: str):
    assert hash(Version.from_string(version)) == hash(Version.from_string(version))


@pytest.mark.parametrize(
    ("version", "public"),
    [
        ("1.0", "1.0"),
        ("1.0.dev0", "1.0.dev0"),
        ("1.0.dev6", "1.0.dev6"),
        ("1.0a1", "1.0a1"),
        ("1.0a1.post5", "1.0a1.post5"),
        ("1.0a1.post5.dev6", "1.0a1.post5.dev6"),
        ("1.0rc4", "1.0rc4"),
        ("1.0.post5", "1.0.post5"),
        ("1!1.0", "1!1.0"),
        ("1!1.0.dev6", "1!1.0.dev6"),
        ("1!1.0a1", "1!1.0a1"),
        ("1!1.0a1.post5", "1!1.0a1.post5"),
        ("1!1.0a1.post5.dev6", "1!1.0a1.post5.dev6"),
        ("1!1.0rc4", "1!1.0rc4"),
        ("1!1.0.post5", "1!1.0.post5"),
        ("1.0+deadbeef", "1.0"),
        ("1.0.dev6+deadbeef", "1.0.dev6"),
        ("1.0a1+deadbeef", "1.0a1"),
        ("1.0a1.post5+deadbeef", "1.0a1.post5"),
        ("1.0a1.post5.dev6+deadbeef", "1.0a1.post5.dev6"),
        ("1.0rc4+deadbeef", "1.0rc4"),
        ("1.0.post5+deadbeef", "1.0.post5"),
        ("1!1.0+deadbeef", "1!1.0"),
        ("1!1.0.dev6+deadbeef", "1!1.0.dev6"),
        ("1!1.0a1+deadbeef", "1!1.0a1"),
        ("1!1.0a1.post5+deadbeef", "1!1.0a1.post5"),
        ("1!1.0a1.post5.dev6+deadbeef", "1!1.0a1.post5.dev6"),
        ("1!1.0rc4+deadbeef", "1!1.0rc4"),
        ("1!1.0.post5+deadbeef", "1!1.0.post5"),
    ],
)
def test_version_public(version: str, public: str):
    assert Version.from_string(version).public == public


@pytest.mark.parametrize(
    ("version", "local"),
    [
        ("1.0", None),
        ("1.0.dev0", None),
        ("1.0.dev6", None),
        ("1.0a1", None),
        ("1.0a1.post5", None),
        ("1.0a1.post5.dev6", None),
        ("1.0rc4", None),
        ("1.0.post5", None),
        ("1!1.0", None),
        ("1!1.0.dev6", None),
        ("1!1.0a1", None),
        ("1!1.0a1.post5", None),
        ("1!1.0a1.post5.dev6", None),
        ("1!1.0rc4", None),
        ("1!1.0.post5", None),
        ("1.0+deadbeef", ("deadbeef",)),
        ("1.0.dev6+deadbeef", ("deadbeef",)),
        ("1.0a1+deadbeef", ("deadbeef",)),
        ("1.0a1.post5+deadbeef", ("deadbeef",)),
        ("1.0a1.post5.dev6+deadbeef", ("deadbeef",)),
        ("1.0rc4+deadbeef", ("deadbeef",)),
        ("1.0.post5+deadbeef", ("deadbeef",)),
        ("1!1.0+deadbeef", ("deadbeef",)),
        ("1!1.0.dev6+deadbeef", ("deadbeef",)),
        ("1!1.0a1+deadbeef", ("deadbeef",)),
        ("1!1.0a1.post5+deadbeef", ("deadbeef",)),
        ("1!1.0a1.post5.dev6+deadbeef", ("deadbeef",)),
        ("1!1.0rc4+deadbeef", ("deadbeef",)),
        ("1!1.0.post5+deadbeef", ("deadbeef",)),
    ],
)
def test_version_local(version: str, local: tuple[str | int, ...] | None):
    assert Version.from_string(version).local == local


@pytest.mark.parametrize(
    ("version", "pre"),
    [
        ("1.0", None),
        ("1.0.dev0", None),
        ("1.0.dev6", None),
        ("1.0a1", ("a", 1)),
        ("1.0a1.post5", ("a", 1)),
        ("1.0a1.post5.dev6", ("a", 1)),
        ("1.0rc4", ("rc", 4)),
        ("1.0.post5", None),
        ("1!1.0", None),
        ("1!1.0.dev6", None),
        ("1!1.0a1", ("a", 1)),
        ("1!1.0a1.post5", ("a", 1)),
        ("1!1.0a1.post5.dev6", ("a", 1)),
        ("1!1.0rc4", ("rc", 4)),
        ("1!1.0.post5", None),
        ("1.0+deadbeef", None),
        ("1.0.dev6+deadbeef", None),
        ("1.0a1+deadbeef", ("a", 1)),
        ("1.0a1.post5+deadbeef", ("a", 1)),
        ("1.0a1.post5.dev6+deadbeef", ("a", 1)),
        ("1.0rc4+deadbeef", ("rc", 4)),
        ("1.0.post5+deadbeef", None),
        ("1!1.0+deadbeef", None),
        ("1!1.0.dev6+deadbeef", None),
        ("1!1.0a1+deadbeef", ("a", 1)),
        ("1!1.0a1.post5+deadbeef", ("a", 1)),
        ("1!1.0a1.post5.dev6+deadbeef", ("a", 1)),
        ("1!1.0rc4+deadbeef", ("rc", 4)),
        ("1!1.0.post5+deadbeef", None),
    ],
)
def test_version_pre(version: str, pre: tuple[str, int]):
    assert Version.from_string(version).pre == pre


@pytest.mark.parametrize(
    ("version", "dev"),
    [
        ("1.0", None),
        ("1.0.dev0", 0),
        ("1.0.dev6", 6),
        ("1.0a1", None),
        ("1.0a1.post5", None),
        ("1.0a1.post5.dev6", 6),
        ("1.0rc4", None),
        ("1.0.post5", None),
        ("1!1.0", None),
        ("1!1.0.dev6", 6),
        ("1!1.0a1", None),
        ("1!1.0a1.post5", None),
        ("1!1.0a1.post5.dev6", 6),
        ("1!1.0rc4", None),
        ("1!1.0.post5", None),
        ("1.0+deadbeef", None),
        ("1.0.dev6+deadbeef", 6),
        ("1.0a1+deadbeef", None),
        ("1.0a1.post5+deadbeef", None),
        ("1.0a1.post5.dev6+deadbeef", 6),
        ("1.0rc4+deadbeef", None),
        ("1.0.post5+deadbeef", None),
        ("1!1.0+deadbeef", None),
        ("1!1.0.dev6+deadbeef", 6),
        ("1!1.0a1+deadbeef", None),
        ("1!1.0a1.post5+deadbeef", None),
        ("1!1.0a1.post5.dev6+deadbeef", 6),
        ("1!1.0rc4+deadbeef", None),
        ("1!1.0.post5+deadbeef", None),
    ],
)
def test_version_dev(version: str, dev: int | None):
    assert Version.from_string(version).dev == dev


@pytest.mark.parametrize(
    ("version", "post"),
    [
        ("1.0", None),
        ("1.0.dev0", None),
        ("1.0.dev6", None),
        ("1.0a1", None),
        ("1.0a1.post5", 5),
        ("1.0a1.post5.dev6", 5),
        ("1.0rc4", None),
        ("1.0.post5", 5),
        ("1!1.0", None),
        ("1!1.0.dev6", None),
        ("1!1.0a1", None),
        ("1!1.0a1.post5", 5),
        ("1!1.0a1.post5.dev6", 5),
        ("1!1.0rc4", None),
        ("1!1.0.post5", 5),
        ("1.0+deadbeef", None),
        ("1.0.dev6+deadbeef", None),
        ("1.0a1+deadbeef", None),
        ("1.0a1.post5+deadbeef", 5),
        ("1.0a1.post5.dev6+deadbeef", 5),
        ("1.0rc4+deadbeef", None),
        ("1.0.post5+deadbeef", 5),
        ("1!1.0+deadbeef", None),
        ("1!1.0.dev6+deadbeef", None),
        ("1!1.0a1+deadbeef", None),
        ("1!1.0a1.post5+deadbeef", 5),
        ("1!1.0a1.post5.dev6+deadbeef", 5),
        ("1!1.0rc4+deadbeef", None),
        ("1!1.0.post5+deadbeef", 5),
    ],
)
def test_version_post(version: str, post: int | None):
    assert Version.from_string(version).post == post


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.0", False),
        ("1.0.dev0", True),
        ("1.0.dev6", True),
        ("1.0a1", False),
        ("1.0a1.post5", False),
        ("1.0a1.post5.dev6", True),
        ("1.0rc4", False),
        ("1.0.post5", False),
        ("1!1.0", False),
        ("1!1.0.dev6", True),
        ("1!1.0a1", False),
        ("1!1.0a1.post5", False),
        ("1!1.0a1.post5.dev6", True),
        ("1!1.0rc4", False),
        ("1!1.0.post5", False),
        ("1.0+deadbeef", False),
        ("1.0.dev6+deadbeef", True),
        ("1.0a1+deadbeef", False),
        ("1.0a1.post5+deadbeef", False),
        ("1.0a1.post5.dev6+deadbeef", True),
        ("1.0rc4+deadbeef", False),
        ("1.0.post5+deadbeef", False),
        ("1!1.0+deadbeef", False),
        ("1!1.0.dev6+deadbeef", True),
        ("1!1.0a1+deadbeef", False),
        ("1!1.0a1.post5+deadbeef", False),
        ("1!1.0a1.post5.dev6+deadbeef", True),
        ("1!1.0rc4+deadbeef", False),
        ("1!1.0.post5+deadbeef", False),
    ],
)
def test_version_is_devrelease(version: str, expected: bool):
    assert (Release.Development in Version.from_string(version).type) == expected


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.0.dev1", False),
        ("1.0", False),
        ("1.0+foo", False),
        ("1.0.post1.dev1", True),
        ("1.0.post1", True),
    ],
)
def test_version_is_postrelease(version: str, expected: bool):
    assert (Release.Post in Version.from_string(version).type) == expected


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.0.dev0", True),
        ("1.0.dev1", True),
        ("1.0a1.dev1", True),
        ("1.0b1.dev1", True),
        ("1.0c1.dev1", True),
        ("1.0rc1.dev1", True),
        ("1.0a1", True),
        ("1.0b1", True),
        ("1.0c1", True),
        ("1.0rc1", True),
        ("1.0a1.post1.dev1", True),
        ("1.0b1.post1.dev1", True),
        ("1.0c1.post1.dev1", True),
        ("1.0rc1.post1.dev1", True),
        ("1.0a1.post1", True),
        ("1.0b1.post1", True),
        ("1.0c1.post1", True),
        ("1.0rc1.post1", True),
        ("1.0", False),
        ("1.0+dev", False),
        ("1.0.post1", False),
        ("1.0.post1+dev", False),
    ],
)
def test_version_is_prerelease(version: str, expected: bool):
    assert (Release.Pre in Version.from_string(version).type) == expected


@pytest.mark.parametrize(
    ("left", "right", "op"),
    # Below we'll generate every possible combination of VERSIONS that
    # should be True for the given operator
    chain.from_iterable(
        # Verify that the less than (<) operator works correctly
        [[(x, y, operator.lt) for y in VERSIONS[i + 1 :]] for i, x in enumerate(VERSIONS)]
        +
        # Verify that the less than equal (<=) operator works correctly
        [[(x, y, operator.le) for y in VERSIONS[i:]] for i, x in enumerate(VERSIONS)]
        +
        # Verify that the equal (==) operator works correctly
        [[(x, x, operator.eq) for x in VERSIONS]]
        +
        # Verify that the not equal (!=) operator works correctly
        [
            [(x, y, operator.ne) for j, y in enumerate(VERSIONS) if i != j]
            for i, x in enumerate(VERSIONS)
        ]
        +
        # Verify that the greater than equal (>=) operator works correctly
        [[(x, y, operator.ge) for y in VERSIONS[: i + 1]] for i, x in enumerate(VERSIONS)]
        +
        # Verify that the greater than (>) operator works correctly
        [[(x, y, operator.gt) for y in VERSIONS[:i]] for i, x in enumerate(VERSIONS)]
    ),
)
def test_comparison_true(left: str, right: str, op: Callable[..., bool]):
    assert op(Version.from_string(left), Version.from_string(right))


@pytest.mark.parametrize(
    ("left", "right", "op"),
    # Below we'll generate every possible combination of VERSIONS that
    # should be False for the given operator
    chain.from_iterable(
        # Verify that the less than (<) operator works correctly
        [[(x, y, operator.lt) for y in VERSIONS[: i + 1]] for i, x in enumerate(VERSIONS)]
        +
        # Verify that the less than equal (<=) operator works correctly
        [[(x, y, operator.le) for y in VERSIONS[:i]] for i, x in enumerate(VERSIONS)]
        +
        # Verify that the equal (==) operator works correctly
        [
            [(x, y, operator.eq) for j, y in enumerate(VERSIONS) if i != j]
            for i, x in enumerate(VERSIONS)
        ]
        +
        # Verify that the not equal (!=) operator works correctly
        [[(x, x, operator.ne) for x in VERSIONS]]
        +
        # Verify that the greater than equal (>=) operator works correctly
        [[(x, y, operator.ge) for y in VERSIONS[i + 1 :]] for i, x in enumerate(VERSIONS)]
        +
        # Verify that the greater than (>) operator works correctly
        [[(x, y, operator.gt) for y in VERSIONS[i:]] for i, x in enumerate(VERSIONS)]
    ),
)
def test_comparison_false(left: str, right: str, op: Callable[..., bool]):
    assert not op(Version.from_string(left), Version.from_string(right))


def test_major_version():
    assert Version.from_string("2.1.0").major == 2


def test_minor_version():
    assert Version.from_string("2.1.0").minor == 1
    assert Version.from_string("2").minor == 0


def test_micro_version():
    assert Version.from_string("2.1.3").micro == 3
    assert Version.from_string("2.1").micro == 0
    assert Version.from_string("2").micro == 0


# =============================================================================
# Coverage: Version.search (line 175)
# =============================================================================


def test_version_search_finds_version_substring():
    """search() uses VERSION_RE.search (non-strict) to find a version in surrounding text."""
    v = Version.search("prefix 1.2.3 suffix")
    assert v == Version.from_string("1.2.3")


def test_version_search_raises_when_no_version_found():
    """search() raises VersionError when the string contains no valid version."""
    with pytest.raises(VersionError):
        Version.search("no version here")


def test_version_search_with_epoch():
    """search() finds a version with epoch embedded in text."""
    v = Version.search("build 1!3.2.1 done")
    assert v == Version.from_string("1!3.2.1")


# =============================================================================
# Coverage: tag property (lines 182-184)
# =============================================================================


def test_version_tag_property_returns_string():
    """tag property returns the string representation of the version."""
    v = Version.from_string("1.2.3")
    assert v.tag == "1.2.3"


def test_version_tag_property_caches_value():
    """tag property caches the result; second access returns the same object."""
    v = Version.from_string("1.2.3")
    first = v.tag
    second = v.tag
    assert first == second
    assert first is second


def test_version_tag_with_local():
    """tag includes local segment in the string."""
    v = Version.from_string("1.2.3+build42")
    assert v.tag == "1.2.3+build42"


def test_version_tag_with_epoch():
    """tag includes epoch prefix."""
    v = Version.from_string("2!1.0.0")
    assert v.tag == "2!1.0.0"


def test_version_tag_full():
    """tag with all components present."""
    v = Version.from_string("1!1.2.3a4.post5.dev6+local7")
    assert v.tag == "1!1.2.3a4.post5.dev6+local7"


# =============================================================================
# Coverage: Version.__init__ constructor (lines 245-284)
# =============================================================================


def test_version_init_basic():
    """Happy path: construct a simple version with positional args."""
    v = Version(1, 2, 3)
    assert v.major == 1
    assert v.minor == 2
    assert v.micro == 3
    assert v.epoch == 0
    assert v.pre is None
    assert v.post is None
    assert v.dev is None
    assert v.local is None


def test_version_init_with_epoch():
    v = Version(1, 0, 0, epoch=2)
    assert v.epoch == 2


def test_version_init_with_pre():
    v = Version(1, 0, 0, pre=("a", 1))
    assert v.pre == ("a", 1)


def test_version_init_with_post():
    v = Version(1, 0, 0, post=5)
    assert v.post == 5


def test_version_init_with_dev():
    v = Version(1, 0, 0, dev=3)
    assert v.dev == 3


def test_version_init_with_local():
    v = Version(1, 0, 0, local="abc")
    assert v.local == ("abc",)


def test_version_init_with_all_args():
    """Construct with every optional argument."""
    v = Version(1, 2, 3, epoch=1, pre=("a", 1), post=2, dev=3, local="abc")
    assert v == Version.from_string("1!1.2.3a1.post2.dev3+abc")


def test_version_init_negative_major_raises_value_error():
    """Lines 245-260: negative major triggers AssertionError → ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        Version(-1, 0, 0)


def test_version_init_negative_minor_raises_value_error():
    with pytest.raises(ValueError, match="non-negative"):
        Version(0, -1, 0)


def test_version_init_negative_micro_raises_value_error():
    with pytest.raises(ValueError, match="non-negative"):
        Version(0, 0, -1)


def test_version_init_negative_epoch_raises_value_error():
    with pytest.raises(ValueError, match="non-negative"):
        Version(0, 0, 0, epoch=-1)


def test_version_init_negative_post_raises_value_error():
    with pytest.raises(ValueError, match="non-negative"):
        Version(0, 0, 0, post=-1)


def test_version_init_negative_dev_raises_value_error():
    with pytest.raises(ValueError, match="non-negative"):
        Version(0, 0, 0, dev=-1)


def test_version_init_negative_pre_number_raises_value_error():
    with pytest.raises(ValueError, match="non-negative"):
        Version(0, 0, 0, pre=("a", -1))


def test_version_init_non_integer_raises_value_error():
    """Non-numeric components trigger TypeError → ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        Version("1", 0, 0)  # pyright: ignore[reportArgumentType]


def test_version_init_invalid_pre_symbol_raises_value_error():
    """Lines 265-270: pre symbol not in PRE_SYMOBOLS raises ValueError."""
    with pytest.raises(ValueError, match="invalid symbol"):
        Version(0, 0, 0, pre=("x", 1))  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]


def test_version_init_another_invalid_pre_symbol():
    with pytest.raises(ValueError, match="invalid symbol"):
        Version(0, 0, 0, pre=("gamma", 1))  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]


def test_version_init_valid_pre_symbols_all_accepted():
    """All valid pre symbols are accepted without error."""
    for symbol in ("a", "alpha", "b", "beta", "pre", "preview", "c", "rc"):
        v = Version(1, 0, 0, pre=(symbol, 1))
        assert v.pre is not None


def test_version_init_invalid_local_raises_value_error():
    """Line 279/315-316: split_local raises ValueError for invalid local."""
    with pytest.raises(ValueError, match="invalid local version labels"):
        Version(1, 0, 0, local="a+b+c!d")


def test_version_init_invalid_local_special_chars():
    with pytest.raises(ValueError, match="invalid local version labels"):
        Version(1, 0, 0, local="foo@bar")


def test_version_init_invalid_local_empty_segments():
    with pytest.raises(ValueError, match="invalid local version labels"):
        Version(1, 0, 0, local="+")


def test_version_init_local_with_numbers():
    """Local labels with digits are accepted."""
    v = Version(1, 0, 0, local="123")
    assert v.local == (123,)


def test_version_init_local_with_mixed():
    """Local labels mixing letters and digits separated by dots."""
    v = Version(1, 0, 0, local="abc.123.def")
    assert v.local == ("abc", 123, "def")


# =============================================================================
# Coverage: _parse success path (lines 291-310) — post via dash syntax
# =============================================================================


def test_parse_post_via_dash_syntax():
    """Cover post_n1 branch (line 298-300): '1.0-5' uses dash notation."""
    v = Version.from_string("1.0-5")
    assert v.post == 5


def test_parse_post_via_post_label():
    """Cover post_n2 branch (line 301-302): '1.0.post1' uses post label."""
    v = Version.from_string("1.0.post1")
    assert v.post == 1


def test_parse_post_via_r_synonym():
    """Cover post_l branch with 'r' synonym."""
    v = Version.from_string("1.0r1")
    assert v.post == 1


def test_parse_post_via_rev_synonym():
    """Cover post_l branch with 'rev' synonym."""
    v = Version.from_string("1.0rev1")
    assert v.post == 1


def test_parse_no_post():
    """Cover post = None branch (line 303)."""
    v = Version.from_string("1.0.0")
    assert v.post is None


def test_parse_dev_with_number():
    """Cover dev_n branch (line 305)."""
    v = Version.from_string("1.0.0.dev5")
    assert v.dev == 5


def test_parse_dev_without_number():
    """Cover dev_n default (line 305): dev without explicit number → 0."""
    v = Version.from_string("1.0.0.dev")
    assert v.dev == 0


def test_parse_local_with_digits_and_letters():
    """Cover local parsing (line 306) with mixed content."""
    v = Version.from_string("1.0+abc.123.def456")
    assert v.local == ("abc", 123, "def456")


def test_parse_epoch():
    """Cover epoch parsing (line 293)."""
    v = Version.from_string("2!1.0.0")
    assert v.epoch == 2


def test_parse_tag_stored():
    """Cover _tag assignment (line 307)."""
    v = Version.from_string("1.2.3")
    assert v._tag == "1.2.3"  # pyright: ignore[reportPrivateUsage]


# =============================================================================
# Coverage: split_local ValueError (lines 315-316)
# =============================================================================


def test_split_local_valid_string():
    """split_local accepts a valid local label."""
    result = Version.split_local("abc123")
    assert result == ("abc123",)


def test_split_local_segments():
    """split_local splits on separators."""
    result = Version.split_local("abc.def")
    assert result == ("abc", "def")


def test_split_local_with_digits():
    """split_local converts digit-only segments to int."""
    result = Version.split_local("123")
    assert result == (123,)


def test_split_local_invalid_with_special_chars():
    """split_local raises ValueError for strings not matching LOCAL_RE."""
    with pytest.raises(ValueError, match="invalid local version labels"):
        Version.split_local("foo@bar")


def test_split_local_invalid_with_spaces():
    with pytest.raises(ValueError, match="invalid local version labels"):
        Version.split_local("has space")


def test_split_local_invalid_with_plus():
    with pytest.raises(ValueError, match="invalid local version labels"):
        Version.split_local("a+b")


def test_split_local_invalid_with_exclamation():
    with pytest.raises(ValueError, match="invalid local version labels"):
        Version.split_local("a!b")
