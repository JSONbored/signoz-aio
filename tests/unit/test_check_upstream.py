from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def load_check_upstream() -> ModuleType:
    path = Path("scripts/check-upstream.py")
    spec = importlib.util.spec_from_file_location("check_upstream", path)
    assert spec is not None and spec.loader is not None  # nosec B101
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collect_compose_image_tags_resolves_default_substitutions() -> None:
    check_upstream = load_check_upstream()

    compose_text = """
    services:
      clickhouse:
        image: clickhouse/clickhouse-server:25.5.6
      signoz:
        image: signoz/signoz:${VERSION:-v0.120.0}
      otel-collector:
        image: "signoz/signoz-otel-collector:${OTELCOL_TAG:-v0.144.3}"
      zookeeper:
        image: 'signoz/zookeeper:3.7.1'
    """

    assert check_upstream.collect_compose_image_tags(compose_text) == {  # nosec B101
        "clickhouse/clickhouse-server": "25.5.6",
        "signoz/signoz": "v0.120.0",
        "signoz/signoz-otel-collector": "v0.144.3",
        "signoz/zookeeper": "3.7.1",
    }


def test_expected_compose_dependency_values_include_digests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    check_upstream = load_check_upstream()

    monkeypatch.setattr(
        check_upstream,
        "http_text",
        lambda _url: "\n".join(
            [
                "services:",
                "  clickhouse:",
                "    image: clickhouse/clickhouse-server:25.5.6",
                "  otel:",
                "    image: signoz/signoz-otel-collector:${OTELCOL_TAG:-v0.144.3}",
            ]
        ),
    )
    monkeypatch.setattr(
        check_upstream,
        "dockerhub_digest_for_tag",
        lambda image, tag: f"sha256:{image.replace('/', '-')}-{tag}",
    )

    expected = check_upstream.expected_compose_dependency_values(
        upstream={"repo": "SigNoz/signoz"},
        compose_dependencies={
            "path": "deploy/docker/docker-compose.yaml",
            "UPSTREAM_CLICKHOUSE_VERSION": "clickhouse/clickhouse-server",
            "UPSTREAM_OTELCOL_VERSION": "signoz/signoz-otel-collector",
        },
        version="v0.120.0",
    )

    assert expected == {  # nosec B101
        "UPSTREAM_CLICKHOUSE_VERSION": (
            "25.5.6@sha256:clickhouse-clickhouse-server-25.5.6"
        ),
        "UPSTREAM_OTELCOL_VERSION": (
            "v0.144.3@sha256:signoz-signoz-otel-collector-v0.144.3"
        ),
    }


def test_compose_dependency_mismatches_detects_tag_and_digest_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    check_upstream = load_check_upstream()
    local_values = {
        "UPSTREAM_CLICKHOUSE_VERSION": "26.3.9@sha256:newer",
        "UPSTREAM_OTELCOL_VERSION": "v0.144.3@sha256:old",
    }

    monkeypatch.setattr(
        check_upstream, "read_local_value", lambda key: local_values[key]
    )

    mismatches = check_upstream.compose_dependency_mismatches(
        {
            "UPSTREAM_CLICKHOUSE_VERSION": "25.5.6@sha256:upstream",
            "UPSTREAM_OTELCOL_VERSION": "v0.144.3@sha256:current",
        }
    )

    assert mismatches == {  # nosec B101
        "UPSTREAM_CLICKHOUSE_VERSION": "26.3.9@sha256:newer -> 25.5.6@sha256:upstream",
        "UPSTREAM_OTELCOL_VERSION": "v0.144.3@sha256:old -> v0.144.3@sha256:current",
    }


def test_renovate_does_not_update_upstream_compose_managed_images() -> None:
    config = json.loads(Path("renovate.json").read_text())
    disabled_rules = [
        rule for rule in config["packageRules"] if rule.get("enabled") is False
    ]

    assert any(  # nosec B101
        set(rule.get("matchPackageNames", []))
        >= {
            "clickhouse/clickhouse-server",
            "signoz/signoz",
            "signoz/signoz-otel-collector",
            "signoz/zookeeper",
        }
        for rule in disabled_rules
    )
