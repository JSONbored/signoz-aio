from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

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
REDIS_IMAGE = "redis:7-alpine"
SMTP_IMAGE = "python:3.11-alpine"
ROOT_ORG_ID = "01961575-461c-7668-875f-05d374062bfc"
ROOT_EMAIL = "root@example.invalid"
ROOT_PASSWORD = "SignozAioTest1!"  # nosec B105 - integration-only root user
pytestmark = pytest.mark.integration

SMTP_CAPTURE_SCRIPT = r"""
import asyncore
import pathlib
import smtpd
import time

out = pathlib.Path("/messages")
out.mkdir(parents=True, exist_ok=True)


class CaptureServer(smtpd.SMTPServer):
    counter = 0

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        self.counter += 1
        body = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
        message = "\n".join(
            [
                f"PEER: {peer}",
                f"MAIL FROM: {mailfrom}",
                f"RCPT TO: {','.join(rcpttos)}",
                "",
                body,
            ]
        )
        (out / f"{int(time.time() * 1000)}-{self.counter}.eml").write_text(
            message,
            encoding="utf-8",
        )


CaptureServer(("0.0.0.0", 1025), None)
asyncore.loop()
"""


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
def redis_service(network: str) -> Iterator[str]:
    name = f"signoz-aio-redis-{uuid.uuid4().hex[:10]}"
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
            "redis",
            REDIS_IMAGE,
        ]
    )
    try:
        deadline = time.time() + 120
        while time.time() < deadline:
            result = run_command(
                ["docker", "exec", name, "redis-cli", "ping"],
                check=False,
            )
            if result.stdout.strip() == "PONG":
                yield name
                return
            time.sleep(2)
        raise AssertionError(f"Redis did not become ready.\n{logs(name)}")
    finally:
        run_command(["docker", "rm", "-f", name], check=False)


@contextmanager
def container(
    appdata_volume: str,
    *,
    enable_host_agent: bool = False,
    env_overrides: dict[str, str] | None = None,
    extra_volumes: list[tuple[str, str, str]] | None = None,
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
    if extra_volumes:
        for host_path, container_path, mode in extra_volumes:
            command.extend(["-v", f"{host_path}:{container_path}:{mode}"])
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


def post_api_json(
    host_port: int,
    path: str,
    payload: dict[str, object],
    *,
    token: str | None = None,
    expected_statuses: set[int] | None = None,
    timeout: int = 60,
) -> str:
    expected_statuses = expected_statuses or {200, 201, 204}
    body, status = post_api_json_status(
        host_port,
        path,
        payload,
        token=token,
        timeout=timeout,
    )
    assert status in expected_statuses, body  # nosec B101
    return body


def post_api_json_status(
    host_port: int,
    path: str,
    payload: dict[str, object],
    *,
    token: str | None = None,
    timeout: int = 60,
) -> tuple[str, int]:
    command = [
        "curl",
        "-sS",
        "-X",
        "POST",
        f"http://127.0.0.1:{host_port}{path}",
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(payload),
        "-w",
        "\n%{http_code}",
        "--max-time",
        str(timeout),
    ]
    if token:
        command[5:5] = ["-H", f"Authorization: Bearer {token}"]
    result = run_command(command, check=False)
    assert result.returncode == 0, result.stderr  # nosec B101
    body, status = result.stdout.rsplit("\n", 1)
    return body, int(status)


def wait_for_root_token(
    host_port: int,
    *,
    org_id: str = ROOT_ORG_ID,
    email: str = ROOT_EMAIL,
    password: str = ROOT_PASSWORD,
    timeout: int = 120,
) -> str:
    deadline = time.time() + timeout
    payload = {"email": email, "password": password, "orgId": org_id}
    last_output = ""
    while time.time() < deadline:
        result = run_command(
            [
                "curl",
                "-sS",
                "-X",
                "POST",
                f"http://127.0.0.1:{host_port}/api/v2/sessions/email_password",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(payload),
                "-w",
                "\n%{http_code}",
            ],
            check=False,
        )
        last_output = result.stdout + result.stderr
        if result.returncode == 0 and result.stdout.strip():
            body, status = result.stdout.rsplit("\n", 1)
            if status == "200":
                return json.loads(body)["data"]["accessToken"]
        time.sleep(2)
    raise AssertionError(f"Root user login did not succeed.\n{last_output}")


def root_user_env(
    *,
    org_id: str = ROOT_ORG_ID,
    email: str = ROOT_EMAIL,
    password: str = ROOT_PASSWORD,
) -> dict[str, str]:
    return {
        "SIGNOZ_USER_ROOT_ENABLED": "true",
        "SIGNOZ_USER_ROOT_EMAIL": email,
        "SIGNOZ_USER_ROOT_PASSWORD": password,
        "SIGNOZ_USER_ROOT_ORG_ID": org_id,
        "SIGNOZ_USER_ROOT_ORG_NAME": "aio-tests",
    }


@contextmanager
def smtp_capture_service(network: str) -> Iterator[str]:
    name = f"signoz-aio-smtp-{uuid.uuid4().hex[:10]}"
    volume = f"{name}-messages"
    run_command(["docker", "volume", "create", volume])
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
            "smtp",
            "-v",
            f"{volume}:/messages",
            SMTP_IMAGE,
            "python",
            "-u",
            "-c",
            SMTP_CAPTURE_SCRIPT,
        ]
    )
    try:
        deadline = time.time() + 120
        while time.time() < deadline:
            result = run_command(
                [
                    "docker",
                    "exec",
                    name,
                    "python",
                    "-c",
                    "import socket; s=socket.create_connection(('127.0.0.1',1025),2); s.close()",
                ],
                check=False,
            )
            if result.returncode == 0:
                yield name
                return
            time.sleep(2)
        raise AssertionError(
            f"SMTP capture service did not become ready.\n{logs(name)}"
        )
    finally:
        run_command(["docker", "rm", "-f", name], check=False)
        run_command(["docker", "volume", "rm", "-f", volume], check=False)


