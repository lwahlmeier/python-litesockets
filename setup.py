#!/usr/bin/env python
try:
  from setuptools import setup
except ImportError:
  from distutils.core import setup


setup (# Distribution meta-data
       name = "litesockets",
       version = "0.2.5",
       author = "Luke Wahlmeier",
       author_email = "lwahlmeier@gmail.com",
       url = "None",
       license = "lgpl",
       description = "",
       install_requires = ['threadly'],
       packages =  ['litesockets'],
       test_suite = 'tests',
      )
