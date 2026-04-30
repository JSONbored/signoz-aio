#!/command/with-contenv bash
# shellcheck shell=bash
# shellcheck disable=SC2154
set -euo pipefail

# shellcheck source=/dev/null
. /opt/signoz-aio/lib/env.sh
normalize_blank_env "${AIO_BLANK_AS_UNSET_VARS[@]}"

APPDATA_DIR="/appdata"
CONFIG_DIR="${APPDATA_DIR}/config"
CLICKHOUSE_DIR="${APPDATA_DIR}/clickhouse"
SIGNOZ_DIR="${APPDATA_DIR}/signoz"
TMP_DIR="${APPDATA_DIR}/tmp"
ZOOKEEPER_DIR="${APPDATA_DIR}/zookeeper"
ENV_FILE="${CONFIG_DIR}/generated.env"
HOST_AGENT_CONFIG_FILE="${CONFIG_DIR}/generated-host-agent.yaml"
HOST_AGENT_STATUS_FILE="${CONFIG_DIR}/generated-host-agent.status"

mkdir -p "${CONFIG_DIR}" "${CLICKHOUSE_DIR}" "${SIGNOZ_DIR}" "${TMP_DIR}" "${ZOOKEEPER_DIR}" /bitnami /etc/clickhouse-server/config.d /var/log/clickhouse-server
ln -sfn "${ZOOKEEPER_DIR}" /bitnami/zookeeper
touch "${ENV_FILE}"
chmod 600 "${ENV_FILE}"

persist_if_missing() {
	local key="$1"
	local value="$2"
	if ! grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
		printf '%s="%s"\n' "${key}" "${value}" >>"${ENV_FILE}"
	fi
}

if [[ -n ${SIGNOZ_TOKENIZER_JWT_SECRET-} ]]; then
	tokenizer_jwt_secret="${SIGNOZ_TOKENIZER_JWT_SECRET}"
else
	tokenizer_jwt_secret="$(openssl rand -hex 32)"
fi
persist_if_missing "SIGNOZ_TOKENIZER_JWT_SECRET" "${tokenizer_jwt_secret}"

rm -f /etc/clickhouse-server/config.d/signoz-cluster.xml /etc/clickhouse-server/config.d/signoz-custom-function.xml
cp /opt/signoz-aio/config/clickhouse/cluster.xml /etc/clickhouse-server/config.d/signoz-cluster.xml
cp /opt/signoz-aio/config/clickhouse/custom-function.xml /etc/clickhouse-server/config.d/signoz-custom-function.xml

mkdir -p /var/lib/clickhouse/user_scripts
cp /opt/signoz-aio/bin/histogram-quantile /var/lib/clickhouse/user_scripts/histogramQuantile
chmod +x /var/lib/clickhouse/user_scripts/histogramQuantile

chown -R clickhouse:clickhouse "${CLICKHOUSE_DIR}" /var/log/clickhouse-server /var/lib/clickhouse/user_scripts
chmod 755 "${APPDATA_DIR}" "${CONFIG_DIR}" "${SIGNOZ_DIR}" "${TMP_DIR}"

