import os
from typing import TYPE_CHECKING, TypeAlias
import capnp

capnp.remove_import_hook()
exception_report = capnp.load(
    os.path.join(os.path.dirname(__file__), "exception_report.capnp")
)

if TYPE_CHECKING:
    ExceptionReport: TypeAlias = capnp.lib.capnp._DynamicStruct
    ExceptionReportReader: TypeAlias = capnp.lib.capnp._DynamicStructReader
    ExceptionReportBuilder: TypeAlias = capnp.lib.capnp._DynamicStructBuilder
else:
    ExceptionReport: TypeAlias = exception_report.ExceptionReport
    ExceptionReportBuilder: TypeAlias = exception_report.ExceptionReport.Builder
    ExceptionReportReader: TypeAlias = exception_report.ExceptionReport.Reader
