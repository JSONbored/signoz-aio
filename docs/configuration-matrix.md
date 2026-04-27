# Configuration Matrix

This matrix records the supported `signoz-aio` configuration surface. The Unraid
template should expose beginner-safe defaults while still making upstream-backed
power-user controls available without requiring users to hand-edit the template.

Status meanings:

- `exposed`: available in `signoz-aio.xml`.
- `supported-not-CA-exposed`: supported by the wrapper or upstream, but not useful
  enough for the Community Apps form.
- `internal`: controlled by the image wrapper or bundled service topology.
- `deprecated-alias`: accepted by upstream for compatibility, but not exposed as
  a primary Unraid setting.
- `not-applicable`: upstream option exists, but does not fit this single-node AIO
  image.

## Beginner Defaults

| Setting                       | Status  | Default                        | Notes                                                            |
| ----------------------------- | ------- | ------------------------------ | ---------------------------------------------------------------- |
| `8080`                        | exposed | `8080`                         | SigNoz UI/API port.                                              |
| `4317`                        | exposed | `4317`                         | OTLP gRPC ingest port.                                           |
| `4318`                        | exposed | `4318`                         | OTLP HTTP ingest port.                                           |
| `/appdata`                    | exposed | `/mnt/user/appdata/signoz-aio` | Single persistent Unraid root.                                   |
| `SIGNOZ_ENABLE_HOST_AGENT`    | exposed | `false`                        | Optional same-host metrics/logs collector, exposed as advanced.  |
| `SIGNOZ_TOKENIZER_JWT_SECRET` | exposed | generated                      | Persisted under `/appdata/config/generated.env` when left blank. |

## AIO Wrapper Controls

| Setting                             | Status  | Default                      | Notes                                                            |
| ----------------------------------- | ------- | ---------------------------- | ---------------------------------------------------------------- |
| `SIGNOZ_AIO_WAIT_TIMEOUT_SECONDS`   | exposed | `300`                        | Fails startup instead of waiting forever on broken dependencies. |
| `SIGNOZ_USE_EXTERNAL_CLICKHOUSE`    | exposed | `false`                      | Disables bundled ClickHouse and ZooKeeper only when true.        |
| `SIGNOZ_CLICKHOUSE_HEALTHCHECK_URL` | exposed | `http://127.0.0.1:8123/ping` | Must point at external ClickHouse when external mode is enabled. |

## SigNoz Server

| Setting                                         | Status   | Default           | Notes                                                   |
| ----------------------------------------------- | -------- | ----------------- | ------------------------------------------------------- |
| `SIGNOZ_GLOBAL_EXTERNAL__URL`                   | exposed  | blank             | Public UI URL for links and reverse proxy setups.       |
| `SIGNOZ_GLOBAL_INGESTION__URL`                  | exposed  | blank             | Public ingestion URL when it differs from the UI URL.   |
| `SIGNOZ_ANALYTICS_ENABLED`                      | exposed  | `false`           | Upstream Segment analytics toggle.                      |
| `SIGNOZ_STATSREPORTER_ENABLED`                  | exposed  | `true`            | Upstream stats reporter toggle.                         |
| `SIGNOZ_APISERVER_TIMEOUT_DEFAULT`              | exposed  | `60s`             | Default API request timeout.                            |
| `SIGNOZ_APISERVER_TIMEOUT_MAX`                  | exposed  | `600s`            | Maximum API request timeout.                            |
| `SIGNOZ_APISERVER_TIMEOUT_EXCLUDED__ROUTES`     | exposed  | upstream defaults | Comma-separated timeout exclusions.                     |
| `SIGNOZ_APISERVER_LOGGING_EXCLUDED__ROUTES`     | exposed  | upstream defaults | Comma-separated logging exclusions.                     |
| `SIGNOZ_PPROF_ENABLED`                          | exposed  | `true`            | Internal pprof remains un-published by the CA template. |
| `SIGNOZ_PPROF_ADDRESS`                          | exposed  | `0.0.0.0:6060`    | Internal bind address only.                             |
| `SIGNOZ_RULER_EVAL__DELAY`                      | exposed  | `2m`              | Rule evaluation delay.                                  |
| `SIGNOZ_METRICSEXPLORER_TELEMETRYSTORE_THREADS` | exposed  | `8`               | Metrics Explorer ClickHouse query threads.              |
| `SIGNOZ_WEB_ENABLED`                            | internal | `true`            | Disabling the web UI breaks the AIO user path.          |
| `SIGNOZ_WEB_DIRECTORY` / `SIGNOZ_WEB_INDEX`     | internal | image defaults    | Bound to files copied from upstream image.              |

