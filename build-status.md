# Build Status

`signoz-aio` is in the first runnable validation phase.

Current state:

- official upstream Docker architecture researched
- current upstream image versions identified
- single-image runtime implemented around:
  - `signoz`
  - `signoz-otel-collector`
  - `clickhouse`
  - `zookeeper`
- local `linux/amd64` build passed
- local smoke test passed, including restart and persistence

Before enabling automation for this repo:

- run `STRICT_PLACEHOLDERS=true bash scripts/validate-derived-repo.sh .`
- set required Actions variables and `SYNC_TOKEN`
- confirm first GHCR publish and XML sync behavior
- validate real-world Unraid install behavior
