"""HTML转换处理器"""
from bs4 import BeautifulSoup, NavigableString, Comment, Doctype, Declaration
from html2text import HTML2Text
import re

from ..utils.logger import get_logger
from .table_handler import TableHandler

logger = get_logger()

class HtmlToMarkdownConverter:
    """HTML到Markdown转换器"""
    
    def __init__(self, converter_type: str = 'soup'):
        self.converter_type = converter_type
        self.table_handler = TableHandler()  # 使用专门的表格处理器
        if converter_type == 'html2text':
            self.html2text = self._setup_html2text()
    
    def _setup_html2text(self) -> HTML2Text:
        """配置html2text转换器"""
        converter = HTML2Text()
        converter.body_width = 0
        converter.ignore_links = False
        converter.ignore_images = False
        converter.ignore_emphasis = False
        converter.pad_tables = True
        converter.mark_code = True
        converter.wrap_links = False
        converter.escape_snob = False
        converter.ul_item_mark = "-"
        converter.bypass_tables = True  # 我们自己处理表格
        return converter
    
    def convert(self, html: str) -> str:
        """转换HTML到Markdown"""
        if self.converter_type == 'html2text':
            return self._convert_with_html2text(html)
        else:
            return self._convert_with_soup(html)
    
    def _convert_with_html2text(self, html: str) -> str:
        """使用html2text转换"""
        soup = BeautifulSoup(html, 'xml')
        
        # 预处理表格 - 使用新的表格处理器
        for table in soup.find_all('table'):
            markdown_table = self.table_handler.html_table_to_markdown(table)
            table.replace_with(soup.new_string(f"\n{markdown_table}\n"))
        
        # 转换HTML到Markdown
        markdown = self.html2text.handle(str(soup))
        
        # 清理格式
        return self._clean_markdown(markdown)
    
    def _convert_with_soup(self, html: str) -> str:
        """使用BeautifulSoup转换"""
        soup = BeautifulSoup(html, 'xml')
        markdown = self._process_elements(soup)
        return self._clean_markdown(markdown)
    
    def _process_elements(self, element) -> str:
        """递归处理HTML元素"""
        lines = []
        
        for child in element.children:
            # 跳过特殊节点
            if isinstance(child, (Comment, Doctype, Declaration)):
                continue

            # 文本节点
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    lines.append(text)
                continue
            
            # 标题
            if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                content = self._process_elements(child)
                level = int(child.name[1])
                lines.append(f"\n{'#' * level} {content}\n")
            
            # 段落和div
            elif child.name in ['p', 'div']:
                content = self._process_elements(child)
                if content.strip():
                    lines.append(f"{content}\n")
            
            # 换行
            elif child.name == 'br':
                lines.append('\n')
            
            # 列表
            elif child.name in ['ul', 'ol']:
                lines.append(self._convert_list(child))
            
            # 表格 - 使用新的表格处理器
            elif child.name == 'table':
                table_md = self.table_handler.html_table_to_markdown(child)
                lines.append(f"\n{table_md}\n")
            
            # 图片
            elif child.name == 'img':
                src = child.get('src', '')
                alt = child.get('alt', 'image')
                lines.append(f"![{alt}]({src})")
            
            # 链接
            elif child.name == 'a':
                href = child.get('href', '')
                text = self._process_elements(child)
                if href:
                    lines.append(f"[{text}]({href})")
                else:
                    lines.append(text)
            
            # 加粗
            elif child.name in ['strong', 'b']:
                content = self._process_elements(child)
                lines.append(f"**{content}**")
            
            # 斜体
            elif child.name in ['em', 'i']:
                content = self._process_elements(child)
                lines.append(f"*{content}*")
            
            # 代码
            elif child.name == 'code':
                content = self._process_elements(child)
                lines.append(f"`{content}`")
            
            # 代码块
            elif child.name == 'pre':
                code = child.find('code')
                if code:
                    content = code.get_text()
                    lang = self._detect_code_language(code)
                    lines.append(f"\n```{lang}\n{content}\n```\n")
                else:
                    content = child.get_text()
                    lines.append(f"\n```\n{content}\n```\n")
            
            # 引用
            elif child.name == 'blockquote':
                content = self._process_elements(child)
                quoted = '\n'.join(f"> {line}" for line in content.split('\n') if line.strip())
                lines.append(f"\n{quoted}\n")
            
            # 水平线
            elif child.name == 'hr':
                lines.append('\n---\n')
            
            # 其他标签
            else:
                content = self._process_elements(child)
                if content.strip():
                    lines.append(content)
        
        return ''.join(lines)
    
    def _convert_list(self, list_elem) -> str:
        """转换列表"""
        lines = []
        items = list_elem.find_all('li', recursive=False)
        
        for i, item in enumerate(items):
            content = self._process_elements(item).strip()
            # 处理嵌套列表
            content_lines = content.split('\n')
            
            if list_elem.name == 'ol':
                lines.append(f"{i + 1}. {content_lines[0]}")
            else:
                lines.append(f"- {content_lines[0]}")
            
            # 添加缩进的后续行
            for line in content_lines[1:]:
                if line.strip():
                    lines.append(f"  {line}")
        
        return '\n'.join(lines) + '\n'
    
    def _detect_code_language(self, code_elem) -> str:
        """检测代码语言"""
        # 检查class属性
        classes = code_elem.get('class', [])
        for cls in classes:
            if cls.startswith('language-'):
                return cls.replace('language-', '')
            elif cls in ['python', 'javascript', 'java', 'cpp', 'c', 'bash', 'sql']:
                return cls
        return ''
    
    def _clean_markdown(self, content: str) -> str:
        """清理Markdown内容"""
        # 清理多余空行
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # 修复链接
        content = re.sub(r'<(https?://[^>]+)>', r'[\1](\1)', content)
        
        # 清理转义（但保留表格中的转义管道符）
        # content = re.sub(r'\\([#\-*_.>])', r'\1', content)
        
        # 确保列表和其他块级元素前后有空行
        content = re.sub(r'([^\n])\n(\d+\.|-|\*) ', r'\1\n\n\2 ', content)
        
        return content.strip()