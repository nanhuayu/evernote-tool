"""表格处理模块"""
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup, Tag, NavigableString
from dataclasses import dataclass
import re

from ..utils.logger import get_logger

logger = get_logger()


@dataclass
class TableCell:
    """表格单元格"""
    content: str
    rowspan: int = 1
    colspan: int = 1
    is_header: bool = False
    align: Optional[str] = None  # 'left', 'center', 'right'
    
    def __post_init__(self):
        self.content = self.content.strip()


@dataclass
class TableRow:
    """表格行"""
    cells: List[TableCell]
    is_header: bool = False


class TableHandler:
    """表格处理器"""
    
    def __init__(self):
        self.logger = get_logger()
    
    def html_table_to_markdown(self, table: Tag) -> str:
        """
        将HTML表格转换为Markdown格式
        
        支持：
        - 表头和表体
        - 列对齐
        - 简单的合并单元格（通过重复内容）
        - 单元格内的格式（粗体、斜体、链接等）
        """
        try:
            # 解析表格结构
            rows = self._parse_table_structure(table)
            if not rows:
                return ''
            
            # 处理合并单元格
            normalized_rows = self._normalize_merged_cells(rows)
            
            # 检测列对齐
            alignments = self._detect_column_alignment(table, len(normalized_rows[0].cells))
            
            # 生成Markdown表格
            return self._generate_markdown_table(normalized_rows, alignments)
            
        except Exception as e:
            logger.warning(f"表格转换失败: {e}")
            return self._fallback_table_conversion(table)
    
    def _parse_table_structure(self, table: Tag) -> List[TableRow]:
        """解析表格结构"""
        rows = []
        
        # 处理thead中的行（表头）
        thead = table.find('thead')
        if thead:
            for tr in thead.find_all('tr', recursive=False):
                row = self._parse_row(tr, is_header=True)
                if row:
                    rows.append(row)
        
        # 处理tbody中的行（表体）
        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr', recursive=False):
                row = self._parse_row(tr, is_header=False)
                if row:
                    rows.append(row)
        
        # 如果没有thead/tbody，直接处理tr
        if not rows:
            for tr in table.find_all('tr', recursive=False):
                row = self._parse_row(tr, is_header=False)
                if row:
                    rows.append(row)
        
        return rows
    
    def _parse_row(self, tr: Tag, is_header: bool = False) -> Optional[TableRow]:
        """解析表格行"""
        cells = []
        
        for cell in tr.find_all(['td', 'th'], recursive=False):
            # 如果是th标签，强制设为表头
            cell_is_header = is_header or cell.name == 'th'
            
            # 获取单元格内容（保留格式）
            content = self._get_cell_content(cell)
            
            # 获取合并信息
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            
            # 获取对齐方式
            align = self._get_cell_alignment(cell)
            
            cells.append(TableCell(
                content=content,
                rowspan=rowspan,
                colspan=colspan,
                is_header=cell_is_header,
                align=align
            ))
        
        if not cells:
            return None
        
        return TableRow(cells=cells, is_header=is_header)
    
    def _get_cell_content(self, cell: Tag) -> str:
        """获取单元格内容（保留内部格式）"""
        # 处理单元格内的HTML格式
        content_parts = []
        
        for element in cell.children:
            if isinstance(element, NavigableString):
                text = str(element).strip()
                if text:
                    content_parts.append(text)
            elif element.name == 'br':
                content_parts.append('<br>')
            elif element.name in ['strong', 'b']:
                text = element.get_text().strip()
                if text:
                    content_parts.append(f'**{text}**')
            elif element.name in ['em', 'i']:
                text = element.get_text().strip()
                if text:
                    content_parts.append(f'*{text}*')
            elif element.name == 'code':
                text = element.get_text().strip()
                if text:
                    content_parts.append(f'`{text}`')
            elif element.name == 'a':
                href = element.get('href', '')
                text = element.get_text().strip()
                if text and href:
                    content_parts.append(f'[{text}]({href})')
                elif text:
                    content_parts.append(text)
            else:
                text = element.get_text().strip()
                if text:
                    content_parts.append(text)
        
        content = ' '.join(content_parts)
        # 替换<br>为空格（Markdown表格不支持换行）
        content = content.replace('<br>', ' ')
        # 清理多余空格
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip() or ' '
    
    def _get_cell_alignment(self, cell: Tag) -> Optional[str]:
        """获取单元格对齐方式"""
        # 检查align属性
        align = cell.get('align', '').lower()
        if align in ['left', 'center', 'right']:
            return align
        
        # 检查style属性
        style = cell.get('style', '')
        if 'text-align' in style:
            if 'center' in style:
                return 'center'
            elif 'right' in style:
                return 'right'
            elif 'left' in style:
                return 'left'
        
        return None
    
    def _normalize_merged_cells(self, rows: List[TableRow]) -> List[TableRow]:
        """
        处理合并单元格
        将合并的单元格展开为多个单元格（内容相同）
        """
        if not rows:
            return rows
        
        # 确定最大列数
        max_cols = max(sum(cell.colspan for cell in row.cells) for row in rows)
        
        # 创建二维网格来追踪单元格占用
        grid = [[None for _ in range(max_cols)] for _ in range(len(rows))]
        
        # 填充网格
        for row_idx, row in enumerate(rows):
            col_idx = 0
            for cell in row.cells:
                # 找到下一个空位置
                while col_idx < max_cols and grid[row_idx][col_idx] is not None:
                    col_idx += 1
                
                if col_idx >= max_cols:
                    break
                
                # 填充合并的单元格
                for r in range(row_idx, min(row_idx + cell.rowspan, len(rows))):
                    for c in range(col_idx, min(col_idx + cell.colspan, max_cols)):
                        grid[r][c] = cell
                
                col_idx += cell.colspan
        
        # 从网格重建行
        normalized_rows = []
        for row_idx, row in enumerate(rows):
            cells = []
            seen_cells = set()
            
            for col_idx in range(max_cols):
                cell = grid[row_idx][col_idx]
                if cell and id(cell) not in seen_cells:
                    # 对于合并单元格，创建展开的副本
                    for _ in range(cell.colspan):
                        cells.append(TableCell(
                            content=cell.content,
                            is_header=cell.is_header,
                            align=cell.align
                        ))
                    seen_cells.add(id(cell))
                elif not cell:
                    cells.append(TableCell(content=' '))
            
            # 只保留实际需要的列数
            normalized_rows.append(TableRow(
                cells=cells[:max_cols],
                is_header=row.is_header
            ))
        
        return normalized_rows
    
    def _detect_column_alignment(self, table: Tag, num_cols: int) -> List[str]:
        """检测每列的对齐方式"""
        alignments = ['left'] * num_cols
        
        # 检查colgroup
        colgroup = table.find('colgroup')
        if colgroup:
            cols = colgroup.find_all('col')
            for idx, col in enumerate(cols[:num_cols]):
                align = self._get_cell_alignment(col)
                if align:
                    alignments[idx] = align
        
        return alignments
    
    def _generate_markdown_table(self, rows: List[TableRow], 
                                 alignments: List[str]) -> str:
        """生成Markdown表格"""
        if not rows:
            return ''
        
        lines = []
        
        # 确定是否有表头
        has_header = any(row.is_header for row in rows)
        
        if not has_header:
            # 如果没有表头，将第一行作为表头
            rows[0].is_header = True
            has_header = True
        
        # 生成表格行
        for row_idx, row in enumerate(rows):
            cells_text = [self._escape_cell_content(cell.content) for cell in row.cells]
            lines.append('| ' + ' | '.join(cells_text) + ' |')
            
            # 在第一个表头行后添加分隔符
            if row.is_header and (row_idx == 0 or not rows[row_idx + 1].is_header if row_idx + 1 < len(rows) else True):
                separator = self._generate_separator_row(len(row.cells), alignments)
                lines.append(separator)
        
        return '\n'.join(lines) + '\n'
    
    def _generate_separator_row(self, num_cols: int, 
                                alignments: List[str]) -> str:
        """生成分隔符行"""
        separators = []
        
        for i in range(num_cols):
            align = alignments[i] if i < len(alignments) else 'left'
            
            if align == 'center':
                separators.append(':---:')
            elif align == 'right':
                separators.append('---:')
            else:
                separators.append('---')
        
        return '| ' + ' | '.join(separators) + ' |'
    
    def _escape_cell_content(self, content: str) -> str:
        """转义单元格内容"""
        # 转义管道符
        content = content.replace('|', '\\|')
        # 移除换行符
        content = content.replace('\n', ' ')
        # 清理多余空格
        content = re.sub(r'\s+', ' ', content)
        return content.strip() or ' '
    
    def _fallback_table_conversion(self, table: Tag) -> str:
        """降级的表格转换方法"""
        lines = ['| 内容 |', '| --- |']
        
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if cells:
                text = ' | '.join(cell.get_text().strip() for cell in cells)
                lines.append(f'| {text} |')
        
        return '\n'.join(lines) + '\n'
    
    def markdown_table_to_html(self, markdown_table: str) -> str:
        """
        将Markdown表格转换为HTML
        
        Args:
            markdown_table: Markdown格式的表格文本
            
        Returns:
            HTML格式的表格
        """
        try:
            lines = [line.strip() for line in markdown_table.strip().split('\n') if line.strip()]
            
            if len(lines) < 2:
                return markdown_table
            
            # 解析表格
            rows = []
            separator_idx = -1
            alignments = []
            
            for idx, line in enumerate(lines):
                # 移除首尾的管道符
                line = line.strip('|').strip()
                cells = [cell.strip() for cell in line.split('|')]
                
                # 检查是否是分隔符行
                if self._is_separator_row(cells):
                    separator_idx = idx
                    alignments = self._parse_alignments(cells)
                    continue
                
                rows.append(cells)
            
            # 生成HTML
            return self._generate_html_table(rows, separator_idx, alignments)
            
        except Exception as e:
            logger.warning(f"Markdown表格转HTML失败: {e}")
            return markdown_table
    
    def _is_separator_row(self, cells: List[str]) -> bool:
        """检查是否是分隔符行"""
        for cell in cells:
            # 分隔符应该只包含 -、: 和空格
            if not re.match(r'^:?-+:?$', cell.strip()):
                return False
        return True
    
    def _parse_alignments(self, separator_cells: List[str]) -> List[str]:
        """解析列对齐方式"""
        alignments = []
        
        for cell in separator_cells:
            cell = cell.strip()
            if cell.startswith(':') and cell.endswith(':'):
                alignments.append('center')
            elif cell.endswith(':'):
                alignments.append('right')
            else:
                alignments.append('left')
        
        return alignments
    
    def _generate_html_table(self, rows: List[List[str]], 
                            separator_idx: int,
                            alignments: List[str]) -> str:
        """生成HTML表格"""
        soup = BeautifulSoup(features='html.parser')
        table = soup.new_tag('table')
        
        # 表头
        if separator_idx > 0:
            thead = soup.new_tag('thead')
            for row_data in rows[:separator_idx]:
                tr = soup.new_tag('tr')
                for col_idx, cell_content in enumerate(row_data):
                    th = soup.new_tag('th')
                    if col_idx < len(alignments):
                        th['align'] = alignments[col_idx]
                    th.string = self._unescape_cell_content(cell_content)
                    tr.append(th)
                thead.append(tr)
            table.append(thead)
        
        # 表体
        tbody = soup.new_tag('tbody')
        start_idx = separator_idx if separator_idx >= 0 else 0
        for row_data in rows[start_idx:]:
            tr = soup.new_tag('tr')
            for col_idx, cell_content in enumerate(row_data):
                td = soup.new_tag('td')
                if col_idx < len(alignments):
                    td['align'] = alignments[col_idx]
                # 处理单元格内的Markdown格式
                td.append(BeautifulSoup(self._process_cell_markdown(cell_content), 'html.parser'))
                tr.append(td)
            tbody.append(tr)
        table.append(tbody)
        
        return str(table)
    
    def _process_cell_markdown(self, content: str) -> str:
        """处理单元格内的Markdown格式"""
        # 处理粗体
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        # 处理斜体
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        # 处理代码
        content = re.sub(r'`(.+?)`', r'<code>\1</code>', content)
        # 处理链接
        content = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', content)
        return content
    
    def _unescape_cell_content(self, content: str) -> str:
        """反转义单元格内容"""
        return content.replace('\\|', '|')


# 便捷函数
def html_table_to_markdown(table: Tag) -> str:
    """HTML表格转Markdown"""
    handler = TableHandler()
    return handler.html_table_to_markdown(table)


def markdown_table_to_html(markdown: str) -> str:
    """Markdown表格转HTML"""
    handler = TableHandler()
    return handler.markdown_table_to_html(markdown)