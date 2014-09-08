import os
from setuptools import setup

version = '0.1'

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
HISTORY = open(os.path.join(here, 'HISTORY.txt')).read()

install_requires = [
    'setuptools',
    'supervisor'
]

try:
    import argparse
    argparse
except ImportError:
    install_requires.append('argparse')

setup(
    name='supervisord-nagios',
    version=version,
    description='nagios checks for supervisord services',
    long_description='a supervisorctl plugin which provides a nagios-plugin-like interface for checking on supervised services',
    keywords=['nagios','supervisord'],
    author='Jeremy Kitchen',
    author_email='jeremy@nationbuilder.com',
    url='http://github.com/3dna/supervisord-nagios',
    license='BSD-3',
    packages=['supervisord_nagios'],
    namespace_packages=['supervisord_nagios'],
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
)

