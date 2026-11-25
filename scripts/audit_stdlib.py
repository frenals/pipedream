"""Prove that importing PipeDream pulls in nothing but the standard library.

Run with ``python -S scripts/audit_stdlib.py`` — the ``-S`` flag disables
site-packages, so any accidental third-party import fails loudly instead of
silently borrowing from the local environment.  CI runs this on every push.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pipedream                    # noqa: E402
import pipedream.cache              # noqa: E402
import pipedream.cli               # noqa: E402
import pipedream.dag                # noqa: E402
import pipedream.data               # noqa: E402
import pipedream.engine             # noqa: E402
import pipedream.render             # noqa: E402
import pipedream.steps              # noqa: E402

if not hasattr(sys, "stdlib_module_names"):  # Python 3.10+
    print("SKIP: sys.stdlib_module_names requires Python 3.10+")
    raise SystemExit(0)

foreign = (
    {module.split(".")[0] for module in sys.modules}
    - set(sys.stdlib_module_names)
    - {"pipedream", "__main__"}
)

if foreign:
    print("FAIL: non-stdlib modules imported: " + ", ".join(sorted(foreign)))
    raise SystemExit(1)

print(
    f"OK: pipedream {pipedream.__version__} imports cleanly on "
    f"Python {sys.version.split()[0]} with zero third-party modules."
)
