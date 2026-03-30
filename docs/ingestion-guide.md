# Ingestion Guide

`signoz-aio` bundles the SigNoz backend stack, but it still needs telemetry sent into it. This guide explains the practical options for traces, metrics, and logs on Unraid.

## Core Endpoints

The AIO image exposes:

- `8080/tcp`
  - SigNoz UI and API
- `4317/tcp`
  - OTLP gRPC ingest
- `4318/tcp`
  - OTLP HTTP ingest

These are the main entry points for your applications and any external collectors.

## Best-Practice Layout

For most Unraid users, the cleanest design is:

1. run `signoz-aio` as the central SigNoz backend
2. run a separate host collector if you want:
   - host metrics
   - Docker container metrics
   - Docker container logs
   - Prometheus scraping
3. point instrumented apps at either:
   - `signoz-aio` directly, or
   - the host collector, which then forwards to `signoz-aio`

This keeps the main SigNoz container simple and avoids giving it broad host-level permissions.

## Option 1: Send OTLP Directly From Applications

Use this when an app already supports OpenTelemetry exporters.

Examples:

- OTLP gRPC endpoint:
  - `http://YOUR-UNRAID-IP:4317`
- OTLP HTTP endpoint:
  - `http://YOUR-UNRAID-IP:4318`

This is the fastest way to get:

- traces
- application metrics
- application logs, if the app exports them via OTLP

## Option 2: Scrape Prometheus Endpoints

Use a collector with the `prometheus` receiver to scrape apps that expose Prometheus metrics.

Example config:

- [otelcol-prometheus-scrape.yaml](/tmp/signoz-aio/docs/examples/otelcol-prometheus-scrape.yaml)

Good use cases:

- apps that already expose `/metrics`
- exporters such as `node_exporter`, `cadvisor`, or app-native Prometheus endpoints
- consolidating many scrape targets into one forwarding agent

If you already have exporters on your Unraid box, this is usually the cleanest first expansion after basic OTLP ingest.

## Option 3: Collect Docker Host Metrics And Logs

Use a host collector with:

- `hostmetrics`
- `docker_stats`
- `filelog`
- `otlp`

Example config:

- [otelcol-docker-host-agent.yaml](/tmp/signoz-aio/docs/examples/otelcol-docker-host-agent.yaml)

This pattern can collect:

- host CPU, memory, filesystem, and network metrics
- Docker container CPU, memory, and network metrics
- Docker container stdout/stderr logs
- OTLP data from local applications

Typical mounts for a Docker-hosted collector are:

- `/var/run/docker.sock:/var/run/docker.sock`
- `/:/hostfs:ro`
- `/var/lib/docker/containers:/var/lib/docker/containers:ro`

That collector then forwards everything to:

- `YOUR-UNRAID-IP:4317`

This keeps those privileged host mounts out of the main `signoz-aio` container.

## Option 4: Combine Both

Many users will want:

- direct OTLP from instrumented apps
- Prometheus scraping for legacy apps/exporters
- Docker and host metrics via a host collector

That combination works well with `signoz-aio`. SigNoz becomes the backend, while the host collector becomes the local ingestion hub.

## What We Intentionally Do Not Pre-Bundle

This repo does not currently pre-bundle a host-level scraping agent into the main SigNoz image.

Reasons:

- it would require broader host access
- it would complicate the main Unraid CA template
- it would make troubleshooting harder for beginners
- it mixes backend/database concerns with host-collection concerns

If you want a one-click host collector later, the cleaner path is to create a separate optional template or companion repo rather than overloading the main SigNoz container.

## Suggested Future UX

The most newcomer-friendly long-term setup is likely:

1. `signoz-aio`
   - backend, UI, ClickHouse, internal collector, persistence
2. optional `signoz-agent` or `signoz-collector`
   - host metrics
   - Docker metrics
   - Docker logs
   - Prometheus scraping

That split keeps the main CA template simple while still giving advanced users a clean and well-documented expansion path.
