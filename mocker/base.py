class BaseDockerCommand(object):
    """Docker命令抽象基类，定义命令执行接口
    
    所有具体Docker命令类应继承此类并实现run方法
    """
    def run(*args):
        """命令执行入口方法，由子类实现具体逻辑"""
        raise NotImplementedError()
