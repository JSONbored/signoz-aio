# checkov:skip=CKV_DOCKER_3: Optional host and Docker collection needs runtime access to mounted host paths.
ARG ALPINE_VERSION=3.22.2
ARG ALPINE_DIGEST=sha256:4b7ce07002c69e8f3d704a9c5d6fd3053be500b7f1c69fc0d80990c2ad8dd412
ARG UPSTREAM_OTELCOL_VERSION=0.151.0
ARG UPSTREAM_OTELCOL_DIGEST=sha256:d57bfe8eee2378f31cb1193239fbcac521d54a5a071fca2bfc106916a32b892d

FROM otel/opentelemetry-collector-contrib:${UPSTREAM_OTELCOL_VERSION}@${UPSTREAM_OTELCOL_DIGEST} AS otelcol

FROM alpine:${ALPINE_VERSION}@${ALPINE_DIGEST}

ARG UPSTREAM_OTELCOL_VERSION
ARG UPSTREAM_OTELCOL_DIGEST

LABEL org.opencontainers.image.title="signoz-agent" \
      org.opencontainers.image.description="Unraid-friendly SigNoz OpenTelemetry collector companion for remote and local hosts." \
      org.opencontainers.image.source="https://github.com/JSONbored/signoz-aio" \
      org.opencontainers.image.licenses="MIT" \
      io.jsonbored.upstream.name="OpenTelemetry Collector Contrib" \
      io.jsonbored.upstream.version="${UPSTREAM_OTELCOL_VERSION}" \
      io.jsonbored.upstream.digest="${UPSTREAM_OTELCOL_DIGEST}" \
      io.jsonbored.wrapper.name="signoz-agent" \
      io.jsonbored.wrapper.type="unraid-agent"

RUN apk add --no-cache \
    bash=5.2.37-r0 \
    ca-certificates=20260413-r0 \
    curl=8.14.1-r2 && \
    addgroup -S signoz-agent && \
    adduser -S -G signoz-agent -h /appdata signoz-agent && \
    mkdir -p /appdata /opt/signoz-agent && \
    chown -R signoz-agent:signoz-agent /appdata /opt/signoz-agent

COPY --from=otelcol /otelcol-contrib /usr/local/bin/otelcol-contrib
COPY --chmod=755 rootfs/usr/local/bin/signoz-agent-entrypoint /usr/local/bin/signoz-agent-entrypoint

EXPOSE 4317/tcp 4318/tcp 13133/tcp
VOLUME ["/appdata"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
    CMD curl -fsS http://127.0.0.1:13133/ >/dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/signoz-agent-entrypoint"]
