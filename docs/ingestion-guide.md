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
2. optionally enable the built-in local host agent if you want this same Unraid machine to feed host metrics, Docker metrics, and Docker logs into SigNoz
3. run a separate host collector only if you want:
   - host metrics
   - Docker container metrics
   - Docker container logs
   - Prometheus scraping
4. point instrumented apps at either:
   - `signoz-aio` directly, or
   - the host collector, which then forwards to `signoz-aio`

The built-in local host agent is the easiest one-box option. A separate host collector is still the better fit for remote systems or users who want stricter separation.

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

Use the built-in local host agent or a separate host collector with:

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

With the built-in host agent mode, those mounts are attached to the main container only when you explicitly enable that feature in the template.

## Option 4: Combine Both

Many users will want:

- direct OTLP from instrumented apps
- Prometheus scraping for legacy apps/exporters
- Docker and host metrics via a host collector

That combination works well with `signoz-aio`. SigNoz becomes the backend, while the host collector becomes the local ingestion hub.

## What We Intentionally Do Not Pre-Bundle

This repo now supports an optional built-in local host agent mode for the same Unraid machine.

We still recommend a separate companion agent for:

- remote hosts
- stricter privilege separation
- more advanced collector customization
- environments where you do not want Docker socket and host mounts attached to the main SigNoz container

## Suggested Future UX

The most newcomer-friendly long-term setup is likely:

1. `signoz-aio`
   - backend, UI, ClickHouse, internal collector, persistence
   - optional built-in local host agent for the same Unraid machine
2. optional `signoz-agent` or `signoz-collector`
   - remote hosts
   - stricter separation
   - more advanced edge collection

That split keeps the main CA template simple while still giving advanced users a clean and well-documented expansion path.

## Useful Official References

- [SigNoz Docker install docs](https://signoz.io/docs/install/docker/)
- [SigNoz Docker Collection Agent overview](https://signoz.io/docs/opentelemetry-collection-agents/docker/overview/)
- [SigNoz Docker Collection Agent configuration](https://signoz.io/docs/opentelemetry-collection-agents/docker/configure/)
- [SigNoz Prometheus metrics guide](https://signoz.io/docs/userguide/prometheus-metrics)
