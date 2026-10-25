from __future__ import annotations

from pydantic import BaseModel, Field


class KubernetesConfig(BaseModel):
    """The `kubernetes:` section of ascendra.yaml."""

    cluster: str = "cluster"
    # chart name -> Helm repository URL or local dir with an index.yaml (overrides `helm repo list` discovery)
    charts: dict[str, str] = Field(default_factory=dict)
    # releases to leave alone, as "<namespace>/<release>"
    ignore_releases: list[str] = Field(default_factory=list)
    allow_prerelease_charts: bool = False
