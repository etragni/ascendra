import pytest

from ascendra.versions import Version, minor_hops, satisfies, supports_minor


@pytest.mark.parametrize("v,c,ok", [
    ("1.30.2", ">=1.22.0-0", True),
    ("1.31.0", ">= 1.22.0-0 < 1.31.0-0", False),
    ("1.30.9", ">= 1.22.0-0 < 1.31.0-0", True),
    ("1.29.0", ">=1.26.0-0, <1.32.0-0", True),
    ("1.27.3", "~1.27.0", True),
    ("1.28.0", "~1.27.0", False),
    ("1.30.0", "1.28 - 1.30", True),
    ("1.31.0", "1.28 - 1.30", False),
    ("1.30.1", "1.30.x", True),
    ("1.25.0", "<1.24 || >=1.25", True),
    ("1.30.0", "", True),
])
def test_satisfies(v, c, ok):
    assert satisfies(v, c) is ok


def test_supports_minor_patch_tolerance():
    assert supports_minor(Version.parse("1.30"), ">=1.30.1")
    assert not supports_minor(Version.parse("1.31"), "<1.31.0-0")


def test_ordering_and_hops():
    assert Version.parse("v1.2.3-rc.1") < Version.parse("1.2.3")
    assert [v.minor_str for v in minor_hops(Version.parse("1.29.4"), Version.parse("1.32"))] == ["1.30", "1.31", "1.32"]
