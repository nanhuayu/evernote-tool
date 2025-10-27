"""写入器基类"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union
from ..models import Note

class BaseWriter(ABC):
    """写入器基类"""
    
    def __init__(self, output: Union[str, Path]):
        self.output = Path(output)
        self._prepare_output()
    
    def _prepare_output(self) -> None:
        """准备输出目录"""
        if self.output.suffix:  # 是文件
            self.output.parent.mkdir(parents=True, exist_ok=True)
        else:  # 是目录
            self.output.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def write(self, note: Note) -> None:
        """写入单个笔记"""
        pass
    
    def write_all(self, notes: List[Note]) -> None:
        """写入多个笔记"""
        for note in notes:
            self.write(note)