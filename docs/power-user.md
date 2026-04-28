# Power User Notes

`signoz-aio` defaults to a self-contained SigNoz install with bundled ClickHouse,
ZooKeeper, SigNoz, and the SigNoz OpenTelemetry Collector. The advanced settings
exist for operators who already understand the upstream SigNoz deployment model.

## External Metadata Database

The default metadata store is SQLite at `/appdata/signoz/signoz.db`. Set
`SIGNOZ_SQLSTORE_PROVIDER=postgres` and provide
`SIGNOZ_SQLSTORE_POSTGRES_DSN` only when you already have an external PostgreSQL
database ready.

PostgreSQL only replaces SigNoz metadata storage. It does not replace ClickHouse,
which still stores traces, metrics, logs, and telemetry-derived tables.

## External ClickHouse

Set `SIGNOZ_USE_EXTERNAL_CLICKHOUSE=true` only for advanced deployments where you
manage ClickHouse outside this container. You must also set the ClickHouse DSN
and healthcheck URL so the SigNoz service and collector wait on the correct
endpoint.

The default internal ClickHouse and ZooKeeper path is simpler for Unraid, but it
is heavier than a typical single-service app. Budget RAM, disk, and startup time
accordingly.

## Local Host Agent

`SIGNOZ_ENABLE_HOST_AGENT=true` enables an optional local collector for the same
Unraid host. Host metrics, Docker metrics, and Docker log collection only activate
when the matching advanced path fields are explicitly populated. The default
template leaves these host/Docker mounts blank.

Mounting `/var/run/docker.sock` is powerful and sensitive. It gives the container
Docker control access, so enable it only when the local host telemetry benefit is
worth that security tradeoff.

Use the separate `signoz-agent` template instead when you want to monitor remote
machines, keep host/Docker mounts out of the backend container, or maintain a
collector lifecycle separate from the SigNoz UI/database stack.

## Companion Agent

`signoz-agent` generates an OpenTelemetry Collector config from Unraid template
variables and forwards OTLP data to `signoz-aio` or another SigNoz endpoint. Its
beginner surface is intentionally small: endpoint, appdata, and OTLP ports. Host
metrics, Docker metrics, Docker logs, Prometheus scraping, custom headers, cloud
ingestion keys, resource attributes, and custom collector config mode are all
advanced opt-in settings.

The agent template also leaves `/hostfs`, `/var/run/docker.sock`, and
`/var/lib/docker/containers` blank by default. Enabling a receiver without the
matching mount fails fast instead of silently running a misleading partial
collector.

## Collector Overrides

The collector options expose the upstream ClickHouse DSNs, migration timeout,
cluster, replication, resource attributes, batch sizing, pprof endpoint,
self-metrics scrape interval, and low-cardinality exception grouping controls.
Leave them at the defaults unless you are matching an existing SigNoz deployment
or a known upstream tuning recommendation.

## Runtime Preflight

The wrapper treats blank Unraid fields as unset for supported optional
configuration variables. It also fails fast for invalid external ClickHouse,
external PostgreSQL, root-user, boolean, and integer combinations instead of
letting the upstream services sit in misleading wait loops.

## Config Inventory

See [configuration-matrix.md](configuration-matrix.md) for the supported
upstream and AIO wrapper options, including which settings are intentionally not
exposed in the Community Apps template.
