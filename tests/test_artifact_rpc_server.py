from __future__ import annotations

from io import BytesIO
from pathlib import Path

from imperaos.artifacts.models import PrincipalType
from imperaos.artifacts.rpc_protocol import (
    ArtifactRpcMethod,
    RpcFrameDecoder,
    RpcPrincipal,
    RpcRequest,
    RpcResponse,
    encode_frame,
)
from imperaos.artifacts.rpc_server import ArtifactRpcServer
from imperaos.artifacts.service import ArtifactService


def _document(text: str) -> dict[str, object]:
    return {
        "kind": "document",
        "schemaVersion": 1,
        "language": "tr",
        "pageMode": "document",
        "blocks": [
            {
                "id": "block-1",
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def _request(
    request_id: str,
    method: ArtifactRpcMethod,
    params: dict[str, object] | None = None,
    *,
    idempotency_key: str | None = None,
) -> RpcRequest:
    return RpcRequest(
        contract_version="1.0",
        request_id=request_id,
        method=method,
        workspace_id="workspace-1",
        principal=RpcPrincipal(
            principal_id="user-1",
            principal_type=PrincipalType.USER,
            roles=("artifact_admin",),
        ),
        idempotency_key=idempotency_key,
        params=params or {},
    )


def _decode_responses(payload: bytes) -> list[RpcResponse]:
    decoder = RpcFrameDecoder()
    return [RpcResponse.model_validate_json(frame) for frame in decoder.feed(payload)]


def test_server_dispatches_service_calls_and_deduplicates_request_ids(tmp_path: Path) -> None:
    service = ArtifactService(tmp_path / "artifacts")
    server = ArtifactRpcServer(service)
    create = _request(
        "request-create",
        ArtifactRpcMethod.ARTIFACT_CREATE,
        {
            "artifactId": "artifact-1",
            "kind": "document",
            "title": "RPC document",
            "dataClass": "internal",
            "content": _document("rpc-v1"),
            "idempotencyKey": "create-1",
        },
        idempotency_key="create-1",
    )

    first = server.handle_request(create)
    replay = server.handle_request(create)
    mismatch = server.handle_request(
        create.model_copy(update={"params": {**create.params, "title": "Changed"}})
    )
    loaded = server.handle_request(
        _request(
            "request-get",
            ArtifactRpcMethod.ARTIFACT_GET,
            {"artifactId": "artifact-1"},
        )
    )

    assert first.ok is True
    assert replay == first
    assert mismatch.ok is False
    assert mismatch.error is not None
    assert mismatch.error.code == "ARTIFACT_RPC_PROTOCOL_MISMATCH"
    assert loaded.ok is True
    assert loaded.result is not None
    assert loaded.result["artifact"]["artifactId"] == "artifact-1"
    assert service.store.get_artifact("workspace-1", "artifact-1").current_revision_number == 1


def test_server_stdio_is_framed_protocol_only_and_shutdown_stops_admission(
    tmp_path: Path,
) -> None:
    server = ArtifactRpcServer(ArtifactService(tmp_path / "artifacts"))
    stdin = BytesIO(
        encode_frame(_request("hello", ArtifactRpcMethod.RPC_HANDSHAKE))
        + encode_frame(_request("health", ArtifactRpcMethod.RPC_HEALTH))
        + encode_frame(_request("shutdown", ArtifactRpcMethod.RPC_SHUTDOWN))
        + encode_frame(_request("ignored", ArtifactRpcMethod.RPC_HEALTH))
    )
    stdout = BytesIO()
    stderr = BytesIO()

    exit_code = server.serve(stdin, stdout, stderr)
    responses = _decode_responses(stdout.getvalue())

    assert exit_code == 0
    assert [response.request_id for response in responses] == [
        "hello",
        "health",
        "shutdown",
    ]
    assert responses[0].result is not None
    assert responses[0].result["networkListener"] is False
    assert responses[1].result is not None
    assert responses[1].result["status"] == "ready"
    assert responses[2].result == {"drained": True}
    assert stderr.getvalue() == b""


def test_server_malformed_input_fails_closed_without_stdout_or_raw_diagnostic(
    tmp_path: Path,
) -> None:
    server = ArtifactRpcServer(ArtifactService(tmp_path / "artifacts"))
    stdout = BytesIO()
    stderr = BytesIO()

    exit_code = server.serve(
        BytesIO(b"\x00\x00\x00\x10raw-secret-frame"),
        stdout,
        stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == b""
    assert b"raw-secret-frame" not in stderr.getvalue()
    assert b"ARTIFACT_RPC_PROTOCOL_MISMATCH" in stderr.getvalue()
