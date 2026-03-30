# Signoz-AIO Implementation Plan

This document captures the first concrete implementation plan for `signoz-aio`.

## Official Upstream Shape

The current official Docker deployment in `SigNoz/signoz` uses:

- `signoz/signoz:v0.117.1`
- `signoz/signoz-otel-collector:v0.144.2`
- `clickhouse/clickhouse-server:25.5.6`
- `signoz/zookeeper:3.7.1`
- an `init-clickhouse` setup step
- a `signoz-telemetrystore-migrator` setup step

Relevant official ports:

- `8080` UI and API
- `4317` OTLP gRPC ingest
- `4318` OTLP HTTP ingest

## Proposed AIO Runtime

The intended AIO image should supervise these long-lived services:

- ZooKeeper
- ClickHouse
- SigNoz
- SigNoz OTel collector

And these one-shot/bootstrap tasks:

- ClickHouse setup step
- telemetry store migrations

## Proposed Persistence Layout

Use one main Unraid mount:

- `/appdata`

Internal subpaths:

- `/appdata/clickhouse`
- `/appdata/zookeeper`
- `/appdata/signoz`
- `/appdata/config`
- `/appdata/tmp`

This keeps the Unraid template simple while still preserving the important stateful layers.

## Proposed Unraid Contract

Expose:

- `8080/tcp`
- `4317/tcp`
- `4318/tcp`

Likely user-facing variables:

- `TZ`
- optional JWT/secret override if SigNoz still needs one instead of auto-generation
- optional retention/performance knobs later

## Main Risks

- ClickHouse inside a single AIO image is heavy and needs careful restart ordering
- ZooKeeper persistence and health sequencing must be reliable
- the migrator/bootstrap jobs must run idempotently
- this repo should stay honest about resource requirements

## Implementation Order

1. Build a supervised runtime that can run ZooKeeper and ClickHouse reliably.
2. Add SigNoz server and confirm `/api/v1/health`.
3. Add OTel collector with the official config.
4. Add one-shot bootstrap/migration logic.
5. Draft a realistic smoke test with persisted `/appdata`.
6. Finish the Unraid XML and docs.
