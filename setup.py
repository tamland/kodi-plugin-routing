#!/usr/bin/python
# -*- coding: utf-8 -*-

import os.path
from xml.dom.minidom import parse
from setuptools import setup

project_dir = os.path.dirname(os.path.abspath(__file__))
metadata = parse(os.path.join(project_dir, 'addon.xml'))
addon_version = metadata.firstChild.getAttribute('version')

setup(
    name='routing',
    version=addon_version,
    url='https://github.com/tamland/kodi-plugin-routing',
    author='tamland',
    description='A routing module for kodi plugins',
    long_description=open(os.path.join(project_dir, 'README.md')).read(),
    keywords='Kodi, plugin, routing',
    license='GPL-3.0',
    package_dir={'': 'lib'},
    py_modules=['routing'],
    zip_safe=False,
)
