from typing import Any
from collections.abc import Sequence

from rich.highlighter import ReprHighlighter
from rich.syntax import Syntax
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Grid, VerticalGroup
from textual.widgets import Collapsible, Footer, Header, Static

from birgus.exception_report import ExceptionReport, ExceptionReportReader

from .config import Config


class BirgusLocals(Grid):
    DEFAULT_CSS = """
    BirgusLocals {
        grid-size: 3;
        grid-columns: auto auto 3fr;
        height: auto;
        padding: 0 1;
        border: round $accent;
    }
    .local-name {
        text-align: right;
    }
    .local-equals {
        text-align: center;
    }
    .local-value {
        text-align: left;
    }
    .local-none {
        color: $text-muted;
    }
    """

    def __init__(
        self, local_vars: ExceptionReportReader, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.local_vars = local_vars

    def compose(self) -> ComposeResult:
        if len(self.local_vars) == 0:
            yield Static(
                "No local variables in current stack frame", classes="local-none"
            )
            return

        repr_highlighter = ReprHighlighter()

        for local_var in self.local_vars:
            yield Static(f"[yellow]{local_var.name}[/]", classes="local-name")
            yield Static(" [red]=[/] ", classes="local-equals")
            value_repr = repr_highlighter(local_var.valueRepr)
            if local_var.valueTrunc:
                if local_var.valueLen is not None and local_var.valueLen > 0:
                    value_repr += Text.from_markup(
                        f" [italic red on green]+{local_var.valueLen - len(local_var.valueRepr)} chars[/]"
                    )
                else:
                    value_repr += Text.from_markup(" [italic red on green]+more[/]")
            yield Static(value_repr, classes="local-value", markup=False)


class BirgusSourceLines(Horizontal):
    DEFAULT_CSS = """
    BirgusSourceLines {
        height: auto;
        padding: 1;
    }
    .birgus-linenos {
        width: auto;
        padding-right: 1;
        color: $text-muted;
    }
    .birgus-lines {
        width: 1fr;
    }
    """

    def __init__(
        self, source_context: Sequence[ExceptionReportReader], *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.source_context = source_context

    def compose(self) -> ComposeResult:
        lineno_width = len(str(self.source_context[-1].lineno)) + 1
        linenos = []
        lines = []

        for source_context in self.source_context:
            if source_context.isTarget:
                lineno_leader = "[bold red]>[/]"
            else:
                lineno_leader = " "
            linenos.append(
                lineno_leader + str(source_context.lineno).rjust(lineno_width)
            )
            lines.append(source_context.code)

        yield Static("\n".join(linenos), classes="birgus-linenos")
        yield Static(Syntax("\n".join(lines), "python"), classes="birgus-lines")


class BirgusStackFrame(VerticalGroup):
    def __init__(
        self, stack_frame: ExceptionReportReader, *args: Any, **kwargs: Any
    ) -> None:
        self.stack_frame = stack_frame
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        stack_frame = self.stack_frame
        with Collapsible(
            title=f"{stack_frame.filename}:{stack_frame.lineno} in {stack_frame.functionName}",
            collapsed=False,
        ):
            yield BirgusLocals(self.stack_frame.locals)
            yield BirgusSourceLines(self.stack_frame.sourceContext)


class BirgusErrorReport(VerticalGroup):
    def __init__(
        self, exception_report: ExceptionReport, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.error_report = exception_report

    def compose(self) -> ComposeResult:
        for stack_frame in self.error_report.traceback:
            yield BirgusStackFrame(stack_frame)


class BirgusViewerApp(App[None]):
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]
    TITLE = "Birgus Viewer"

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.config: Config = config
        self.reports: Sequence[ExceptionReportReader] = []
        for report in self.config.reports:
            with open(report, "rb") as report_file:
                self.reports.append(ExceptionReport.read(report_file))

        self.current_report = self.reports[0]

    def compose(self) -> ComposeResult:
        yield Header()
        yield BirgusErrorReport(self.current_report)
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )
