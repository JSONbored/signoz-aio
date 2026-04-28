from __future__ import annotations

from pathlib import Path

from scripts import components


def test_load_components_reads_signoz_suite_manifest() -> None:
    loaded = components.load_components()

    assert [component.name for component in loaded] == [  # nosec B101
        "signoz-aio",
        "signoz-agent",
    ]
    assert loaded[0].template == Path("signoz-aio.xml")  # nosec B101
    assert loaded[0].release_suffix == "aio"  # nosec B101
    assert loaded[1].context == Path("components/signoz-agent")  # nosec B101
    assert loaded[1].template == Path("signoz-agent.xml")  # nosec B101
    assert loaded[1].dockerhub_image == "jsonbored/signoz-agent"  # nosec B101
    assert loaded[1].release_suffix == "agent"  # nosec B101


def test_changed_components_selects_component_specific_paths() -> None:
    selected = components.changed_components(["components/signoz-agent/Dockerfile"])
    assert [component.name for component in selected] == ["signoz-agent"]  # nosec B101

    selected = components.changed_components(["Dockerfile"])
    assert [component.name for component in selected] == ["signoz-aio"]  # nosec B101

    selected = components.changed_components(["scripts/components.py"])
    assert [component.name for component in selected] == [  # nosec B101
        "signoz-aio",
        "signoz-agent",
    ]
