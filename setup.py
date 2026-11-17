"""Compatibility shim for old pip.

`pip install -e .` from a pyproject.toml alone needs pip >= 21.3 (PEP 660). macOS ships Python 3.9
with pip 21.2, which refuses with "File setup.py or setup.cfg not found ... editable mode currently
requires a setuptools-based build". The presence of this file is all that pip 21.2 needs; every real
setting stays in pyproject.toml, so there is one place to read.
"""
from setuptools import setup

setup()
