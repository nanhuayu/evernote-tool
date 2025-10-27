"""Markdown格式解析器"""
import re
from pathlib import Path
from typing import List, Optional
import frontmatter
from markdown import Markdown
from PIL import Image

from .base import BaseParser
from ..models import Note, Resource
from ..utils.logger import get_logger
from ..utils.helpers import (
    parse_timestamp, calculate_hash, 
    guess_extension, find_file
)
from ..config import Config

logger = get_logger()

class MarkdownParser(BaseParser):
    """Markdown文件解析器"""
    
    def __init__(self, source: Path, resource_paths: List[Path] = None):
        super().__init__(source)
        self.resource_paths = self._init_resource_paths(resource_paths)
        self.html_converter = Markdown(extensions=Config.MARKDOWN_EXTENSIONS)
    
    def _init_resource_paths(self, paths: List[Path] = None) -> List[Path]:
        """初始化资源搜索路径"""
        base_paths = [self.source.parent]
        for dir_name in Config.DEFAULT_RESOURCE_DIRS:
            base_paths.append(self.source.parent / dir_name)
        
        if paths:
            base_paths.extend(paths)
        
        return base_paths
    
    def parse(self) -> Optional[Note]:
        """解析Markdown文件"""
        try:
            # 读取文件
            with open(self.source, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # 转换为HTML
            html_content = self.html_converter.convert(post.content)
            
            # 创建笔记
            metadata = post.metadata
            note = Note(
                title=metadata.get('title', self.source.stem),
                content=html_content,
                created=parse_timestamp(metadata.get('created')),
                updated=parse_timestamp(metadata.get('updated')),
                tags=self._parse_tags(metadata.get('tags', [])),
                author=metadata.get('author'),
                source_url=metadata.get('source'),
                notebook=metadata.get('notebook')
            )
            
            # 解析资源
            resources = self._parse_resources(post.content)
            for resource in resources:
                note.add_resource(resource)
                # 替换HTML中的引用
                note.content = self._replace_resource_ref(
                    note.content, resource
                )
            
            return note
            
        except Exception as e:
            logger.error(f"Markdown解析失败 {self.source}: {e}")
            return None
    
    def _parse_tags(self, tags) -> List[str]:
        """解析标签"""
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(',') if t.strip()]
        return tags if isinstance(tags, list) else []
    
    def _parse_resources(self, content: str) -> List[Resource]:
        """解析资源"""
        resources = []
        # 匹配Markdown图片语法: ![alt](path)
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        for match in re.finditer(pattern, content):
            file_path = match.group(2)
            resource = self._load_resource(file_path)
            if resource:
                resources.append(resource)
        
        return resources
    
    def _load_resource(self, file_path: str) -> Optional[Resource]:
        """加载资源文件"""
        try:
            # 查找文件
            full_path = find_file(file_path, self.resource_paths)
            if not full_path:
                logger.warning(f"资源文件未找到: {file_path}")
                return None
            
            # 读取数据
            with open(full_path, 'rb') as f:
                data = f.read()
            
            # 获取MIME类型
            import mimetypes
            mime_type = mimetypes.guess_type(str(full_path))[0]
            mime_type = mime_type or 'application/octet-stream'
            
            # 获取图片尺寸
            width, height = None, None
            if mime_type.startswith('image/'):
                try:
                    with Image.open(full_path) as img:
                        width, height = img.size
                except Exception:
                    pass
            
            return Resource(
                mime=mime_type,
                data=data,
                hash=calculate_hash(data),
                file_name=full_path.name,
                width=width,
                height=height
            )
            
        except Exception as e:
            logger.warning(f"加载资源失败 {file_path}: {e}")
            return None
    
    def _replace_resource_ref(self, html: str, resource: Resource) -> str:
        """替换HTML中的资源引用为ENEX媒体标签"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if resource.file_name and resource.file_name in src:
                media = soup.new_tag('en-media')
                media['type'] = resource.mime
                media['hash'] = resource.hash
                img.replace_with(media)
        
        return str(soup)