# syntax=docker/dockerfile:1

ARG UPSTREAM_SIGNOZ_VERSION=v0.117.1
ARG UPSTREAM_OTELCOL_VERSION=v0.144.2
ARG UPSTREAM_CLICKHOUSE_VERSION=25.5.6
ARG UPSTREAM_ZOOKEEPER_VERSION=3.7.1
ARG HISTOGRAM_QUANTILE_VERSION=v0.0.1
ARG S6_OVERLAY_VERSION=3.2.1.0

FROM signoz/signoz:${UPSTREAM_SIGNOZ_VERSION} AS signoz

FROM signoz/signoz-otel-collector:${UPSTREAM_OTELCOL_VERSION} AS otelcol

FROM signoz/zookeeper:${UPSTREAM_ZOOKEEPER_VERSION} AS zookeeper

FROM clickhouse/clickhouse-server:${UPSTREAM_CLICKHOUSE_VERSION}

ARG TARGETARCH
ARG UPSTREAM_SIGNOZ_VERSION
ARG UPSTREAM_OTELCOL_VERSION
ARG UPSTREAM_CLICKHOUSE_VERSION
ARG UPSTREAM_ZOOKEEPER_VERSION
ARG HISTOGRAM_QUANTILE_VERSION
ARG S6_OVERLAY_VERSION

USER root

LABEL org.opencontainers.image.title="signoz-aio" \
      org.opencontainers.image.description="Single-image Unraid-friendly SigNoz stack bundling SigNoz, the SigNoz OTel collector, ClickHouse, and ZooKeeper." \
      org.opencontainers.image.source="https://github.com/JSONbored/signoz-aio" \
      org.opencontainers.image.vendor="JSONbored" \
      io.jsonbored.upstream.signoz.version="${UPSTREAM_SIGNOZ_VERSION}" \
      io.jsonbored.upstream.otel_collector.version="${UPSTREAM_OTELCOL_VERSION}" \
      io.jsonbored.upstream.clickhouse.version="${UPSTREAM_CLICKHOUSE_VERSION}" \
      io.jsonbored.upstream.zookeeper.version="${UPSTREAM_ZOOKEEPER_VERSION}"

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    openssl \
    xz-utils && \
    curl -fsSL -o /tmp/s6-overlay-noarch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz" && \
    tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz && \
    case "${TARGETARCH}" in \
      amd64) s6_arch="x86_64"; histogram_arch="amd64" ;; \
      arm64) s6_arch="aarch64"; histogram_arch="arm64" ;; \
      *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL -o /tmp/s6-overlay-arch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${s6_arch}.tar.xz" && \
    tar -C / -Jxpf /tmp/s6-overlay-arch.tar.xz && \
    curl -fsSL -o /tmp/histogram-quantile.tar.gz "https://github.com/SigNoz/signoz/releases/download/histogram-quantile%2F${HISTOGRAM_QUANTILE_VERSION}/histogram-quantile_linux_${histogram_arch}.tar.gz" && \
    mkdir -p /opt/signoz-aio/bin && \
    tar -C /opt/signoz-aio/bin -xzf /tmp/histogram-quantile.tar.gz && \
    chmod +x /opt/signoz-aio/bin/histogram-quantile && \
    mkdir -p /appdata /opt/signoz /opt/signoz-otel-collector /opt/signoz-aio/config/clickhouse && \
    rm -rf /tmp/* /var/lib/apt/lists/*

COPY --from=signoz /root/signoz /opt/signoz/signoz
COPY --from=signoz /root/templates /opt/signoz/templates
COPY --from=signoz /root/templates /root/templates
COPY --from=signoz /etc/signoz/web /etc/signoz/web
COPY --from=otelcol /signoz-otel-collector /opt/signoz-otel-collector/signoz-otel-collector
COPY --from=zookeeper /opt/bitnami /opt/bitnami
COPY rootfs/ /

RUN find /etc/cont-init.d -type f -exec chmod +x {} \; && \
    find /etc/services.d -type f -name run -exec chmod +x {} \; && \
    rm -rf /etc/services.d/app /etc/services.d/postgres && \
    chmod +x /opt/signoz/signoz /opt/signoz-otel-collector/signoz-otel-collector && \
    chmod +x /opt/bitnami/scripts/zookeeper/*.sh

VOLUME ["/appdata"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8080/api/v1/health >/dev/null || exit 1

ENTRYPOINT ["/init"]
