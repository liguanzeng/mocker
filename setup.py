#!/usr/bin/env python
"""项目打包配置文件"""
from setuptools import setup
import mocker

setup(
    name='Mocker',
    version=mocker.__version__,
    description='Python容器实现教学项目',
    author='Anthony Shaw',
    author_email='gward@python.net',
    url='https://github.com/example/mocker',
    packages=['mocker'],
    package_dir={'mocker': 'mocker'},
    entry_points={
        'console_scripts': [
            'mocker = mocker.mocker:main'
        ]
    },
    install_requires=[
        'requests',
        'docopt',
        'terminaltables',
        'pyroute2',
        'cgroups',
        'colorama'
    ])
