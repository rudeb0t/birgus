from abc import ABC, abstractmethod
from typing import Sequence


from ..exception_report import exception_report


class AbstractTransport(ABC):
    @abstractmethod
    def send(self, report: exception_report.ExceptionReport.Reader) -> None:
        pass


type TransportList = Sequence[AbstractTransport]


__all__ = ["AbstractTransport", "TransportList", "exception_report"]