## Metadata Store

| Setting                                    | Status           | Default                     | Notes                                              |
| ------------------------------------------ | ---------------- | --------------------------- | -------------------------------------------------- |
| `SIGNOZ_SQLSTORE_PROVIDER`                 | exposed          | `sqlite`                    | `postgres` requires a DSN and external PostgreSQL. |
| `SIGNOZ_SQLSTORE_SQLITE_PATH`              | exposed          | `/appdata/signoz/signoz.db` | Default metadata database path.                    |
| `SIGNOZ_SQLSTORE_SQLITE_MODE`              | exposed          | `wal`                       | SQLite journal mode.                               |
| `SIGNOZ_SQLSTORE_SQLITE_BUSY__TIMEOUT`     | exposed          | `10s`                       | SQLite lock wait.                                  |
| `SIGNOZ_SQLSTORE_SQLITE_TRANSACTION__MODE` | exposed          | `deferred`                  | SQLite transaction mode.                           |
| `SIGNOZ_SQLSTORE_MAX__OPEN__CONNS`         | exposed          | `100`                       | SQL metadata connection pool size.                 |
| `SIGNOZ_SQLSTORE_MAX__CONN__LIFETIME`      | exposed          | `0s`                        | SQL metadata connection lifetime.                  |
| `SIGNOZ_SQLSTORE_POSTGRES_DSN`             | exposed          | blank                       | Required when provider is `postgres`.              |
| `SIGNOZ_LOCAL_DB_PATH`                     | deprecated-alias | blank                       | Upstream alias for SQLite path. Do not expose.     |

## Telemetry Store And Collector

| Setting                                        | Status  | Default                               | Notes                                                                                                       |
| ---------------------------------------------- | ------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_DSN`         | exposed | `tcp://127.0.0.1:9000`                | Base ClickHouse DSN.                                                                                        |
| `SIGNOZ_TELEMETRYSTORE_MAX__OPEN__CONNS`       | exposed | `100`                                 | SigNoz ClickHouse pool size.                                                                                |
| `SIGNOZ_TELEMETRYSTORE_MAX__IDLE__CONNS`       | exposed | `50`                                  | SigNoz ClickHouse idle pool size.                                                                           |
| `SIGNOZ_TELEMETRYSTORE_DIAL__TIMEOUT`          | exposed | `5s`                                  | ClickHouse dial timeout.                                                                                    |
| `SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_SETTINGS_*`  | exposed | blank                                 | Optional ClickHouse query settings, including ignored data-skipping indices; blank keeps upstream defaults. |
| `SIGNOZ_OTEL_COLLECTOR_CLICKHOUSE_DSN`         | exposed | derived                               | Collector-specific base DSN override.                                                                       |
| `SIGNOZ_CLICKHOUSE_TRACES_DSN`                 | exposed | derived                               | Traces database DSN.                                                                                        |
| `SIGNOZ_CLICKHOUSE_METRICS_DSN`                | exposed | derived                               | Metrics database DSN.                                                                                       |
| `SIGNOZ_CLICKHOUSE_LOGS_DSN`                   | exposed | derived                               | Logs database DSN.                                                                                          |
| `SIGNOZ_CLICKHOUSE_METER_DSN`                  | exposed | derived                               | Meter database DSN.                                                                                         |
| `SIGNOZ_CLICKHOUSE_METADATA_DSN`               | exposed | derived                               | Telemetry metadata database DSN.                                                                            |
| `SIGNOZ_OTEL_COLLECTOR_CLICKHOUSE_CLUSTER`     | exposed | `cluster`                             | Must match external ClickHouse topology.                                                                    |
| `SIGNOZ_OTEL_COLLECTOR_CLICKHOUSE_REPLICATION` | exposed | `false`                               | Internal AIO default avoids multi-replica assumptions.                                                      |
| `SIGNOZ_OTEL_COLLECTOR_TIMEOUT`                | exposed | `10m`                                 | Collector migration/query timeout.                                                                          |
| `SIGNOZ_OTEL_COLLECTOR_BATCH_*`                | exposed | upstream defaults                     | Regular telemetry batch controls.                                                                           |
| `SIGNOZ_OTEL_COLLECTOR_METER_BATCH_*`          | exposed | upstream defaults                     | SigNoz meter batch controls.                                                                                |
| `SIGNOZ_OTEL_COLLECTOR_SELF_SCRAPE_INTERVAL`   | exposed | `60s`                                 | Collector self-metrics scrape interval.                                                                     |
| `SIGNOZ_OTEL_COLLECTOR_PPROF_ENDPOINT`         | exposed | `0.0.0.0:1777`                        | Internal pprof endpoint, not CA-published.                                                                  |
| `LOW_CARDINAL_EXCEPTION_GROUPING`              | exposed | `false`                               | Upstream collector trace option.                                                                            |
| `OTEL_RESOURCE_ATTRIBUTES`                     | exposed | `host.name=signoz-host,os.type=linux` | Applied to internal collector output.                                                                       |

