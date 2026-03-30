# signoz-aio Agent Notes

`signoz-aio` packages a self-contained SigNoz deployment for Unraid and also supports an optional built-in local host agent mode.

## Runtime Shape

- `signoz`
- `signoz-otel-collector`
- `clickhouse`
- `zookeeper`
- optional built-in local host agent collector behavior when enabled

## Storage Model

- Telemetry data lives in ClickHouse.
- SigNoz app/config metadata uses SQLite by default and persists under `/appdata/signoz`.
- Advanced users may switch SigNoz metadata to PostgreSQL.
- Advanced users may also point the stack at external ClickHouse instead of the bundled ClickHouse and ZooKeeper.

## Important Behavior

- Default installs should remain fully self-contained and work with bundled SQLite, ClickHouse, and ZooKeeper.
- The built-in host agent is optional and should stay easy to enable from the core template UI, not buried as a hidden trick.
- Host-agent mode should degrade cleanly if optional host mounts are absent.
- The smoke test must cover both:
  - default mode
  - built-in host-agent mode

## Advanced Config Surface

- Metadata DB:
  - `SIGNOZ_SQLSTORE_PROVIDER`
  - `SIGNOZ_SQLSTORE_SQLITE_PATH`
  - `SIGNOZ_SQLSTORE_POSTGRES_DSN`
- Root user provisioning:
  - `SIGNOZ_USER_ROOT_ENABLED`
  - `SIGNOZ_USER_ROOT_EMAIL`
  - `SIGNOZ_USER_ROOT_PASSWORD`
  - `SIGNOZ_USER_ROOT_ORG_NAME`
  - `SIGNOZ_USER_ROOT_ORG_ID`
- External telemetry DB:
  - `SIGNOZ_USE_EXTERNAL_CLICKHOUSE`
  - `SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_DSN`
  - `SIGNOZ_CLICKHOUSE_HEALTHCHECK_URL`
  - collector ClickHouse override variables

## CI And Publish Policy

- Validation and smoke tests should run on PRs and branch pushes.
- `smoke-test` is a matrix and should exercise both default and host-agent modes.
- Publish should happen only from the default branch.
- GHCR image naming must stay lowercase.

## What To Preserve

- Keep the README public-facing and user/community focused.
- Keep the Unraid XML beginner-friendly while exposing advanced options for power users.
- Do not claim this repo is vulnerability-free; upstream SigNoz components can still carry inherited CVEs.
