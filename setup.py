#!/usr/bin/env python
from setuptools import setup


VERSION = "0.7.1"

setup (# Distribution meta-data
       name = "litesockets",
       version = VERSION,
       author = "Luke Wahlmeier",
       author_email = "lwahlmeier@gmail.com",
       url = "https://github.com/lwahlmeier/python-litesockets",
       download_url = "https://github.com/lwahlmeier/python-litesockets/tarball/%s"%(VERSION),
       test_suite = "tests",
       license = "unlicense",
       description = "A multi threaded socket library for python",
       install_requires = ['threadly>=0.7.2'],
       packages =  ['litesockets'],
       keywords = ["networking"],
       classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities',
        'License :: Public Domain'
        ],

      )
