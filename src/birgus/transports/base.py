import time

from abc import ABC, abstractmethod
from typing import Sequence

from ..exception_report import ExceptionReportBuilder, ExceptionReportReader


type TransportPayload = ExceptionReportBuilder | ExceptionReportReader | bytes


class AbstractTransport(ABC):
    @abstractmethod
    def send(
        self,
        report: TransportPayload,
        name_prefix: str = "",
    ) -> None:
        pass

    def generate_name(self, name_prefix: str = "") -> str:
        return f"{name_prefix}{time.monotonic_ns()}.birgus"


type TransportList = Sequence[AbstractTransport]


__all__ = ["AbstractTransport", "TransportList", "TransportPayload"]
