from __future__ import annotations

import time
from pathlib import Path

from binliquid.experts.base import ExpertBase
from binliquid.schemas.models import ExpertRequest, ExpertResult, ExpertStatus
from binliquid.tools.local_search import find_matches
from binliquid.tools.retrieval import retrieve_top_chunks


class ResearchLiteExpert(ExpertBase):
    name = "research_expert"

    def __init__(self, workspace: str | Path = "."):
        self.workspace = Path(workspace)

    def run(self, request: ExpertRequest) -> ExpertResult:
        started = time.perf_counter()
        chunks = retrieve_top_chunks(request.user_input, root_dir=self.workspace, max_chunks=5)
        matches = find_matches(request.user_input, root_dir=self.workspace, max_matches=4)

        if not chunks and not matches:
            payload = {
                "summary": "Local source bulunamadı. Genel yanıta dönülmeli.",
                "matches": [],
                "chunks": [],
            }
            elapsed = int((time.perf_counter() - started) * 1000)
            return ExpertResult(
                expert_name=self.name,
                status=ExpertStatus.OK,
                confidence=0.45,
                payload=payload,
                elapsed_ms=elapsed,
            )

        bullets = [f"{item['path']}:{item['line']} -> {item['text']}" for item in matches[:3]]
        for chunk in chunks[:2]:
            bullets.append(
                f"{chunk['path']}:{chunk['line_start']}-{chunk['line_end']} "
                f"(score={chunk['score']})"
            )
        payload = {
            "summary": "Yerel dosyalarda ilgili satırlar bulundu.",
            "matches": matches,
            "chunks": chunks,
            "evidence": bullets,
        }
        elapsed = int((time.perf_counter() - started) * 1000)
        return ExpertResult(
            expert_name=self.name,
            status=ExpertStatus.OK,
            confidence=0.78 if chunks else 0.72,
            payload=payload,
            elapsed_ms=elapsed,
        )
