from temporalio import activity

from ..exception_hooks import exception_hook


@activity.defn
def birgus_send_report(report_bytes: bytes, name_prefix: str = "") -> None:
    exception_hook.send_report(report_bytes, name_prefix)
