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
| `SIGNOZ_STATSREPORTER_ENABLED`                  | exposed  | `false`           | Upstream stats reporter toggle; privacy opt-in.         |
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
| `SIGNOZ_TELEMETRYSTORE_CLICKHOUSE_CLUSTER`     | exposed | `cluster`                             | ClickHouse cluster name used by the SigNoz server.                                                          |
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

| Setting                                        | Status  | Default    | Notes                                                                      |
| ---------------------------------------------- | ------- | ---------- | -------------------------------------------------------------------------- |
| `/hostfs`                                      | exposed | blank      | Optional host metrics mount; explicitly set to `/` only when needed.       |
| `/var/run/docker.sock`                         | exposed | blank      | Optional Docker metrics mount; security-sensitive Docker control access.   |
| `/var/lib/docker/containers`                   | exposed | blank      | Optional Docker log mount; explicitly set to `/var/lib/docker/containers`. |
| `SIGNOZ_HOST_AGENT_PROMETHEUS_TARGETS`         | exposed | blank      | Comma-separated local scrape targets.                                      |
| `SIGNOZ_HOST_AGENT_PROMETHEUS_METRICS_PATH`    | exposed | `/metrics` | Metrics path for simple scrape targets.                                    |
| `SIGNOZ_HOST_AGENT_PROMETHEUS_SCRAPE_INTERVAL` | exposed | `30s`      | Scrape interval for simple targets.                                        |

## Email, Cache, And Feature Flags

| Setting                                            | Status  | Default        | Notes                                                                                    |
| -------------------------------------------------- | ------- | -------------- | ---------------------------------------------------------------------------------------- |
| `SIGNOZ_EMAILING_ENABLED`                          | exposed | `false`        | Enables SMTP email delivery; requires a valid SMTP from address when true.               |
| `SIGNOZ_EMAILING_SMTP_ADDRESS`                     | exposed | `localhost:25` | SMTP host:port.                                                                          |
| `SIGNOZ_EMAILING_SMTP_FROM`                        | exposed | blank          | Sender address.                                                                          |
| `SIGNOZ_EMAILING_SMTP_AUTH_USERNAME`               | exposed | blank          | SMTP username.                                                                           |
| `SIGNOZ_EMAILING_SMTP_AUTH_PASSWORD`               | exposed | blank          | SMTP password.                                                                           |
| `SIGNOZ_EMAILING_SMTP_TLS_ENABLED`                 | exposed | `false`        | SMTP TLS toggle.                                                                         |
| `SIGNOZ_CACHE_PROVIDER`                            | exposed | `memory`       | `redis` requires external Redis.                                                         |
| `SIGNOZ_CACHE_MEMORY_MAX__COST`                    | exposed | `134217728`    | In-memory cache size.                                                                    |
| `SIGNOZ_CACHE_MEMORY_NUM__COUNTERS`                | exposed | `100000`       | In-memory cache counter count.                                                           |
| `SIGNOZ_CACHE_REDIS_HOST`                          | exposed | blank          | External Redis host.                                                                     |
| `SIGNOZ_CACHE_REDIS_PORT`                          | exposed | `6379`         | External Redis port.                                                                     |
| `SIGNOZ_CACHE_REDIS_DB`                            | exposed | `0`            | External Redis database number.                                                          |
| `SIGNOZ_CACHE_REDIS_PASSWORD`                      | exposed | blank          | External Redis password.                                                                 |
| `SIGNOZ_FLAGGER_CONFIG_BOOLEAN_USE__SPAN__METRICS` | exposed | `upstream`     | Optional upstream feature flag; dropdown sentinel leaves the upstream default untouched. |
| `SIGNOZ_FLAGGER_CONFIG_BOOLEAN_KAFKA__SPAN__EVAL`  | exposed | `upstream`     | Optional upstream feature flag; dropdown sentinel leaves the upstream default untouched. |

## Expanded Upstream v0.120.0 Controls

These are advanced-only leaf settings from upstream `conf/example.yaml` and
official self-hosted docs that are safe to represent as Unraid fields and
locally boot-test through environment propagation.

