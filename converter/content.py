from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Resource:
    """表示笔记中的附件或资源"""
    mime: str
    data: bytes
    hash: str
    file_name: Optional[str] = None
    size: Optional[int] = None
    width: Optional[int] = None  # 添加宽度属性
    height: Optional[int] = None  # 添加高度属性

@dataclass
class Content:
    """Represents the main content structure of an Evernote note"""
    title: str
    content: str
    created: datetime
    updated: datetime
    tags: List[str] = None
    resources: List[Resource] = None
    notebook: Optional[str] = None
    author: Optional[str] = None
    source_url: Optional[str] = None

    def __post_init__(self):
        """Initialize default values"""
        if self.tags is None:
            self.tags = []
        if self.resources is None:
            self.resources = []

    def add_resource(self, resource: Resource):
        """Add a resource to the note"""
        self.resources.append(resource)

    def add_tag(self, tag: str):
        """Add a tag to the note"""
        if tag not in self.tags:
            self.tags.append(tag)