from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from tests.helpers import (
    create_docker_volume,
    docker_available,
    docker_image_exists,
    read_container_file,
    remove_docker_volume,
    reserve_host_port,
    run_command,
)

IMAGE_TAG = os.environ.get("SIGNOZ_AGENT_IMAGE_TAG", "signoz-agent:pytest")
pytestmark = pytest.mark.integration


@dataclass
class AgentContainer:
    name: str
    grpc_port: int
    http_port: int
    health_port: int
    appdata_volume: str


class CaptureHandler(BaseHTTPRequestHandler):
    server: "CaptureServer"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/metrics":
            body = (
                b"# TYPE signoz_agent_test_metric gauge\nsignoz_agent_test_metric 1\n"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(200)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.server.records.append(
            {
                "path": self.path,
                "headers": dict(self.headers.items()),
                "body_size": len(body),
            }
        )
        self.send_response(200)
        self.end_headers()

    def log_message(self, _format: str, *_args: object) -> None:
        return


class CaptureServer(ThreadingHTTPServer):
    records: list[dict[str, object]]


@contextmanager
def capture_backend() -> Iterator[tuple[str, list[dict[str, object]]]]:
    port = reserve_host_port()
    server = CaptureServer(("0.0.0.0", port), CaptureHandler)  # nosec B104
    server.records = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://host.docker.internal:{port}", server.records
    finally:
        server.shutdown()
        thread.join(timeout=5)


def ensure_agent_image() -> None:
    if os.environ.get("SIGNOZ_AGENT_PYTEST_USE_PREBUILT_IMAGE") == "true":
        if not docker_image_exists(IMAGE_TAG):
            raise AssertionError(f"Expected prebuilt agent image {IMAGE_TAG}.")
        return

    run_command(
        [
            "docker",
            "build",
            "--platform",
            "linux/amd64",
            "-t",
            IMAGE_TAG,
            "components/signoz-agent",
        ]
    )


@pytest.fixture(scope="session", autouse=True)
def build_image() -> None:
    if not docker_available():
        pytest.skip("Docker is unavailable; agent integration tests require Docker.")
    ensure_agent_image()


def logs(name: str) -> str:
    result = run_command(["docker", "logs", name], check=False)
    return result.stdout + result.stderr


def inspect_state(name: str) -> str:
    result = run_command(
        ["docker", "inspect", "-f", "{{.State.Status}}", name],
        check=False,
    )
    return result.stdout.strip()


def wait_for_http(url: str, *, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = run_command(["curl", "-fsS", url], check=False)
        if result.returncode == 0:
            return
        time.sleep(1)
    raise AssertionError(f"HTTP endpoint did not become ready: {url}")


def wait_for_exit(name: str, *, timeout: int = 30) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = inspect_state(name)
        if state in {"exited", "dead"}:
            return logs(name)
        time.sleep(1)
    raise AssertionError(f"{name} did not exit.\n{logs(name)}")


def wait_for_backend_paths(
    records: list[dict[str, object]], required_paths: set[str], *, timeout: int = 90
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        seen = {str(record["path"]) for record in records}
        if required_paths <= seen:
            return
        time.sleep(1)
    raise AssertionError(
        f"Backend did not receive {required_paths}. Records: {records}"
    )


@contextmanager
def agent_container(
    *,
    env: dict[str, str] | None = None,
    extra_volumes: list[tuple[str, str, str]] | None = None,
) -> Iterator[AgentContainer]:
    name = f"signoz-agent-pytest-{uuid.uuid4().hex[:10]}"
    appdata_volume = create_docker_volume(f"{name}-appdata")
    grpc_port = reserve_host_port()
    http_port = reserve_host_port()
    health_port = reserve_host_port()
    command = [
        "docker",
        "run",
        "-d",
        "--platform",
        "linux/amd64",
        "--name",
        name,
        "--add-host",
        "host.docker.internal:host-gateway",
        "-p",
        f"{grpc_port}:4317",
        "-p",
        f"{http_port}:4318",
        "-p",
        f"{health_port}:13133",
        "-v",
        f"{appdata_volume}:/appdata",
    ]
    if extra_volumes:
        for host_path, container_path, mode in extra_volumes:
            command.extend(["-v", f"{host_path}:{container_path}:{mode}"])
    if env:
        for key, value in env.items():
            command.extend(["-e", f"{key}={value}"])
    command.append(IMAGE_TAG)
    run_command(command)
    try:
        yield AgentContainer(name, grpc_port, http_port, health_port, appdata_volume)
    finally:
        run_command(["docker", "rm", "-f", name], check=False)
        remove_docker_volume(appdata_volume)


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


def emit_test_telemetry(host_port: int) -> None:
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
                                "value": {"stringValue": "signoz-agent-test"},
                            }
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "00000000000000000000000000000002",
                                    "spanId": "0000000000000002",
                                    "name": "signoz-agent-test-span",
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
                                "value": {"stringValue": "signoz-agent-test"},
                            }
                        ]
                    },
                    "scopeLogs": [
                        {
                            "logRecords": [
                                {
                                    "timeUnixNano": str(now),
                                    "severityText": "INFO",
                                    "body": {"stringValue": "signoz-agent-test-log"},
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
                                "value": {"stringValue": "signoz-agent-test"},
                            }
                        ]
                    },
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "signoz_agent_test_metric",
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


def test_agent_forwards_otlp_without_host_mounts_and_masks_secret_logs() -> None:
    secret = "agent-secret-value"  # nosec B105 - integration test fixture
    with capture_backend() as (endpoint, records):
        with agent_container(
            env={
                "SIGNOZ_AGENT_ENDPOINT": endpoint,
                "SIGNOZ_AGENT_PROTOCOL": "http/protobuf",
                "SIGNOZ_AGENT_INGESTION_KEY": secret,
                "SIGNOZ_AGENT_RESOURCE_ATTRIBUTES": "service.namespace=unraid-aio",
                "SIGNOZ_AGENT_DEPLOYMENT_ENVIRONMENT": "pytest",
            }
        ) as agent:
            wait_for_http(f"http://127.0.0.1:{agent.health_port}/")
            config = read_container_file(
                agent.name, "/appdata/config/generated-collector.yaml"
            )
            assert "hostmetrics:" not in config  # nosec B101
            assert "docker_stats:" not in config  # nosec B101
            assert "filelog/docker:" not in config  # nosec B101
            assert "signoz-ingestion-key" in config  # nosec B101

            emit_test_telemetry(agent.http_port)
            wait_for_backend_paths(records, {"/v1/traces", "/v1/metrics", "/v1/logs"})
            assert secret not in logs(agent.name)  # nosec B101


def test_agent_prometheus_scrape_reaches_backend() -> None:
    with capture_backend() as (endpoint, records):
        target = endpoint.removeprefix("http://")
        with agent_container(
            env={
                "SIGNOZ_AGENT_ENDPOINT": endpoint,
                "SIGNOZ_AGENT_PROTOCOL": "http/protobuf",
                "SIGNOZ_AGENT_PROMETHEUS_TARGETS": target,
                "SIGNOZ_AGENT_PROMETHEUS_SCRAPE_INTERVAL": "1s",
            }
        ) as agent:
            wait_for_http(f"http://127.0.0.1:{agent.health_port}/")
            wait_for_backend_paths(records, {"/v1/metrics"})


def test_agent_missing_endpoint_fails_fast() -> None:
    with agent_container() as agent:
        output = wait_for_exit(agent.name)
        assert "SIGNOZ_AGENT_ENDPOINT is required" in output  # nosec B101


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        (
            {"SIGNOZ_AGENT_ENABLE_HOST_METRICS": "true"},
            "Host metrics are enabled, but /hostfs is not mounted",
        ),
        (
            {"SIGNOZ_AGENT_ENABLE_DOCKER_METRICS": "true"},
            "Docker metrics are enabled, but /var/run/docker.sock is not mounted",
        ),
        (
            {"SIGNOZ_AGENT_ENABLE_DOCKER_LOGS": "true"},
            "Docker logs are enabled, but /var/lib/docker/containers is not mounted",
        ),
    ],
)
def test_agent_host_features_fail_fast_without_mounts(
    env: dict[str, str], expected: str
) -> None:
    with capture_backend() as (endpoint, _records):
        run_env = {"SIGNOZ_AGENT_ENDPOINT": endpoint, **env}
        with agent_container(env=run_env) as agent:
            output = wait_for_exit(agent.name)
            assert expected in output  # nosec B101


def test_agent_custom_config_mode_validates_config_path(tmp_path: Path) -> None:
    missing = "/appdata/config/missing.yaml"
    with agent_container(
        env={
            "SIGNOZ_AGENT_CONFIG_MODE": "custom",
            "SIGNOZ_AGENT_CUSTOM_CONFIG_PATH": missing,
        }
    ) as agent:
        output = wait_for_exit(agent.name)
        assert f"Custom collector config not found at {missing}" in output  # nosec B101

    custom_config = tmp_path / "collector.yaml"
    custom_config.write_text(
        """
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
processors:
  batch:
exporters:
  debug:
service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]
""".strip(),
        encoding="utf-8",
    )
    with agent_container(
        env={
            "SIGNOZ_AGENT_CONFIG_MODE": "custom",
            "SIGNOZ_AGENT_CUSTOM_CONFIG_PATH": "/custom/collector.yaml",
        },
        extra_volumes=[(str(custom_config), "/custom/collector.yaml", "ro")],
    ) as agent:
        wait_for_http(f"http://127.0.0.1:{agent.health_port}/")
        assert inspect_state(agent.name) == "running"  # nosec B101
