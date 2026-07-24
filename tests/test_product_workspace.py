from imperaos.artifacts.rpc_protocol import ArtifactRpcMethod, RpcPrincipal, RpcRequest
from imperaos.artifacts.rpc_server import ArtifactRpcServer
from imperaos.artifacts.service import ArtifactService
from imperaos.product_workspace import ProductWorkspaceService, ProductWorkspaceStore


def test_workspace_project_task_and_message_are_durable_and_scoped(tmp_path):
    service = ProductWorkspaceService(ProductWorkspaceStore(tmp_path / "product.sqlite3"))
    project = service.create_project("workspace-a", "Launch")
    task = service.create_task("workspace-a", project.project_id, "Prepare release", "session-a")
    service.add_message("workspace-a", task.task_id, "user", "Prepare release")
    link = service.add_link("workspace-a", task.task_id, "artifact", "artifact-a")
    service.set_preference("workspace-a", "operator-a", "shell", '{"theme":"dark"}')
    assert service.list_projects("workspace-a")[0].project_id == project.project_id
    assert (
        service.list_tasks("workspace-a", project.project_id)[0].assistant_session_id == "session-a"
    )
    assert service.list_projects("workspace-b") == []
    assert link.target_id == "artifact-a"
    assert (
        service.get_preference("workspace-a", "operator-a", "shell").value_json
        == '{"theme":"dark"}'
    )
    try:
        service.create_task("workspace-b", project.project_id, "Escape")
    except PermissionError:
        pass
    else:
        raise AssertionError("cross-workspace project access must be denied")


def test_product_workspace_rpc_reuses_the_artifact_sidecar(tmp_path):
    server = ArtifactRpcServer(ArtifactService(tmp_path / "artifacts"))
    response = server.handle_request(
        RpcRequest(
            contractVersion="1.0",
            requestId="project-create-1",
            method=ArtifactRpcMethod.PROJECT_CREATE,
            workspaceId="workspace-a",
            principal=RpcPrincipal(principalId="operator-a", principalType="user"),
            params={"title": "Launch"},
        )
    )
    assert response.ok
    project_id = response.result["projectId"]
    listed = server.handle_request(
        RpcRequest(
            contractVersion="1.0",
            requestId="project-list-1",
            method=ArtifactRpcMethod.PROJECT_LIST,
            workspaceId="workspace-a",
            principal=RpcPrincipal(principalId="operator-a", principalType="user"),
            params={},
        )
    )
    assert listed.result["projects"][0]["projectId"] == project_id
