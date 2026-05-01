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

The CA templates use the Docker Hub image names:

- `jsonbored/signoz-aio`
- `jsonbored/signoz-agent`

## Release flow

1. From `aio-fleet`, run `python -m aio_fleet release status --repo signoz-aio` to inspect the next wrapper release.
2. Run `python -m aio_fleet release prepare --repo signoz-aio` on a release branch, then open a `chore(release): <version>` PR.
3. Review and merge that PR into `main`.
4. Run the central `aio-fleet` control check for the release target commit with publish enabled, and require `aio-fleet / required` to pass.
5. Run `python -m aio_fleet release publish --repo signoz-aio` from `aio-fleet` to create the GitHub Release.

SigNoz Agent component releases use the same control-plane path; component-specific versioning and image names are declared in `.aio-fleet.yml`.
