from abc import ABC, abstractmethod
from typing import Sequence

from ..exception_report import ExceptionReportBuilder, ExceptionReportReader


type TransportPayload = ExceptionReportBuilder | ExceptionReportReader | bytes


class AbstractTransport(ABC):
    @abstractmethod
    def send(self, report: TransportPayload, name: str) -> None:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


type TransportList = Sequence[AbstractTransport]


__all__ = ["AbstractTransport", "TransportList", "TransportPayload"]