generate_host_agent_config() {
	rm -f "${HOST_AGENT_CONFIG_FILE}"
	: >"${HOST_AGENT_STATUS_FILE}"

	if ! is_true "${SIGNOZ_ENABLE_HOST_AGENT:-false}"; then
		echo "disabled" >"${HOST_AGENT_STATUS_FILE}"
		return
	fi

	local metrics_receivers=()
	local logs_receivers=()
	local hostmetrics_block=""
	local docker_stats_block=""
	local filelog_block=""
	local prometheus_block=""
	local scrape_interval="${SIGNOZ_HOST_AGENT_PROMETHEUS_SCRAPE_INTERVAL:-30s}"
	local metrics_path="${SIGNOZ_HOST_AGENT_PROMETHEUS_METRICS_PATH:-/metrics}"

	if [[ -d /hostfs/proc ]] || [[ -d /hostfs/sys ]]; then
		hostmetrics_block=$(
			cat <<'EOF'
  hostmetrics:
    collection_interval: 30s
    root_path: /hostfs
    scrapers:
      cpu: {}
      disk: {}
      filesystem: {}
      load: {}
      memory: {}
      network: {}
      paging: {}
      process:
        mute_process_name_error: true
        mute_process_exe_error: true
        mute_process_io_error: true
        mute_process_user_error: true
      processes: {}
EOF
		)
		metrics_receivers+=("hostmetrics")
	fi

	if [[ -S /var/run/docker.sock ]]; then
		docker_stats_block=$(
			cat <<'EOF'
  docker_stats:
    endpoint: unix:///var/run/docker.sock
    collection_interval: 30s
    timeout: 20s
EOF
		)
		metrics_receivers+=("docker_stats")
	fi

	if [[ -d /var/lib/docker/containers ]]; then
		filelog_block=$(
			cat <<'EOF'
  filelog/docker:
    include:
      - /var/lib/docker/containers/*/*-json.log
    start_at: end
    include_file_name: false
    operators:
      - type: json_parser
        parse_from: body
        timestamp:
          parse_from: attributes.time
          layout_type: gotime
          layout: 2006-01-02T15:04:05.999999999Z07:00
EOF
		)
		logs_receivers+=("filelog/docker")
	fi

	if [[ -n ${SIGNOZ_HOST_AGENT_PROMETHEUS_TARGETS-} ]]; then
		local valid_prometheus_targets=0
		prometheus_block=$(
			cat <<EOF
  prometheus/simple:
    config:
      global:
        scrape_interval: ${scrape_interval}
      scrape_configs:
        - job_name: signoz_aio_targets
          metrics_path: ${metrics_path}
          static_configs:
            - targets:
EOF
		)
		IFS=',' read -r -a prometheus_targets <<<"${SIGNOZ_HOST_AGENT_PROMETHEUS_TARGETS}"
		for target in "${prometheus_targets[@]}"; do
			target="${target#"${target%%[![:space:]]*}"}"
			target="${target%"${target##*[![:space:]]}"}"
			if [[ -n ${target} ]]; then
				prometheus_block+=$'\n'"                - ${target}"
				valid_prometheus_targets=1
			fi
		done
		if [[ ${valid_prometheus_targets} -eq 1 ]]; then
			metrics_receivers+=("prometheus/simple")
		else
			prometheus_block=""
		fi
	fi

	if [[ ${#metrics_receivers[@]} -eq 0 ]] && [[ ${#logs_receivers[@]} -eq 0 ]]; then
		echo "enabled-but-no-sources" >"${HOST_AGENT_STATUS_FILE}"
		return
	fi

	{
		cat <<'EOF'
extensions:
  health_check:
    endpoint: 0.0.0.0:13134

receivers:
EOF
		[[ -n ${hostmetrics_block} ]] && printf '%s\n' "${hostmetrics_block}"
		[[ -n ${docker_stats_block} ]] && printf '%s\n' "${docker_stats_block}"
		[[ -n ${filelog_block} ]] && printf '%s\n' "${filelog_block}"
		[[ -n ${prometheus_block} ]] && printf '%s\n' "${prometheus_block}"
		cat <<'EOF'

processors:
  batch: {}
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
  resourcedetection:
    detectors: [env, system]
    timeout: 2s
    override: false

exporters:
  otlp/signoz:
    endpoint: 127.0.0.1:4317
    tls:
      insecure: true

service:
  telemetry:
    metrics:
      readers:
        - pull:
            exporter:
              prometheus:
                host: 127.0.0.1
                port: 8889
  extensions: [health_check]
EOF
		if [[ ${#metrics_receivers[@]} -gt 0 ]]; then
			printf '  pipelines:\n'
			printf '    metrics:\n'
			printf '      receivers: [%s]\n' "$(
				IFS=', '
				echo "${metrics_receivers[*]}"
			)"
			printf '      processors: [memory_limiter, resourcedetection, batch]\n'
			printf '      exporters: [otlp/signoz]\n'
			if [[ ${#logs_receivers[@]} -gt 0 ]]; then
				printf '    logs:\n'
				printf '      receivers: [%s]\n' "$(
					IFS=', '
					echo "${logs_receivers[*]}"
				)"
				printf '      processors: [memory_limiter, batch]\n'
				printf '      exporters: [otlp/signoz]\n'
			fi
		else
			printf '  pipelines:\n'
			printf '    logs:\n'
			printf '      receivers: [%s]\n' "$(
				IFS=', '
				echo "${logs_receivers[*]}"
			)"
			printf '      processors: [memory_limiter, batch]\n'
			printf '      exporters: [otlp/signoz]\n'
		fi
	} >"${HOST_AGENT_CONFIG_FILE}"

	echo "enabled" >"${HOST_AGENT_STATUS_FILE}"
}

generate_host_agent_config

echo "[signoz-aio] Runtime bootstrap complete."