def smtp_messages(name: str) -> str:
    return run_command(
        [
            "docker",
            "exec",
            name,
            "python",
            "-c",
            "from pathlib import Path; print('\\n---MESSAGE---\\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in sorted(Path('/messages').glob('*.eml'))))",
        ],
        check=False,
    ).stdout


def wait_for_smtp_message(
    name: str, required_fragments: list[str], timeout: int = 90
) -> str:
    deadline = time.time() + timeout
    text = ""
    while time.time() < deadline:
        text = smtp_messages(name)
        if all(fragment in text for fragment in required_fragments):
            return text
        time.sleep(2)
    raise AssertionError(
        f"SMTP capture did not receive expected fragments {required_fragments}.\n{text}"
    )


def wait_for_alertmanager_channel_test(
    host_port: int,
    token: str,
    payload: dict[str, object],
    *,
    timeout: int = 150,
) -> None:
    deadline = time.time() + timeout
    last_body = ""
    while time.time() < deadline:
        body, status = post_api_json_status(
            host_port,
            "/api/v1/channels/test",
            payload,
            token=token,
        )
        if status == 204:
            return
        last_body = body
        assert status == 404, body  # nosec B101
        time.sleep(5)
    raise AssertionError(
        f"Alertmanager test channel did not become ready.\n{last_body}"
    )


