"""Markdown格式写入器"""
import re
from pathlib import Path
import frontmatter
from bs4 import BeautifulSoup

from .base import BaseWriter
from ..models import Note
from ..utils.logger import get_logger
from ..utils.helpers import sanitize_filename, format_timestamp, guess_extension
from ..processors.html_converter import HtmlToMarkdownConverter
from ..config import Config

logger = get_logger()

class MarkdownWriter(BaseWriter):
    """Markdown文件写入器"""
    
    def __init__(self, output: str, converter_type: str = 'soup'):
        super().__init__(output)
        self.assets_dir = self.output / Config.ASSETS_DIR_NAME
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.html_converter = HtmlToMarkdownConverter(converter_type)
    
    def write(self, note: Note) -> None:
        """写入单个笔记"""
        try:
            # 处理资源
            content = self._process_resources(note)
            
            # 转换HTML到Markdown
            markdown_content = self.html_converter.convert(content)
            
            # 创建元数据
            metadata = self._create_metadata(note)
            
            # 创建frontmatter文档
            post = frontmatter.Post(markdown_content, **metadata)
            
            # 保存文件
            filename = sanitize_filename(note.title) + '.md'
            filepath = self.output / filename
            
            # 避免文件名冲突
            filepath = self._get_unique_filepath(filepath)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
            
            logger.info(f"已保存: {filepath.name}")
            
        except Exception as e:
            logger.error(f"写入笔记失败 {note.title}: {e}")
    
    def _process_resources(self, note: Note) -> str:
        """处理资源并更新内容"""
        content = note.content
        
        for resource in note.resources:
            # 确定文件名
            if not resource.file_name:
                ext = guess_extension(resource.mime)
                resource.file_name = f"{resource.hash}{ext}"
            
            # 保存资源
            asset_path = self.assets_dir / resource.file_name
            with open(asset_path, 'wb') as f:
                f.write(resource.data)
            
            # 替换内容中的引用
            relative_path = f"{Config.ASSETS_DIR_NAME}/{resource.file_name}"
            content = self._replace_media_tag(content, resource, relative_path)
        
        return content
    
    def _replace_media_tag(self, content: str, resource, path: str) -> str:
        """替换ENEX媒体标签为Markdown格式"""
        # 匹配 <en-media hash="xxx" .../>
        pattern = rf'<en-media[^>]*?hash="{resource.hash}"[^>]*?(?:></en-media>|/>)'
        
        if resource.mime.startswith('image/'):
            replacement = f'![{resource.file_name}]({path})'
        else:
            replacement = f'[{resource.file_name}]({path})'
        
        return re.sub(pattern, replacement, content)
    
    def _create_metadata(self, note: Note) -> dict:
        """创建frontmatter元数据"""
        metadata = {
            'title': note.title,
            'created': format_timestamp(note.created),
            'updated': format_timestamp(note.updated),
        }
        
        if note.tags:
            metadata['tags'] = note.tags
        if note.author:
            metadata['author'] = note.author
        if note.source_url:
            metadata['source'] = note.source_url
        if note.notebook:
            metadata['notebook'] = note.notebook
        
        return metadata
    
    def _get_unique_filepath(self, filepath: Path) -> Path:
        """获取唯一的文件路径(避免覆盖)"""
        if not filepath.exists():
            return filepath
        
        stem = filepath.stem
        suffix = filepath.suffix
        counter = 1
        
        while True:
            new_path = filepath.parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1