## Host Agent

| Setting                                        | Status  | Default                      | Notes                                              |
| ---------------------------------------------- | ------- | ---------------------------- | -------------------------------------------------- |
| `/hostfs`                                      | exposed | `/`                          | Optional host metrics mount.                       |
| `/var/run/docker.sock`                         | exposed | `/var/run/docker.sock`       | Optional Docker metrics mount; security-sensitive. |
| `/var/lib/docker/containers`                   | exposed | `/var/lib/docker/containers` | Optional Docker log mount.                         |
| `SIGNOZ_HOST_AGENT_PROMETHEUS_TARGETS`         | exposed | blank                        | Comma-separated local scrape targets.              |
| `SIGNOZ_HOST_AGENT_PROMETHEUS_METRICS_PATH`    | exposed | `/metrics`                   | Metrics path for simple scrape targets.            |
| `SIGNOZ_HOST_AGENT_PROMETHEUS_SCRAPE_INTERVAL` | exposed | `30s`                        | Scrape interval for simple targets.                |

## Email, Cache, And Feature Flags

| Setting                                            | Status  | Default        | Notes                                                                      |
| -------------------------------------------------- | ------- | -------------- | -------------------------------------------------------------------------- |
| `SIGNOZ_EMAILING_ENABLED`                          | exposed | `false`        | Enables SMTP email delivery; requires a valid SMTP from address when true. |
| `SIGNOZ_EMAILING_SMTP_ADDRESS`                     | exposed | `localhost:25` | SMTP host:port.                                                            |
| `SIGNOZ_EMAILING_SMTP_FROM`                        | exposed | blank          | Sender address.                                                            |
| `SIGNOZ_EMAILING_SMTP_AUTH_USERNAME`               | exposed | blank          | SMTP username.                                                             |
| `SIGNOZ_EMAILING_SMTP_AUTH_PASSWORD`               | exposed | blank          | SMTP password.                                                             |
| `SIGNOZ_EMAILING_SMTP_TLS_ENABLED`                 | exposed | `false`        | SMTP TLS toggle.                                                           |
| `SIGNOZ_CACHE_PROVIDER`                            | exposed | `memory`       | `redis` requires external Redis.                                           |
| `SIGNOZ_CACHE_MEMORY_MAX__COST`                    | exposed | `134217728`    | In-memory cache size.                                                      |
| `SIGNOZ_CACHE_REDIS_HOST`                          | exposed | blank          | External Redis host.                                                       |
| `SIGNOZ_CACHE_REDIS_PORT`                          | exposed | `6379`         | External Redis port.                                                       |
| `SIGNOZ_CACHE_REDIS_PASSWORD`                      | exposed | blank          | External Redis password.                                                   |
| `SIGNOZ_FLAGGER_CONFIG_BOOLEAN_USE__SPAN__METRICS` | exposed | blank          | Optional upstream feature flag.                                            |
| `SIGNOZ_FLAGGER_CONFIG_BOOLEAN_KAFKA__SPAN__EVAL`  | exposed | blank          | Optional upstream feature flag.                                            |

## Auth And Token Lifetimes

