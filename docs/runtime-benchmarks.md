# Runtime Benchmarks

These measurements are local development evidence, not hard pass/fail limits.
They should be refreshed before release candidates and after major upstream
version changes.

## 2026-04-27 Local Docker / OrbStack

Command:

```bash
AIO_PYTEST_USE_PREBUILT_IMAGE=true pytest tests/integration/test_container_runtime.py::test_happy_path_boot_ingests_persists_and_restarts -q -s
AIO_PYTEST_USE_PREBUILT_IMAGE=true AIO_PYTEST_SOAK_SECONDS=90 pytest tests/integration/test_container_runtime.py::test_signoz_invite_email_delivery_with_local_smtp_fixture tests/integration/test_container_runtime.py::test_alertmanager_email_channel_delivery_with_local_smtp_fixture tests/integration/test_container_runtime.py::test_sustained_ingest_records_resource_samples -q -s
AIO_PYTEST_USE_PREBUILT_IMAGE=true pytest tests/integration -m integration -q -s
```

Image:

- Tag: `signoz-aio:test`
- Size: `1,715,588,619` bytes, about `1.72 GB`
- Previous known WIP size before Dockerfile layer cleanup: about `2.3 GB`
- Post-copy chmod/setup layer after cleanup: `14.4 kB`

Runtime:

- Default first-ready time to `/api/v2/readyz`: `10.2s`
- Restart-ready time to `/api/v2/readyz`: `16.6s`
- Idle `docker stats` sample after first readiness: `71.14% CPU`, `1.262 GiB / 15.66 GiB`
- Full integration re-run sample after rebuild: first-ready `10.2s`,
  restart-ready `16.7s`, idle `63.47% CPU`, `604.8 MiB / 15.66 GiB`

Final-issue local tests:

- SigNoz invite SMTP delivery passed against a local `python:3.11-alpine`
  SMTP capture container.
- Alertmanager email channel test delivery passed against the same local SMTP
  fixture, including the post-root-org Alertmanager poll/sync path.
- Sustained ingest passed with a 90-second soak: `23` trace/log/metric batches
  sent through OTLP HTTP and verified in ClickHouse.
- Full integration matrix passed after the final SMTP/Alertmanager additions:
  `14 passed in 412.69s`.

Notes:

- CPU is a point-in-time sample immediately after first boot, so ClickHouse and
  migration/background startup work can make it look high.
- The measured happy path posts OTLP traces, logs, and metrics, then verifies
  ClickHouse persistence before restart.
- The remaining largest layers are required upstream payloads: ZooKeeper,
  SigNoz OTel collector, SigNoz web assets, and the SigNoz binary.
