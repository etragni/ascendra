"""Linux target (planned for v0.3): OS upgrades for fleets of cloud and on-prem machines.

Planned domain agents:
  Scout          inventory via SSH / Ansible facts / cloud APIs: distro, release, kernel, packages, uptime
  Compatibility  EOL dates, supported upgrade paths (e.g. RHEL 8 -> 9 via Leapp, Ubuntu LTS -> LTS),
                 kernel module and driver compatibility, third-party repositories
  Researcher     security advisories (USN, RHSA/ALAS...), package changelogs, pending reboots
  Planner        rolling waves respecting service redundancy (one replica at a time), maintenance windows
"""
from ascendra.targets.base import PlannedTarget


class LinuxTarget(PlannedTarget):
    name = "linux"
    title = "Linux OS"
    description = "Distribution upgrades and patching for cloud and on-prem machines"
