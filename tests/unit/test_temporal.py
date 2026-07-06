import glob
import os

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest

from temporalio import activity, workflow
from temporalio.client import WorkflowFailureError
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment

from birgus.exception_hooks import ExceptionHook
from birgus.temporal.activities import birgus_send_report
from birgus.temporal.interceptors import BirgusWorkerInterceptor

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@pytest.fixture
def activity_env() -> ActivityEnvironment:
    return ActivityEnvironment()


@pytest.fixture
def sample_report_bytes() -> bytes:
    report_path = os.path.join(DATA_DIR, "valid-report.bin")
    with open(report_path, "rb") as f:
        return f.read()


@activity.defn
def failing_activity(non_retryable: bool) -> None:
    raise ApplicationError(
        "An activity failed",
        repr(ValueError("This is a test exception")),
        non_retryable=non_retryable,
    )


@workflow.defn
class FailingActivityWorkflow:
    @workflow.run
    async def run(self, maximum_attempts: int = 1, non_retryable: bool = True) -> None:
        return await workflow.execute_activity(
            failing_activity,
            non_retryable,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=maximum_attempts),
        )


@pytest.mark.temporal
def test_birgus_send_report(
    activity_env: ActivityEnvironment,
    sample_report_bytes: bytes,
    fake_monotonic_ns: int,
) -> None:
    with patch("birgus.exception_hooks.time.monotonic_ns") as mocked_monotonic_ns:
        mocked_monotonic_ns.return_value = fake_monotonic_ns
        expected_filename = f"{fake_monotonic_ns}.birgus"
        activity_env.run(birgus_send_report, sample_report_bytes)

        assert os.path.exists(expected_filename)

        try:
            os.remove(expected_filename)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.temporal
async def test_interceptor_no_retries(fake_monotonic_ns: int) -> None:
    task_queue = "test-birgus-activity-interceptor"
    with patch("birgus.exception_hooks.time.monotonic_ns") as mocked_monotonic_ns:
        mocked_monotonic_ns.return_value = fake_monotonic_ns
        with ThreadPoolExecutor() as activity_executor:
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue=task_queue,
                    workflows=[FailingActivityWorkflow],
                    activities=[
                        failing_activity,
                        birgus_send_report,
                    ],
                    activity_executor=activity_executor,
                    interceptors=[BirgusWorkerInterceptor()],
                ):
                    with pytest.raises(WorkflowFailureError):
                        await env.client.execute_workflow(
                            FailingActivityWorkflow.run,
                            id="failing-activity-workflow",
                            task_queue=task_queue,
                        )

    assert os.path.exists(f"activity-{fake_monotonic_ns}.birgus")
    assert os.path.exists(f"workflow-{fake_monotonic_ns}.birgus")

    return
    for globbed_file in glob.glob("*.birgus"):
        try:
            os.remove(globbed_file)
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.temporal
async def test_interceptor_with_retries(fake_monotonic_ns: int) -> None:
    task_queue = "test-birgus-activity-interceptor"
    with (
        patch("birgus.exception_hooks.time.monotonic_ns") as mocked_monotonic_ns,
        patch.object(ExceptionHook, "send_report", MagicMock()) as mocked_send_report,
    ):
        mocked_monotonic_ns.return_value = fake_monotonic_ns
        with ThreadPoolExecutor() as activity_executor:
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue=task_queue,
                    workflows=[FailingActivityWorkflow],
                    activities=[
                        failing_activity,
                        birgus_send_report,
                    ],
                    activity_executor=activity_executor,
                    interceptors=[BirgusWorkerInterceptor()],
                ):
                    with pytest.raises(WorkflowFailureError):
                        await env.client.execute_workflow(
                            FailingActivityWorkflow.run,
                            args=(5, False),
                            id="failing-activity-workflow",
                            task_queue=task_queue,
                        )
        assert mocked_send_report.call_count == 2
        mocked_send_report.call_args_list[0][0][1] == "activity-"
        mocked_send_report.call_args_list[0][0][1] == "workflow-"
