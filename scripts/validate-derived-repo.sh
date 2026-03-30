#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-.}"
cd "${repo_root}"
strict_placeholders="${STRICT_PLACEHOLDERS:-${ENABLE_AIO_AUTOMATION:-false}}"

fail() {
    echo "template validation error: $*" >&2
    exit 1
}

require_file() {
    local path="$1"
    [ -f "${path}" ] || fail "missing required file: ${path}"
}

require_absent() {
    local path="$1"
    [ ! -e "${path}" ] || fail "remove template placeholder path before enabling automation: ${path}"
}

check_no_placeholder() {
    local pattern="$1"
    shift
    if rg -n --fixed-strings "${pattern}" "$@" >/dev/null 2>&1; then
        fail "found unresolved placeholder '${pattern}' in: $*"
    fi
}

require_file "Dockerfile"
require_file "README.md"
require_file "scripts/smoke-test.sh"

if [ "${ENABLE_AIO_AUTOMATION:-}" = "true" ]; then
    [ -n "${TEMPLATE_XML:-}" ] || fail "ENABLE_AIO_AUTOMATION=true requires TEMPLATE_XML"
    require_file "${TEMPLATE_XML}"
    require_absent "template-aio.xml"
fi

critical_files=(
    "Dockerfile"
    "scripts/smoke-test.sh"
)

xml_files=()
if [ -n "${TEMPLATE_XML:-}" ] && [ -f "${TEMPLATE_XML}" ]; then
    xml_files+=("${TEMPLATE_XML}")
fi

if [ "${strict_placeholders}" = "true" ]; then
    check_no_placeholder "ghcr.io/example/upstream-image:latest" "Dockerfile"
    if [ ${#xml_files[@]} -gt 0 ]; then
        check_no_placeholder "yourapp-aio" "${xml_files[@]}"
        check_no_placeholder "Replace this overview with the real app description and first-run guidance." "${xml_files[@]}"
    fi
    check_no_placeholder "replace me with the app ready log line" "scripts/smoke-test.sh"
    check_no_placeholder "Replace this starter service with the real app start command." rootfs/etc/services.d/app/run
fi

if [ "${ENABLE_AIO_AUTOMATION:-}" = "true" ]; then
    [ -n "${AWESOME_UNRAID_REPOSITORY:-}" ] || fail "missing AWESOME_UNRAID_REPOSITORY"
    [ -n "${AWESOME_UNRAID_XML_NAME:-}" ] || fail "missing AWESOME_UNRAID_XML_NAME"
    [ -n "${AWESOME_UNRAID_ICON_NAME:-}" ] || fail "missing AWESOME_UNRAID_ICON_NAME"
fi

echo "Derived repo validation passed."
