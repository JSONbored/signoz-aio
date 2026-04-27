from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import pytest

from tests.helpers import (
    container_file_size,
    container_path_exists,
    docker_available,
    docker_volume,
    ensure_pytest_image,
    read_container_file,
    reserve_host_port,
    run_command,
)

IMAGE_TAG = "signoz-aio:pytest"
POSTGRES_IMAGE = "postgres:16-alpine"
pytestmark = pytest.mark.integration


@dataclass
class SigNozContainer:
    name: str
    ui_port: int
    grpc_port: int
    http_port: int


def logs(name: str) -> str:
    result = run_command(["docker", "logs", name], check=False)
    return result.stdout + result.stderr


def inspect_state(name: str) -> str:
    result = run_command(
        ["docker", "inspect", "-f", "{{.State.Status}}", name],
        check=False,
    )
    return result.stdout.strip()


def docker_exec(name: str, command: str, *, check: bool = True) -> str:
    result = run_command(["docker", "exec", name, "bash", "-lc", command], check=check)
    return result.stdout.strip()


def wait_for_host_http(
    name: str, host_port: int, path: str = "/api/v2/readyz", timeout: int = 900
) -> float:
    started_at = time.time()
    deadline = started_at + timeout
    url = f"http://127.0.0.1:{host_port}{path}"
    while time.time() < deadline:
        if inspect_state(name) != "running":
            raise AssertionError(f"{name} stopped before becoming ready.\n{logs(name)}")
        if run_command(["curl", "-fsS", url], check=False).returncode == 0:
            return time.time() - started_at
        time.sleep(2)
    raise AssertionError(f"{name} did not become ready.\n{logs(name)}")


