#!/usr/bin/python
"""Mocker 命令行入口模块

负责命令路由和参数解析的主程序
"""
from docopt import docopt

import mocker
from mocker.base import BaseDockerCommand
from mocker.pull import PullCommand
from mocker.images import ImagesCommand
from mocker.run import RunCommand


if __name__ == '__main__':
    # 解析命令行参数
    arguments = docopt(mocker.__doc__, version=mocker.__version__)
    
    # 根据参数选择对应命令类
    command = BaseDockerCommand
    if arguments['pull']:
        command = PullCommand
    elif arguments['images']:
        command = ImagesCommand
    elif arguments['run']:
        command = RunCommand

    # 实例化并执行命令
    cls = command(**arguments)
    cls.run(**arguments)
