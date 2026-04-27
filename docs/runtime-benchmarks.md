# Runtime Benchmarks

These measurements are local development evidence, not hard pass/fail limits.
They should be refreshed before release candidates and after major upstream
version changes.

## 2026-04-27 Local Docker / OrbStack

Command:

```bash
AIO_PYTEST_USE_PREBUILT_IMAGE=true pytest tests/integration/test_container_runtime.py::test_happy_path_boot_ingests_persists_and_restarts -q -s
```

Image:

- Tag: `signoz-aio:test`
- Size: `1,715,588,619` bytes, about `1.72 GB`
- Previous known WIP size before Dockerfile layer cleanup: about `2.3 GB`
- Post-copy chmod/setup layer after cleanup: `14.4 kB`

Runtime:

- Default first-ready time to `/api/v2/readyz`: `10.2s`
- Restart-ready time to `/api/v2/readyz`: `16.6s`
- Idle `docker stats` sample after first readiness: `64.50% CPU`, `727.7 MiB / 15.66 GiB`

Notes:

- CPU is a point-in-time sample immediately after first boot, so ClickHouse and
  migration/background startup work can make it look high. Treat sustained idle
  CPU as a separate release-candidate check.
- The remaining largest layers are required upstream payloads: ZooKeeper,
  SigNoz OTel collector, SigNoz web assets, and the SigNoz binary.
