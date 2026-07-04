import logging
import os.path

from .base import AbstractTransport, TransportPayload

logger = logging.getLogger(__name__)


class LocalFileTransport(AbstractTransport):
    def __init__(self, base_dir: str = ""):
        self.base_dir = base_dir

    def send(self, report: TransportPayload, name: str) -> None:
        try:
            exc_filename = os.path.join(self.base_dir, name)
            with open(exc_filename, "wb") as exc_file:
                if isinstance(report, bytes):
                    exc_file.write(report)
                elif hasattr(report, "to_bytes"):
                    exc_file.write(report.to_bytes())
                else:
                    report.write(exc_file)
                logger.info("Exception report written to %s", exc_filename)
        except Exception as exc:
            logger.warning("Failed to write exception report: %r", exc)

    @property
    def name(self) -> str:
        return "Local File Transport"
