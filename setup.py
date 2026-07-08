#!/usr/bin/env python
from __future__ import absolute_import, unicode_literals

import os
from setuptools import setup, find_packages

__doc__ = "Django CoreAPI client"


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


readme = read('README.rst')
changelog = read('CHANGELOG.rst')
version = read('VERSION').strip()

install_requires = [
    'Django>=4.2',
    'requests>=2.25',
    'uritemplate>=3.0',
]

tests_require = [
    'pytest>=7.0',
    'pytest-django>=4.5',
    'responses>=0.23',
]

dev_require = [
    'django_extensions',
    'ipython',
]

extras_require = {
    'testing': tests_require,
    'dev': dev_require,
}


setup(
    name='django-coreapi-client',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + changelog,
    author='murchik',
    author_email='tech+djangocoreapiclient@vericant.com',
    url='https://github.com/vericant/django-coreapi-client',
    packages=[package for package in find_packages(exclude=['tests'])],
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    license="GPLv3",
    zip_safe=True,
    keywords='django-coreapi-client',
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Framework :: Django',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
