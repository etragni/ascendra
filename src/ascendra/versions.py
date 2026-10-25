"""Version parsing and Helm-style (Masterminds semver) constraint matching.

Kept dependency-free on purpose: it is the deterministic core every agent relies on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering

_VERSION_RE = re.compile(r"^\s*v?(\d+)(?:\.(\d+|x|X|\*))?(?:\.(\d+|x|X|\*))?(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?\s*$")


@total_ordering
@dataclass(frozen=True)
class Version:
    major: int
    minor: int = 0
    patch: int = 0
    prerelease: str = ""

    @classmethod
    def parse(cls, raw: str) -> Version:
        m = _VERSION_RE.match(str(raw))
        if not m:
            raise ValueError(f"not a version: {raw!r}")
        major, minor, patch, pre = m.groups()
        def to_int(p):
            return int(p) if p and p.isdigit() else 0
        return cls(int(major), to_int(minor), to_int(patch), pre or "")

    @classmethod
    def try_parse(cls, raw: str | None) -> Version | None:
        try:
            return cls.parse(raw) if raw else None
        except ValueError:
            return None

    @property
    def minor_str(self) -> str:
        return f"{self.major}.{self.minor}"

    def _key(self):
        # a prerelease sorts before the release it precedes
        return (self.major, self.minor, self.patch, self.prerelease == "", self.prerelease)

    def __lt__(self, other: Version) -> bool:
        return self._key() < other._key()

    def __str__(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        return f"{s}-{self.prerelease}" if self.prerelease else s


def _release(v: Version) -> Version:
    return Version(v.major, v.minor, v.patch)


def _check(op: str, raw: str, v: Version) -> bool:
    m = _VERSION_RE.match(raw)
    if not m:
        raise ValueError(f"bad constraint version: {raw!r}")
    _major, minor, patch, _ = m.groups()
    def wild(p):
        return p is None or p in ("x", "X", "*")
    c = _release(Version.parse(raw))
    v = _release(v)  # prerelease tags such as "-0" are ignored for matching cluster versions

    # wildcards: "1.2.x", "1.x", "1.2"
    if op in ("", "=") and (wild(minor) or wild(patch)):
        if wild(minor):
            return v.major == c.major
        return v.major == c.major and v.minor == c.minor
    if op in ("~", "~>"):
        upper = Version(c.major + 1) if minor is None else Version(c.major, c.minor + 1)
        return c <= v < upper
    if op == "^":
        if c.major > 0:
            upper = Version(c.major + 1)
        elif c.minor > 0:
            upper = Version(0, c.minor + 1)
        else:
            upper = Version(0, 0, c.patch + 1)
        return c <= v < upper
    return {
        "": v == c, "=": v == c, "!=": v != c,
        ">": v > c, "<": v < c,
        ">=": v >= c, "=>": v >= c,
        "<=": v <= c, "=<": v <= c,
    }[op]


_TERM_RE = re.compile(r"(>=|=>|<=|=<|!=|~>|>|<|=|~|\^)?\s*(v?[0-9xX*][0-9A-Za-z.*+-]*)")


def satisfies(version: str | Version, constraint: str | None) -> bool:
    """True if `version` satisfies a Helm `kubeVersion`-style constraint. Empty constraint matches all."""
    if not constraint or not constraint.strip():
        return True
    v = version if isinstance(version, Version) else Version.parse(version)
    for alternative in constraint.split("||"):
        alt = alternative.strip()
        # hyphen range: "1.20 - 1.28"
        hy = re.match(r"^(\S+)\s+-\s+(\S+)$", alt)
        if hy:
            if _check(">=", hy.group(1), v) and _check("<=", hy.group(2), v):
                return True
            continue
        terms = _TERM_RE.findall(alt.replace(",", " "))
        if terms and all(_check(op or "", ver, v) for op, ver in terms):
            return True
    return False


def supports_minor(minor: Version, constraint: str | None) -> bool:
    """Does the constraint accept *some* patch release of a Kubernetes minor (e.g. 1.31)?"""
    return any(satisfies(Version(minor.major, minor.minor, p), constraint) for p in (0, 99))


def minor_hops(current: Version, target: Version) -> list[Version]:
    """Control-plane upgrades must go one minor at a time: 1.29 -> 1.32 gives [1.30, 1.31, 1.32]."""
    if target.major != current.major:
        raise ValueError("major-version Kubernetes upgrades are not supported")
    return [Version(current.major, m) for m in range(current.minor + 1, target.minor + 1)]
