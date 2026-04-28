#!/usr/bin/env python3
from __future__ import annotations

import configparser
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import NoReturn

ROOT = pathlib.Path(".")
UPSTREAM_FILE = ROOT / "upstream.toml"
DOCKERFILE = ROOT / "Dockerfile"
SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?$"
)


def fail(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def http_json(url: str, headers: dict[str, str] | None = None) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json, application/json",
            "User-Agent": "jsonbored-signoz-aio",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            return json.load(response)
    except urllib.error.HTTPError as exc:
        fail(f"HTTP error while requesting {url}: {exc.code} {exc.reason}")
    except urllib.error.URLError as exc:
        fail(f"Network error while requesting {url}: {exc.reason}")


def http_text(url: str, headers: dict[str, str] | None = None) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/plain, application/octet-stream",
            "User-Agent": "jsonbored-signoz-aio",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        fail(f"HTTP error while requesting {url}: {exc.code} {exc.reason}")
    except urllib.error.URLError as exc:
        fail(f"Network error while requesting {url}: {exc.reason}")


def parse_version(value: str) -> tuple[int, int, int, bool, str]:
    match = SEMVER_RE.match(value)
    if not match:
        fail(f"Unsupported version format: {value}")
    prerelease = match.group("prerelease")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        prerelease is not None,
        prerelease or "",
    )


def prerelease_sort_key(prerelease: str) -> tuple[tuple[int, object], ...]:
    parts: list[tuple[int, object]] = []
    for item in prerelease.split("."):
        if item.isdigit():
            parts.append((0, int(item)))
        else:
            parts.append((1, item))
    return tuple(parts)


def version_sort_key(
    value: str,
) -> tuple[int, int, int, int, tuple[tuple[int, object], ...]]:
    major, minor, patch, is_prerelease, prerelease = parse_version(value)
    return (
        major,
        minor,
        patch,
        0 if is_prerelease else 1,
        prerelease_sort_key(prerelease),
    )


def filter_versions(values: list[str], stable_only: bool) -> list[str]:
    semver_values = [value for value in values if SEMVER_RE.match(value)]
    if not stable_only:
        return semver_values
    stable_values: list[str] = []
    for value in semver_values:
        _, _, _, is_prerelease, _ = parse_version(value)
        if not is_prerelease:
            stable_values.append(value)
    return stable_values


def github_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def latest_github_tag(repo: str, stable_only: bool) -> str:
    data = http_json(
        f"https://api.github.com/repos/{repo}/tags?per_page=100", github_headers()
    )
    if not isinstance(data, list):
        fail(f"Unexpected GitHub tags response for {repo}")
    tags = [
        entry["name"]
        for entry in data
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    ]
    candidates = filter_versions(tags, stable_only)
    if not candidates:
        fail(f"No matching tags found for upstream repo {repo}")
    return sorted(candidates, key=version_sort_key)[-1]


def latest_github_release(repo: str, stable_only: bool) -> str:
    data = http_json(
        f"https://api.github.com/repos/{repo}/releases?per_page=100", github_headers()
    )
    if not isinstance(data, list):
        fail(f"Unexpected GitHub releases response for {repo}")
    releases: list[str] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        tag = entry.get("tag_name")
        if not isinstance(tag, str) or not SEMVER_RE.match(tag):
            continue
        prerelease = bool(entry.get("prerelease"))
        if stable_only and prerelease:
            continue
        releases.append(tag)
    if not releases:
        fail(f"No matching releases found for upstream repo {repo}")
    return sorted(releases, key=version_sort_key)[-1]


def latest_ghcr_tag(image: str, stable_only: bool) -> str:
    token_data = http_json(f"https://ghcr.io/token?scope=repository:{image}:pull")
    if not isinstance(token_data, dict) or not token_data.get("token"):
        fail(f"Could not get GHCR token for {image}")
    token = str(token_data["token"])
    data = http_json(
        f"https://ghcr.io/v2/{image}/tags/list",
        {"Authorization": f"Bearer {token}"},
    )
    if not isinstance(data, dict):
        fail(f"Unexpected GHCR tags response for {image}")
    tags = [tag for tag in data.get("tags", []) if isinstance(tag, str)]
    candidates = filter_versions(tags, stable_only)
    if not candidates:
        fail(f"No matching GHCR tags found for {image}")
    return sorted(candidates, key=version_sort_key)[-1]


