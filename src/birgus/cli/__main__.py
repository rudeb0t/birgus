import shutil
import sys

from datetime import datetime, timezone

from ..exception_report import ExceptionReport, ExceptionReportReader

f = sys.argv[1]
with open(f, "rb") as exc_file:
    report: ExceptionReportReader = ExceptionReport.read(exc_file)

terminal_size = shutil.get_terminal_size((80, 20))
stack_frame_sep = terminal_size.columns * "="
section_sep = terminal_size.columns * "-"

exception_dt = datetime.fromtimestamp(report.timestamp, tz=timezone.utc)

print(stack_frame_sep)
print(f"Timestamp: {exception_dt}")
print(f"Exception Type: {report.exceptionType}")
print(f"Exception Value: {report.exceptionValue}")
for traceback in report.traceback:
    print(stack_frame_sep)
    print(f"File: {traceback.filename}")
    print(f"Line: {traceback.lineno}")
    print(f"Function: {traceback.functionName}")
    print(section_sep)
    print("Local Variables:")
    for local_var in traceback.locals:
        print(f"{local_var.name}: {local_var.typeName} = {local_var.valueRepr}")
    print(section_sep)
    for source_line in traceback.sourceContext:
        source_line_indicator = "->" if source_line.isTarget else "  "
        print(f"{source_line.lineno}:{source_line_indicator}{source_line.code}")
print(stack_frame_sep)