def wait_for_container_http(name: str, url: str, timeout: int = 900) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if inspect_state(name) != "running":
            raise AssertionError(
                f"{name} stopped while waiting for {url}.\n{logs(name)}"
            )
        result = run_command(
            ["docker", "exec", name, "curl", "-fsS", url],
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise AssertionError(f"{name} did not expose {url}.\n{logs(name)}")


def wait_for_container_tcp(name: str, port: int, timeout: int = 900) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if inspect_state(name) != "running":
            raise AssertionError(
                f"{name} stopped while waiting for TCP {port}.\n{logs(name)}"
            )
        result = run_command(
            [
                "docker",
                "exec",
                name,
                "bash",
                "-lc",
                f"exec 3<>/dev/tcp/127.0.0.1/{port}",
            ],
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise AssertionError(f"{name} did not expose TCP {port}.\n{logs(name)}")


def wait_for_container_path(name: str, path: str, timeout: int = 900) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if inspect_state(name) != "running":
            raise AssertionError(
                f"{name} stopped while waiting for {path}.\n{logs(name)}"
            )
        if container_path_exists(name, path):
            return
        time.sleep(2)
    raise AssertionError(f"{name} did not create {path}.\n{logs(name)}")


def wait_for_container_exit(name: str, timeout: int = 90) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = inspect_state(name)
        if state in {"exited", "dead"}:
            return logs(name)
        time.sleep(1)
    raise AssertionError(f"{name} did not exit within {timeout}s.\n{logs(name)}")


def clickhouse_query(name: str, query: str) -> str:
    return docker_exec(name, f"clickhouse-client --query {json.dumps(query)}")


def wait_for_clickhouse_count(
    name: str, query: str, *, minimum: int = 1, timeout: int = 180
) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = run_command(
            [
                "docker",
                "exec",
                name,
                "bash",
                "-lc",
                f"clickhouse-client --query {json.dumps(query)}",
            ],
            check=False,
        )
        if result.returncode == 0:
            value = int((result.stdout.strip() or "0").splitlines()[-1])
            if value >= minimum:
                return value
        time.sleep(2)
    raise AssertionError(
        f"ClickHouse query did not reach {minimum}: {query}\n{logs(name)}"
    )


def image_size_bytes() -> int:
    return int(
        run_command(
            ["docker", "image", "inspect", IMAGE_TAG, "--format", "{{.Size}}"]
        ).stdout.strip()
    )


def stats_snapshot(name: str) -> str:
    return run_command(
        [
            "docker",
            "stats",
            "--no-stream",
            "--format",
            "{{.CPUPerc}} {{.MemUsage}}",
            name,
        ],
        check=False,
    ).stdout.strip()


@contextmanager
def docker_network(prefix: str) -> Iterator[str]:
    name = f"{prefix}-{uuid.uuid4().hex[:10]}"
    run_command(["docker", "network", "create", name])
    try:
        yield name
    finally:
        run_command(["docker", "network", "rm", name], check=False)


@contextmanager
def postgres_service(network: str) -> Iterator[str]:
    name = f"signoz-aio-postgres-{uuid.uuid4().hex[:10]}"
    run_command(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--network",
            network,
            "--network-alias",
            "postgres",
            "-e",
            "POSTGRES_USER=signoz",
            "-e",
            "POSTGRES_PASSWORD=signoz",
            "-e",
            "POSTGRES_DB=signoz",
            POSTGRES_IMAGE,
        ]
    )
    try:
        deadline = time.time() + 120
        while time.time() < deadline:
            result = run_command(
                ["docker", "exec", name, "pg_isready", "-U", "signoz", "-d", "signoz"],
                check=False,
            )
            if result.returncode == 0:
                yield name
                return
            time.sleep(2)
        raise AssertionError(f"PostgreSQL did not become ready.\n{logs(name)}")
    finally:
        run_command(["docker", "rm", "-f", name], check=False)


@contextmanager
def container(
    appdata_volume: str,
    *,
    enable_host_agent: bool = False,
    env_overrides: dict[str, str] | None = None,
    network: str | None = None,
    network_alias: str | None = None,
    name_prefix: str = "signoz-aio-pytest",
) -> Iterator[SigNozContainer]:
    name = f"{name_prefix}-{uuid.uuid4().hex[:10]}"
    ui_port = reserve_host_port()
    grpc_port = reserve_host_port()
    http_port = reserve_host_port()
    command = [
        "docker",
        "run",
        "-d",
        "--platform",
        "linux/amd64",
        "--name",
        name,
    ]
    if network:
        command.extend(["--network", network])
    if network_alias:
        command.extend(["--network-alias", network_alias])
    command.extend(
        [
            "-p",
            f"{ui_port}:8080",
            "-p",
            f"{grpc_port}:4317",
            "-p",
            f"{http_port}:4318",
            "-v",
            f"{appdata_volume}:/appdata",
        ]
    )
    if enable_host_agent:
        command.extend(["-e", "SIGNOZ_ENABLE_HOST_AGENT=true"])
    if env_overrides:
        for key, value in env_overrides.items():
            command.extend(["-e", f"{key}={value}"])
    command.append(IMAGE_TAG)
    run_command(command)
    try:
        yield SigNozContainer(name, ui_port, grpc_port, http_port)
    finally:
        run_command(["docker", "rm", "-f", name], check=False)


@pytest.fixture(scope="session", autouse=True)
def build_image() -> None:
    if not docker_available():
        pytest.skip("Docker is unavailable; integration tests require Docker/OrbStack.")
    ensure_pytest_image(IMAGE_TAG)


def post_otlp_json(host_port: int, path: str, payload: dict[str, object]) -> None:
    result = run_command(
        [
            "curl",
            "-fsS",
            "-X",
            "POST",
            f"http://127.0.0.1:{host_port}{path}",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload),
        ],
        check=False,
    )
    assert result.returncode == 0, result.stderr  # nosec B101


