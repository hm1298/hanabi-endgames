"""Setup for install or develop."""

from setuptools import setup

setup(name='endgames', version='1.0', packages=['endgames'], install_requires=[
    "requests",
    "inflection"
])
