from __future__ import annotations

import json
import re
from pathlib import Path

from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "Dockerfile"
CONFIG_MATRIX = ROOT / "docs" / "configuration-matrix.md"
UPSTREAM_SIGNOZ_ENV_FIXTURE = (
    ROOT / "tests" / "fixtures" / "signoz-v0.120.0-upstream-env.txt"
)

SECRET_KEYWORDS = (
    "ACCESS_KEY",
    "API_KEY",
    "AUTH_TOKEN",
    "CLIENT_SECRET",
    "PASSWORD",
    "PRIVATE_KEY",
    "SECRET",
    "TOKEN",
)

OPTIONAL_SENSITIVE_PATH_TARGETS = {
    "/hostfs": "ro",
    "/var/lib/docker/containers": "ro",
    "/var/run/docker.sock": "rw",
}

PRIVACY_OPT_IN_DEFAULT_FALSE_TARGETS = {
    "SIGNOZ_ANALYTICS_ENABLED",
    "SIGNOZ_SERVICEACCOUNT_ANALYTICS_ENABLED",
    "SIGNOZ_STATSREPORTER_COLLECT_IDENTITIES",
    "SIGNOZ_STATSREPORTER_ENABLED",
}


def _template_path() -> Path:
    candidates = sorted(ROOT.glob("*.xml"))
    assert candidates, "repository must include an Unraid XML template"  # nosec B101
    return candidates[0]


def _template_root() -> ET.Element:
    return ET.parse(_template_path()).getroot()


def _dockerfile_text() -> str:
    return DOCKERFILE.read_text()


def _dockerfile_volumes() -> set[str]:
    volumes: set[str] = set()
    for match in re.finditer(r"(?m)^VOLUME\s+(\[[^\]]+\])", _dockerfile_text()):
        volumes.update(json.loads(match.group(1)))
    return volumes


def _exposed_ports() -> set[str]:
    ports: set[str] = set()
    for line in _dockerfile_text().splitlines():
        if not line.startswith("EXPOSE "):
            continue
        for token in line.split()[1:]:
            ports.add(token.split("/", 1)[0])
    return ports


def _arg_defaults() -> dict[str, str]:
    defaults: dict[str, str] = {}
    for line in _dockerfile_text().splitlines():
        if not line.startswith("ARG ") or "=" not in line:
            continue
        name, value = line.removeprefix("ARG ").split("=", 1)
        defaults[name] = value
    return defaults


def _config_elements() -> list[ET.Element]:
    return list(_template_root().findall("Config"))


def _configs_by_target() -> dict[str, ET.Element]:
    return {
        config.get("Target"): config
        for config in _config_elements()
        if config.get("Target")
    }


def test_unraid_metadata_contract_is_complete_and_unprivileged() -> None:
    root = _template_root()

    assert root.findtext("Privileged") == "false"  # nosec B101
    for tag in (
        "Name",
        "Repository",
        "Support",
        "Project",
        "TemplateURL",
        "Icon",
        "Category",
        "WebUI",
    ):
        value = root.findtext(tag)
        assert value and value.strip(), f"{tag} must be populated"  # nosec B101
    assert (
        _config_elements()
    ), "template must expose configurable settings"  # nosec B101


def test_secret_like_template_variables_are_masked() -> None:
    for config in _config_elements():
        name = config.get("Name") or ""
        target = config.get("Target") or ""
        default = config.get("Default") or ""
        if (
            target.endswith("_PATH")
            or target.endswith("_FILE")
            or target.endswith("_ENABLED")
            or target.startswith(("MAX_", "MIN_"))
            or "MAX__TOKEN__LIFETIME" in target
            or "TOKEN_LIFETIME" in target
            or "TOKENIZER_LIFETIME" in target
            or "TOKENIZER_ROTATION" in target
            or "IDENTN_TOKENIZER_HEADERS" in target
            or "TOKENIZER_OPAQUE_GC" in target
            or "TOKENIZER_OPAQUE_TOKEN_MAX" in target
            or name.upper().endswith(" PATH")
            or set(default.split("|")) == {"false", "true"}
        ):
            continue
        haystack = " ".join(filter(None, (name, target))).upper()
        if any(keyword in haystack for keyword in SECRET_KEYWORDS):
            assert (
                config.get("Mask") == "true"
            ), (  # nosec B101
                f"{config.get('Name') or config.get('Target')} should be masked"
            )


