"""ENEX格式解析器"""
import base64
import xml.etree.ElementTree as ET
from typing import List, Optional
from .base import BaseParser
from ..models import Note, Resource
from ..utils.logger import get_logger
from ..utils.helpers import calculate_hash, parse_timestamp

logger = get_logger()

class EnexParser(BaseParser):
    """ENEX文件解析器"""
    
    def parse(self) -> List[Note]:
        """解析ENEX文件并返回笔记列表"""
        try:
            tree = ET.parse(self.source)
            root = tree.getroot()
            notes = []
            
            for note_elem in root.findall('note'):
                note = self._parse_note(note_elem)
                if note:
                    notes.append(note)
            
            logger.info(f"成功解析 {len(notes)} 个笔记")
            return notes
            
        except ET.ParseError as e:
            logger.error(f"ENEX文件解析失败: {e}")
            raise ValueError(f"无效的ENEX文件: {e}")
    
    def _parse_note(self, elem: ET.Element) -> Optional[Note]:
        """解析单个笔记"""
        try:
            note = Note(
                title=elem.findtext('title', '无标题'),
                content=elem.findtext('content', ''),
                created=parse_timestamp(elem.findtext('created', '')),
                updated=parse_timestamp(elem.findtext('updated', '')),
                tags=[tag.text for tag in elem.findall('tag') if tag.text]
            )
            
            # 解析属性
            attrs = elem.find('note-attributes')
            if attrs is not None:
                note.author = attrs.findtext('author')
                note.source_url = attrs.findtext('source-url')
                note.notebook = attrs.findtext('notebook')
            
            # 解析资源
            for res_elem in elem.findall('resource'):
                resource = self._parse_resource(res_elem)
                if resource:
                    note.add_resource(resource)
            
            return note
            
        except Exception as e:
            logger.error(f"笔记解析失败: {e}")
            return None
    
    def _parse_resource(self, elem: ET.Element) -> Optional[Resource]:
        """解析资源"""
        try:
            data_elem = elem.find('data')
            if data_elem is None or not data_elem.text:
                return None
            
            data = base64.b64decode(data_elem.text)
            hash_value = data_elem.get('hash') or calculate_hash(data)
            
            # 获取属性
            attrs = elem.find('resource-attributes')
            filename = attrs.findtext('file-name') if attrs is not None else None
            
            return Resource(
                mime=elem.findtext('mime', 'application/octet-stream'),
                data=data,
                hash=hash_value,
                file_name=filename,
                width=self._parse_int(elem.findtext('width')),
                height=self._parse_int(elem.findtext('height'))
            )
            
        except Exception as e:
            logger.warning(f"资源解析失败: {e}")
            return None
    
    @staticmethod
    def _parse_int(value: str) -> Optional[int]:
        """安全解析整数"""
        try:
            return int(value) if value else None
        except ValueError:
            return None