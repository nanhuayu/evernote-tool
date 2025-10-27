"""HTML转换处理器"""
from bs4 import BeautifulSoup, NavigableString, Comment, Doctype, Declaration
from html2text import HTML2Text
import re

from ..utils.logger import get_logger

logger = get_logger()

class HtmlToMarkdownConverter:
    """HTML到Markdown转换器"""
    
    def __init__(self, converter_type: str = 'soup'):
        self.converter_type = converter_type
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
        
        # 预处理表格
        for table in soup.find_all('table'):
            table_md = self._convert_table(table)
            table.replace_with(soup.new_string(f"\n{table_md}\n"))
        
        markdown = self.html2text.handle(str(soup))
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
                level = int(child.name[1])
                content = self._process_elements(child)
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
            
            # 表格
            elif child.name == 'table':
                lines.append(self._convert_table(child))
            
            # 图片
            elif child.name == 'img':
                src = child.get('src', '')
                alt = child.get('alt', 'image')
                lines.append(f"![{alt}]({src})")
            
            # 链接
            elif child.name == 'a':
                href = child.get('href', '')
                text = self._process_elements(child)
                lines.append(f"[{text}]({href})")
            
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
            if list_elem.name == 'ol':
                lines.append(f"{i + 1}. {content}")
            else:
                lines.append(f"- {content}")
        
        return '\n'.join(lines) + '\n'
    
    def _convert_table(self, table) -> str:
        """转换表格为Markdown"""
        rows = table.find_all('tr')
        if not rows:
            return ''
        
        table_data = []
        max_cols = 0
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = [
                ' '.join(cell.stripped_strings) or ' '
                for cell in cells
            ]
            table_data.append(row_data)
            max_cols = max(max_cols, len(row_data))
        
        # 补齐列数
        for row in table_data:
            while len(row) < max_cols:
                row.append(' ')
        
        # 生成Markdown表格
        lines = []
        lines.append('| ' + ' | '.join(table_data[0]) + ' |')
        lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
        for row in table_data[1:]:
            lines.append('| ' + ' | '.join(row) + ' |')
        
        return '\n'.join(lines) + '\n'
    
    def _clean_markdown(self, content: str) -> str:
        """清理Markdown内容"""
        # 清理多余空行
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # 修复链接
        content = re.sub(r'<(https?://[^>]+)>', r'[\1](\1)', content)
        
        # 清理转义
        content = re.sub(r'\\([#\-*_.>])', r'\1', content)
        
        return content.strip()