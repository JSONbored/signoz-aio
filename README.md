# SigNoz AIO For Unraid

`signoz-aio` packages the full self-hosted SigNoz stack into a single Unraid-friendly image and CA template.

This repo is being built around the current official SigNoz Docker deployment, not a guessed rewrite. The planned AIO image is meant to supervise the services that SigNoz currently expects for a complete small-to-medium self-hosted install:

- `signoz`
- `signoz-otel-collector`
- `clickhouse`
- `zookeeper`

## Current Status

The single-image runtime is now implemented and locally validated.

- the image supervises `signoz`, `signoz-otel-collector`, `clickhouse`, and `zookeeper`
- local `linux/amd64` build passes
- local smoke testing passes, including:
  - first boot
  - telemetry-store migrations
  - OTLP listener readiness
  - restart and persistence

The next step is real Unraid validation before CA submission.

## Upstream Snapshot

Based on the official `SigNoz/signoz` Docker deployment checked on March 29, 2026, the upstream stack currently pins:

- `signoz/signoz:v0.117.1`
- `signoz/signoz-otel-collector:v0.144.2`
- `clickhouse/clickhouse-server:25.5.6`
- `signoz/zookeeper:3.7.1`

The official Docker deployment exposes:

- `8080` for the SigNoz UI and API
- `4317` for OTLP gRPC ingest
- `4318` for OTLP HTTP ingest

## Unraid AIO Shape

The current `signoz-aio` contract is:

- one custom image
- one primary appdata root, likely `/appdata`
- persisted internal data for:
  - ClickHouse
  - ZooKeeper
  - SigNoz SQLite/config state
- exposed ports for:
  - `8080`
  - `4317`
  - `4318`
- local smoke tests that verify:
  - bootstrap
  - service readiness
  - OTLP listener availability
  - persistence across restart
  - health endpoint response

## Important Design Constraints

- this should mirror official SigNoz behavior closely enough to remain maintainable
- it should be honest about embedded services and storage cost
- it should prefer stable upstream versions and PR-first updates
- it should be beginner-safe for Unraid without hiding important observability tradeoffs

## Key Docs

- [Implementation plan](/tmp/signoz-aio/docs/implementation-plan.md)
- [Upstream tracking notes](/tmp/signoz-aio/docs/upstream-tracking.md)
- [Release checklist](/tmp/signoz-aio/docs/release-checklist.md)

## Sources Used For Bootstrap

- [SigNoz self-host Docker docs](https://signoz.io/docs/install/docker/)
- [SigNoz deployment README](https://github.com/SigNoz/signoz/tree/main/deploy)
- [SigNoz single-binary consolidation issue](https://github.com/SigNoz/signoz/issues/7309)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=JSONbored/signoz-aio&type=date&legend=top-left)](https://www.star-history.com/#JSONbored/signoz-aio&Date)
