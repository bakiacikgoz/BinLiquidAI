from __future__ import annotations

from abc import ABC, abstractmethod

from binliquid.schemas.models import ExpertRequest, ExpertResult


class ExpertBase(ABC):
    name: str

    @abstractmethod
    def run(self, request: ExpertRequest) -> ExpertResult:
        raise NotImplementedError
