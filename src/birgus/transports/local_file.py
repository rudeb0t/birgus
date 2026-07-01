import logging
import os.path
import uuid

from .base import AbstractTransport, exception_report

logger = logging.getLogger(__name__)


class LocalFileTransport(AbstractTransport):
    def __init__(self, base_dir: str = ""):
        self.base_dir = base_dir

    def _generate_filename(self) -> str:
        return os.path.join(self.base_dir, f"{uuid.uuid4()}.birgus")

    def send(self, report: exception_report.ExceptionReport.Builder) -> None:
        try:
            exc_filename = self._generate_filename()
            with open(exc_filename, "wb") as exc_file:
                report.write(exc_file)
                logger.info("Exception report written to %s", exc_filename)
        except Exception as exc:
            logger.warning(f"Failed to write exception report: {exc}")
