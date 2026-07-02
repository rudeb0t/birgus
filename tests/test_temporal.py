import glob
import os

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest

from temporalio import activity, workflow
from temporalio.client import WorkflowFailureError
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment

from birgus.temporal.activities import birgus_send_report
from birgus.temporal.interceptors import BirgusWorkerInterceptor


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


@pytest.fixture
def activity_env() -> ActivityEnvironment:
    return ActivityEnvironment()


@pytest.fixture
def sample_report_bytes() -> bytes:
    report_path = os.path.join(DATA_DIR, "valid-report.bin")
    with open(report_path, "rb") as f:
        return f.read()


@activity.defn
def failing_activity() -> None:
    raise ApplicationError(
        "An activity failed",
        repr(ValueError("This is a test exception")),
        non_retryable=True,
    )


@workflow.defn
class FailingActivityWorkflow:
    @workflow.run
    async def run(self) -> None:
        return await workflow.execute_activity(
            failing_activity,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )


def test_birgus_send_report(
    activity_env: ActivityEnvironment,
    sample_report_bytes: bytes,
    fake_monotonic_ns: int,
) -> None:
    with patch("birgus.transports.base.time.monotonic_ns") as mocked_monotonic_ns:
        mocked_monotonic_ns.return_value = fake_monotonic_ns

        activity_env.run(birgus_send_report, sample_report_bytes)

        expected_filename = f"{fake_monotonic_ns}.birgus"
        assert os.path.exists(expected_filename)

        try:
            os.remove(expected_filename)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_interceptor(fake_monotonic_ns: int) -> None:
    task_queue = "test-birgus-activity-interceptor"
    with patch("birgus.transports.base.time.monotonic_ns") as mocked_monotonic_ns:
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

    for globbed_file in glob.glob("*.birgus"):
        try:
            os.remove(globbed_file)
        except Exception:
            pass
