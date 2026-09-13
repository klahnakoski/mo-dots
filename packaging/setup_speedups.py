# LOCAL DEV BUILD OF THE C ACCELERATOR, RUN FROM REPO ROOT:
#   python packaging/setup_speedups.py build_ext --inplace
from setuptools import setup, Extension

setup(
    name="mo-dots",
    ext_modules=[Extension("mo_dots._speedups", sources=["mo_dots/_speedups.c"])],
)
