# Releases

`signoz-aio` uses upstream-version-plus-AIO-revision releases such as `v0.120.0-aio.1`.

`signoz-agent` uses upstream-collector-version-plus-agent-revision releases such as `0.139.0-agent.1`.

## Version format

- first wrapper release for upstream `v0.120.0`: `v0.120.0-aio.1`
- second wrapper-only release on the same upstream: `v0.120.0-aio.2`
- first wrapper release after upgrading upstream: `v0.121.0-aio.1`
- first agent wrapper release for collector `0.139.0`: `0.139.0-agent.1`

## Published image tags

Every `main` build publishes changed component images:

- `latest`
- the exact pinned upstream version
- the exact release package tag when the current commit is the release target
- `sha-<commit>`

Images publish independently:

- `ghcr.io/jsonbored/signoz-aio` and `jsonbored/signoz-aio`
- `ghcr.io/jsonbored/signoz-agent` and `jsonbored/signoz-agent`

## Release flow

1. Trigger **Prepare Release / SigNoz-AIO** or **Prepare Release / SigNoz Agent** from `main`.
2. The workflow computes the next component-specific version and opens a release PR.
3. Review and merge that PR into `main`.
4. Trigger the matching **Publish Release / SigNoz-AIO** or **Publish Release / SigNoz Agent** workflow from `main`.
5. The workflow reads the merged `CHANGELOG.md` entry, creates the Git tag, and publishes the GitHub Release.

The publish workflow requires a successful CI run for the release target commit
before it creates the tag or GitHub Release.
