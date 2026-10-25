import pytest

from ascendra.config import Config
from ascendra.targets import TARGETS, get_target


def test_registry():
    assert get_target("k8s").name == "kubernetes"
    assert {"kubernetes", "linux", "vmware"} <= set(TARGETS)


@pytest.mark.parametrize("name", ["linux", "vmware"])
def test_planned_targets_are_explicit(name):
    t = get_target(name)
    assert t.status == "planned"
    with pytest.raises(NotImplementedError):
        t.domain_agents({})


def test_config_sections(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text("llm: {provider: openai}\nkubernetes: {cluster: prod}\n")
    cfg = Config.load(p)
    assert cfg.llm.provider == "openai" and cfg.section("kubernetes") == {"cluster": "prod"}
    assert cfg.section("linux") == {}
