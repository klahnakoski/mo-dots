# BUILD mo-dots WITH THE C ACCELERATOR AND pip-INSTALL IT INTO THIS PYTHON:
#   py -3.13 packaging/install_speedups.py
# COMPILE FAILURE FAILS THE INSTALL (NO SILENT PURE FALLBACK); NEEDS A C COMPILER
import os
import shutil
import subprocess
import sys
import tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
setup_py = os.path.join(root, "setup.py")

shutil.copyfile(os.path.join(root, "packaging", "setup.py"), setup_py)
try:
    subprocess.run(
        [sys.executable, os.path.join(root, "packaging", "add_speedups.py"), setup_py, "--required"],
        check=True,
    )
    subprocess.run([sys.executable, "-m", "pip", "install", root], check=True)
finally:
    os.remove(setup_py)

# VERIFY FROM OUTSIDE THE REPO SO THE INSTALLED COPY IS IMPORTED
check = (
    "import mo_dots;"
    "assert type(mo_dots.to_data).__name__ == 'builtin_function_or_method', 'C accelerator not active';"
    "d = mo_dots.to_data({'a': {'b': 1}});"
    "assert d.a.b == 1 and d.x.y == None;"
    "print('mo-dots C accelerator installed for', sys.executable)"
)
subprocess.run(
    [sys.executable, "-c", "import sys;" + check], check=True, cwd=tempfile.gettempdir(),
)
