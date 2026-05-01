#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess  # nosec B404
import sys
from pathlib import Path

from defusedxml import ElementTree as ET

try:
    from components import load_components
except ImportError:  # pragma: no cover - used when imported as a package module
    from scripts.components import load_components

ROOT = Path(__file__).resolve().parents[1]

GENERATED_CHANGELOG_NOTE = (
    "Generated from CHANGELOG.md during release preparation. Do not edit manually."
)
GENERATED_CHANGELOG_BULLET = f"- {GENERATED_CHANGELOG_NOTE}"
CHANGELOG_HEADER_PATTERN = re.compile(
    r"^### (?:\d{4}-\d{2}-\d{2}|Replace with release date)$"
)
LEGACY_CHANGELOG_MARKERS = (
    "[b]Latest release[/b]",
    "GitHub Releases",
    "Full changelog and release notes:",
)
EXPECTED_CATEGORY = "Network:Management Tools:Utilities"
EXPECTED_DONATE_TEXT = "Support JSONbored on GitHub Sponsors."
EXPECTED_DONATE_LINK = "https://github.com/sponsors/JSONbored"
AIO_EXTRA_SEARCH_TERMS = (
    "observability monitoring telemetry opentelemetry otel traces metrics logs apm "
    "clickhouse dashboards alerts collector"
)
AIO_REQUIRES_TERMS = (
    "4GB Docker memory",
    "Back up /appdata",
    "/var/run/docker.sock",
    "Docker control access",
)
AGENT_EXTRA_SEARCH_TERMS = (
    "observability monitoring telemetry opentelemetry otel collector agent traces "
    "metrics logs prometheus docker hostmetrics signoz"
)
AGENT_REQUIRES_TERMS = (
    "reachable SigNoz OTLP endpoint",
    "default 4317 and 4318 host ports will conflict",
    "/var/run/docker.sock",
    "Docker control access",
)


