from datetime import timedelta
from typing import Any, Type

from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
    ExecuteWorkflowInput,
)
from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.workflow import ActivityCancellationType

from .activities import birgus_send_report
from ..classes import FrameList
from ..exception_hooks import create_report, extract_traceback_data


class BirgusActivityInterceptor(ActivityInboundInterceptor):
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        try:
            return await super().execute_activity(input)
        except Exception as exc:
            if activity.info().attempt == 1:
                exc_type = type(exc)
                exc_value = exc
                exc_traceback = exc.__traceback__
                traceback: FrameList = extract_traceback_data(exc_traceback)
                report = create_report(exc_type, exc_value, traceback)
                birgus_send_report(report.to_bytes(), "activity-")
            raise


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
                args=(report.to_bytes(), "workflow-"),
                start_to_close_timeout=timedelta(seconds=10),
                cancellation_type=ActivityCancellationType.ABANDON,
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            raise


class BirgusWorkerInterceptor(Interceptor):
    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        return BirgusActivityInterceptor(super().intercept_activity(next))

    def workflow_interceptor_class(
        self, input: WorkflowInterceptorClassInput
    ) -> Type[WorkflowInboundInterceptor] | None:
        return BirgusWorkflowInterceptor