| Setting                                                                      | Status  | Default                                | Notes                                                                       |
| ---------------------------------------------------------------------------- | ------- | -------------------------------------- | --------------------------------------------------------------------------- |
| `SIGNOZ_VERSION_BANNER_ENABLED`                                              | exposed | `true`                                 | Startup version banner toggle.                                              |
| `SIGNOZ_INSTRUMENTATION_LOGS_LEVEL`                                          | exposed | `info`                                 | SigNoz internal instrumentation log level.                                  |
| `SIGNOZ_INSTRUMENTATION_TRACES_ENABLED`                                      | exposed | `false`                                | SigNoz self-tracing toggle.                                                 |
| `SIGNOZ_INSTRUMENTATION_TRACES_PROCESSORS_BATCH_EXPORTER_OTLP_ENDPOINT`      | exposed | `localhost:4317`                       | OTLP endpoint for self-tracing.                                             |
| `SIGNOZ_INSTRUMENTATION_METRICS_ENABLED`                                     | exposed | `true`                                 | SigNoz self-metrics toggle.                                                 |
| `SIGNOZ_INSTRUMENTATION_METRICS_READERS_PULL_EXPORTER_PROMETHEUS_HOST`       | exposed | `0.0.0.0`                              | Internal self-metrics Prometheus host.                                      |
| `SIGNOZ_INSTRUMENTATION_METRICS_READERS_PULL_EXPORTER_PROMETHEUS_PORT`       | exposed | `9090`                                 | Internal self-metrics Prometheus port.                                      |
| `SIGNOZ_ANALYTICS_SEGMENT_KEY`                                               | exposed | blank                                  | Segment key used only when analytics are enabled.                           |
| `SIGNOZ_STATSREPORTER_INTERVAL`                                              | exposed | `6h`                                   | Stats reporter collection interval.                                         |
| `SIGNOZ_STATSREPORTER_COLLECT_IDENTITIES`                                    | exposed | `false`                                | Stats reporter identity/trait collection toggle; privacy opt-in.            |
| `SIGNOZ_QUERIER_CACHE__TTL`                                                  | exposed | `168h`                                 | TTL for cached query results.                                               |
| `SIGNOZ_QUERIER_FLUX__INTERVAL`                                              | exposed | `5m`                                   | Recent-data interval that SigNoz should not cache.                          |
| `SIGNOZ_QUERIER_MAX__CONCURRENT__QUERIES`                                    | exposed | `4`                                    | Missing-range query concurrency limit.                                      |
| `SIGNOZ_PROMETHEUS_TIMEOUT`                                                  | exposed | `2m`                                   | PromQL query timeout.                                                       |
| `SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_ENABLED`                           | exposed | `true`                                 | Active query tracker toggle.                                                |
| `SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_PATH`                              | exposed | blank                                  | Optional active query tracker path.                                         |
| `SIGNOZ_PROMETHEUS_ACTIVE__QUERY__TRACKER_MAX__CONCURRENT`                   | exposed | `20`                                   | Active query tracker concurrency limit.                                     |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_POLL__INTERVAL`                                  | exposed | `1m`                                   | Built-in Alertmanager store sync interval.                                  |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_GROUP__BY`                                 | exposed | `alertname`                            | Comma-separated alert grouping labels.                                      |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_GROUP__INTERVAL`                           | exposed | `1m`                                   | Alert group resend interval.                                                |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_ROUTE_GROUP__WAIT`                               | exposed | `1m`                                   | Initial alert group wait.                                                   |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_ALERTS_GC__INTERVAL`                             | exposed | `30m`                                  | Alert garbage collection interval.                                          |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_MAX`                                    | exposed | `0`                                    | Maximum stored silences; `0` means no limit.                                |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_MAX__SIZE__BYTES`                       | exposed | `0`                                    | Maximum silences size; `0` means no limit.                                  |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_MAINTENANCE__INTERVAL`                  | exposed | `15m`                                  | Silence maintenance/snapshot interval.                                      |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_SILENCES_RETENTION`                              | exposed | `120h`                                 | Silence retention.                                                          |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_NFLOG_MAINTENANCE__INTERVAL`                     | exposed | `15m`                                  | Notification log maintenance interval.                                      |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_NFLOG_RETENTION`                                 | exposed | `120h`                                 | Notification log retention.                                                 |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__FROM`                               | exposed | blank                                  | Sender address for built-in Alertmanager email notifications.               |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__HELLO`                              | exposed | `localhost`                            | HELO/EHLO hostname for Alertmanager SMTP delivery.                          |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__SMARTHOST`                          | exposed | blank                                  | Alertmanager SMTP host:port.                                                |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__USERNAME`                     | exposed | blank                                  | Alertmanager SMTP username.                                                 |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__PASSWORD`                     | exposed | blank                                  | Alertmanager SMTP password.                                                 |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__PASSWORD_FILE`                | exposed | blank                                  | Alertmanager SMTP password file path inside the container.                  |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__SECRET`                       | exposed | blank                                  | Alertmanager SMTP auth secret.                                              |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__AUTH__IDENTITY`                     | exposed | blank                                  | Alertmanager SMTP PLAIN identity.                                           |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__REQUIRE__TLS`                       | exposed | `true`                                 | Alertmanager SMTP TLS requirement toggle.                                   |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CA__FILE`                      | exposed | blank                                  | Alertmanager SMTP TLS CA file path inside the container.                    |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CERT__FILE`                    | exposed | blank                                  | Alertmanager SMTP TLS client certificate file path inside the container.    |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__KEY__FILE`                     | exposed | blank                                  | Alertmanager SMTP TLS client key file path inside the container.            |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__SERVER__NAME`                  | exposed | blank                                  | Alertmanager SMTP TLS SNI/server name.                                      |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CONFIG_INSECURE__SKIP__VERIFY` | exposed | `false`                                | Alertmanager SMTP TLS verification bypass for trusted internal relays only. |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__MIN__VERSION`                  | exposed | `upstream`                             | Dropdown sentinel keeps upstream default, or choose `TLS12`/`TLS13`.        |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__MAX__VERSION`                  | exposed | `upstream`                             | Dropdown sentinel keeps upstream default, or choose `TLS12`/`TLS13`.        |
| `SIGNOZ_EMAILING_SMTP_HELLO`                                                 | exposed | blank                                  | Optional SMTP HELO/EHLO hostname.                                           |
| `SIGNOZ_EMAILING_SMTP_AUTH_SECRET`                                           | exposed | blank                                  | Optional SMTP auth secret.                                                  |
| `SIGNOZ_EMAILING_SMTP_AUTH_IDENTITY`                                         | exposed | blank                                  | Optional SMTP auth identity.                                                |
| `SIGNOZ_EMAILING_SMTP_TLS_INSECURE__SKIP__VERIFY`                            | exposed | `false`                                | Skip SMTP TLS verification for trusted internal relays only.                |
| `SIGNOZ_EMAILING_SMTP_TLS_CA__FILE__PATH`                                    | exposed | blank                                  | Optional SMTP TLS CA file path.                                             |
| `SIGNOZ_EMAILING_SMTP_TLS_CERT__FILE__PATH`                                  | exposed | blank                                  | Optional SMTP TLS client certificate path.                                  |
| `SIGNOZ_EMAILING_SMTP_TLS_KEY__FILE__PATH`                                   | exposed | blank                                  | Optional SMTP TLS client key path.                                          |
| `SIGNOZ_EMAILING_TEMPLATES_FORMAT_HEADER_ENABLED`                            | exposed | `false`                                | Email template header toggle.                                               |
| `SIGNOZ_EMAILING_TEMPLATES_FORMAT_HEADER_LOGO__URL`                          | exposed | blank                                  | Email template header logo URL.                                             |
| `SIGNOZ_EMAILING_TEMPLATES_FORMAT_HELP_ENABLED`                              | exposed | `false`                                | Email template help block toggle.                                           |
| `SIGNOZ_EMAILING_TEMPLATES_FORMAT_HELP_EMAIL`                                | exposed | blank                                  | Email template help email address.                                          |
| `SIGNOZ_EMAILING_TEMPLATES_FORMAT_FOOTER_ENABLED`                            | exposed | `false`                                | Email template footer toggle.                                               |
| `SIGNOZ_IDENTN_TOKENIZER_ENABLED`                                            | exposed | `true`                                 | Tokenizer identity resolver toggle.                                         |
| `SIGNOZ_IDENTN_TOKENIZER_HEADERS`                                            | exposed | `Authorization,Sec-WebSocket-Protocol` | Headers used for tokenizer identity resolution.                             |
| `SIGNOZ_IDENTN_APIKEY_ENABLED`                                               | exposed | `true`                                 | API-key identity resolver toggle.                                           |
| `SIGNOZ_IDENTN_APIKEY_HEADERS`                                               | exposed | `SIGNOZ-API-KEY`                       | Headers used for API-key identity resolution.                               |
| `SIGNOZ_IDENTN_IMPERSONATION_ENABLED`                                        | exposed | `false`                                | Dangerous root impersonation mode; advanced-only.                           |
| `SIGNOZ_SERVICEACCOUNT_EMAIL_DOMAIN`                                         | exposed | `signozserviceaccount.com`             | Service account principal email domain.                                     |
| `SIGNOZ_SERVICEACCOUNT_ANALYTICS_ENABLED`                                    | exposed | `false`                                | Service account analytics toggle; privacy opt-in.                           |
| `SIGNOZ_GATEWAY_URL`                                                         | exposed | `http://localhost:8080`                | Gateway URL for deployments using licensed gateway features.                |
| `SIGNOZ_AUDITOR_PROVIDER`                                                    | exposed | `noop`                                 | Audit event provider.                                                       |
| `SIGNOZ_AUDITOR_BUFFER__SIZE`                                                | exposed | `1000`                                 | Audit event channel capacity.                                               |
| `SIGNOZ_AUDITOR_BATCH__SIZE`                                                 | exposed | `100`                                  | Audit export batch size.                                                    |
| `SIGNOZ_AUDITOR_FLUSH__INTERVAL`                                             | exposed | `1s`                                   | Audit export flush interval.                                                |
| `SIGNOZ_AUDITOR_OTLPHTTP_ENDPOINT`                                           | exposed | `http://localhost:4318/v1/logs`        | Audit OTLP HTTP endpoint.                                                   |
| `SIGNOZ_AUDITOR_OTLPHTTP_INSECURE`                                           | exposed | `false`                                | Audit OTLP HTTP insecure transport toggle.                                  |
| `SIGNOZ_AUDITOR_OTLPHTTP_TIMEOUT`                                            | exposed | `10s`                                  | Audit OTLP HTTP export timeout.                                             |
| `SIGNOZ_AUDITOR_OTLPHTTP_RETRY_ENABLED`                                      | exposed | `true`                                 | Audit export retry toggle.                                                  |
| `SIGNOZ_AUDITOR_OTLPHTTP_RETRY_INITIAL__INTERVAL`                            | exposed | `5s`                                   | Audit retry initial interval.                                               |
| `SIGNOZ_AUDITOR_OTLPHTTP_RETRY_MAX__INTERVAL`                                | exposed | `30s`                                  | Audit retry maximum interval.                                               |
| `SIGNOZ_AUDITOR_OTLPHTTP_RETRY_MAX__ELAPSED__TIME`                           | exposed | `60s`                                  | Audit retry maximum elapsed time.                                           |
| `SIGNOZ_CLOUDINTEGRATION_AGENT_VERSION`                                      | exposed | `v0.0.8`                               | Upstream cloud integration agent version.                                   |

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
| `SIGNOZ_TOKENIZER_OPAQUE_GC_INTERVAL`              | exposed          | `1h`      | Opaque session-token garbage collection interval.  |
| `SIGNOZ_TOKENIZER_OPAQUE_TOKEN_MAX__PER__USER`     | exposed          | `5`       | Opaque token cap.                                  |
| `SIGNOZ_JWT_SECRET`                                | deprecated-alias | blank     | Upstream alias; use `SIGNOZ_TOKENIZER_JWT_SECRET`. |

