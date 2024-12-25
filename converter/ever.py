from datetime import datetime
import logging
from typing import Optional

from bs4 import BeautifulSoup, CData, Doctype
from .content import Content, Resource
import base64
import hashlib

import xml.etree.ElementTree as ET

class EvernoteParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def parse(self) -> list[Content]:
        """解析ENEX文件并返回Content对象列表"""
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            notes = []
            
            for note in root.findall('note'):
                content_obj = self._parse_note(note)
                if content_obj:
                    notes.append(content_obj)
                    
            return notes
        except ET.ParseError as e:
            raise ValueError(f"ENEX文件解析失败: {e}")

    def _parse_note(self, note: ET.Element) -> Optional[Content]:
        """解析单个笔记元素"""
        try:
            # 解析基本字段
            basic_fields = self._parse_basic_fields(note)
            
            # 解析笔记属性
            attributes = self._parse_note_attributes(note)
            
            # 创建Content对象
            note_content = Content(
                **basic_fields,
                **attributes
            )
            
            # 解析资源
            self._parse_resources(note, note_content)
            
            return note_content
            
        except Exception as e:
            logging.error(f"笔记解析失败: {e}")
            return None

    def _parse_basic_fields(self, note: ET.Element) -> dict:
        """解析笔记基本字段"""
        return {
            'title': note.findtext('title', ''),
            'content': note.findtext('content', ''),
            'created': self._parse_timestamp(note.findtext('created', '')),
            'updated': self._parse_timestamp(note.findtext('updated', '')),
            'tags': [tag.text for tag in note.findall('tag')]
        }

    def _parse_note_attributes(self, note: ET.Element) -> dict:
        """解析笔记属性"""
        attrs = note.find('note-attributes')
        if attrs is None:
            return {}
            
        return {
            'author': attrs.findtext('author'),
            'source_url': attrs.findtext('source-url'),
            'notebook': attrs.findtext('notebook')
        }

    def _parse_resources(self, note: ET.Element, content: Content) -> None:
        """解析笔记资源"""
        for resource in note.findall('resource'):
            res = self._parse_resource(resource)
            if res:
                content.add_resource(res)

    def _parse_resource(self, resource: ET.Element) -> Optional[Resource]:
        """解析单个资源"""
        try:
            # 获取必需字段
            mime = resource.findtext('mime', '')
            data = resource.find('data')
            
            if data is None:
                return None
                
            # 处理数据和哈希
            data_bytes = base64.b64decode(data.text)
            hash_value = data.get('hash') or hashlib.md5(data_bytes).hexdigest()
            
            # 获取可选属性
            attrs = resource.find('resource-attributes')
            filename = attrs.findtext('file-name') if attrs is not None else None
            size = int(resource.findtext('size', 0))
            width = int(resource.findtext('width', 0)) or None
            height = int(resource.findtext('height', 0)) or None
            
            return Resource(
                mime=mime,
                data=data_bytes,
                hash=hash_value,
                file_name=filename,
                size=size,
                width=width,
                height=height
            )
        except Exception as e:
            logging.error(f"资源解析失败: {e}")
            return None

    def _parse_timestamp(self, timestamp: str) -> datetime:
        """解析时间戳"""
        try:
            return datetime.strptime(timestamp, '%Y%m%dT%H%M%SZ')
        except ValueError:
            return datetime.now()

def parse_enex_file(file_path: str) -> list[Content]:
    """解析ENEX文件的入口函数"""
    parser = EvernoteParser(file_path)
    return parser.parse()



class EvernoteWriter:
    def __init__(self):
        # Initialize BeautifulSoup with XML features
        self.soup = BeautifulSoup(features="xml")
        self.soup.append(Doctype('en-export SYSTEM "http://xml.evernote.com/pub/evernote-export3.dtd"'))
        self.root = self.soup.new_tag("en-export")
        self.soup.append(self.root)

    def create_note_element(self, content: Content) -> None:
        """Create and append a note element to the ENEX document"""
        note = self.soup.new_tag('note')

        # Add title
        title = self.soup.new_tag('title')
        title.string = content.title
        note.append(title)

        # Add content
        note_content = self._create_note_content(content.content)
        content_tag = self.soup.new_tag('content')
        content_tag.string = CData(str(note_content))
        note.append(content_tag)

        # Add created timestamp
        created = self.soup.new_tag('created')
        created.string = content.created.strftime('%Y%m%dT%H%M%SZ')
        note.append(created)

        # Add updated timestamp
        updated = self.soup.new_tag('updated')
        updated.string = content.updated.strftime('%Y%m%dT%H%M%SZ')
        note.append(updated)

        # Add tags
        for tag in content.tags:
            tag_element = self.soup.new_tag('tag')
            tag_element.string = tag
            note.append(tag_element)

        # Add note attributes
        attributes = self.soup.new_tag('note-attributes')
        
        if content.author:
            author = self.soup.new_tag('author')
            author.string = content.author
            attributes.append(author)
            
        if content.source_url:
            source_url = self.soup.new_tag('source-url')
            source_url.string = content.source_url
            attributes.append(source_url)
            
        if content.notebook:
            notebook = self.soup.new_tag('notebook')
            notebook.string = content.notebook
            attributes.append(notebook)

        note.append(attributes)

        # Add resources
        for resource in content.resources:
            resource_element = self._create_resource_element(resource)
            note.append(resource_element)

        self.root.append(note)

    def _create_note_content(self, content: str) -> BeautifulSoup:
        """Create the ENML content structure"""
        content_soup = BeautifulSoup(features="xml")
        content_soup.append(Doctype('en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd"'))
        en_note = self.soup.new_tag('en-note')
        en_note.string = content
        content_soup.append(en_note)
        return content_soup

    def _create_resource_element(self, resource: Resource):
        """Create a resource element for attachments"""
        resource_tag = self.soup.new_tag('resource')

        # Add data
        data = self.soup.new_tag('data')
        data['encoding'] = 'base64'
        data['hash'] = resource.hash
        data.string = base64.b64encode(resource.data).decode()
        resource_tag.append(data)

        # Add mime type
        mime = self.soup.new_tag('mime')
        mime.string = resource.mime
        resource_tag.append(mime)

        # Add width/height for images if needed
        if resource.width and resource.height:
            width = self.soup.new_tag('width')
            width.string = str(resource.width)
            resource_tag.append(width)

            height = self.soup.new_tag('height')
            height.string = str(resource.height)
            resource_tag.append(height)

        # Add resource attributes
        if resource.file_name:
            attributes = self.soup.new_tag('resource-attributes')
            filename = self.soup.new_tag('file-name')
            filename.string = resource.file_name
            attributes.append(filename)
            resource_tag.append(attributes)

        return resource_tag

    def save(self, file_path: str) -> None:
        """Save the ENEX file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(self.soup))

    def add_note(self, content: Content) -> None:
        """Add a note to the ENEX file"""
        self.create_note_element(content)
