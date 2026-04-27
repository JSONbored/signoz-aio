#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from defusedxml import ElementTree as ET

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

REQUIRED_TEXT_FIELDS = (
    "Support",
    "Project",
    "Overview",
    "Category",
    "TemplateURL",
    "Icon",
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


def main() -> int:
    xml_path = resolve_template_path()
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

    template_url = (root.findtext("TemplateURL") or "").strip()
    if (
        template_url
        != "https://raw.githubusercontent.com/JSONbored/awesome-unraid/main/signoz-aio.xml"
    ):
        return fail(
            f"{xml_path.name} TemplateURL should point at raw awesome-unraid/main/signoz-aio.xml"
        )

    icon_url = (root.findtext("Icon") or "").strip()
    if (
        icon_url
        != "https://raw.githubusercontent.com/JSONbored/awesome-unraid/main/icons/signoz.png"
    ):
        return fail(
            f"{xml_path.name} Icon should point at raw awesome-unraid/main/icons/signoz.png"
        )

    if root.findtext("Name") != "signoz-aio":
        return fail(f"{xml_path.name} should have <Name>signoz-aio</Name>")
    if root.findtext("Project") != "https://github.com/JSONbored/signoz-aio":
        return fail(f"{xml_path.name} Project should point at the signoz-aio repo")
    if root.findtext("Support") != "https://github.com/JSONbored/signoz-aio/issues":
        return fail(f"{xml_path.name} Support should point at signoz-aio issues")
    if "Monitoring" not in (root.findtext("Category") or ""):
        return fail(f"{xml_path.name} Category should include Monitoring")

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
    targets = {
        config.attrib["Target"]
        for config in root.findall(".//Config")
        if config.attrib.get("Target")
    }
    missing_targets = sorted(REQUIRED_TARGETS - targets)
    if missing_targets:
        print(
            f"{xml_path.name} is missing required SigNoz config targets:",
            file=sys.stderr,
        )
        for target in missing_targets:
            print(f"  - {target}", file=sys.stderr)
        return 1

    for config in root.findall(".//Config"):
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


if __name__ == "__main__":
    raise SystemExit(main())