def ghcr_digest_for_tag(image: str, tag: str) -> str:
    token_data = http_json(f"https://ghcr.io/token?scope=repository:{image}:pull")
    if not isinstance(token_data, dict) or not token_data.get("token"):
        fail(f"Could not get GHCR token for {image}")
    token = str(token_data["token"])
    request = urllib.request.Request(
        f"https://ghcr.io/v2/{image}/manifests/{tag}",
        method="HEAD",
        headers={
            "Accept": ",".join(
                [
                    "application/vnd.oci.image.index.v1+json",
                    "application/vnd.oci.image.manifest.v1+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                    "application/vnd.docker.distribution.manifest.v2+json",
                ]
            ),
            "Authorization": f"Bearer {token}",
            "User-Agent": "jsonbored-signoz-aio",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            digest = response.headers.get("docker-content-digest", "").strip()
            if digest:
                return digest
    except urllib.error.HTTPError as exc:
        fail(
            f"HTTP error while requesting GHCR manifest for {image}:{tag}: "
            f"{exc.code} {exc.reason}"
        )
    except urllib.error.URLError as exc:
        fail(
            f"Network error while requesting GHCR manifest for {image}:{tag}: {exc.reason}"
        )

    fail(f"Could not determine digest for GHCR image {image}:{tag}")


def dockerhub_digest_for_tag(image: str, tag: str) -> str:
    token_url = (
        "https://auth.docker.io/token"
        f"?service=registry.docker.io&scope=repository:{image}:pull"
    )
    token_data = http_json(token_url)
    if not isinstance(token_data, dict) or not token_data.get("token"):
        fail(f"Could not get Docker Hub token for {image}")

    request = urllib.request.Request(
        f"https://registry-1.docker.io/v2/{image}/manifests/{tag}",
        method="HEAD",
        headers={
            "Accept": ",".join(
                [
                    "application/vnd.oci.image.index.v1+json",
                    "application/vnd.oci.image.manifest.v1+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                    "application/vnd.docker.distribution.manifest.v2+json",
                ]
            ),
            "Authorization": f"Bearer {token_data['token']}",
            "User-Agent": "jsonbored-signoz-aio",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            digest = response.headers.get("docker-content-digest", "").strip()
            if digest:
                return digest
    except urllib.error.HTTPError as exc:
        fail(
            f"HTTP error while requesting Docker Hub manifest for {image}:{tag}: "
            f"{exc.code} {exc.reason}"
        )
    except urllib.error.URLError as exc:
        fail(
            f"Network error while requesting Docker Hub manifest for {image}:{tag}: {exc.reason}"
        )

    fail(f"Could not determine digest for Docker Hub image {image}:{tag}")


def read_local_value(arg_name: str) -> str:
    pattern = re.compile(rf"^\s*ARG\s+{re.escape(arg_name)}=(.+?)\s*$")
    for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1)
    fail(f"Could not find ARG {arg_name} in Dockerfile")


def write_local_value(arg_name: str, new_value: str) -> None:
    pattern = re.compile(rf"^(\s*ARG\s+{re.escape(arg_name)}=).+?(\s*)$")
    updated_lines: list[str] = []
    changed = False
    for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            updated_lines.append(f"{match.group(1)}{new_value}{match.group(2)}")
            changed = True
        else:
            updated_lines.append(line)
    if not changed:
        fail(f"Could not update ARG {arg_name} in Dockerfile")
    DOCKERFILE.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def split_tag_and_digest(value: str) -> tuple[str, str]:
    tag, separator, digest = value.partition("@")
    return tag, digest if separator else ""


def with_digest(tag: str, digest: str) -> str:
    return f"{tag}@{digest}" if digest else tag


def resolve_compose_image_ref(value: str) -> str:
    cleaned = value.strip().strip("'\"")
    cleaned = re.sub(r"\$\{[A-Za-z_][A-Za-z0-9_]*:-([^}]+)\}", r"\1", cleaned)
    return cleaned


def collect_compose_image_tags(compose_text: str) -> dict[str, str]:
    images: dict[str, str] = {}
    for raw_line in compose_text.splitlines():
        line = raw_line.split("#", 1)[0]
        match = re.match(r"^\s*image:\s*(\S+)\s*$", line)
        if not match:
            continue
        image_ref = resolve_compose_image_ref(match.group(1))
        if ":" not in image_ref:
            continue
        image, tag = image_ref.rsplit(":", 1)
        if image in images and images[image] != tag:
            fail(
                f"Upstream compose references {image} with conflicting tags: "
                f"{images[image]} and {tag}"
            )
        images[image] = tag
    return images


def compose_dependency_mapping(
    config: Mapping[str, object],
) -> tuple[str, dict[str, str]]:
    path = str(config.get("path", "")).strip()
    mappings = {
        key: str(value).strip()
        for key, value in config.items()
        if key != "path" and str(value).strip()
    }
    return path, mappings


def upstream_compose_url(repo: str, version: str, path: str) -> str:
    if not repo:
        fail("compose_dependencies requires [upstream].repo")
    if not path:
        fail("compose_dependencies requires path")
    return f"https://raw.githubusercontent.com/{repo}/{version}/{path}"


def expected_compose_dependency_values(
    *,
    upstream: Mapping[str, object],
    compose_dependencies: Mapping[str, object],
    version: str,
) -> dict[str, str]:
    compose_path, arg_to_image = compose_dependency_mapping(compose_dependencies)
    if not arg_to_image:
        return {}

    compose_url = upstream_compose_url(
        str(upstream.get("repo", "")).strip(), version, compose_path
    )
    compose_text = http_text(compose_url)
    compose_images = collect_compose_image_tags(compose_text)

    expected: dict[str, str] = {}
    for arg_name, image in arg_to_image.items():
        tag = compose_images.get(image)
        if tag is None:
            fail(
                f"Could not find required image {image} in upstream compose for {version}"
            )
        digest = dockerhub_digest_for_tag(image, tag)
        expected[arg_name] = with_digest(tag, digest)
    return expected


def compose_dependency_mismatches(expected: Mapping[str, str]) -> dict[str, str]:
    mismatches: dict[str, str] = {}
    for arg_name, expected_value in expected.items():
        current_value = read_local_value(arg_name)
        current_tag, current_digest = split_tag_and_digest(current_value)
        expected_tag, expected_digest = split_tag_and_digest(expected_value)
        if current_tag != expected_tag or (
            expected_digest and current_digest != expected_digest
        ):
            mismatches[arg_name] = (
                f"{current_value} -> {with_digest(expected_tag, expected_digest)}"
            )
    return mismatches


def write_outputs(outputs: dict[str, str]) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            for key, value in outputs.items():
                handle.write(f"{key}={value}\n")
    else:
        for key, value in outputs.items():
            print(f"{key}={value}")


def parse_upstream_toml(path: pathlib.Path) -> dict[str, dict[str, object]]:
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read_string(path.read_text(encoding="utf-8"))

    result: dict[str, dict[str, object]] = {}
    for section in parser.sections():
        values: dict[str, object] = {}
        for key, raw_value in parser.items(section):
            value = raw_value.strip()
            lower = value.lower()
            if lower == "true":
                values[key] = True
            elif lower == "false":
                values[key] = False
            else:
                values[key] = value.strip('"')
        result[section] = values
    return result


def latest_version_for_config(upstream: dict[str, object], stable_only: bool) -> str:
    upstream_type = str(upstream.get("type", "")).strip()
    if upstream_type == "github-tag":
        return latest_github_tag(str(upstream.get("repo", "")).strip(), stable_only)
    if upstream_type == "github-release":
        return latest_github_release(str(upstream.get("repo", "")).strip(), stable_only)
    if upstream_type == "ghcr-container-tag":
        return latest_ghcr_tag(str(upstream.get("image", "")).strip(), stable_only)
    fail(f"Unsupported upstream type: {upstream_type}")


def latest_digest_for_config(upstream: dict[str, object], version: str) -> str:
    digest_source = str(upstream.get("digest_source", "")).strip()
    if not digest_source:
        return ""

    digest_key = str(upstream.get("digest_key", "")).strip()
    image = str(upstream.get("image", "")).strip()
    if not digest_key:
        fail("digest_source is set but digest_key is missing in upstream.toml")
    if not image:
        fail("digest_source is set but image is missing in upstream.toml")

    digest_tag = str(upstream.get("digest_tag", "")).strip() or version
    if digest_source == "ghcr-manifest":
        return ghcr_digest_for_tag(image, digest_tag)
    if digest_source == "dockerhub-manifest":
        return dockerhub_digest_for_tag(image, digest_tag)
    fail(f"Unsupported digest_source: {digest_source}")


def main() -> None:
    if not UPSTREAM_FILE.exists():
        fail("Missing upstream.toml")

    config = parse_upstream_toml(UPSTREAM_FILE)
    upstream = config.get("upstream")
    compose_dependencies = config.get("compose_dependencies", {})
    notifications = config.get("notifications", {})
    if not isinstance(upstream, dict):
        fail("Invalid upstream.toml: missing [upstream]")
    if not isinstance(compose_dependencies, dict):
        fail("Invalid upstream.toml: [compose_dependencies] must be a table")

    stable_only = bool(upstream.get("stable_only", True))
    version_key = str(upstream.get("version_key", "")).strip()
    if not version_key:
        fail("Invalid upstream.toml: missing [upstream].version_key")

    current_version = read_local_value(version_key)
    latest_version = latest_version_for_config(upstream, stable_only)

    digest_key = str(upstream.get("digest_key", "")).strip()
    current_digest = read_local_value(digest_key) if digest_key else ""
    latest_digest = latest_digest_for_config(upstream, latest_version)
    expected_dependencies = expected_compose_dependency_values(
        upstream=upstream,
        compose_dependencies=compose_dependencies,
        version=latest_version,
    )
    dependency_mismatches = compose_dependency_mismatches(expected_dependencies)
    updates_available = (
        latest_version != current_version
        or bool(dependency_mismatches)
        or (latest_digest != "" and latest_digest != current_digest)
    )

    if os.environ.get("WRITE_UPSTREAM_VERSION") == "true" and updates_available:
        write_local_value(version_key, latest_version)
        if latest_digest and digest_key:
            write_local_value(digest_key, latest_digest)
        for arg_name, expected_value in expected_dependencies.items():
            write_local_value(arg_name, expected_value)

    release_notes = ""
    if isinstance(notifications, dict):
        release_notes = str(notifications.get("release_notes_url", "")).strip()
    if not release_notes and upstream.get("repo"):
        release_notes = f"https://github.com/{upstream['repo']}/releases"

    branch_name = f"codex/upstream-{latest_version}"
    pr_title = f"chore(deps): bump upstream to {latest_version}"
    if (
        latest_version == current_version
        and latest_digest
        and latest_digest != current_digest
    ):
        branch_name = f"codex/upstream-{latest_version}-digest-refresh"
        pr_title = f"chore(deps): refresh upstream digest for {latest_version}"
    elif latest_version == current_version and dependency_mismatches:
        branch_name = f"codex/upstream-{latest_version}-compose-sync"
        pr_title = f"chore(deps): sync bundled images with SigNoz {latest_version}"

    write_outputs(
        {
            "current_version": current_version,
            "latest_version": latest_version,
            "current_digest": current_digest,
            "latest_digest": latest_digest,
            "compose_mismatches": "; ".join(dependency_mismatches.values()),
            "updates_available": "true" if updates_available else "false",
            "strategy": str(upstream.get("strategy", "pr")).strip() or "pr",
            "upstream_name": str(upstream.get("name", "")).strip(),
            "release_notes_url": release_notes,
            "branch_name": branch_name,
            "pr_title": pr_title,
        }
    )


if __name__ == "__main__":
    main()
