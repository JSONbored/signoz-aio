# syntax=docker/dockerfile:1@sha256:2780b5c3bab67f1f76c781860de469442999ed1a0d7992a5efdf2cffc0e3d769
# checkov:skip=CKV_DOCKER_7: Upstream images are pinned by immutable digests instead of mutable tags.
# checkov:skip=CKV_DOCKER_8: s6-overlay needs root to coordinate bundled SigNoz, ClickHouse, ZooKeeper, and collector services.

ARG UPSTREAM_SIGNOZ_VERSION=v0.128.0
ARG UPSTREAM_SIGNOZ_DIGEST=sha256:3eac4573b40a03950e68183a277a759a69f1c07395e3c01f8b0c56ee76b7b23f
ARG UPSTREAM_OTELCOL_VERSION=v0.144.5@sha256:f9bf94d566055d06581f3befbf361cc26d670f31ad00cb31fda2ec380210c5ec
ARG UPSTREAM_CLICKHOUSE_VERSION=25.5.6@sha256:4536143e22dc9bddb217c7e610f6b7ed5e6efd8fefdbc61acdeadb5d8022213a
ARG UPSTREAM_ZOOKEEPER_VERSION=3.7.1@sha256:fcc4a3288154ccaa3bdb5ae6dc10180c084d29a8a6a26b62ac8e30a8940dc2e6
ARG HISTOGRAM_QUANTILE_VERSION=v0.0.1

FROM jsonbored/aio-base:s6-3.2.1.0@sha256:07db479a01a95ba28480b4605f5d1cc8bedb574b77cf167ee46e29b9558fee90 AS aio-base

FROM signoz/signoz:${UPSTREAM_SIGNOZ_VERSION}@${UPSTREAM_SIGNOZ_DIGEST} AS signoz

FROM signoz/signoz-otel-collector:${UPSTREAM_OTELCOL_VERSION} AS otelcol

FROM signoz/zookeeper:${UPSTREAM_ZOOKEEPER_VERSION} AS zookeeper

FROM clickhouse/clickhouse-server:${UPSTREAM_CLICKHOUSE_VERSION}

ARG UPSTREAM_SIGNOZ_VERSION
ARG UPSTREAM_SIGNOZ_DIGEST
ARG UPSTREAM_OTELCOL_VERSION
ARG UPSTREAM_CLICKHOUSE_VERSION
ARG UPSTREAM_ZOOKEEPER_VERSION
ARG HISTOGRAM_QUANTILE_VERSION

# trunk-ignore(hadolint/DL3002)
USER root

LABEL org.opencontainers.image.title="signoz-aio" \
      org.opencontainers.image.description="Single-image Unraid-friendly SigNoz stack bundling SigNoz, the SigNoz OTel collector, ClickHouse, and ZooKeeper." \
      org.opencontainers.image.source="https://github.com/JSONbored/signoz-aio" \
      org.opencontainers.image.vendor="JSONbored" \
      io.jsonbored.upstream.signoz.version="${UPSTREAM_SIGNOZ_VERSION}" \
      io.jsonbored.upstream.signoz.digest="${UPSTREAM_SIGNOZ_DIGEST}" \
      io.jsonbored.upstream.otel_collector.version="${UPSTREAM_OTELCOL_VERSION}" \
      io.jsonbored.upstream.clickhouse.version="${UPSTREAM_CLICKHOUSE_VERSION}" \
      io.jsonbored.upstream.zookeeper.version="${UPSTREAM_ZOOKEEPER_VERSION}"

# trunk-ignore(hadolint/DL3008)
# Shared, pinned s6-overlay from the fleet aio-base overlay.
COPY --from=aio-base /aio-overlay/ /

RUN aio-harden pre && \
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    openssl \
    xz-utils && \
    curl -fsSL -o /tmp/histogram-quantile.tar.gz "https://github.com/SigNoz/signoz/releases/download/histogram-quantile%2F${HISTOGRAM_QUANTILE_VERSION}/histogram-quantile_linux_${histogram_arch}.tar.gz" && \
    mkdir -p /opt/signoz-aio/bin && \
    tar -C /opt/signoz-aio/bin -xzf /tmp/histogram-quantile.tar.gz && \
    chmod +x /opt/signoz-aio/bin/histogram-quantile && \
    mkdir -p /appdata /opt/signoz /opt/signoz-otel-collector /opt/signoz-aio/config/clickhouse && \
    rm -rf /tmp/* /var/lib/apt/lists/*

COPY --chmod=755 --from=signoz /root/signoz /opt/signoz/signoz
COPY --from=signoz /root/templates /opt/signoz/templates
COPY --from=signoz /root/templates /root/templates
COPY --from=signoz /etc/signoz/web /etc/signoz/web
COPY --chmod=755 --from=otelcol /signoz-otel-collector /opt/signoz-otel-collector/signoz-otel-collector
COPY --from=zookeeper /opt/bitnami /opt/bitnami
COPY rootfs/ /

RUN find /etc/cont-init.d -type f -exec chmod +x {} \; && \
    find /etc/services.d -type f -name run -exec chmod +x {} \; && \
    rm -rf /etc/services.d/app /etc/services.d/postgres

VOLUME ["/appdata"]

EXPOSE 8080 4317 4318

ENV S6_CMD_WAIT_FOR_SERVICES_MAXTIME=600000
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8080/api/v2/readyz >/dev/null || exit 1

ENTRYPOINT ["/init"]
