from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from tests.helpers import (
    container_file_size,
    container_path_exists,
    docker_available,
    docker_volume,
    ensure_pytest_image,
    reserve_host_port,
    run_command,
)

IMAGE_TAG = "signoz-aio:pytest"
pytestmark = pytest.mark.integration


def logs(name: str) -> str:
    result = run_command(["docker", "logs", name], check=False)
    return result.stdout + result.stderr


def inspect_state(name: str) -> str:
    result = run_command(
        ["docker", "inspect", "-f", "{{.State.Status}}", name],
        check=False,
    )
    return result.stdout.strip()


def wait_for_host_http(
    name: str, host_port: int, path: str = "/api/v2/readyz", timeout: int = 900
) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{host_port}{path}"
    while time.time() < deadline:
        if inspect_state(name) != "running":
            raise AssertionError(f"{name} stopped before becoming ready.\n{logs(name)}")
        if run_command(["curl", "-fsS", url], check=False).returncode == 0:
            return
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


@contextmanager
def container(
    appdata_volume: str, *, enable_host_agent: bool = False
) -> Iterator[tuple[str, int]]:
    name = f"signoz-aio-pytest-{uuid.uuid4().hex[:10]}"
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
        "-p",
        f"{ui_port}:8080",
        "-p",
        f"{grpc_port}:4317",
        "-p",
        f"{http_port}:4318",
        "-v",
        f"{appdata_volume}:/appdata",
    ]
    if enable_host_agent:
        command.extend(["-e", "SIGNOZ_ENABLE_HOST_AGENT=true"])
    command.append(IMAGE_TAG)
    run_command(command)
    try:
        yield name, ui_port
    finally:
        run_command(["docker", "rm", "-f", name], check=False)


@pytest.fixture(scope="session", autouse=True)
def build_image() -> None:
    if not docker_available():
        pytest.skip("Docker is unavailable; integration tests require Docker/OrbStack.")
    ensure_pytest_image(IMAGE_TAG)


def test_happy_path_boot_persists_and_restarts() -> None:
    with docker_volume("signoz-aio-appdata") as appdata_volume:
        with container(appdata_volume) as (name, ui_port):
            wait_for_host_http(name, ui_port)
            assert container_path_exists(
                name, "/appdata/config/generated.env"
            )  # nosec B101
            assert container_path_exists(
                name, "/appdata/signoz/signoz.db"
            )  # nosec B101
            assert (
                container_file_size(name, "/appdata/signoz/signoz.db") > 0
            )  # nosec B101
            wait_for_container_http(name, "http://127.0.0.1:13133/")
            wait_for_container_path(
                name, "/appdata/.telemetrystore-migrations-complete"
            )
            wait_for_container_tcp(name, 4317)
            wait_for_container_tcp(name, 4318)

            run_command(["docker", "restart", name])
            wait_for_host_http(name, ui_port)
            assert (
                container_file_size(name, "/appdata/config/generated.env") > 0
            )  # nosec B101
            wait_for_container_http(name, "http://127.0.0.1:13133/")
            wait_for_container_tcp(name, 4317)
            wait_for_container_tcp(name, 4318)


def test_host_agent_mode_records_source_detection_status() -> None:
    with docker_volume("signoz-aio-host-agent-appdata") as appdata_volume:
        with container(appdata_volume, enable_host_agent=True) as (name, ui_port):
            wait_for_host_http(name, ui_port)
            assert container_path_exists(  # nosec B101
                name, "/appdata/config/generated-host-agent.status"
            )
            status = run_command(
                [
                    "docker",
                    "exec",
                    name,
                    "cat",
                    "/appdata/config/generated-host-agent.status",
                ]
            ).stdout.strip()
            assert status in {"enabled", "enabled-but-no-sources"}  # nosec B101
            if status == "enabled":
                wait_for_container_http(name, "http://127.0.0.1:13134/")
