# SigNoz AIO For Unraid

`signoz-aio` is an in-progress attempt to package the full self-hosted SigNoz stack into a single Unraid-friendly image and CA template.

This repo is being built around the current official SigNoz Docker deployment, not a guessed rewrite. The planned AIO image is meant to supervise the services that SigNoz currently expects for a complete small-to-medium self-hosted install:

- `signoz`
- `signoz-otel-collector`
- `clickhouse`
- `zookeeper`

## Current Status

This repo is in active bootstrap and architecture work.

- official upstream deployment has been researched
- version pins for the current Docker stack have been identified
- Unraid-facing ports and persistence layout are being defined
- the final single-image runtime has not been completed yet

So: this repo is not ready for Community Applications yet, but it is now set up to move in a clean, deliberate direction.

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

## Planned Unraid AIO Shape

The intended `signoz-aio` contract is:

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
