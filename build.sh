#!/bin/sh
set -e

#Check the python files and exit on error.
python3 -m pyflakes pcbzip/*.py

rm -rf dist
rm -rf doc
rm -rf build
rm -rf *.egg-info
doxygen
python3 -m pip install --upgrade build
python3 -m build