def test_beginner_surface_is_minimal_and_fixed_booleans_are_dropdowns() -> None:
    always_visible = [
        config.get("Target")
        for config in _config_elements()
        if config.get("Display") == "always"
    ]
    assert always_visible == [  # nosec B101
        "8080",
        "4317",
        "4318",
        "/appdata",
    ]

    fixed_boolean_targets = {
        "LOW_CARDINAL_EXCEPTION_GROUPING",
        "SIGNOZ_ANALYTICS_ENABLED",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__REQUIRE__TLS",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CONFIG_INSECURE__SKIP__VERIFY",
        "SIGNOZ_AUDITOR_OTLPHTTP_INSECURE",
        "SIGNOZ_AUDITOR_OTLPHTTP_RETRY_ENABLED",
        "SIGNOZ_EMAILING_ENABLED",
        "SIGNOZ_EMAILING_SMTP_TLS_ENABLED",
        "SIGNOZ_EMAILING_SMTP_TLS_INSECURE__SKIP__VERIFY",
        "SIGNOZ_EMAILING_TEMPLATES_FORMAT_FOOTER_ENABLED",
        "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HEADER_ENABLED",
        "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HELP_ENABLED",
        "SIGNOZ_ENABLE_HOST_AGENT",
        "SIGNOZ_IDENTN_APIKEY_ENABLED",
        "SIGNOZ_IDENTN_IMPERSONATION_ENABLED",
        "SIGNOZ_IDENTN_TOKENIZER_ENABLED",
        "SIGNOZ_INSTRUMENTATION_METRICS_ENABLED",
        "SIGNOZ_INSTRUMENTATION_TRACES_ENABLED",
        "SIGNOZ_OTEL_COLLECTOR_CLICKHOUSE_REPLICATION",
        "SIGNOZ_PPROF_ENABLED",
        "SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_ENABLED",
        "SIGNOZ_SERVICEACCOUNT_ANALYTICS_ENABLED",
        "SIGNOZ_STATSREPORTER_ENABLED",
        "SIGNOZ_STATSREPORTER_COLLECT_IDENTITIES",
        "SIGNOZ_USE_EXTERNAL_CLICKHOUSE",
        "SIGNOZ_USER_PASSWORD_RESET_ALLOW__SELF",
        "SIGNOZ_USER_ROOT_ENABLED",
        "SIGNOZ_VERSION_BANNER_ENABLED",
    }
    configs_by_target = _configs_by_target()
    for target in fixed_boolean_targets:
        config = configs_by_target[target]
        assert config.get("Default") in {  # nosec B101
            "false|true",
            "true|false",
        }, f"{target} should use a pipe-delimited Unraid dropdown"

    expected_dropdowns = {
        "SIGNOZ_AUDITOR_PROVIDER": "noop|otlphttp",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__MAX__VERSION": "upstream|TLS12|TLS13",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__MIN__VERSION": "upstream|TLS12|TLS13",
        "SIGNOZ_CACHE_PROVIDER": "memory|redis",
        "SIGNOZ_FLAGGER_CONFIG_BOOLEAN_KAFKA__SPAN__EVAL": "upstream|true|false",
        "SIGNOZ_FLAGGER_CONFIG_BOOLEAN_USE__SPAN__METRICS": "upstream|true|false",
        "SIGNOZ_INSTRUMENTATION_LOGS_LEVEL": "info|debug|warn|error",
        "SIGNOZ_SQLSTORE_PROVIDER": "sqlite|postgres",
        "SIGNOZ_SQLSTORE_SQLITE_MODE": "wal|delete",
        "SIGNOZ_SQLSTORE_SQLITE_TRANSACTION__MODE": "deferred|immediate|exclusive",
    }
    for target, expected_default in expected_dropdowns.items():
        config = configs_by_target[target]
        assert config.get("Default") == expected_default  # nosec B101


