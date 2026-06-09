# syntax=docker/dockerfile:1@sha256:2780b5c3bab67f1f76c781860de469442999ed1a0d7992a5efdf2cffc0e3d769
# checkov:skip=CKV_DOCKER_7: Upstream images are pinned by immutable digests instead of mutable tags.
# checkov:skip=CKV_DOCKER_8: s6-overlay needs root to coordinate bundled SigNoz, ClickHouse, ZooKeeper, and collector services.

ARG UPSTREAM_SIGNOZ_VERSION=v0.127.1
ARG UPSTREAM_SIGNOZ_DIGEST=sha256:77de0af293c030e409147d1fdb71d1499f5ce720cd1eb083880ea1349d8880b4
ARG UPSTREAM_OTELCOL_VERSION=v0.144.5@sha256:f9bf94d566055d06581f3befbf361cc26d670f31ad00cb31fda2ec380210c5ec
ARG UPSTREAM_CLICKHOUSE_VERSION=25.5.6@sha256:4536143e22dc9bddb217c7e610f6b7ed5e6efd8fefdbc61acdeadb5d8022213a
ARG UPSTREAM_ZOOKEEPER_VERSION=3.7.1@sha256:fcc4a3288154ccaa3bdb5ae6dc10180c084d29a8a6a26b62ac8e30a8940dc2e6
ARG HISTOGRAM_QUANTILE_VERSION=v0.0.1
ARG S6_OVERLAY_VERSION=3.2.1.0
ARG S6_OVERLAY_NOARCH_SHA256=42e038a9a00fc0fef70bf0bc42f625a9c14f8ecdfe77d4ad93281edf717e10c5
ARG S6_OVERLAY_X86_64_SHA256=8bcbc2cada58426f976b159dcc4e06cbb1454d5f39252b3bb0c778ccf71c9435
ARG S6_OVERLAY_AARCH64_SHA256=c8fd6b1f0380d399422fc986a1e6799f6a287e2cfa24813ad0b6a4fb4fa755cc

FROM signoz/signoz:${UPSTREAM_SIGNOZ_VERSION}@${UPSTREAM_SIGNOZ_DIGEST} AS signoz

FROM signoz/signoz-otel-collector:${UPSTREAM_OTELCOL_VERSION} AS otelcol

FROM signoz/zookeeper:${UPSTREAM_ZOOKEEPER_VERSION} AS zookeeper

FROM clickhouse/clickhouse-server:${UPSTREAM_CLICKHOUSE_VERSION}

ARG TARGETARCH
ARG UPSTREAM_SIGNOZ_VERSION
ARG UPSTREAM_SIGNOZ_DIGEST
ARG UPSTREAM_OTELCOL_VERSION
ARG UPSTREAM_CLICKHOUSE_VERSION
ARG UPSTREAM_ZOOKEEPER_VERSION
ARG HISTOGRAM_QUANTILE_VERSION
ARG S6_OVERLAY_VERSION
ARG S6_OVERLAY_NOARCH_SHA256
ARG S6_OVERLAY_X86_64_SHA256
ARG S6_OVERLAY_AARCH64_SHA256

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
RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i 's|http://|https://|g' {} + && \
    printf 'Acquire::Retries "5";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' > /etc/apt/apt.conf.d/80-retries && \
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    openssl \
    xz-utils && \
    curl -fsSL -o /tmp/s6-overlay-noarch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz" && \
    printf '%s  /tmp/s6-overlay-noarch.tar.xz\n' "${S6_OVERLAY_NOARCH_SHA256}" > /tmp/s6-overlay-noarch.sha256 && \
    sha256sum -c /tmp/s6-overlay-noarch.sha256 && \
    tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz && \
    case "${TARGETARCH}" in \
      amd64) s6_arch="x86_64"; histogram_arch="amd64"; s6_arch_sha256="${S6_OVERLAY_X86_64_SHA256}" ;; \
      arm64) s6_arch="aarch64"; histogram_arch="arm64"; s6_arch_sha256="${S6_OVERLAY_AARCH64_SHA256}" ;; \
      *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL -o /tmp/s6-overlay-arch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${s6_arch}.tar.xz" && \
    printf '%s  /tmp/s6-overlay-arch.tar.xz\n' "${s6_arch_sha256}" > /tmp/s6-overlay-arch.sha256 && \
    sha256sum -c /tmp/s6-overlay-arch.sha256 && \
    tar -C / -Jxpf /tmp/s6-overlay-arch.tar.xz && \
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
