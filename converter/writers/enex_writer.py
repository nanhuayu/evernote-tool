"""ENEX格式写入器"""
import base64
from bs4 import BeautifulSoup, CData, Doctype

from .base import BaseWriter
from ..models import Note, Resource
from ..utils.logger import get_logger
from ..utils.helpers import format_timestamp
from ..config import Config

logger = get_logger()

class EnexWriter(BaseWriter):
    """ENEX文件写入器"""
    
    def __init__(self, output: str):
        super().__init__(output)
        self._init_document()
    
    def _init_document(self) -> None:
        """初始化ENEX文档"""
        self.soup = BeautifulSoup(features="xml")
        doctype = Doctype(
            'en-export SYSTEM '
            '"http://xml.evernote.com/pub/evernote-export3.dtd"'
        )
        self.soup.append(doctype)
        self.root = self.soup.new_tag("en-export")
        self.soup.append(self.root)
    
    def write(self, note: Note) -> None:
        """添加笔记到文档"""
        note_elem = self._create_note_element(note)
        self.root.append(note_elem)
    
    def save(self) -> None:
        """保存ENEX文件"""
        with open(self.output, 'w', encoding='utf-8') as f:
            f.write(str(self.soup))
        logger.info(f"已保存ENEX文件: {self.output}")
    
    def write_all(self, notes: list[Note]) -> None:
        """写入所有笔记并保存"""
        for note in notes:
            self.write(note)
        self.save()
    
    def _create_note_element(self, note: Note):
        """创建笔记元素"""
        elem = self.soup.new_tag('note')
        
        # 标题
        title = self.soup.new_tag('title')
        title.string = note.title
        elem.append(title)
        
        # 内容
        content = self.soup.new_tag('content')
        content.string = CData(self._create_enml_content(note.content))
        elem.append(content)
        
        # 时间戳
        created = self.soup.new_tag('created')
        created.string = format_timestamp(note.created)
        elem.append(created)
        
        updated = self.soup.new_tag('updated')
        updated.string = format_timestamp(note.updated)
        elem.append(updated)
        
        # 标签
        for tag in note.tags:
            tag_elem = self.soup.new_tag('tag')
            tag_elem.string = tag
            elem.append(tag_elem)
        
        # 属性
        attrs = self._create_attributes(note)
        if attrs.contents:
            elem.append(attrs)
        
        # 资源
        for resource in note.resources:
            res_elem = self._create_resource_element(resource)
            elem.append(res_elem)
        
        return elem
    
    def _create_enml_content(self, content: str) -> str:
        """创建ENML内容"""
        soup = BeautifulSoup(features="xml")
        doctype = Doctype(
            'en-note SYSTEM '
            '"http://xml.evernote.com/pub/enml2.dtd"'
        )
        soup.append(doctype)
        
        en_note = self.soup.new_tag('en-note')
        en_note.string = content
        soup.append(en_note)
        
        return str(soup)
    
    def _create_attributes(self, note: Note):
        """创建笔记属性元素"""
        attrs = self.soup.new_tag('note-attributes')
        
        if note.author:
            author = self.soup.new_tag('author')
            author.string = note.author
            attrs.append(author)
        
        if note.source_url:
            source = self.soup.new_tag('source-url')
            source.string = note.source_url
            attrs.append(source)
        
        if note.notebook:
            notebook = self.soup.new_tag('notebook')
            notebook.string = note.notebook
            attrs.append(notebook)
        
        return attrs
    
    def _create_resource_element(self, resource: Resource):
        """创建资源元素"""
        elem = self.soup.new_tag('resource')
        
        # 数据
        data = self.soup.new_tag('data')
        data['encoding'] = 'base64'
        data['hash'] = resource.hash
        data.string = base64.b64encode(resource.data).decode()
        elem.append(data)
        
        # MIME类型
        mime = self.soup.new_tag('mime')
        mime.string = resource.mime
        elem.append(mime)
        
        # 尺寸(图片)
        if resource.width and resource.height:
            width = self.soup.new_tag('width')
            width.string = str(resource.width)
            elem.append(width)
            
            height = self.soup.new_tag('height')
            height.string = str(resource.height)
            elem.append(height)
        
        # 文件名
        if resource.file_name:
            attrs = self.soup.new_tag('resource-attributes')
            filename = self.soup.new_tag('file-name')
            filename.string = resource.file_name
            attrs.append(filename)
            elem.append(attrs)
        
        return elem