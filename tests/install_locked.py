"""Install the test requirements frozen for THIS python, no resolution.

pip cannot resolve the managed packages: they pin each other with ==, and
generations mix - mo-testing 8.685.25166 wants mo-logs==8.685.25166 while
mo-json 6.703.26061 wants mo-logs==8.703.26061. The lock is the set
mo-deploy's run_tests proved on this interpreter, so install it verbatim.

Run from the test cwd cibuildwheel builds out of CIBW_TEST_SOURCES.
"""
import subprocess
import sys
from pathlib import Path

LOCK = Path(__file__).resolve().parent / "requirements-{}.{}.lock".format(*sys.version_info[:2])
if not LOCK.exists():
    sys.exit(LOCK.name + " is missing; mo-deploy writes one per tested python")
sys.exit(subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "-r", str(LOCK)]).returncode)