## Upstream Fields Intentionally Not CA-Exposed

| Setting                                                                                                                                                                     | Status                   | Reason                                                                                                    |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------- |
| `SIGNOZ_WEB_ENABLED`                                                                                                                                                        | internal                 | The web UI is the primary AIO entrypoint; disabling it would make the Unraid app look broken.             |
| `SIGNOZ_WEB_DIRECTORY` / `SIGNOZ_WEB_INDEX`                                                                                                                                 | internal                 | Bound to the upstream web assets copied into the image.                                                   |
| `SIGNOZ_TELEMETRYSTORE_PROVIDER`                                                                                                                                            | internal                 | The AIO image supports ClickHouse telemetry storage only.                                                 |
| `SIGNOZ_ALERTMANAGER_PROVIDER`                                                                                                                                              | internal                 | The bundled single-node app uses SigNoz's built-in Alertmanager provider.                                 |
| `SIGNOZ_TOKENIZER_PROVIDER`                                                                                                                                                 | internal                 | The wrapper manages the JWT tokenizer secret and does not support alternate tokenizers.                   |
| `SIGNOZ_EMAILING_TEMPLATES_DIRECTORY`                                                                                                                                       | internal                 | Email templates are bundled from the upstream image.                                                      |
| `SIGNOZ_SHARDER_PROVIDER` / `SIGNOZ_SHARDER_SINGLE_ORG__ID`                                                                                                                 | not-applicable           | Upstream marks sharding experimental; this AIO image is a single-node beginner-first deployment.          |
| `SIGNOZ_FLAGGER_CONFIG_STRING` / `SIGNOZ_FLAGGER_CONFIG_FLOAT` / `SIGNOZ_FLAGGER_CONFIG_INTEGER` / `SIGNOZ_FLAGGER_CONFIG_OBJECT`                                           | supported-not-CA-exposed | Arbitrary maps are not a good Unraid CA field; specific stable boolean feature flags are exposed instead. |
| `SIGNOZ_EMAILING_SMTP_HEADERS`                                                                                                                                              | supported-not-CA-exposed | Arbitrary SMTP header maps are not represented safely in the CA form.                                     |
| `SIGNOZ_AUDITOR_OTLPHTTP_HEADERS`                                                                                                                                           | supported-not-CA-exposed | Arbitrary OTLP HTTP header maps are not represented safely in the CA form.                                |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CA` / `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CERT` / `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__KEY`                | supported-not-CA-exposed | Raw multi-line PEM material is not suitable for a CA variable field; file-path variants are exposed.      |
| `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CA__REF` / `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__CERT__REF` / `SIGNOZ_ALERTMANAGER_SIGNOZ_GLOBAL_SMTP__TLS__KEY__REF` | not-applicable           | Secret-manager references are not wired into this single-container Unraid deployment.                     |

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
