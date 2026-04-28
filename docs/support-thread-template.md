# SigNoz Unraid Suite Support Thread Draft

Use this as the first-post draft when preparing `signoz-aio` and `signoz-agent`
for Community Apps. Replace the support-thread URL in the XML files only if the
project moves away from GitHub Issues.

```md
# Support: SigNoz AIO and Agent for Unraid

## What this is

SigNoz is a self-hosted observability platform for traces, metrics, and logs.

This repo provides two Unraid templates:

- `signoz-aio`: a self-contained backend/UI/database stack.
- `signoz-agent`: a lightweight OpenTelemetry Collector companion for remote
  hosts, stricter separation, and custom edge collection.

## Who this is for

- Unraid users who want a local observability backend
- Homelab operators who want OTLP endpoints for apps, collectors, and agents
- Power users who understand that ClickHouse-backed observability stacks are
  heavier than typical single-service apps

## Tradeoffs

- This container bundles SigNoz, the SigNoz OpenTelemetry Collector, ClickHouse,
  and ZooKeeper, so first boot is heavier than a small web app.
- Telemetry still has to be sent into SigNoz. This app does not automatically
  instrument every service you run.
- The optional local host agent can collect host and Docker telemetry from the
  same Unraid machine after you explicitly populate the advanced host/Docker
  path fields. Mounting the Docker socket has security implications.
- The separate `signoz-agent` template is the recommended option for remote
  machines or when you do not want host/Docker mounts attached to the main
  backend container.
- Advanced external ClickHouse and PostgreSQL settings are exposed for operators
  who already understand those services.

## Quick install notes

- Image: `ghcr.io/jsonbored/signoz-aio:latest`
- Companion agent image: `ghcr.io/jsonbored/signoz-agent:latest`
- Default WebUI: `http://[UNRAID-IP]:8080`
- OTLP gRPC: `4317`
- OTLP HTTP: `4318`
- Main appdata path: `/mnt/user/appdata/signoz-aio`
- Required setup fields: none beyond the default appdata path and ports

### First boot expectations

First startup can take several minutes while ClickHouse, ZooKeeper, SigNoz, and
the collector initialize and run telemetry-store migrations. Check the container
logs before assuming the app is hung.

## Persistence

The container stores persistent state under `/appdata`, including:

- ClickHouse telemetry data
- ZooKeeper state
- SigNoz SQLite metadata by default
- generated runtime secrets and collector config

## Support scope

This thread covers the JSONbored Unraid packaging for `signoz-aio` and
`signoz-agent`.

For support, please include:

- which template you are using: `signoz-aio`, `signoz-agent`, or both
- your Unraid version
- the relevant template settings
- container logs from first failure onward
- whether you enabled the local host agent or external services
- what data source is sending telemetry into SigNoz

If the issue is upstream SigNoz behavior rather than the Unraid packaging layer,
I may redirect you to the upstream project.

## Links

- Project repo: https://github.com/JSONbored/signoz-aio
- Upstream project: https://github.com/SigNoz/signoz
- SigNoz docs: https://signoz.io/docs/
- Catalog repo: https://github.com/JSONbored/awesome-unraid
- GitHub Sponsors: https://github.com/sponsors/JSONbored
- Ko-fi: https://ko-fi.com/jsonbored
```
