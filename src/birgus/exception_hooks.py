import asyncio
import importlib.util
import linecache
import logging
import sys
import time
import traceback
import threading
import warnings

from dataclasses import dataclass
from types import TracebackType
from typing import Sequence, Type, Optional, Any

from .classes import FrameList, LocalVarList, SourceContext
from .exception_report import ExceptionReport, ExceptionReportBuilder
from .transports import DEFAULT_TRANSPORTS, TransportList, TransportPayload


logger = logging.getLogger(__name__)

_VALUE_REPR_LIMIT: int = 1000
_DEFAULT_CONTEXT_LINES: int = 5


@dataclass(frozen=True)
class SendReportResults:
    report_name: str
    transport_names: Sequence[str]


class ExceptionHook:
    _transports: TransportList
    _name_prefix: str

    def __init__(
        self,
        transports: TransportList | None = None,
        name_prefix: str | None = None,
        source_context_lines: int = _DEFAULT_CONTEXT_LINES,
    ) -> None:
        if transports is not None:
            self.transports = transports
        else:
            self.transports = DEFAULT_TRANSPORTS

        if name_prefix is not None:
            self.name_prefix = name_prefix
        else:
            self.name_prefix = ""

        self.source_context_lines = source_context_lines

    @property
    def transports(self) -> TransportList:
        return self._transports

    @transports.setter
    def transports(self, transports: TransportList) -> None:
        if not transports:
            raise ValueError("At least one transport must be provided.")

        self._transports = transports

    @property
    def name_prefix(self) -> str:
        return self._name_prefix

    @name_prefix.setter
    def name_prefix(self, name_prefix: str) -> None:
        self._name_prefix = name_prefix

    def __call__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        traceback = extract_traceback_data(exc_traceback)

        report = create_report(exc_type, exc_value, traceback)
        self.send_report(report)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    def generate_name(self, name_prefix: str = "") -> str:
        _name_prefix = name_prefix or self.name_prefix
        return f"{_name_prefix}{time.monotonic_ns()}.birgus"

    def send_report(
        self,
        report: TransportPayload,
        name_prefix: str = "",
    ) -> SendReportResults:
        report_name = self.generate_name(name_prefix)
        transport_names = []
        for transport in self.transports:
            try:
                transport.send(report, report_name)
                transport_names.append(transport.name)
            except Exception as exc:
                logger.warning(
                    "Failed to send exception report via %r: %r", transport, exc
                )

        return SendReportResults(
            report_name=report_name, transport_names=transport_names
        )


exception_hook = ExceptionHook()


def get_source_context(
    filename: str, target_lineno: int, context_lines: int = _DEFAULT_CONTEXT_LINES
) -> SourceContext:
    source_lines: SourceContext = []

    start = max(1, target_lineno - context_lines)
    end = target_lineno + context_lines + 1

    for current_lineno in range(start, end):
        line = linecache.getline(filename, current_lineno).rstrip()
        if line:
            source_lines.append(
                {
                    "lineno": current_lineno,
                    "code": line,
                    "isTarget": current_lineno == target_lineno,
                }
            )

    return source_lines


def extract_traceback_data(
    exc_traceback: Optional[TracebackType],
    source_context_lines: int = _DEFAULT_CONTEXT_LINES,
) -> FrameList:
    frames: FrameList = []

    for frame_obj, lineno in traceback.walk_tb(exc_traceback):
        local_vars: LocalVarList = []

        for name, value in frame_obj.f_locals.items():
            value_trunc = False
            try:
                value_repr = repr(value)
                value_len = len(value_repr)
                if value_len > _VALUE_REPR_LIMIT:
                    value_repr = value_repr[:_VALUE_REPR_LIMIT]
                    value_trunc = True

            except Exception:
                value_repr = "<Unrepresentable Object>"

            local_vars.append(
                {
                    "name": str(name),
                    "typeName": type(value).__name__,
                    "valueRepr": value_repr,
                    "valueTrunc": value_trunc,
                    "valueLen": value_len,
                }
            )

        frames.append(
            {
                "filename": frame_obj.f_code.co_filename,
                "lineno": lineno,
                "functionName": frame_obj.f_code.co_name,
                "locals": local_vars,
                "sourceContext": get_source_context(
                    frame_obj.f_code.co_filename, lineno, source_context_lines
                ),
            }
        )

    return frames


def create_report(
    exc_type: Type[BaseException], exc_value: BaseException, traceback: FrameList
) -> ExceptionReportBuilder:
    report: ExceptionReportBuilder = ExceptionReport.new_message()
    report.exceptionType = repr(exc_type.__name__)
    report.exceptionValue = repr(exc_value)
    report.traceback = traceback
    report.timestamp = time.time()

    return report


def asyncio_exception_hook(
    loop: asyncio.AbstractEventLoop, context: dict["str", Any]
) -> None:
    exc = context.get("exception")

    if exc is not None:
        exc_type = type(exc)
        exc_value = exc
        exc_traceback = exc.__traceback__
        exception_hook(exc_type, exc_value, exc_traceback)

    loop.default_exception_handler(context)


def threading_exception_hook(args: threading.ExceptHookArgs) -> None:
    exception_hook(args.exc_type, args.exc_value, args.exc_traceback)  # type: ignore[arg-type]


def install(
    loop: asyncio.AbstractEventLoop | None = None,
    transports: TransportList = DEFAULT_TRANSPORTS,
) -> None:
    if importlib.util.find_spec("temporalio") is not None:
        warnings.warn(
            "Temporal SDK detected. Installing exception hooks may interfere with Temporal's own exception handling. Proceed with caution.",
            UserWarning,
        )

    exception_hook.transports = transports
    sys.excepthook = exception_hook
    threading.excepthook = threading_exception_hook

    if loop is not None:
        loop.set_exception_handler(asyncio_exception_hook)
