#!/command/with-contenv bash
set -euo pipefail

APPDATA_DIR="/appdata"
CONFIG_DIR="${APPDATA_DIR}/config"
CLICKHOUSE_DIR="${APPDATA_DIR}/clickhouse"
SIGNOZ_DIR="${APPDATA_DIR}/signoz"
TMP_DIR="${APPDATA_DIR}/tmp"
ZOOKEEPER_DIR="${APPDATA_DIR}/zookeeper"
ENV_FILE="${CONFIG_DIR}/generated.env"

mkdir -p "${CONFIG_DIR}" "${CLICKHOUSE_DIR}" "${SIGNOZ_DIR}" "${TMP_DIR}" "${ZOOKEEPER_DIR}" /bitnami /etc/clickhouse-server/config.d /var/log/clickhouse-server
ln -sfn "${ZOOKEEPER_DIR}" /bitnami/zookeeper
touch "${ENV_FILE}"
chmod 600 "${ENV_FILE}"

persist_if_missing() {
    local key="$1"
    local value="$2"
    if ! grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
        printf '%s="%s"\n' "${key}" "${value}" >> "${ENV_FILE}"
    fi
}

persist_if_missing "SIGNOZ_TOKENIZER_JWT_SECRET" "${SIGNOZ_TOKENIZER_JWT_SECRET:-$(openssl rand -hex 32)}"

rm -f /etc/clickhouse-server/config.d/signoz-cluster.xml /etc/clickhouse-server/config.d/signoz-custom-function.xml
cp /opt/signoz-aio/config/clickhouse/cluster.xml /etc/clickhouse-server/config.d/signoz-cluster.xml
cp /opt/signoz-aio/config/clickhouse/custom-function.xml /etc/clickhouse-server/config.d/signoz-custom-function.xml

mkdir -p /var/lib/clickhouse/user_scripts
cp /opt/signoz-aio/bin/histogram-quantile /var/lib/clickhouse/user_scripts/histogramQuantile
chmod +x /var/lib/clickhouse/user_scripts/histogramQuantile

chown -R clickhouse:clickhouse "${CLICKHOUSE_DIR}" /var/log/clickhouse-server /var/lib/clickhouse/user_scripts
chmod 755 "${APPDATA_DIR}" "${CONFIG_DIR}" "${SIGNOZ_DIR}" "${TMP_DIR}"

echo "[signoz-aio] Runtime bootstrap complete."
