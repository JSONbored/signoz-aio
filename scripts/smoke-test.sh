#!/usr/bin/env bash
set -euo pipefail

IMAGE_TAG="${1:-signoz-aio:test}"
CONTAINER_NAME="${CONTAINER_NAME:-signoz-aio-smoke}"
HOST_PORT="${HOST_PORT:-18080}"
CONTAINER_PORT="${CONTAINER_PORT:-8080}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://127.0.0.1:${HOST_PORT}/api/v1/health}"
READY_TIMEOUT_SECONDS="${READY_TIMEOUT_SECONDS:-600}"
HTTP_TIMEOUT_SECONDS="${HTTP_TIMEOUT_SECONDS:-60}"
KEEP_SMOKE_ARTIFACTS="${KEEP_SMOKE_ARTIFACTS:-0}"
IMAGE_PLATFORM="${IMAGE_PLATFORM:-linux/amd64}"
ENABLE_HOST_AGENT_SMOKE="${ENABLE_HOST_AGENT_SMOKE:-0}"

TMP_APPDATA="$(mktemp -d /tmp/signoz-aio-appdata.XXXXXX)"

cleanup() {
    local exit_code=$?
    if [[ "${KEEP_SMOKE_ARTIFACTS}" == "1" && "${exit_code}" -ne 0 ]]; then
        echo "Smoke test failed; preserving artifacts for debugging."
        echo "SMOKE_CONTAINER_NAME=${CONTAINER_NAME}"
        echo "SMOKE_APPDATA_DIR=${TMP_APPDATA}"
        exit "${exit_code}"
    fi
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    rm -rf "${TMP_APPDATA}"
    exit "${exit_code}"
}
trap cleanup EXIT

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

docker_run_args=(
    --platform "${IMAGE_PLATFORM}" \
    --name "${CONTAINER_NAME}" \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    -p 4317:4317 \
    -p 4318:4318 \
    -v "${TMP_APPDATA}:/appdata" \
)

if [[ "${ENABLE_HOST_AGENT_SMOKE}" == "1" ]]; then
    docker_run_args+=(
        -e SIGNOZ_ENABLE_HOST_AGENT=true
    )
    if [[ -S /var/run/docker.sock ]]; then
        docker_run_args+=(-v /var/run/docker.sock:/var/run/docker.sock)
    fi
    if [[ "$(uname -s)" == "Linux" && -d /proc ]]; then
        docker_run_args+=(-v /:/hostfs:ro)
    fi
    if [[ -d /var/lib/docker/containers ]]; then
        docker_run_args+=(-v /var/lib/docker/containers:/var/lib/docker/containers:ro)
    fi
fi

docker run -d \
    "${docker_run_args[@]}" \
    "${IMAGE_TAG}" >/dev/null

ready_deadline=$((SECONDS + READY_TIMEOUT_SECONDS))
while (( SECONDS < ready_deadline )); do
    if curl -fsS "${HEALTHCHECK_URL}" >/dev/null 2>&1; then
        break
    fi
    if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
        echo "Smoke test container exited unexpectedly." >&2
        docker logs "${CONTAINER_NAME}" >&2 || true
        exit 1
    fi
    sleep 2
done

wait_for_container_http() {
    local url="$1"
    local deadline="$2"
    while (( SECONDS < deadline )); do
        if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
            echo "Smoke test container exited unexpectedly while waiting for ${url}." >&2
            docker logs "${CONTAINER_NAME}" >&2 || true
            return 1
        fi
        if docker exec "${CONTAINER_NAME}" curl -fsS "${url}" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    return 1
}

wait_for_container_tcp() {
    local port="$1"
    local deadline="$2"
    while (( SECONDS < deadline )); do
        if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
            echo "Smoke test container exited unexpectedly while waiting for TCP port ${port}." >&2
            docker logs "${CONTAINER_NAME}" >&2 || true
            return 1
        fi
        if docker exec "${CONTAINER_NAME}" bash -lc "exec 3<>/dev/tcp/127.0.0.1/${port}" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    return 1
}

http_deadline=$((SECONDS + HTTP_TIMEOUT_SECONDS))
while (( SECONDS < http_deadline )); do
    if curl -fsS "${HEALTHCHECK_URL}" >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

curl -fsS "${HEALTHCHECK_URL}" >/dev/null
docker exec "${CONTAINER_NAME}" test -f /appdata/config/generated.env
docker exec "${CONTAINER_NAME}" test -f /appdata/signoz/signoz.db
docker exec "${CONTAINER_NAME}" bash -lc 'find /appdata/clickhouse -mindepth 1 | head -n 1 >/dev/null'
wait_for_container_http "http://127.0.0.1:13133/" "$((SECONDS + READY_TIMEOUT_SECONDS))"
wait_for_container_tcp 4317 "$((SECONDS + READY_TIMEOUT_SECONDS))"
wait_for_container_tcp 4318 "$((SECONDS + READY_TIMEOUT_SECONDS))"
if [[ "${ENABLE_HOST_AGENT_SMOKE}" == "1" ]]; then
    docker exec "${CONTAINER_NAME}" test -f /appdata/config/generated-host-agent.status
    wait_for_container_http "http://127.0.0.1:13134/" "$((SECONDS + READY_TIMEOUT_SECONDS))"
fi

docker restart "${CONTAINER_NAME}" >/dev/null

ready_deadline=$((SECONDS + READY_TIMEOUT_SECONDS))
while (( SECONDS < ready_deadline )); do
    if curl -fsS "${HEALTHCHECK_URL}" >/dev/null 2>&1; then
        break
    fi
    if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
        echo "Smoke test container exited unexpectedly after restart." >&2
        docker logs "${CONTAINER_NAME}" >&2 || true
        exit 1
    fi
    sleep 2
done

curl -fsS "${HEALTHCHECK_URL}" >/dev/null
docker exec "${CONTAINER_NAME}" test -f /appdata/signoz/signoz.db
wait_for_container_http "http://127.0.0.1:13133/" "$((SECONDS + READY_TIMEOUT_SECONDS))"
wait_for_container_tcp 4317 "$((SECONDS + READY_TIMEOUT_SECONDS))"
wait_for_container_tcp 4318 "$((SECONDS + READY_TIMEOUT_SECONDS))"
if [[ "${ENABLE_HOST_AGENT_SMOKE}" == "1" ]]; then
    wait_for_container_http "http://127.0.0.1:13134/" "$((SECONDS + READY_TIMEOUT_SECONDS))"
fi
