# signoz-agent

`signoz-agent` is the lightweight companion collector for `signoz-aio`.

Use it on remote Unraid servers, Docker hosts, or machines where you want host,
Docker, log, Prometheus, and application OTLP collection separated from the main
SigNoz backend container.

The image wraps OpenTelemetry Collector Contrib with Unraid-friendly config
generation:

- OTLP gRPC receiver on `4317`
- OTLP HTTP receiver on `4318`
- optional host metrics from `/hostfs`
- optional Docker metrics from `/var/run/docker.sock`
- optional Docker JSON log tailing from `/var/lib/docker/containers`
- optional Prometheus scrape targets
- OTLP export to a self-hosted `signoz-aio` endpoint or compatible SigNoz Cloud
  endpoint

Host root, Docker socket, and Docker log mounts are intentionally blank by
default in the Unraid template. Enable only the collection sources you need.
Mounting the Docker socket has security implications because it exposes Docker
control access to the collector container.
