from temporalio import activity

from ..exception_hooks import exception_hook
from ..exception_report import exception_report


@activity.defn
def birgus_send_report(report_bytes: bytes) -> None:
    with exception_report.ExceptionReport.from_bytes(report_bytes) as report:
        exception_hook.send_report(report)
