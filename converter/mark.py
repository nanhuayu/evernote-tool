import logging
import re
from bs4 import BeautifulSoup, Declaration, Doctype, NavigableString, Comment
import frontmatter
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from markdown import Markdown
from .content import Content, Resource
import mimetypes
import hashlib
from html2text import HTML2Text

class MarkdownParser:
    def __init__(self, file_path: str, resource_paths: List[Path] = None):
        self.file_path = Path(file_path)
        self.resource_paths = self._init_resource_paths(resource_paths)
        self.post = None
        self.html_content = None
        
    def _init_resource_paths(self, paths: List[Path] = None) -> List[Path]:
        """初始化资源搜索路径"""
        base_paths = [
            self.file_path.parent,
            self.file_path.parent / 'assets',
            self.file_path.parent / 'images'
        ]
        if paths:
            base_paths.extend(paths)
        return base_paths

    def parse(self) -> Optional[Content]:
        """解析Markdown文件并返回Content对象"""
        try:
            self._read_markdown_file()
            self._convert_to_html()
            metadata = self._parse_metadata()
            resources = self._parse_resources()
            
            note = Content(
                title=metadata['title'],
                content=self.html_content,
                created=metadata['created'],
                updated=metadata['updated'],
                tags=metadata['tags'],
                source_url=metadata.get('source'),
                author=metadata.get('author')
            )
            
            # 添加资源并替换引用
            for resource in resources:
                note.add_resource(resource)
                self.html_content = self._replace_resource_reference(resource)
                
            note.content = self.html_content
            return note
            
        except Exception as e:
            logging.error(f"解析Markdown文件失败 {self.file_path}: {e}")
            return None

    def _read_markdown_file(self):
        """读取Markdown文件内容"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            self.post = frontmatter.load(f)

    def _convert_to_html(self):
        """将Markdown转换为HTML"""
        html_converter = Markdown(extensions=[
            'extra',
            'tables',
            'fenced_code',
            'nl2br'
        ])
        self.html_content = html_converter.convert(self.post.content)

    def _parse_metadata(self) -> dict:
        """解析元数据"""
        metadata = self.post.metadata
        return {
            'title': metadata.get('title', self.file_path.stem),
            'created': self._parse_datetime(metadata.get('created')),
            'updated': self._parse_datetime(metadata.get('updated')),
            'tags': self._parse_tags(metadata.get('tags', [])),
            'source': metadata.get('source'),
            'author': metadata.get('author')
        }

    def _parse_datetime(self, dt_str: str) -> datetime:
        """解析日期时间字符串"""
        if not dt_str:
            return datetime.fromtimestamp(self.file_path.stat().st_mtime)
        try:
            return datetime.strptime(dt_str, '%Y%m%dT%H%M%SZ')
        except ValueError:
            return datetime.fromtimestamp(self.file_path.stat().st_mtime)

    def _parse_tags(self, tags) -> List[str]:
        """解析标签"""
        if isinstance(tags, str):
            return [tag.strip() for tag in tags.split(',')]
        return tags if isinstance(tags, list) else []

    def _parse_resources(self) -> List[Resource]:
        """解析资源文件"""
        resources = []
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        for match in re.finditer(img_pattern, self.post.content):
            resource = self._process_resource(match.group(2))
            if resource:
                resources.append(resource)
                
        return resources

    def _process_resource(self, file_path: str) -> Optional[Resource]:
        """处理单个资源文件"""
        try:
            resolved_path = self._find_resource_file(file_path)
            if not resolved_path:
                return None

            with open(resolved_path, 'rb') as f:
                data = f.read()

            # 获取MIME类型
            mime_type = mimetypes.guess_type(str(resolved_path))[0] or 'application/octet-stream'
            
            # 如果是图片,尝试获取尺寸
            width = None
            height = None
            if mime_type.startswith('image/'):
                try:
                    from PIL import Image
                    with Image.open(resolved_path) as img:
                        width, height = img.size
                except:
                    pass

            return Resource(
                mime=mime_type,
                data=data,
                hash=hashlib.md5(data).hexdigest(),
                file_name=resolved_path.name,
                size=len(data),
                width=width,
                height=height
            )
        except Exception as e:
            logging.warning(f"处理资源文件失败 {file_path}: {e}")
            return None

    def _find_resource_file(self, file_path: str) -> Optional[Path]:
        """在所有资源路径中查找文件"""
        for path in self.resource_paths:
            full_path = path / file_path
            if full_path.exists():
                return full_path
        return None

    def _replace_resource_reference(self, resource: Resource) -> str:
        """替换HTML中的图片引用为Evernote媒体标签"""
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if resource.file_name in src:
                media = soup.new_tag('en-media')
                media['type'] = resource.mime
                media['hash'] = resource.hash
                img.replace_with(media)
                
        return str(soup)

def parse_markdown_file(file_path: str, resource_paths: List[Path] = None) -> Optional[Content]:
    """解析Markdown文件的入口函数"""
    parser = MarkdownParser(file_path, resource_paths)
    return parser.parse()


class MarkdownWriter:
    def __init__(self, output_dir: str, parser_type: str = 'soup'):
        """
        初始化 MarkdownWriter
        :param output_dir: 输出目录
        :param parser_type: 解析器类型 ('html2text' 或 'soup')
        """
        self.output_dir = Path(output_dir)
        self.assets_dir = self.output_dir / 'assets'
        self.parser_type = parser_type if parser_type in ['html2text', 'soup'] else 'soup'
        self.html_converter = self._setup_html_converter() if parser_type == 'html2text' else None
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def _setup_html_converter(self) -> HTML2Text:
        """配置HTML到Markdown转换器"""
        converter = HTML2Text()
        converter.body_width = 0  # 禁用自动换行
        converter.ignore_links = True
        converter.ignore_images = False
        converter.ignore_emphasis = False
        converter.ignore_tables = True  # 忽略表格,使用自定义转换
        converter.pad_tables = True
        converter.mark_code = True
        converter.wrap_links = False
        converter.use_automatic_links = False
        converter.escape_snob = False # 防止转义特殊字符
        # converter.single_line_break = True   # 保留换行符
        # 保持列表格式
        converter.ul_item_mark = "-"  # 无序列表使用-
        return converter

    def write_note(self, content: Content) -> None:
        """将Content对象写入Markdown文件"""
        try:
            # 处理资源
            content_with_resources = self._process_resources(content)
            
            # 转换HTML到Markdown
            markdown_content = self._convert_to_markdown(content_with_resources)
            
            # 创建frontmatter元数据
            metadata = {
                'title': content.title,
                'created': content.created.strftime('%Y%m%dT%H%M%SZ'),
                'updated': content.updated.strftime('%Y%m%dT%H%M%SZ'),
                'tags': content.tags or []
            }

            if content.author:
                metadata['author'] = content.author
            if content.source_url:
                metadata['source'] = content.source_url
            if content.notebook:
                metadata['notebook'] = content.notebook

            # 创建带frontmatter的markdown文件
            post = frontmatter.Post(markdown_content, **metadata)
            
            # 生成安全的文件名
            file_path = self.output_dir / f"{self._safe_filename(content.title)}.md"
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
                
        except Exception as e:
            logging.error(f"写入笔记失败 {content.title}: {e}")

    def _convert_to_markdown(self, html_content: str) -> str:
        """转换HTML内容为Markdown格式"""
        try:
            if self.parser_type == 'html2text':
                return self._convert_with_html2text(html_content)
            else:
                return self._convert_with_soup(html_content)
        except Exception as e:
            logging.error(f"HTML转Markdown失败: {e}")
            return html_content

    def _convert_with_html2text(self, html_content: str) -> str:
        """使用html2text转换"""
        soup = BeautifulSoup(html_content, features='xml')
        
        # 预处理表格
        tables = soup.find_all('table')
        for table in tables:
            markdown_table = self._convert_table_to_markdown(table)
            placeholder = soup.new_string(f"\n{markdown_table}\n")
            table.replace_with(placeholder)
        
        # 转换HTML到Markdown
        markdown_content = self.html_converter.handle(str(soup))
        
        # 清理格式
        return self._clean_markdown(markdown_content)

    def _convert_with_soup(self, html_content: str) -> str:
        """使用BeautifulSoup转换"""
        soup = BeautifulSoup(html_content, features='xml')
        markdown_content = self._process_soup_elements(soup)
        return self._clean_markdown(markdown_content)

    def _process_soup_elements(self, soup):
        """处理HTML元素"""
        markdown_lines = []
        
        for element in soup.contents:
            if isinstance(element, (Doctype, Comment, Declaration)):
                continue

            elif isinstance(element, NavigableString):
                text = str(element).strip()
                if text:
                    markdown_lines.append(text)
                    
            elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                content = self._process_soup_elements(element)
                level = int(element.name[1])
                markdown_lines.append(f"\n{'#' * level} {content}\n\n")
                
            elif element.name == 'div' or element.name == 'p':
                content = self._process_soup_elements(element)
                markdown_lines.append(content + '\n')
                
            elif element.name == 'br':
                markdown_lines.append('\n')
                
            elif element.name == 'span':
                content = self._process_soup_elements(element)
                markdown_lines.append(content)
                
            elif element.name == 'table':
                table_md = self._convert_table_to_markdown(element)
                markdown_lines.append(table_md + '\n')
                
            elif element.name == 'img':
                img_src = element.get('src', '')
                alt = element.get('alt', '') 
                markdown_lines.append(f"![{alt}]({img_src})\n")
                
            elif element.name in ['ol', 'ul']:
                list_items = element.find_all('li', recursive=False)
                for i, li in enumerate(list_items):
                    content = self._process_soup_elements(li)
                    if element.name == 'ol':
                        markdown_lines.append(f"{i + 1}. {content}\n")
                    else:
                        markdown_lines.append(f"* {content}\n")
                        
                
            else:
                content = self._process_soup_elements(element)
                if content.strip():
                    markdown_lines.append(content)
                    
        return ''.join(markdown_lines)

    def _clean_markdown(self, content: str) -> str:
        """清理Markdown格式"""
        # 清理表格标记
        content = content.replace('<!--BREAK-->', '\n')

        # 修复链接格式
        content = re.sub(r'<(http[s]?://[^>]+)>', r'[\1](\1)', content)
        
        # 清理多余的转义字符
        content = re.sub(r'\\([#\-*_.>])', r'\1', content)
        
        # 清理多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # 确保列表格式正确
        content = re.sub(r'\\(\d+\.)', r'\1', content)  # 修复有序列表
        content = re.sub(r'\\(-)', r'-', content)  # 修复无序列表 
        
        return content.strip()

    def _convert_table_to_markdown(self, table) -> str:
        """转换表格为Markdown格式"""
        rows = table.find_all('tr')
        if not rows:
            return ''

        table_data = []
        max_cols = 0
        
        # 收集所有行数据并确定最大列数
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = []
            for cell in cells:
                text = ' '.join(cell.stripped_strings)
                row_data.append(text.strip() or ' ')
            table_data.append(row_data)
            max_cols = max(max_cols, len(row_data))
            
        # 确保所有行都有相同的列数
        for row in table_data:
            while len(row) < max_cols:
                row.append(' ')
                
        # 生成Markdown表格
        md_lines = []
        # 表头
        md_lines.append('| ' + ' | '.join(table_data[0]) + ' |')
        # 分隔行
        md_lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
        # 数据行
        for row in table_data[1:]:
            md_lines.append('| ' + ' | '.join(row) + ' |')
            
        return '<!--BREAK-->'.join(md_lines) + '\n\n'

    def _process_resources(self, content: Content) -> str:
        """处理资源并更新内容中的引用"""
        processed_content = content.content

        for resource in content.resources:
            # if not resource.file_name:
            resource.file_name = f"{resource.hash}{mimetypes.guess_extension(resource.mime) or ''}"

            # 保存资源文件
            asset_path = self.assets_dir / resource.file_name
            with open(asset_path, 'wb') as f:
                f.write(resource.data)

            # 更新内容中的引用
            relative_path = f"assets/{resource.file_name}"
            media_tag = f'<en-media.*?hash="{resource.hash}".*?(?:></en-media>|/>)'
            if resource.mime.startswith('image/'):
                replacement = f'![{resource.file_name}]({relative_path})'
            else:
                replacement = f'[{resource.file_name}]({relative_path})'
            # processed_content = processed_content.replace(media_tag, replacement)
            processed_content = re.sub(media_tag, replacement, processed_content)

        return processed_content

    def _safe_filename(self, filename: str) -> str:
        """转换为安全的文件名"""
        invalid_chars = '<>:"/\\|?*'
        safe_name = ''.join(c if c not in invalid_chars else '_' for c in filename)
        return safe_name.strip()

    def save_all(self, contents: list[Content]) -> None:
        """保存多个Content对象为markdown文件"""
        for content in contents:
            self.write_note(content)