def run_common_template_validation() -> int:
    candidates = []
    explicit = os.environ.get("AIO_FLEET_MANIFEST", "").strip()
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            ROOT / ".aio-fleet" / "fleet.yml",
            ROOT.parent / "aio-fleet" / "fleet.yml",
        ]
    )
    manifest = next((candidate for candidate in candidates if candidate.exists()), None)
    if manifest is None:
        print(
            "warning: aio-fleet manifest not found; skipping common template validation",
            file=sys.stderr,
        )
        return 0

    env = os.environ.copy()
    fleet_src = manifest.parent / "src"
    if fleet_src.exists():
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{fleet_src}{os.pathsep}{existing}" if existing else str(fleet_src)
        )
    python = sys.executable
    fleet_python = manifest.parent / ".venv" / "bin" / "python"
    if fleet_python.exists():
        python = str(fleet_python)

    result = subprocess.run(  # nosec B603
        [
            python,
            "-m",
            "aio_fleet.cli",
            "--manifest",
            str(manifest),
            "validate-template-common",
            "--repo",
            ROOT.name,
            "--repo-path",
            str(ROOT),
        ],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode


REQUIRED_TEXT_FIELDS = (
    "Support",
    "Project",
    "Overview",
    "Category",
    "TemplateURL",
    "Icon",
    "ExtraSearchTerms",
    "Requires",
    "DonateText",
    "DonateLink",
    "Changes",
)

REQUIRED_TARGETS = {
    "/appdata",
    "/hostfs",
    "/var/lib/docker/containers",
    "/var/run/docker.sock",
    "4317",
    "4318",
    "8080",
    "LOW_CARDINAL_EXCEPTION_GROUPING",
    "OTEL_RESOURCE_ATTRIBUTES",
    "SIGNOZ_AIO_WAIT_TIMEOUT_SECONDS",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_ALERTS_GC__INTERVAL",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_EXTERNAL__URL",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__IDENTITY",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__PASSWORD",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__PASSWORD_FILE",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__SECRET",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__USERNAME",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__FROM",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__HELLO",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__REQUIRE__TLS",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__SMARTHOST",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CA__FILE",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CERT__FILE",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CONFIG_INSECURE__SKIP__VERIFY",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__KEY__FILE",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__MAX__VERSION",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__MIN__VERSION",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__SERVER__NAME",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_RESOLVE__TIMEOUT",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_NFLOG_MAINTENANCE__INTERVAL",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_NFLOG_RETENTION",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_POLL__INTERVAL",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_GROUP__BY",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_GROUP__INTERVAL",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_GROUP__WAIT",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_REPEAT__INTERVAL",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_MAINTENANCE__INTERVAL",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_MAX",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_MAX__SIZE__BYTES",
    "SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_RETENTION",
    "SIGNOZ_ANALYTICS_ENABLED",
    "SIGNOZ_ANALYTICS_SEGMENT_KEY",
    "SIGNOZ_APISERVER_LOGGING_EXCLUDED__ROUTES",
    "SIGNOZ_APISERVER_TIMEOUT_DEFAULT",
    "SIGNOZ_APISERVER_TIMEOUT_EXCLUDED__ROUTES",
    "SIGNOZ_APISERVER_TIMEOUT_MAX",
    "SIGNOZ_AUDITOR_BATCH__SIZE",
    "SIGNOZ_AUDITOR_BUFFER__SIZE",
    "SIGNOZ_AUDITOR_FLUSH__INTERVAL",
    "SIGNOZ_AUDITOR_OTLPHTTP_ENDPOINT",
    "SIGNOZ_AUDITOR_OTLPHTTP_INSECURE",
    "SIGNOZ_AUDITOR_OTLPHTTP_RETRY_ENABLED",
    "SIGNOZ_AUDITOR_OTLPHTTP_RETRY_INITIAL__INTERVAL",
    "SIGNOZ_AUDITOR_OTLPHTTP_RETRY_MAX__ELAPSED__TIME",
    "SIGNOZ_AUDITOR_OTLPHTTP_RETRY_MAX__INTERVAL",
    "SIGNOZ_AUDITOR_OTLPHTTP_TIMEOUT",
    "SIGNOZ_AUDITOR_PROVIDER",
    "SIGNOZ_CACHE_MEMORY_MAX__COST",
    "SIGNOZ_CACHE_MEMORY_NUM__COUNTERS",
    "SIGNOZ_CACHE_PROVIDER",
    "SIGNOZ_CACHE_REDIS_DB",
    "SIGNOZ_CACHE_REDIS_HOST",
    "SIGNOZ_CACHE_REDIS_PASSWORD",
    "SIGNOZ_CACHE_REDIS_PORT",
    "SIGNOZ_CLICKHOUSE_HEALTHCHECK_URL",
    "SIGNOZ_CLOUDINTEGRATION_AGENT_VERSION",
    "SIGNOZ_CLICKHOUSE_LOGS_DSN",
    "SIGNOZ_CLICKHOUSE_METADATA_DSN",
    "SIGNOZ_CLICKHOUSE_METER_DSN",
    "SIGNOZ_CLICKHOUSE_METRICS_DSN",
    "SIGNOZ_CLICKHOUSE_TRACES_DSN",
    "SIGNOZ_EMAILING_ENABLED",
    "SIGNOZ_EMAILING_SMTP_ADDRESS",
    "SIGNOZ_EMAILING_SMTP_AUTH_IDENTITY",
    "SIGNOZ_EMAILING_SMTP_AUTH_PASSWORD",
    "SIGNOZ_EMAILING_SMTP_AUTH_SECRET",
    "SIGNOZ_EMAILING_SMTP_AUTH_USERNAME",
    "SIGNOZ_EMAILING_SMTP_FROM",
    "SIGNOZ_EMAILING_SMTP_HELLO",
    "SIGNOZ_EMAILING_SMTP_TLS_CA__FILE__PATH",
    "SIGNOZ_EMAILING_SMTP_TLS_CERT__FILE__PATH",
    "SIGNOZ_EMAILING_SMTP_TLS_ENABLED",
    "SIGNOZ_EMAILING_SMTP_TLS_INSECURE__SKIP__VERIFY",
    "SIGNOZ_EMAILING_SMTP_TLS_KEY__FILE__PATH",
    "SIGNOZ_EMAILING_TEMPLATES_FORMAT_FOOTER_ENABLED",
    "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HEADER_ENABLED",
    "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HEADER_LOGO__URL",
    "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HELP_EMAIL",
    "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HELP_ENABLED",
    "SIGNOZ_ENABLE_HOST_AGENT",
    "SIGNOZ_FLAGGER_CONFIG_BOOLEAN_KAFKA__SPAN__EVAL",
    "SIGNOZ_FLAGGER_CONFIG_BOOLEAN_USE__SPAN__METRICS",
    "SIGNOZ_GLOBAL_EXTERNAL__URL",
    "SIGNOZ_GLOBAL_INGESTION__URL",
    "SIGNOZ_GATEWAY_URL",
    "SIGNOZ_HOST_AGENT_PROMETHEUS_METRICS_PATH",
    "SIGNOZ_HOST_AGENT_PROMETHEUS_SCRAPE_INTERVAL",
    "SIGNOZ_HOST_AGENT_PROMETHEUS_TARGETS",
    "SIGNOZ_IDENTN_APIKEY_ENABLED",
    "SIGNOZ_IDENTN_APIKEY_HEADERS",
    "SIGNOZ_IDENTN_IMPERSONATION_ENABLED",
    "SIGNOZ_IDENTN_TOKENIZER_ENABLED",
    "SIGNOZ_IDENTN_TOKENIZER_HEADERS",
    "SIGNOZ_INSTRUMENTATION_LOGS_LEVEL",
    "SIGNOZ_INSTRUMENTATION_METRICS_ENABLED",
    "SIGNOZ_INSTRUMENTATION_METRICS_READERS_PULL_EXPORTER_PROMETHEUS_HOST",
    "SIGNOZ_INSTRUMENTATION_METRICS_READERS_PULL_EXPORTER_PROMETHEUS_PORT",
    "SIGNOZ_INSTRUMENTATION_TRACES_ENABLED",
    "SIGNOZ_INSTRUMENTATION_TRACES_PROCESSORS_BATCH_EXPORTER_OTLP_ENDPOINT",
    "SIGNOZ_METRICSEXPLORER_TELEMETRYSTORE_THREADS",
    "SIGNOZ_OTEL_COLLECTOR_BATCH_SEND_MAX_SIZE",
    "SIGNOZ_OTEL_COLLECTOR_BATCH_SEND_SIZE",
    "SIGNOZ_OTEL_COLLECTOR_BATCH_TIMEOUT",
    "SIGNOZ_OTEL_COLLECTOR_CLICKHOUSE_CLUSTER",
    "SIGNOZ_OTEL_COLLECTOR_CLICKHOUSE_DSN",
    "SIGNOZ_OTEL_COLLECTOR_CLICKHOUSE_REPLICATION",
    "SIGNOZ_OTEL_COLLECTOR_METER_BATCH_SEND_MAX_SIZE",
    "SIGNOZ_OTEL_COLLECTOR_METER_BATCH_SEND_SIZE",
    "SIGNOZ_OTEL_COLLECTOR_METER_BATCH_TIMEOUT",
    "SIGNOZ_OTEL_COLLECTOR_PPROF_ENDPOINT",
    "SIGNOZ_OTEL_COLLECTOR_SELF_SCRAPE_INTERVAL",
    "SIGNOZ_OTEL_COLLECTOR_TIMEOUT",
    "SIGNOZ_PPROF_ADDRESS",
    "SIGNOZ_PPROF_ENABLED",
    "SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_ENABLED",
    "SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_MAX__CONCURRENT",
    "SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_PATH",
    "SIGNOZ_PROMETHEUS_TIMEOUT",
    "SIGNOZ_QUERIER_CACHE__TTL",
    "SIGNOZ_QUERIER_FLUX__INTERVAL",
    "SIGNOZ_QUERIER_MAX__CONCURRENT__QUERIES",
    "SIGNOZ_RULER_EVAL__DELAY",
    "SIGNOZ_SERVICEACCOUNT_ANALYTICS_ENABLED",
    "SIGNOZ_SERVICEACCOUNT_EMAIL_DOMAIN",
    "SIGNOZ_SQLSTORE_MAX__CONN__LIFETIME",
    "SIGNOZ_SQLSTORE_MAX__OPEN__CONNS",
    "SIGNOZ_SQLSTORE_POSTGRES_DSN",
    "SIGNOZ_SQLSTORE_PROVIDER",
    "SIGNOZ_SQLSTORE_SQLITE_BUSY__TIMEOUT",
    "SIGNOZ_SQLSTORE_SQLITE_MODE",
    "SIGNOZ_SQLSTORE_SQLITE_PATH",
    "SIGNOZ_SQLSTORE_SQLITE_TRANSACTION__MODE",
    "SIGNOZ_STATSREPORTER_ENABLED",
    "SIGNOZ_STATSREPORTER_COLLECT_IDENTITIES",
    "SIGNOZ_STATSREPORTER_INTERVAL",
    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_CLUSTER",
    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_DSN",
    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_IGNORE__DATA__SKIPPING__INDICES",
    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_MAX__BYTES__TO__READ",
    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_MAX__EXECUTION__TIME",
    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_MAX__EXECUTION__TIME__LEAF",
    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_MAX__RESULT__ROWS",
    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_SECONDARY__INDICES__ENABLE__BULK__FILTERING",
    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_TIMEOUT__BEFORE__CHECKING__EXECUTION__SPEED",
    "SIGNOZ_TELEMETRYSTORE_DIAL__TIMEOUT",
    "SIGNOZ_TELEMETRYSTORE_MAX__IDLE__CONNS",
    "SIGNOZ_TELEMETRYSTORE_MAX__OPEN__CONNS",
    "SIGNOZ_TOKENIZER_LIFETIME_IDLE",
    "SIGNOZ_TOKENIZER_LIFETIME_MAX",
    "SIGNOZ_TOKENIZER_OPAQUE_GC_INTERVAL",
    "SIGNOZ_TOKENIZER_OPAQUE_TOKEN_MAX__PER__USER",
    "SIGNOZ_TOKENIZER_ROTATION_DURATION",
    "SIGNOZ_TOKENIZER_ROTATION_INTERVAL",
    "SIGNOZ_TOKENIZER_JWT_SECRET",
    "SIGNOZ_USE_EXTERNAL_CLICKHOUSE",
    "SIGNOZ_USER_PASSWORD_INVITE_MAX__TOKEN__LIFETIME",
    "SIGNOZ_USER_PASSWORD_RESET_ALLOW__SELF",
    "SIGNOZ_USER_PASSWORD_RESET_MAX__TOKEN__LIFETIME",
    "SIGNOZ_USER_ROOT_EMAIL",
    "SIGNOZ_USER_ROOT_ENABLED",
    "SIGNOZ_USER_ROOT_ORG_ID",
    "SIGNOZ_USER_ROOT_ORG_NAME",
    "SIGNOZ_USER_ROOT_PASSWORD",
    "SIGNOZ_VERSION_BANNER_ENABLED",
    "TZ",
    "ZOO_AUTOPURGE_INTERVAL",
    "ZOO_ENABLE_PROMETHEUS_METRICS",
    "ZOO_PROMETHEUS_METRICS_PORT_NUMBER",
}

AGENT_REQUIRED_TARGETS = {
    "/appdata",
    "/hostfs",
    "/var/lib/docker/containers",
    "/var/run/docker.sock",
    "4317",
    "4318",
    "SIGNOZ_AGENT_BATCH_SEND_SIZE",
    "SIGNOZ_AGENT_BATCH_TIMEOUT",
    "SIGNOZ_AGENT_CONFIG_MODE",
    "SIGNOZ_AGENT_CUSTOM_CONFIG_PATH",
    "SIGNOZ_AGENT_DEPLOYMENT_ENVIRONMENT",
    "SIGNOZ_AGENT_DOCKER_COLLECTION_INTERVAL",
    "SIGNOZ_AGENT_ENABLE_DOCKER_LOGS",
    "SIGNOZ_AGENT_ENABLE_DOCKER_METRICS",
    "SIGNOZ_AGENT_ENABLE_HOST_METRICS",
    "SIGNOZ_AGENT_ENDPOINT",
    "SIGNOZ_AGENT_HEADERS",
    "SIGNOZ_AGENT_HEALTH_ENDPOINT",
    "SIGNOZ_AGENT_HOST_COLLECTION_INTERVAL",
    "SIGNOZ_AGENT_INGESTION_KEY",
    "SIGNOZ_AGENT_INSECURE",
    "SIGNOZ_AGENT_LOG_LEVEL",
    "SIGNOZ_AGENT_MEMORY_LIMIT_MIB",
    "SIGNOZ_AGENT_OTLP_GRPC_ENDPOINT",
    "SIGNOZ_AGENT_OTLP_HTTP_ENDPOINT",
    "SIGNOZ_AGENT_PROMETHEUS_METRICS_PATH",
    "SIGNOZ_AGENT_PROMETHEUS_SCRAPE_INTERVAL",
    "SIGNOZ_AGENT_PROMETHEUS_TARGETS",
    "SIGNOZ_AGENT_PROTOCOL",
    "SIGNOZ_AGENT_RESOURCE_ATTRIBUTES",
    "TZ",
}

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

AGENT_PRIVACY_OPT_IN_DEFAULT_FALSE_TARGETS = {
    "SIGNOZ_AGENT_ENABLE_DOCKER_LOGS",
    "SIGNOZ_AGENT_ENABLE_DOCKER_METRICS",
    "SIGNOZ_AGENT_ENABLE_HOST_METRICS",
}

TEMPLATE_CONTRACTS = {
    "signoz-aio": {
        "template_url": "https://raw.githubusercontent.com/JSONbored/awesome-unraid/main/signoz-aio.xml",
        "icon": "https://raw.githubusercontent.com/JSONbored/awesome-unraid/main/icons/signoz.png",
        "project": "https://github.com/JSONbored/signoz-aio",
        "support": "https://github.com/JSONbored/signoz-aio/issues",
        "extra_search_terms": AIO_EXTRA_SEARCH_TERMS,
        "requires_terms": AIO_REQUIRES_TERMS,
        "required_targets": REQUIRED_TARGETS,
        "sensitive_path_targets": OPTIONAL_SENSITIVE_PATH_TARGETS,
        "privacy_false_targets": PRIVACY_OPT_IN_DEFAULT_FALSE_TARGETS,
    },
    "signoz-agent": {
        "template_url": "https://raw.githubusercontent.com/JSONbored/awesome-unraid/main/signoz-agent.xml",
        "icon": "https://raw.githubusercontent.com/JSONbored/awesome-unraid/main/icons/signoz.png",
        "project": "https://github.com/JSONbored/signoz-aio",
        "support": "https://github.com/JSONbored/signoz-aio/issues",
        "extra_search_terms": AGENT_EXTRA_SEARCH_TERMS,
        "requires_terms": AGENT_REQUIRES_TERMS,
        "required_targets": AGENT_REQUIRED_TARGETS,
        "sensitive_path_targets": {
            "/hostfs": "ro",
            "/var/lib/docker/containers": "ro",
            "/var/run/docker.sock": "ro",
        },
        "privacy_false_targets": AGENT_PRIVACY_OPT_IN_DEFAULT_FALSE_TARGETS,
    },
}


def resolve_template_path() -> Path:
    explicit = os.environ.get("TEMPLATE_XML", "").strip()
    if explicit:
        return ROOT / explicit

    repo_xml = ROOT / f"{ROOT.name}.xml"
    if repo_xml.exists():
        return repo_xml

    xml_files = sorted(ROOT.glob("*.xml"))
    if len(xml_files) == 1:
        return xml_files[0]

    return ROOT / "template-aio.xml"


def is_placeholder_template(xml_path: Path) -> bool:
    return xml_path.name == "template-aio.xml" or ROOT.name == "unraid-aio-template"


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def validate_changes_block(xml_path: Path, changes: str) -> int:
    for marker in LEGACY_CHANGELOG_MARKERS:
        if marker in changes:
            return fail(
                f"{xml_path.name} <Changes> still includes the legacy release-link format: {marker}"
            )

    lines = [line.strip() for line in changes.splitlines() if line.strip()]
    if len(lines) < 2:
        return fail(
            f"{xml_path.name} <Changes> must contain a date heading and bullet lines"
        )

    if not CHANGELOG_HEADER_PATTERN.fullmatch(lines[0]):
        return fail(
            f"{xml_path.name} <Changes> must start with '### YYYY-MM-DD' or the template placeholder heading"
        )

    if lines[1] != GENERATED_CHANGELOG_BULLET:
        return fail(
            f"{xml_path.name} <Changes> second line should be '{GENERATED_CHANGELOG_BULLET}'"
        )

    invalid_lines = [line for line in lines[1:] if not line.startswith("- ")]
    if invalid_lines:
        return fail(
            f"{xml_path.name} <Changes> must use bullet lines only after the heading; found {invalid_lines[0]!r}"
        )

    return 0


def validate_template(xml_path: Path) -> int:
    if not xml_path.exists():
        return fail(f"Template XML not found: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()
    if root.tag != "Container":
        return fail(f"{xml_path.name} root tag should be <Container>")
    if root.attrib.get("version") != "2":
        return fail(f'{xml_path.name} should declare <Container version="2">')

    for field in REQUIRED_TEXT_FIELDS:
        value = (root.findtext(field) or "").strip()
        if not value:
            return fail(f"{xml_path.name} is missing a non-empty <{field}> field")

    name = root.findtext("Name") or ""
    contract = TEMPLATE_CONTRACTS.get(name)
    if contract is None:
        return fail(f"{xml_path.name} has unsupported <Name>{name}</Name>")

    template_url = (root.findtext("TemplateURL") or "").strip()
    if template_url != contract["template_url"]:
        return fail(
            f"{xml_path.name} TemplateURL should point at {contract['template_url']}"
        )

    icon_url = (root.findtext("Icon") or "").strip()
    if icon_url != contract["icon"]:
        return fail(f"{xml_path.name} Icon should point at {contract['icon']}")

    if root.findtext("Project") != contract["project"]:
        return fail(f"{xml_path.name} Project should point at {contract['project']}")
    if root.findtext("Support") != contract["support"]:
        return fail(f"{xml_path.name} Support should point at {contract['support']}")
    if root.findtext("Category") != EXPECTED_CATEGORY:
        return fail(f"{xml_path.name} Category should be {EXPECTED_CATEGORY}")
    if root.findtext("DonateText") != EXPECTED_DONATE_TEXT:
        return fail(f"{xml_path.name} DonateText should point users at GitHub Sponsors")
    if root.findtext("DonateLink") != EXPECTED_DONATE_LINK:
        return fail(f"{xml_path.name} DonateLink should point at JSONbored sponsors")
    if root.findtext("ExtraSearchTerms") != contract["extra_search_terms"]:
        return fail(
            f"{xml_path.name} ExtraSearchTerms should match the CA search contract"
        )

    requires = root.findtext("Requires") or ""
    for term in contract["requires_terms"]:
        if term not in requires:
            return fail(f"{xml_path.name} Requires should mention {term}")

    changes = (root.findtext("Changes") or "").strip()
    if GENERATED_CHANGELOG_NOTE not in changes:
        return fail(
            f"{xml_path.name} <Changes> should include the generated-from-CHANGELOG note"
        )
    changes_status = validate_changes_block(xml_path, changes)
    if changes_status:
        return changes_status

    invalid_option_configs: list[str] = []
    invalid_pipe_configs: list[str] = []
    configs = root.findall(".//Config")
    configs_by_target = {
        config.attrib["Target"]: config
        for config in configs
        if config.attrib.get("Target")
    }
    targets = {
        config.attrib["Target"] for config in configs if config.attrib.get("Target")
    }
    missing_targets = sorted(contract["required_targets"] - targets)
    if missing_targets:
        print(
            f"{xml_path.name} is missing required SigNoz config targets:",
            file=sys.stderr,
        )
        for target in missing_targets:
            print(f"  - {target}", file=sys.stderr)
        return 1

    for target, expected_mode in contract["sensitive_path_targets"].items():
        config = configs_by_target.get(target)
        if config is None:
            continue

        selected = (config.text or "").strip()
        default = config.attrib.get("Default", "")
        if (
            config.attrib.get("Type") != "Path"
            or config.attrib.get("Display") != "advanced"
            or config.attrib.get("Required") != "false"
            or config.attrib.get("Mode") != expected_mode
            or default
            or selected
        ):
            return fail(
                f"{xml_path.name} optional sensitive path {target} must be advanced, optional, mode={expected_mode}, and blank by default"
            )

    for target in contract["privacy_false_targets"]:
        config = configs_by_target.get(target)
        if config is None:
            continue

        selected = (config.text or "").strip()
        if config.attrib.get("Default") != "false|true" or selected != "false":
            return fail(
                f"{xml_path.name} privacy-sensitive toggle {target} must default to false"
            )

    for config in configs:
        name = config.attrib.get("Name", config.attrib.get("Target", "<unnamed>"))
        if config.findall("Option"):
            invalid_option_configs.append(name)

        default = config.attrib.get("Default", "")
        if "|" not in default:
            continue

        allowed_values = default.split("|")
        if any(value == "" for value in allowed_values):
            invalid_pipe_configs.append(
                f"{name} (allowed={allowed_values!r}, empty pipe options are not allowed)"
            )
            continue

        selected_value = (config.text or "").strip()
        if selected_value not in allowed_values:
            invalid_pipe_configs.append(
                f"{name} (selected={selected_value!r}, allowed={allowed_values!r})"
            )

    if invalid_option_configs:
        print(
            f"{xml_path.name} uses nested <Option> tags, which are not allowed by the catalog-safe template format:",
            file=sys.stderr,
        )
        for name in invalid_option_configs:
            print(f"  - {name}", file=sys.stderr)
        return 1

    if invalid_pipe_configs:
        print(
            f"{xml_path.name} has pipe-delimited defaults whose selected value is not one of the allowed options:",
            file=sys.stderr,
        )
        for detail in invalid_pipe_configs:
            print(f"  - {detail}", file=sys.stderr)
        return 1

    template_kind = "placeholder " if is_placeholder_template(xml_path) else ""
    print(
        f"{xml_path.name} parsed successfully and passed {template_kind}catalog-safe validation"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SigNoz suite Unraid XML.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate every template referenced by components.toml.",
    )
    args = parser.parse_args()

    common_status = run_common_template_validation()
    if common_status:
        return common_status

    if args.all:
        failures = 0
        for component in load_components():
            failures += validate_template(ROOT / component.template)
        return 1 if failures else 0

    return validate_template(resolve_template_path())


if __name__ == "__main__":
    raise SystemExit(main())
