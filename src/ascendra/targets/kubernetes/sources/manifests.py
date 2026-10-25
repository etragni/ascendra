"""Parse Kubernetes objects out of YAML (files, directories or rendered Helm manifests)."""
from __future__ import annotations

from pathlib import Path

import yaml

from ascendra.targets.kubernetes.models import KubeObject


def parse_manifest_text(text: str, source: str) -> list[KubeObject]:
    objects: list[KubeObject] = []
    try:
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError:
        return objects  # templated / invalid YAML is skipped, not fatal
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if doc.get("kind", "").endswith("List") and isinstance(doc.get("items"), list):
            for item in doc["items"]:
                objects.extend(parse_manifest_text(yaml.safe_dump(item), source))
            continue
        if "apiVersion" in doc and "kind" in doc:
            meta = doc.get("metadata") or {}
            objects.append(
                KubeObject(
                    api_version=doc["apiVersion"],
                    kind=doc["kind"],
                    name=meta.get("name", "<unnamed>"),
                    namespace=meta.get("namespace"),
                    source=source,
                )
            )
    return objects


def scan_paths(paths: list[Path]) -> list[KubeObject]:
    objects: list[KubeObject] = []
    for root in paths:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.suffix in (".yaml", ".yml"))
        for f in files:
            objects.extend(parse_manifest_text(f.read_text(errors="replace"), str(f)))
    return objects
