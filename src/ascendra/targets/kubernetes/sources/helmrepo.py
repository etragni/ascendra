"""Fetch and query Helm repository index.yaml files (HTTP(S) or local file paths)."""
from __future__ import annotations

from pathlib import Path

import httpx
import yaml

from ascendra.versions import Version


class HelmRepoIndex:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}

    def load(self, repo_url: str) -> dict:
        if repo_url not in self._cache:
            if repo_url.startswith(("http://", "https://")):
                resp = httpx.get(repo_url.rstrip("/") + "/index.yaml", timeout=30, follow_redirects=True)
                resp.raise_for_status()
                text = resp.text
            else:
                path = Path(repo_url.removeprefix("file://"))
                text = (path / "index.yaml" if path.is_dir() else path).read_text()
            self._cache[repo_url] = yaml.safe_load(text) or {}
        return self._cache[repo_url]

    def entries(self, repo_url: str, chart: str, allow_prerelease: bool = False) -> list[dict]:
        """Chart versions, newest first."""
        raw = (self.load(repo_url).get("entries") or {}).get(chart, [])
        out = []
        for e in raw:
            v = Version.try_parse(e.get("version"))
            if v is None or (v.prerelease and not allow_prerelease):
                continue
            out.append({**e, "_v": v})
        return sorted(out, key=lambda e: e["_v"], reverse=True)

    def has_chart(self, repo_url: str, chart: str) -> bool:
        try:
            return chart in (self.load(repo_url).get("entries") or {})
        except (OSError, ValueError, httpx.HTTPError, yaml.YAMLError):
            return False
