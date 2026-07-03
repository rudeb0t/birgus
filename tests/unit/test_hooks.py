import os
import sys

from unittest.mock import patch


def test_hook() -> None:
    import birgus

    birgus.install()
    assert sys.excepthook == birgus.exception_hooks.exception_hook
    assert (
        sys.modules["threading"].excepthook
        == birgus.exception_hooks.threading_exception_hook
    )


def test_exception_hook_writes_report(fake_monotonic_ns: int) -> None:
    import birgus

    birgus.install()

    with patch("birgus.transports.base.time.monotonic_ns") as mocked_monotonic_ns:
        mocked_monotonic_ns.return_value = fake_monotonic_ns
        try:
            raise ValueError("Test exception")
        except ValueError as exc:
            exc_type = type(exc)
            exc_value = exc
            exc_traceback = exc.__traceback__

            birgus.exception_hooks.exception_hook(exc_type, exc_value, exc_traceback)

            expected_filename = f"{fake_monotonic_ns}.birgus"
            assert os.path.exists(expected_filename)

            try:
                os.remove(expected_filename)
            except Exception:
                pass
