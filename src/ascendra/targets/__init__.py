"""Registry of upgrade targets. Add a new platform by implementing ascendra.targets.base.Target."""
from __future__ import annotations

from ascendra.targets.base import Target
from ascendra.targets.kubernetes import KubernetesTarget
from ascendra.targets.linux import LinuxTarget
from ascendra.targets.vmware import VMwareTarget

TARGETS: dict[str, Target] = {t.name: t for t in (KubernetesTarget(), LinuxTarget(), VMwareTarget())}


def get_target(name: str) -> Target:
    for t in TARGETS.values():
        if name == t.name or name in t.aliases:
            return t
    raise KeyError(f"unknown target '{name}', available: {', '.join(TARGETS)}")
