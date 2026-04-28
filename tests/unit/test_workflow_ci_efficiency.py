from __future__ import annotations

from pathlib import Path

BUILD_WORKFLOW = Path(".github/workflows/build.yml")
RELEASE_WORKFLOW = Path(".github/workflows/release.yml")
PYTEST_ACTION = Path(".github/actions/run-pytest/action.yml")
ALLOWED_CREATE_PULL_REQUEST_REF = (
    "peter-evans/create-pull-request@"
    "c0f553fe549906ede9cf27b5156039d195d2ece0 # v8.1.0"
)


def test_pytest_jobs_use_shared_local_action() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert workflow.count("uses: ./.github/actions/run-pytest") == 3  # nosec B101
    assert "Upload unit test results to Trunk" not in workflow  # nosec B101
    assert "Upload integration test results to Trunk" not in workflow  # nosec B101
    assert "trunk-io/analytics-uploader@" in PYTEST_ACTION.read_text()  # nosec B101


def test_integration_and_publish_share_docker_cache_scope() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert "DOCKER_CACHE_SCOPE: signoz-aio-image" in workflow  # nosec B101
    assert "AGENT_DOCKER_CACHE_SCOPE: signoz-agent-image" in workflow  # nosec B101
    assert (  # nosec B101
        workflow.count("cache-from: type=gha,scope=${{ env.DOCKER_CACHE_SCOPE }}") == 3
    )
    assert (  # nosec B101
        workflow.count(
            "cache-to: type=gha,mode=max,scope=${{ env.DOCKER_CACHE_SCOPE }}"
        )
        == 3
    )
    assert (  # nosec B101
        workflow.count("cache-from: type=gha,scope=${{ env.AGENT_DOCKER_CACHE_SCOPE }}")
        == 2
    )
    assert (  # nosec B101
        workflow.count(
            "cache-to: type=gha,mode=max,scope=${{ env.AGENT_DOCKER_CACHE_SCOPE }}"
        )
        == 2
    )


def test_suite_component_paths_participate_in_ci_change_detection() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert "- components.toml" in workflow  # nosec B101
    assert "- components/**" in workflow  # nosec B101
    assert "- signoz-agent.xml" in workflow  # nosec B101
    assert (
        "aio_related: ${{ steps.filter.outputs.aio_related }}" in workflow
    )  # nosec B101
    assert (
        "agent_related: ${{ steps.filter.outputs.agent_related }}" in workflow
    )  # nosec B101
    assert (
        "pytest-args: tests/integration_agent -m integration" in workflow
    )  # nosec B101
    assert "AGENT_IMAGE_NAME: jsonbored/signoz-agent" in workflow  # nosec B101
    assert "Prebuild AIO backend image" in workflow  # nosec B101
    assert (  # nosec B101
        "needs.detect-changes.outputs.agent_related == 'true' || "
        "needs.detect-changes.outputs.aio_related == 'true'"
    ) in workflow
    assert (  # nosec B101
        "assets/*)\n                aio_related=true\n                agent_related=true"
        in workflow
    )


def test_template_only_changes_do_not_publish_component_images() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert (  # nosec B101
        "needs.detect-changes.outputs.aio_related == 'true' && "
        "needs.detect-changes.outputs.build_related == 'true' && "
        "github.event_name == 'push'"
    ) in workflow
    assert (  # nosec B101
        "needs.detect-changes.outputs.agent_related == 'true' && "
        "needs.detect-changes.outputs.build_related == 'true' && "
        "github.event_name == 'push'"
    ) in workflow
    assert (  # nosec B101
        "needs.detect-changes.outputs.build_related == 'true' || "
        "needs.detect-changes.outputs.xml_related == 'true') && "
        "github.event_name == 'push'"
    ) not in workflow
    assert (  # nosec B101
        "github.event_name == 'push' && github.ref == 'refs/heads/main' && "
        "needs.detect-changes.outputs.publish_requested == 'true'))"
    ) not in workflow


def test_local_actions_participate_in_ci_change_detection_and_pin_checks() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert "- .github/actions/**" in workflow  # nosec B101
    assert ".github/actions/**|.github/workflows/*)" in workflow  # nosec B101
    assert (
        'pathlib.Path(".github/actions").glob("*/action.yml")' in workflow
    )  # nosec B101


def test_dockerhub_publish_uses_variable_with_secret_fallback() -> None:
    workflow = BUILD_WORKFLOW.read_text()

    assert (  # nosec B101
        "DOCKERHUB_IMAGE_NAME: ${{ vars.DOCKERHUB_IMAGE_NAME }}" in workflow
    )
    assert (  # nosec B101
        "DOCKERHUB_IMAGE_NAME_SECRET: ${{ secrets.DOCKERHUB_IMAGE_NAME }}" in workflow
    )
    assert (  # nosec B101
        'resolved_image_name="${DOCKERHUB_IMAGE_NAME:-${DOCKERHUB_IMAGE_NAME_SECRET}}"'
        in workflow
    )


def test_workflows_use_org_allowed_create_pull_request_pin() -> None:
    workflow_paths = [BUILD_WORKFLOW, *Path(".github/workflows").glob("release*.yml")]
    assert RELEASE_WORKFLOW in workflow_paths  # nosec B101

    for workflow_path in workflow_paths:
        workflow = workflow_path.read_text()

        if "peter-evans/create-pull-request@" not in workflow:
            continue
        assert ALLOWED_CREATE_PULL_REQUEST_REF in workflow  # nosec B101
        assert "peter-evans/create-pull-request@5f6978" not in workflow  # nosec B101