def emit_telemetry_batch(host_port: int, marker: str, index: int) -> None:
    now = time.time_ns()
    post_otlp_json(
        host_port,
        "/v1/traces",
        {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": marker},
                            }
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": f"{index + 1:032x}",
                                    "spanId": f"{index + 1:016x}",
                                    "name": f"{marker}-span-{index}",
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
    post_otlp_json(
        host_port,
        "/v1/logs",
        {
            "resourceLogs": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": marker},
                            }
                        ]
                    },
                    "scopeLogs": [
                        {
                            "logRecords": [
                                {
                                    "timeUnixNano": str(now),
                                    "severityText": "INFO",
                                    "body": {"stringValue": f"{marker}-log-{index}"},
                                }
                            ]
                        }
                    ],
                }
            ]
        },
    )
    post_otlp_json(
        host_port,
        "/v1/metrics",
        {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": marker},
                            }
                        ]
                    },
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": f"{marker}_metric",
                                    "gauge": {
                                        "dataPoints": [
                                            {
                                                "timeUnixNano": str(now),
                                                "asDouble": float(index),
                                            }
                                        ]
                                    },
                                }
                            ]
                        }
                    ],
                }
            ]
        },
    )


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
            post_otlp_json(
                runtime.http_port,
                "/v1/logs",
                {
                    "resourceLogs": [
                        {
                            "resource": {
                                "attributes": [
                                    {
                                        "key": "service.name",
                                        "value": {"stringValue": "signoz-aio-test"},
                                    }
                                ]
                            },
                            "scopeLogs": [
                                {
                                    "logRecords": [
                                        {
                                            "timeUnixNano": str(now),
                                            "severityText": "INFO",
                                            "body": {
                                                "stringValue": "signoz-aio-test-log"
                                            },
                                        }
                                    ]
                                }
                            ],
                        }
                    ]
                },
            )
            post_otlp_json(
                runtime.http_port,
                "/v1/metrics",
                {
                    "resourceMetrics": [
                        {
                            "resource": {
                                "attributes": [
                                    {
                                        "key": "service.name",
                                        "value": {"stringValue": "signoz-aio-test"},
                                    }
                                ]
                            },
                            "scopeMetrics": [
                                {
                                    "metrics": [
                                        {
                                            "name": "signoz_aio_test_metric",
                                            "description": "SigNoz AIO test metric",
                                            "unit": "1",
                                            "gauge": {
                                                "dataPoints": [
                                                    {
                                                        "timeUnixNano": str(now),
                                                        "asDouble": 42.0,
                                                    }
                                                ]
                                            },
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
                "SELECT count() FROM signoz_metrics.samples_v4 WHERE metric_name='signoz_aio_test_metric'",
                minimum=1,
            )
            wait_for_clickhouse_count(
                runtime.name,
                "SELECT count() FROM signoz_logs.logs_v2 WHERE body='signoz-aio-test-log'",
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
            wait_for_clickhouse_count(
                runtime.name,
                "SELECT count() FROM signoz_logs.logs_v2 WHERE body='signoz-aio-test-log'",
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


def test_invalid_external_redis_cache_fails_fast() -> None:
    env = {
        "SIGNOZ_CACHE_PROVIDER": "redis",
        "SIGNOZ_AIO_WAIT_TIMEOUT_SECONDS": "5",
    }
    with docker_volume("signoz-aio-invalid-redis-appdata") as appdata_volume:
        with container(appdata_volume, env_overrides=env) as runtime:
            output = wait_for_container_exit(runtime.name)
            assert "requires SIGNOZ_CACHE_REDIS_HOST" in output  # nosec B101


def test_external_redis_cache_boots_with_local_fixture() -> None:
    with docker_network("signoz-aio-redis-net") as network:
        with redis_service(network):
            env = {
                "SIGNOZ_CACHE_PROVIDER": "redis",
                "SIGNOZ_CACHE_REDIS_HOST": "redis",
                "SIGNOZ_CACHE_REDIS_PORT": "6379",
                "SIGNOZ_CACHE_REDIS_DB": "0",
            }
            with docker_volume("signoz-aio-redis-appdata") as appdata_volume:
                with container(
                    appdata_volume, env_overrides=env, network=network
                ) as runtime:
                    wait_for_host_http(runtime.name, runtime.ui_port)
                    signoz_env = docker_exec(
                        runtime.name,
                        "pid=$(pgrep -f './signoz server' | head -n1); tr '\\0' '\\n' </proc/${pid}/environ",
                    )
                    assert "SIGNOZ_CACHE_PROVIDER=redis" in signoz_env  # nosec B101
                    assert "SIGNOZ_CACHE_REDIS_HOST=redis" in signoz_env  # nosec B101


def test_signoz_invite_email_delivery_with_local_smtp_fixture() -> None:
    with docker_network("signoz-aio-email-net") as network:
        with smtp_capture_service(network) as smtp:
            env = root_user_env()
            env.update(
                {
                    "SIGNOZ_EMAILING_ENABLED": "true",
                    "SIGNOZ_EMAILING_SMTP_ADDRESS": "smtp:1025",
                    "SIGNOZ_EMAILING_SMTP_FROM": "signoz@example.invalid",
                    "SIGNOZ_EMAILING_SMTP_HELLO": "signoz-aio.local",
                    "SIGNOZ_EMAILING_SMTP_TLS_ENABLED": "false",
                }
            )
            with docker_volume("signoz-aio-email-appdata") as appdata_volume:
                with container(
                    appdata_volume, env_overrides=env, network=network
                ) as runtime:
                    wait_for_host_http(runtime.name, runtime.ui_port)
                    token = wait_for_root_token(runtime.ui_port)
                    post_api_json(
                        runtime.ui_port,
                        "/api/v1/invite",
                        {
                            "name": "Invitee",
                            "email": "invitee@example.invalid",
                            "role": "VIEWER",
                            "frontendBaseUrl": "http://127.0.0.1:8080",
                        },
                        token=token,
                        expected_statuses={201},
                    )
                    message = wait_for_smtp_message(
                        smtp,
                        [
                            "MAIL FROM: signoz@example.invalid",
                            "RCPT TO: invitee@example.invalid",
                            "You're Invited to Join SigNoz",
                        ],
                    )
                    assert "http://127.0.0.1:8080" in message  # nosec B101


def test_alertmanager_email_channel_delivery_with_local_smtp_fixture() -> None:
    with docker_network("signoz-aio-alert-email-net") as network:
        with smtp_capture_service(network) as smtp:
            env = root_user_env()
            env.update(
                {
                    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__FROM": "alerts@example.invalid",
                    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__HELLO": "signoz-aio.local",
                    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__SMARTHOST": "smtp:1025",
                    "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__REQUIRE__TLS": "false",
                    "SIGNOZ_ALERTMANAGER_SIGNOZ_POLL__INTERVAL": "5s",
                }
            )
            with docker_volume("signoz-aio-alert-email-appdata") as appdata_volume:
                with container(
                    appdata_volume, env_overrides=env, network=network
                ) as runtime:
                    wait_for_host_http(runtime.name, runtime.ui_port)
                    token = wait_for_root_token(runtime.ui_port)
                    wait_for_alertmanager_channel_test(
                        runtime.ui_port,
                        token,
                        {
                            "name": "email-aio-test",
                            "email_configs": [
                                {
                                    "send_resolved": True,
                                    "to": "alerts-to@example.invalid",
                                    "html": "SigNoz AIO Alertmanager test {{ .CommonLabels.alertname }}",
                                }
                            ],
                        },
                    )
                    wait_for_smtp_message(
                        smtp,
                        [
                            "MAIL FROM: alerts@example.invalid",
                            "RCPT TO: alerts-to@example.invalid",
                            "Test Alert (email-aio-test)",
                            "SigNoz AIO Alertmanager test",
                        ],
                    )


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


def test_host_agent_docker_socket_mount_starts_active_collector() -> None:
    docker_socket = Path("/var/run/docker.sock")
    if not docker_socket.exists():
        pytest.skip("Docker socket is unavailable on this host.")

    with docker_volume("signoz-aio-host-agent-docker-appdata") as appdata_volume:
        with container(
            appdata_volume,
            enable_host_agent=True,
            extra_volumes=[("/var/run/docker.sock", "/var/run/docker.sock", "rw")],
        ) as runtime:
            wait_for_host_http(runtime.name, runtime.ui_port)
            status = docker_exec(
                runtime.name, "cat /appdata/config/generated-host-agent.status"
            )
            assert status == "enabled"  # nosec B101
            config = read_container_file(
                runtime.name, "/appdata/config/generated-host-agent.yaml"
            )
            assert "docker_stats" in config  # nosec B101
            wait_for_container_http(runtime.name, "http://127.0.0.1:13134/")


def test_advanced_signoz_env_surface_boots_and_reaches_process_env() -> None:
    env = {
        "SIGNOZ_VERSION_BANNER_ENABLED": "false",
        "SIGNOZ_INSTRUMENTATION_LOGS_LEVEL": "warn",
        "SIGNOZ_INSTRUMENTATION_TRACES_ENABLED": "false",
        "SIGNOZ_INSTRUMENTATION_TRACES_PROCESSORS_BATCH_EXPORTER_OTLP_ENDPOINT": "localhost:4317",
        "SIGNOZ_INSTRUMENTATION_METRICS_ENABLED": "true",
        "SIGNOZ_INSTRUMENTATION_METRICS_READERS_PULL_EXPORTER_PROMETHEUS_HOST": "0.0.0.0",  # nosec B104
        "SIGNOZ_INSTRUMENTATION_METRICS_READERS_PULL_EXPORTER_PROMETHEUS_PORT": "9090",
        "SIGNOZ_ANALYTICS_ENABLED": "false",
        "SIGNOZ_ANALYTICS_SEGMENT_KEY": "segment-test-key",
        "SIGNOZ_STATSREPORTER_ENABLED": "false",
        "SIGNOZ_STATSREPORTER_INTERVAL": "12h",
        "SIGNOZ_STATSREPORTER_COLLECT_IDENTITIES": "false",
        "SIGNOZ_EMAILING_ENABLED": "true",
        "SIGNOZ_EMAILING_SMTP_ADDRESS": "127.0.0.1:25",
        "SIGNOZ_EMAILING_SMTP_FROM": "signoz@example.invalid",
        "SIGNOZ_EMAILING_SMTP_HELLO": "signoz-aio.local",
        "SIGNOZ_EMAILING_SMTP_AUTH_USERNAME": "smtp-user",
        "SIGNOZ_EMAILING_SMTP_AUTH_PASSWORD": ":".join(("smtp", "auth", "value")),
        "SIGNOZ_EMAILING_SMTP_AUTH_SECRET": ":".join(("smtp", "shared", "value")),
        "SIGNOZ_EMAILING_SMTP_AUTH_IDENTITY": "smtp-identity",
        "SIGNOZ_EMAILING_SMTP_TLS_ENABLED": "false",
        "SIGNOZ_EMAILING_SMTP_TLS_INSECURE__SKIP__VERIFY": "false",
        "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HEADER_ENABLED": "false",
        "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HEADER_LOGO__URL": "https://example.invalid/logo.png",
        "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HELP_ENABLED": "false",
        "SIGNOZ_EMAILING_TEMPLATES_FORMAT_HELP_EMAIL": "help@example.invalid",
        "SIGNOZ_EMAILING_TEMPLATES_FORMAT_FOOTER_ENABLED": "false",
        "SIGNOZ_APISERVER_TIMEOUT_DEFAULT": "70s",
        "SIGNOZ_APISERVER_TIMEOUT_MAX": "700s",
        "SIGNOZ_QUERIER_CACHE__TTL": "24h",
        "SIGNOZ_QUERIER_FLUX__INTERVAL": "10m",
        "SIGNOZ_QUERIER_MAX__CONCURRENT__QUERIES": "2",
        "SIGNOZ_PROMETHEUS_TIMEOUT": "90s",
        "SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_ENABLED": "true",
        "SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_PATH": "/appdata/config/prometheus-active-queries.log",
        "SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_MAX__CONCURRENT": "10",
        "SIGNOZ_PPROF_ENABLED": "false",
        "SIGNOZ_RULER_EVAL__DELAY": "3m",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_POLL__INTERVAL": "45s",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_EXTERNAL__URL": "http://localhost:8080",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_RESOLVE__TIMEOUT": "4m",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_GROUP__BY": "alertname,severity",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_GROUP__INTERVAL": "2m",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_GROUP__WAIT": "30s",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_REPEAT__INTERVAL": "2h",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_ALERTS_GC__INTERVAL": "20m",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_MAX": "0",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_MAX__SIZE__BYTES": "0",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_MAINTENANCE__INTERVAL": "20m",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_RETENTION": "96h",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_NFLOG_MAINTENANCE__INTERVAL": "20m",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_NFLOG_RETENTION": "96h",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__FROM": "alerts@example.invalid",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__HELLO": "signoz-aio.local",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__SMARTHOST": "127.0.0.1:25",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__USERNAME": "alert-user",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__PASSWORD": ":".join(
            ("alert", "auth", "value")
        ),
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__SECRET": ":".join(
            ("alert", "shared", "value")
        ),
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__IDENTITY": "alert-identity",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__REQUIRE__TLS": "false",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CONFIG_INSECURE__SKIP__VERIFY": "true",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__MIN__VERSION": "TLS12",
        "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__MAX__VERSION": "TLS13",
        "SIGNOZ_TOKENIZER_ROTATION_INTERVAL": "45m",
        "SIGNOZ_TOKENIZER_ROTATION_DURATION": "2m",
        "SIGNOZ_TOKENIZER_LIFETIME_IDLE": "240h",
        "SIGNOZ_TOKENIZER_LIFETIME_MAX": "960h",
        "SIGNOZ_TOKENIZER_OPAQUE_GC_INTERVAL": "2h",
        "SIGNOZ_TOKENIZER_OPAQUE_TOKEN_MAX__PER__USER": str(7),
        "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_MAX__RESULT__ROWS": "10000",
        "SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_CLUSTER": "cluster",
        "SIGNOZ_OTEL_COLLECTOR_BATCH_SEND_SIZE": "512",
        "SIGNOZ_OTEL_COLLECTOR_BATCH_SEND_MAX_SIZE": "1024",
        "SIGNOZ_OTEL_COLLECTOR_BATCH_TIMEOUT": "5s",
        "SIGNOZ_OTEL_COLLECTOR_SELF_SCRAPE_INTERVAL": "30s",
        "SIGNOZ_CACHE_PROVIDER": "memory",
        "SIGNOZ_CACHE_MEMORY_NUM__COUNTERS": "200000",
        "SIGNOZ_CACHE_MEMORY_MAX__COST": "134217728",
        "SIGNOZ_CACHE_REDIS_DB": "0",
        "SIGNOZ_FLAGGER_CONFIG_BOOLEAN_USE__SPAN__METRICS": "true",
        "SIGNOZ_FLAGGER_CONFIG_BOOLEAN_KAFKA__SPAN__EVAL": "false",
        "SIGNOZ_IDENTN_TOKENIZER_ENABLED": "true",
        "SIGNOZ_IDENTN_TOKENIZER_HEADERS": "Authorization,Sec-WebSocket-Protocol",
        "SIGNOZ_IDENTN_APIKEY_ENABLED": "true",
        "SIGNOZ_IDENTN_APIKEY_HEADERS": "SIGNOZ-API-KEY",
        "SIGNOZ_IDENTN_IMPERSONATION_ENABLED": "false",
        "SIGNOZ_SERVICEACCOUNT_EMAIL_DOMAIN": "signozserviceaccount.com",
        "SIGNOZ_SERVICEACCOUNT_ANALYTICS_ENABLED": "true",
        "SIGNOZ_GATEWAY_URL": "http://localhost:8080",
        "SIGNOZ_AUDITOR_PROVIDER": "noop",
        "SIGNOZ_AUDITOR_BUFFER__SIZE": "1000",
        "SIGNOZ_AUDITOR_BATCH__SIZE": "100",
        "SIGNOZ_AUDITOR_FLUSH__INTERVAL": "1s",
        "SIGNOZ_AUDITOR_OTLPHTTP_ENDPOINT": "http://localhost:4318/v1/logs",
        "SIGNOZ_AUDITOR_OTLPHTTP_INSECURE": "false",
        "SIGNOZ_AUDITOR_OTLPHTTP_TIMEOUT": "10s",
        "SIGNOZ_AUDITOR_OTLPHTTP_RETRY_ENABLED": "true",
        "SIGNOZ_AUDITOR_OTLPHTTP_RETRY_INITIAL__INTERVAL": "5s",
        "SIGNOZ_AUDITOR_OTLPHTTP_RETRY_MAX__INTERVAL": "30s",
        "SIGNOZ_AUDITOR_OTLPHTTP_RETRY_MAX__ELAPSED__TIME": "60s",
        "SIGNOZ_CLOUDINTEGRATION_AGENT_VERSION": "v0.0.8",
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
            assert "SIGNOZ_INSTRUMENTATION_LOGS_LEVEL=warn" in signoz_env  # nosec B101
            assert (  # nosec B101
                "SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__SMARTHOST=127.0.0.1:25"
                in signoz_env
            )
            assert "SIGNOZ_TOKENIZER_OPAQUE_GC_INTERVAL=2h" in signoz_env  # nosec B101
            assert "SIGNOZ_AUDITOR_PROVIDER=noop" in signoz_env  # nosec B101
            assert "SIGNOZ_IDENTN_APIKEY_ENABLED=true" in signoz_env  # nosec B101
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


def test_sustained_ingest_records_resource_samples() -> None:
    soak_seconds = max(int(os.environ.get("AIO_PYTEST_SOAK_SECONDS", "45")), 15)
    marker = f"signoz_aio_soak_{uuid.uuid4().hex[:8]}"
    with docker_volume("signoz-aio-soak-appdata") as appdata_volume:
        with container(appdata_volume) as runtime:
            wait_for_host_http(runtime.name, runtime.ui_port)
            wait_for_container_http(runtime.name, "http://127.0.0.1:13133/")

            start = time.time()
            samples: list[str] = []
            index = 0
            while time.time() - start < soak_seconds:
                emit_telemetry_batch(runtime.http_port, marker, index)
                samples.append(stats_snapshot(runtime.name))
                index += 1
                time.sleep(3)

            wait_for_clickhouse_count(
                runtime.name,
                f"SELECT count() FROM signoz_logs.logs_v2 WHERE body LIKE '{marker}-log-%'",  # nosec B608 - marker is generated by this test.
                minimum=index,
            )
            wait_for_clickhouse_count(
                runtime.name,
                f"SELECT count() FROM signoz_metrics.samples_v4 WHERE metric_name='{marker}_metric'",  # nosec B608 - marker is generated by this test.
                minimum=index,
            )
            wait_for_clickhouse_count(
                runtime.name,
                f"SELECT count() FROM signoz_traces.signoz_index_v3 WHERE serviceName='{marker}'",  # nosec B608 - marker is generated by this test.
                minimum=index,
            )
            print(f"soak_seconds={soak_seconds}")
            print(f"soak_batches={index}")
            print(f"soak_stats_samples={json.dumps(samples)}")