| Setting                                            | Status           | Default   | Notes                                              |
| -------------------------------------------------- | ---------------- | --------- | -------------------------------------------------- |
| `SIGNOZ_USER_ROOT_ENABLED`                         | exposed          | `false`   | Enables root user reconciliation.                  |
| `SIGNOZ_USER_ROOT_EMAIL`                           | exposed          | blank     | Required when root user is enabled.                |
| `SIGNOZ_USER_ROOT_PASSWORD`                        | exposed          | blank     | Required when root user is enabled.                |
| `SIGNOZ_USER_ROOT_ORG_NAME`                        | exposed          | `default` | Root organization name.                            |
| `SIGNOZ_USER_ROOT_ORG_ID`                          | exposed          | blank     | Optional deterministic UUIDv7.                     |
| `SIGNOZ_USER_PASSWORD_INVITE_MAX__TOKEN__LIFETIME` | exposed          | `48h`     | Invite token lifetime.                             |
| `SIGNOZ_USER_PASSWORD_RESET_ALLOW__SELF`           | exposed          | `false`   | Self-service password reset.                       |
| `SIGNOZ_USER_PASSWORD_RESET_MAX__TOKEN__LIFETIME`  | exposed          | `6h`      | Reset token lifetime.                              |
| `SIGNOZ_TOKENIZER_ROTATION_INTERVAL`               | exposed          | `30m`     | Token rotation interval.                           |
| `SIGNOZ_TOKENIZER_ROTATION_DURATION`               | exposed          | `1m`      | Previous-token grace period.                       |
| `SIGNOZ_TOKENIZER_LIFETIME_IDLE`                   | exposed          | `168h`    | Idle session lifetime.                             |
| `SIGNOZ_TOKENIZER_LIFETIME_MAX`                    | exposed          | `720h`    | Maximum session lifetime.                          |
| `SIGNOZ_TOKENIZER_OPAQUE_TOKEN_MAX__PER__USER`     | exposed          | `5`       | Opaque token cap.                                  |
| `SIGNOZ_JWT_SECRET`                                | deprecated-alias | blank     | Upstream alias; use `SIGNOZ_TOKENIZER_JWT_SECRET`. |

## Bundled ClickHouse And ZooKeeper

| Setting                                 | Status         | Default     | Notes                                                    |
| --------------------------------------- | -------------- | ----------- | -------------------------------------------------------- |
| `CLICKHOUSE_SKIP_USER_SETUP`            | internal       | `1`         | Matches upstream Compose.                                |
| ClickHouse ports `8123`, `9000`, `9009` | internal       | inherited   | Used inside the container; not published by CA template. |
| `ZOO_AUTOPURGE_INTERVAL`                | exposed        | `1`         | ZooKeeper housekeeping interval.                         |
| `ZOO_ENABLE_PROMETHEUS_METRICS`         | exposed        | `yes`       | Internal ZooKeeper metrics toggle.                       |
| `ZOO_PROMETHEUS_METRICS_PORT_NUMBER`    | exposed        | `9141`      | Internal metrics port.                                   |
| `ZOO_SERVER_ID` / `ZOO_SERVERS`         | not-applicable | single-node | HA ZooKeeper topology is outside the AIO model.          |

## Deprecated Upstream Aliases Not Exposed

| Setting                                       | Replacement                                                                                             |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `CONTEXT_TIMEOUT`                             | `SIGNOZ_APISERVER_TIMEOUT_DEFAULT`                                                                      |
| `CONTEXT_TIMEOUT_MAX_ALLOWED`                 | `SIGNOZ_APISERVER_TIMEOUT_MAX`                                                                          |
| `STORAGE`                                     | `SIGNOZ_TELEMETRYSTORE_PROVIDER`                                                                        |
| `ClickHouseUrl`                               | `SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_DSN`                                                                  |
| `SMTP_ENABLED`                                | `SIGNOZ_EMAILING_ENABLED`                                                                               |
| `SMTP_HOST`, `SMTP_PORT`                      | `SIGNOZ_EMAILING_SMTP_ADDRESS`                                                                          |
| `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | `SIGNOZ_EMAILING_SMTP_AUTH_USERNAME`, `SIGNOZ_EMAILING_SMTP_AUTH_PASSWORD`, `SIGNOZ_EMAILING_SMTP_FROM` |
| `TELEMETRY_ENABLED`                           | `SIGNOZ_ANALYTICS_ENABLED`                                                                              |
| `USE_SPAN_METRICS`                            | `SIGNOZ_FLAGGER_CONFIG_BOOLEAN_USE__SPAN__METRICS`                                                      |
| `KAFKA_SPAN_EVAL`                             | `SIGNOZ_FLAGGER_CONFIG_BOOLEAN_KAFKA__SPAN__EVAL`                                                       |
| `RULES_EVAL_DELAY`                            | `SIGNOZ_RULER_EVAL__DELAY`                                                                              |
