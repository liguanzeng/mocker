import requests
import os, platform
import json
import tarfile
from mocker import _base_dir_
from .base import BaseDockerCommand


class PullCommand(BaseDockerCommand):
    """镜像拉取命令类，继承自BaseDockerCommand
    
    功能：从Docker仓库拉取镜像并保存到本地
    """
    registry_base = 'https://registry-1.docker.io/v2'  # Docker仓库基础地址

    def __init__(self, *args, **kwargs):
        """初始化拉取命令实例
        
        参数:
            kwargs: 命令行参数，包含镜像名称和标签
        """
        self.image = kwargs['<name>']
        self.library = 'library'  # 默认官方仓库
        self.tag = kwargs['<tag>'] if kwargs['<tag>'] is not None else 'latest'  # 默认最新标签

    def auth(self, library, image):
        """获取Docker仓库认证token
        
        参数:
            library: 仓库分类（如官方library）
            image: 镜像名称
            
        返回:
            str: 认证token字符串
        """
        token_req = requests.get(
            'https://auth.docker.io/token?service=registry.docker.io&scope=repository:%s/%s:pull'
            % (library, image))
        return token_req.json()['token']

    def get_manifest(self):
        """获取镜像清单（manifest）
        
        返回:
            dict: 镜像清单JSON数据
        """
        print("Fetching manifest for %s:%s..." % (self.image, self.tag))
        manifest = requests.get('%s/%s/%s/manifests/%s' %
                                (self.registry_base, self.library, self.image, self.tag),
                                headers=self.headers)
        return manifest.json()

    def run(self, *args, **kwargs):
        """执行镜像拉取流程
        
        步骤:
        1. 匿名认证获取token
        2. 下载镜像清单
        3. 创建本地存储目录
        4. 分层下载镜像内容
        5. 解压并保存镜像层
        """
        # 设置认证头信息
        self.headers = {'Authorization': 'Bearer %s' % self.auth(self.library, self.image)}
        
        # 获取并保存镜像清单
        manifest = self.get_manifest()
        image_name_friendly = manifest['name'].replace('/', '_')
        with open(os.path.join(_base_dir_, image_name_friendly+'.json'), 'w') as cache:
            cache.write(json.dumps(manifest))
            
        # 创建镜像层存储目录
        dl_path = os.path.join(_base_dir_, image_name_friendly, 'layers')
        os.makedirs(dl_path, exist_ok=True)

        # 处理镜像层
        layer_sigs = [layer['blobSum'] for layer in manifest['fsLayers']]
        unique_layer_sigs = set(layer_sigs)  # 去重

        # 创建内容解压目录
        contents_path = os.path.join(dl_path, 'contents')
        os.makedirs(contents_path, exist_ok=True)

        # 下载并处理每个镜像层
        for sig in unique_layer_sigs:
            print('Fetching layer %s..' % sig)
            url = f'{self.registry_base}/{self.library}/{self.image}/blobs/{sig}'
            local_filename = os.path.join(dl_path, f'{sig}.tar')

            # 流式下载大文件
            with requests.get(url, stream=True, headers=self.headers) as r, \
                 open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            # 解压并列出部分文件
            with tarfile.open(local_filename, 'r') as tar:
                print("Layer contents sample:")
                for member in tar.getmembers()[:10]:  # 显示前10个文件
                    print(f'- {member.name}')
                print('...')
                tar.extractall(str(contents_path))  # 解压全部内容