def test_happy_path_boot_ingests_persists_and_restarts() -> None:
    with docker_volume("signoz-aio-appdata") as appdata_volume:
        with container(appdata_volume) as runtime:
            ready_seconds = wait_for_host_http(runtime.name, runtime.ui_port)
            print(f"image_size_bytes={image_size_bytes()}")
            print(f"first_ready_seconds={ready_seconds:.1f}")
            print(f"idle_stats={stats_snapshot(runtime.name)}")

            assert container_path_exists(
                runtime.name, "/appdata/config/generated.env"
            )  # nosec B101
            assert container_path_exists(
                runtime.name, "/appdata/signoz/signoz.db"
            )  # nosec B101
            assert (
                container_file_size(runtime.name, "/appdata/signoz/signoz.db") > 0
            )  # nosec B101
            wait_for_container_http(runtime.name, "http://127.0.0.1:13133/")
            wait_for_container_path(
                runtime.name, "/appdata/.telemetrystore-migrations-complete"
            )
            wait_for_container_tcp(runtime.name, 4317)
            wait_for_container_tcp(runtime.name, 4318)

            now = time.time_ns()
            post_otlp_json(
                runtime.http_port,
                "/v1/traces",
                {
                    "resourceSpans": [
                        {
                            "resource": {
                                "attributes": [
                                    {
                                        "key": "service.name",
                                        "value": {"stringValue": "signoz-aio-test"},
                                    }
                                ]
                            },
                            "scopeSpans": [
                                {
                                    "spans": [
                                        {
                                            "traceId": "00000000000000000000000000000001",
                                            "spanId": "0000000000000001",
                                            "name": "signoz-aio-test-span",
                                            "startTimeUnixNano": str(now),
                                            "endTimeUnixNano": str(now + 1000000),
                                        }
                                    ]
                                }
                            ],
                        }
                    ]
                },
            )
            wait_for_clickhouse_count(
                runtime.name,
                "SELECT count() FROM signoz_traces.signoz_index_v3",
                minimum=1,
            )
            wait_for_clickhouse_count(
                runtime.name,
                "SELECT count() FROM signoz_metrics.samples_v4",
                minimum=1,
            )

            restart_started = time.time()
            run_command(["docker", "restart", runtime.name])
            wait_for_host_http(runtime.name, runtime.ui_port)
            print(f"restart_ready_seconds={time.time() - restart_started:.1f}")
            assert (
                container_file_size(runtime.name, "/appdata/config/generated.env") > 0
            )  # nosec B101
            wait_for_container_http(runtime.name, "http://127.0.0.1:13133/")
            wait_for_container_tcp(runtime.name, 4317)
            wait_for_container_tcp(runtime.name, 4318)
            wait_for_clickhouse_count(
                runtime.name,
                "SELECT count() FROM signoz_traces.signoz_index_v3",
                minimum=1,
            )


def test_blank_unraid_env_values_normalize_to_defaults() -> None:
    env = {
        "SIGNOZ_SQLSTORE_PROVIDER": "",
        "SIGNOZ_ANALYTICS_ENABLED": "",
        "SIGNOZ_AIO_WAIT_TIMEOUT_SECONDS": "",
        "SIGNOZ_TOKENIZER_JWT_SECRET": "",  # nosec B105 - blank Unraid field normalization
        "SIGNOZ_OTEL_COLLECTOR_BATCH_SEND_SIZE": "",
    }
    with docker_volume("signoz-aio-blank-env-appdata") as appdata_volume:
        with container(appdata_volume, env_overrides=env) as runtime:
            wait_for_host_http(runtime.name, runtime.ui_port)
            generated_env = read_container_file(
                runtime.name, "/appdata/config/generated.env"
            )
            assert "SIGNOZ_TOKENIZER_JWT_SECRET=" in generated_env  # nosec B101
            assert container_path_exists(  # nosec B101
                runtime.name, "/appdata/signoz/signoz.db"
            )


