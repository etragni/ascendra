"""VMware target (planned): vCenter and ESXi upgrades.

Planned domain agents:
  Scout          vCenter / ESXi inventory (pyVmomi): versions, clusters, hosts, VMs, VIBs, hardware
  Compatibility  supported upgrade paths, hardware and driver/VIB compatibility, VM hardware versions
  Researcher     release notes, known issues, patch levels
  Planner        vCenter first, then hosts cluster by cluster with maintenance mode and DRS evacuation
"""
from ascendra.targets.base import PlannedTarget


class VMwareTarget(PlannedTarget):
    name = "vmware"
    title = "VMware vSphere"
    description = "vCenter and ESXi host upgrades, cluster by cluster"
