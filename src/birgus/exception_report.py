import os

import capnp


capnp.remove_import_hook()
exception_report = capnp.load(
    os.path.join(os.path.dirname(__file__), "exception_report.capnp")
)
