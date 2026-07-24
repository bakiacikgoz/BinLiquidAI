from imperaos.product_workspace import ProductWorkspaceService, ProductWorkspaceStore


def test_workspace_project_task_and_message_are_durable_and_scoped(tmp_path):
    service = ProductWorkspaceService(ProductWorkspaceStore(tmp_path / "product.sqlite3"))
    project = service.create_project("workspace-a", "Launch")
    task = service.create_task("workspace-a", project.project_id, "Prepare release", "session-a")
    service.add_message("workspace-a", task.task_id, "user", "Prepare release")
    assert service.list_projects("workspace-a")[0].project_id == project.project_id
    assert (
        service.list_tasks("workspace-a", project.project_id)[0].assistant_session_id == "session-a"
    )
    assert service.list_projects("workspace-b") == []
    try:
        service.create_task("workspace-b", project.project_id, "Escape")
    except PermissionError:
        pass
    else:
        raise AssertionError("cross-workspace project access must be denied")
