"""解析器基类"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union
from ..models import Note

class BaseParser(ABC):
    """解析器基类"""
    
    def __init__(self, source: Union[str, Path]):
        self.source = Path(source)
        self._validate_source()
    
    def _validate_source(self) -> None:
        """验证源文件"""
        if not self.source.exists():
            raise FileNotFoundError(f"源文件不存在: {self.source}")
    
    @abstractmethod
    def parse(self) -> Union[Note, List[Note]]:
        """解析文件"""
        pass
