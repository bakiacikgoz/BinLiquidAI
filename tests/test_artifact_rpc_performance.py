from __future__ import annotations

from pathlib import Path
from time import perf_counter

from imperaos.artifacts.models import PrincipalType
from imperaos.artifacts.rpc_protocol import ArtifactRpcMethod, RpcPrincipal, RpcRequest
from imperaos.artifacts.rpc_server import ArtifactRpcServer
from imperaos.artifacts.service import ArtifactService


def test_artifact_health_rpc_p95_stays_within_desktop_budget(tmp_path: Path) -> None:
    server = ArtifactRpcServer(ArtifactService(tmp_path / "artifacts"))
    durations: list[float] = []
    for index in range(100):
        request = RpcRequest(
            contract_version="1.0",
            request_id=f"health-{index}",
            method=ArtifactRpcMethod.RPC_HEALTH,
            workspace_id="workspace-performance",
            principal=RpcPrincipal(
                principal_id="system-performance",
                principal_type=PrincipalType.SYSTEM,
                roles=("artifact_admin",),
            ),
            params={},
        )
        started = perf_counter()
        response = server.handle_request(request)
        durations.append((perf_counter() - started) * 1_000)
        assert response.ok is True

    p95 = sorted(durations)[94]
    assert p95 < 250
