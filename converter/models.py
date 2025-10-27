"""数据模型"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class Resource:
    """笔记资源/附件"""
    mime: str
    data: bytes
    hash: str
    file_name: Optional[str] = None
    size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    
    def __post_init__(self):
        if self.size is None and self.data:
            self.size = len(self.data)

@dataclass
class Note:
    """笔记内容"""
    title: str
    content: str
    created: datetime
    updated: datetime
    tags: List[str] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    notebook: Optional[str] = None
    author: Optional[str] = None
    source_url: Optional[str] = None

    def add_resource(self, resource: Resource) -> None:
        """添加资源"""
        self.resources.append(resource)

    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag and tag not in self.tags:
            self.tags.append(tag)
