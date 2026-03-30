# Build Status

`signoz-aio` is in the bootstrap phase.

Current state:

- official upstream Docker architecture researched
- current upstream image versions identified
- repo converted from the generic template into a SigNoz-specific planning starter
- final AIO runtime not implemented yet

Before enabling automation for this repo:

- finish the single-image runtime
- replace all remaining template behavior in Dockerfile, rootfs, and smoke tests
- run `STRICT_PLACEHOLDERS=true bash scripts/validate-derived-repo.sh .`
- validate local Docker build and smoke tests
- set required Actions variables and `SYNC_TOKEN`
- confirm first GHCR publish and XML sync behavior
