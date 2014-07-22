#!/usr/bin/env python
from setuptools import setup


setup (# Distribution meta-data
       name = "litesockets",
       version = "0.2.6",
       author = "Luke Wahlmeier",
       author_email = "lwahlmeier@gmail.com",
       url = "https://github.com/lwahlmeier/python-litesockets",
       download_url = "https://github.com/lwahlmeier/python-litesockets/tarball/0.2.6",
       license = "lgpl",
       description = "A multi threaded socket library for python",
       install_requires = ['threadly'],
       packages =  ['litesockets'],
       platforms = ('linux',),
       keywords = ("networking",),
       test_suite="tests",
      )
