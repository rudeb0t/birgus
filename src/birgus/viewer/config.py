import sys

from argparse import ArgumentParser
from collections.abc import Sequence
from functools import cached_property


class Config:
    def __init__(self) -> None:
        parser = ArgumentParser(
            prog="Birgus Viewer", description="View and inspect Birgus error reports."
        )

        parser.add_argument("reports", nargs="+", metavar="error_report.birgus")

        self.args = parser.parse_args(sys.argv[1:])

    @cached_property
    def reports(self) -> Sequence[str]:
        return [str(report) for report in self.args.reports]