def test_invalid_external_clickhouse_fails_fast() -> None:
    env = {
        "SIGNOZ_USE_EXTERNAL_CLICKHOUSE": "true",
        "SIGNOZ_AIO_WAIT_TIMEOUT_SECONDS": "5",
    }
    with docker_volume("signoz-aio-invalid-clickhouse-appdata") as appdata_volume:
        with container(appdata_volume, env_overrides=env) as runtime:
            output = wait_for_container_exit(runtime.name)
            assert (
                "requires SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_DSN" in output
            )  # nosec B101


def test_invalid_external_postgres_fails_fast() -> None:
    env = {
        "SIGNOZ_SQLSTORE_PROVIDER": "postgres",
        "SIGNOZ_AIO_WAIT_TIMEOUT_SECONDS": "5",
    }
    with docker_volume("signoz-aio-invalid-postgres-appdata") as appdata_volume:
        with container(appdata_volume, env_overrides=env) as runtime:
            output = wait_for_container_exit(runtime.name)
            assert "requires SIGNOZ_SQLSTORE_POSTGRES_DSN" in output  # nosec B101


def test_host_agent_mode_records_source_detection_status_and_prometheus_config() -> (
    None
):
    env = {
        "SIGNOZ_HOST_AGENT_PROMETHEUS_TARGETS": "127.0.0.1:8080",
        "SIGNOZ_HOST_AGENT_PROMETHEUS_METRICS_PATH": "/api/v1/health",
        "SIGNOZ_HOST_AGENT_PROMETHEUS_SCRAPE_INTERVAL": "45s",
    }
    with docker_volume("signoz-aio-host-agent-appdata") as appdata_volume:
        with container(
            appdata_volume, enable_host_agent=True, env_overrides=env
        ) as runtime:
            wait_for_host_http(runtime.name, runtime.ui_port)
            assert container_path_exists(  # nosec B101
                runtime.name, "/appdata/config/generated-host-agent.status"
            )
            status = docker_exec(
                runtime.name, "cat /appdata/config/generated-host-agent.status"
            )
            assert status in {"enabled", "enabled-but-no-sources"}  # nosec B101
            if status == "enabled":
                wait_for_container_http(runtime.name, "http://127.0.0.1:13134/")
            config = read_container_file(
                runtime.name, "/appdata/config/generated-host-agent.yaml"
            )
            assert "prometheus/simple" in config  # nosec B101
            assert "127.0.0.1:8080" in config  # nosec B101


def test_advanced_signoz_env_surface_boots_and_reaches_process_env() -> None:
    env = {
        "SIGNOZ_ANALYTICS_ENABLED": "false",
        "SIGNOZ_STATSREPORTER_ENABLED": "false",
        "SIGNOZ_EMAILING_ENABLED": "true",
        "SIGNOZ_EMAILING_SMTP_ADDRESS": "127.0.0.1:25",
        "SIGNOZ_EMAILING_SMTP_FROM": "signoz@example.invalid",
        "SIGNOZ_APISERVER_TIMEOUT_DEFAULT": "70s",
        "SIGNOZ_APISERVER_TIMEOUT_MAX": "700s",
        "SIGNOZ_PPROF_ENABLED": "false",
        "SIGNOZ_RULER_EVAL__DELAY": "3m",
        "SIGNOZ_TOKENIZER_ROTATION_INTERVAL": "45m",
        "SIGNOZ_TOKENIZER_ROTATION_DURATION": "2m",
        "SIGNOZ_TOKENIZER_LIFETIME_IDLE": "240h",
        "SIGNOZ_TOKENIZER_LIFETIME_MAX": "960h",
        "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_MAX__RESULT__ROWS": "10000",
        "SIGNOZ_OTEL_COLLECTOR_BATCH_SEND_SIZE": "512",
        "SIGNOZ_OTEL_COLLECTOR_BATCH_SEND_MAX_SIZE": "1024",
        "SIGNOZ_OTEL_COLLECTOR_BATCH_TIMEOUT": "5s",
        "SIGNOZ_OTEL_COLLECTOR_SELF_SCRAPE_INTERVAL": "30s",
    }
    with docker_volume("signoz-aio-advanced-env-appdata") as appdata_volume:
        with container(appdata_volume, env_overrides=env) as runtime:
            wait_for_host_http(runtime.name, runtime.ui_port)
            signoz_env = docker_exec(
                runtime.name,
                "pid=$(pgrep -f './signoz server' | head -n1); tr '\\0' '\\n' </proc/${pid}/environ",
            )
            assert "SIGNOZ_APISERVER_TIMEOUT_DEFAULT=70s" in signoz_env  # nosec B101
            assert "SIGNOZ_EMAILING_ENABLED=true" in signoz_env  # nosec B101
            wait_for_container_http(runtime.name, "http://127.0.0.1:13133/")
            collector_env = docker_exec(
                runtime.name,
                "pid=$(pgrep -f '/opt/signoz-otel-collector/signoz-otel-collector' | head -n1); tr '\\0' '\\n' </proc/${pid}/environ",
            )
            assert (  # nosec B101
                "SIGNOZ_OTEL_COLLECTOR_BATCH_SEND_SIZE=512" in collector_env
            )
            assert (  # nosec B101
                "SIGNOZ_OTEL_COLLECTOR_SELF_SCRAPE_INTERVAL=30s" in collector_env
            )


def test_external_postgres_metadata_store_boots() -> None:
    with docker_network("signoz-aio-postgres-net") as network:
        with postgres_service(network) as postgres:
            env = {
                "SIGNOZ_SQLSTORE_PROVIDER": "postgres",
                "SIGNOZ_SQLSTORE_POSTGRES_DSN": "postgres://signoz:signoz@postgres:5432/signoz?sslmode=disable",
            }
            with docker_volume("signoz-aio-postgres-appdata") as appdata_volume:
                with container(
                    appdata_volume, env_overrides=env, network=network
                ) as runtime:
                    wait_for_host_http(runtime.name, runtime.ui_port)
                    table_count = int(
                        run_command(
                            [
                                "docker",
                                "exec",
                                postgres,
                                "psql",
                                "-U",
                                "signoz",
                                "-d",
                                "signoz",
                                "-tAc",
                                "select count(*) from information_schema.tables where table_schema='public';",
                            ]
                        ).stdout.strip()
                    )
                    assert table_count > 0  # nosec B101


def test_external_clickhouse_mode_disables_bundled_clickhouse_and_zookeeper() -> None:
    with docker_network("signoz-aio-clickhouse-net") as network:
        with docker_volume("signoz-aio-clickhouse-source-appdata") as source_volume:
            with container(
                source_volume,
                network=network,
                network_alias="external-clickhouse",
                name_prefix="signoz-aio-clickhouse-source",
            ) as source:
                wait_for_container_http(source.name, "http://127.0.0.1:8123/ping")
                wait_for_container_path(
                    source.name, "/appdata/.telemetrystore-migrations-complete"
                )
                env = {
                    "SIGNOZ_USE_EXTERNAL_CLICKHOUSE": "true",
                    "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_DSN": "tcp://external-clickhouse:9000",
                    "SIGNOZ_CLICKHOUSE_HEALTHCHECK_URL": "http://external-clickhouse:8123/ping",
                    "SIGNOZ_OTEL_COLLECTOR_CLICKHOUSE_DSN": "tcp://external-clickhouse:9000",
                }
                with docker_volume("signoz-aio-external-clickhouse-appdata") as appdata:
                    with container(
                        appdata, env_overrides=env, network=network
                    ) as runtime:
                        wait_for_host_http(runtime.name, runtime.ui_port)
                        output = logs(runtime.name)
                        assert "skipping bundled ClickHouse" in output  # nosec B101
                        assert "skipping bundled ZooKeeper" in output  # nosec B101
                        wait_for_container_tcp(runtime.name, 4317)
