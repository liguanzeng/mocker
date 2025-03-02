import os
import uuid
import json
from pprint import pprint
import subprocess
import traceback
from pyroute2 import IPDB, NetNS, netns
from cgroups import Cgroup
from cgroups.user import create_user_cgroups

from mocker import _base_dir_, log
from .base import BaseDockerCommand
from .images import ImagesCommand
from .pull import PullCommand


try:
    from pychroot import Chroot
except ImportError:
    print('warning: missing chroot options')


class RunCommand(BaseDockerCommand):
    """容器运行命令类，继承自BaseDockerCommand
    
    功能：创建隔离环境运行Docker容器
    实现技术：
    - 网络隔离：使用Linux network namespace
    - 资源限制：cgroups限制CPU/内存
    - 文件隔离：chroot文件系统隔离
    """
    def __init__(self, *args, **kwargs):
        """初始化运行命令实例"""
        pass

    def run(self, *args, **kwargs):
        """执行容器运行流程
        
        步骤：
        1. 检查本地镜像
        2. 自动拉取缺失镜像
        3. 配置网络命名空间
        4. 设置cgroups资源限制
        5. 启动容器进程
        """
        images = ImagesCommand().list_images()
        image_name = kwargs['<name>']
        ip_last_octet = 103  # TODO: 可配置IP末位字节

        # 检查镜像是否存在
        file = [i[3] for i in images if i[0] == image_name]
        if not file:
            # 自动拉取缺失镜像
            kwargs['pull'] = True
            kwargs['<name>'] = kwargs['<name>'].split("/")[1]
            PullCommand(*args, **kwargs).run()
            images = ImagesCommand().list_images()
            file = [i[3] for i in images if i[0] == image_name]
            
        match = file[0]

        # 加载镜像配置
        target_file = os.path.join(_base_dir_, match)
        with open(target_file) as tf:
            image_details = json.loads(tf.read())
        state = json.loads(image_details['history'][0]['v1Compatibility'])

        # 获取容器配置
        env_vars = state['config']['Env']  # 环境变量
        start_cmd = subprocess.list2cmdline(state['config']['Cmd'])  # 启动命令
        working_dir = state['config']['WorkingDir']  # 工作目录

        # 生成唯一标识
        id = uuid.uuid1()
        name = 'c_' + str(id.fields[5])[:4]  # 容器名称
        mac = str(id.fields[5])[:2]  # MAC地址后缀

        # 镜像层路径
        layer_dir = os.path.join(_base_dir_, match.replace('.json', ''), 'layers', 'contents')

        # 配置网络隔离
        with IPDB() as ipdb:
            veth0_name = f'veth0_{name}'
            veth1_name = f'veth1_{name}'
            netns_name = f'netns_{name}'
            bridge_if_name = 'bridge0'

            # 创建虚拟以太网接口
            with ipdb.create(kind='veth', ifname=veth0_name, peer=veth1_name) as i1:
                i1.up()
                if bridge_if_name not in ipdb.interfaces:
                    ipdb.create(kind='bridge', ifname=bridge_if_name).commit()
                i1.set_target('master', bridge_if_name)

            # 创建网络命名空间
            netns.create(netns_name)
            with ipdb.interfaces[veth1_name] as veth1:
                veth1.net_ns_fd = netns_name  # 将接口移入命名空间

            # 配置命名空间内网络
            ns = IPDB(nl=NetNS(netns_name))
            with ns.interfaces.lo as lo:
                lo.up()  # 启用回环接口
            with ns.interfaces[veth1_name] as veth1:
                veth1.address = f"02:42:ac:11:00:{mac}"
                veth1.add_ip(f'10.0.0.{ip_last_octet}/24')
                veth1.up()
            ns.routes.add({'dst': 'default', 'gateway': '10.0.0.1'}).commit()

            try:
                # 配置cgroups资源限制
                user = os.getlogin()
                create_user_cgroups(user)
                cg = Cgroup(name)
                cg.set_cpu_limit(50)  # CPU限制50%
                cg.set_memory_limit(500)  # 内存限制500MB

                # 容器进程启动函数
                def in_cgroup():
                    try:
                        pid = os.getpid()
                        cg = Cgroup(name)
                        
                        # 设置环境变量
                        for env in env_vars:
                            log.info(f'Setting ENV {env}')
                            os.putenv(*env.split('=', 1))

                        # 进入网络命名空间
                        netns.setns(netns_name)
                        cg.add(pid)  # 加入cgroup

                        # 文件系统隔离
                        os.chroot(layer_dir)
                        if working_dir:
                            log.info(f"Setting working directory to {working_dir}")
                            os.chdir(working_dir)
                    except Exception as e:
                        traceback.print_exc()
                        log.error(f"Preexec error: {e}")

                # 启动容器进程
                log.info(f'Running "{start_cmd}"')
                process = subprocess.Popen(start_cmd, 
                                         preexec_fn=in_cgroup, 
                                         shell=True)
                process.wait()
                
                # 处理输出
                if process.stdout:
                    print(process.stdout.read())
                if process.stderr:
                    log.error(process.stderr.read())
                    
            except Exception as e:
                traceback.print_exc()
                log.error(f"Runtime error: {e}")
            finally:
                # 清理资源
                log.info('Finalizing')
                NetNS(netns_name).close()
                netns.remove(netns_name)
                ipdb.interfaces[veth0_name].remove()
                log.info('Container cleanup completed')