def test_upstream_signoz_config_surface_is_exposed_or_classified() -> None:
    targets = {config.get("Target") for config in _config_elements()}
    docs = CONFIG_MATRIX.read_text()
    upstream_keys = {
        line.strip()
        for line in UPSTREAM_SIGNOZ_ENV_FIXTURE.read_text().splitlines()
        if line.strip()
    }

    unaccounted = sorted(
        key for key in upstream_keys if key not in targets and key not in docs
    )
    assert not unaccounted, (  # nosec B101
        "upstream SigNoz env keys must be exposed in XML or classified in docs: "
        + ", ".join(unaccounted)
    )


def test_required_appdata_paths_are_declared_as_container_volumes() -> None:
    volumes = _dockerfile_volumes()
    assert volumes, "Dockerfile must declare persistent volumes"  # nosec B101

    for config in _config_elements():
        if config.get("Type") != "Path" or config.get("Required") != "true":
            continue
        default = config.get("Default") or config.text or ""
        target = config.get("Target") or ""
        if not default.startswith("/mnt/user/appdata"):
            continue
        assert any(
            target == volume or target.startswith(f"{volume.rstrip('/')}/")
            for volume in volumes
        ), f"{target} must be covered by a Dockerfile VOLUME"  # nosec B101


def test_template_ports_are_exposed_by_image() -> None:
    exposed_ports = _exposed_ports()
    assert exposed_ports, "Dockerfile must expose template ports"  # nosec B101

    for config in _config_elements():
        if config.get("Type") == "Port":
            assert config.get("Target") in exposed_ports  # nosec B101


def test_dockerfile_has_runtime_safety_contract() -> None:
    dockerfile = _dockerfile_text()
    arg_defaults = _arg_defaults()
    from_lines = [
        line.split()[1] for line in dockerfile.splitlines() if line.startswith("FROM ")
    ]

    assert from_lines, "Dockerfile must declare at least one base image"  # nosec B101
    for image in from_lines:
        image_arg_defaults = [
            arg_defaults.get(arg_name, "")
            for arg_name in re.findall(r"\$\{([^}]+)\}", image)
        ]
        assert (  # nosec B101
            "@sha256:" in image
            or any(default.startswith("sha256:") for default in image_arg_defaults)
            or any("@sha256:" in default for default in image_arg_defaults)
        ), f"{image} must be digest-pinned"

    assert "HEALTHCHECK" in dockerfile  # nosec B101
    assert "curl -fsS" in dockerfile  # nosec B101
    assert 'ENTRYPOINT ["/init"]' in dockerfile  # nosec B101
    assert "S6_CMD_WAIT_FOR_SERVICES_MAXTIME" in dockerfile  # nosec B101
    assert "S6_BEHAVIOUR_IF_STAGE2_FAILS=2" in dockerfile  # nosec B101


def test_optional_host_agent_mounts_are_blank_and_explicit_by_default() -> None:
    configs_by_target = _configs_by_target()

    for target, expected_mode in OPTIONAL_SENSITIVE_PATH_TARGETS.items():
        config = configs_by_target[target]
        description = (config.get("Description") or "").lower()

        assert config.get("Type") == "Path"  # nosec B101
        assert config.get("Display") == "advanced"  # nosec B101
        assert config.get("Required") == "false"  # nosec B101
        assert config.get("Mode") == expected_mode  # nosec B101
        assert config.get("Default") == ""  # nosec B101
        assert (config.text or "").strip() == ""  # nosec B101
        assert "leave blank" in description  # nosec B101

    socket_description = (
        configs_by_target["/var/run/docker.sock"].get("Description") or ""
    ).lower()
    assert "docker control access" in socket_description  # nosec B101


def test_privacy_sensitive_telemetry_defaults_are_opt_in() -> None:
    configs_by_target = _configs_by_target()

    for target in PRIVACY_OPT_IN_DEFAULT_FALSE_TARGETS:
        config = configs_by_target[target]
        assert config.get("Default") == "false|true"  # nosec B101
        assert (config.text or "").strip() == "false"  # nosec B101
