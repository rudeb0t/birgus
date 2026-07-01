from datetime import timedelta
from typing import Any

from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
    WorkflowInboundInterceptor,
    ExecuteWorkflowInput,
)
from temporalio import workflow

from .activities import birgus_send_report
from ..classes import FrameList
from ..exception_hooks import create_report, extract_traceback_data, exception_hook


class BirgusActivityInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        try:
            return await super().execute_activity(input)
        except Exception as exc:
            exc_type = type(exc)
            exc_value = exc
            exc_traceback = exc.__traceback__
            exception_hook(exc_type, exc_value, exc_traceback)
            raise


class BirgusWorkerInterceptor(Interceptor):
    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return BirgusActivityInterceptor(super().intercept_activity(next))


class BirgusWorkflowInterceptor(WorkflowInboundInterceptor):
    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        try:
            return await super().execute_workflow(input)
        except Exception as exc:
            exc_type = type(exc)
            exc_value = exc
            exc_traceback = exc.__traceback__
            traceback: FrameList = extract_traceback_data(exc_traceback)
            report = create_report(exc_type, exc_value, traceback)
            await workflow.execute_local_activity(
                birgus_send_report,
                report.to_bytes(),
                start_to_close_timeout=timedelta(seconds=10),
            )
            raise
