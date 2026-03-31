# Releases

`signoz-aio` uses upstream-version-plus-AIO-revision releases such as `v0.117.1-aio.1`.

## Version format

- first wrapper release for upstream `v0.117.1`: `v0.117.1-aio.1`
- second wrapper-only release on the same upstream: `v0.117.1-aio.2`
- first wrapper release after upgrading upstream: `v0.118.0-aio.1`

## Published image tags

Every `main` build publishes:

- `latest`
- the exact pinned upstream version
- an explicit packaging line tag like `v0.117.1-aio-v1`
- `sha-<commit>`

## Release flow

1. Trigger **Release / SigNoz-AIO** from `main`.
2. The workflow computes the next `upstream-aio.N` version and opens a release PR.
3. Merge that PR into `main`.
4. After merge, the workflow creates the Git tag and GitHub Release automatically.
