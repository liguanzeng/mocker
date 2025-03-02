import os
import json
from terminaltables import AsciiTable

from mocker import _base_dir_
from .base import BaseDockerCommand


class ImagesCommand(BaseDockerCommand):
    """镜像管理命令类，继承自BaseDockerCommand
    
    功能：列出本地存储的所有Docker镜像信息
    """
    registry_base = 'https://registry-1.docker.io/v2'  # Docker官方仓库地址

    def __init__(self, *args, **kwargs):
        """初始化镜像命令实例"""
        pass

    def list_images(self):
        """扫描镜像存储目录，返回格式化的镜像列表
        
        返回:
            list: 二维数组包含[名称, 版本, 大小, 文件路径]
        """
        images = [['name', 'version', 'size', 'file']]  # 表格标题

        # 遍历存储目录中的JSON文件
        for image_file in os.listdir(_base_dir_):
            if image_file.endswith('.json'):
                # 读取镜像元数据
                with open(os.path.join(_base_dir_, image_file), 'r') as json_f:
                    image = json.loads(json_f.read())
                
                # 计算镜像层总大小
                image_base = os.path.join(_base_dir_, image_file.replace('.json', ''), 'layers')
                size = sum(os.path.getsize(os.path.join(image_base, f)) for f in
                           os.listdir(image_base)
                           if os.path.isfile(os.path.join(image_base, f)))
                
                # 格式化大小并添加到列表
                images.append([image['name'], image['tag'], sizeof_fmt(size), image_file])
        return images

    def run(self, *args, **kwargs):
        """执行镜像列表展示"""
        images = self.list_images()
        table = AsciiTable(images)  # 使用terminaltables生成ASCII表格
        print(table.table)  # 输出格式化表格


def sizeof_fmt(num, suffix='B'):
    ''' Credit : http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size '''
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
