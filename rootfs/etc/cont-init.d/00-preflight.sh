#!/command/with-contenv bash
# shellcheck shell=bash
set -euo pipefail

# shellcheck source=/dev/null
. /opt/signoz-aio/lib/env.sh

validate_runtime_config
aio_log "Runtime preflight complete."
