"""笔记转换工具"""
from pathlib import Path
from typing import Union, List, Optional

from .parsers.enex_parser import EnexParser
from .parsers.markdown_parser import MarkdownParser
from .writers.enex_writer import EnexWriter
from .writers.markdown_writer import MarkdownWriter
from .utils.logger import setup_logger, get_logger
from .config import Config

# 初始化日志
setup_logger()
logger = get_logger()

class Converter:
    """笔记格式转换器"""
    
    @classmethod
    def enex_to_markdown(cls, 
                         source: Union[str, Path],
                         target: Union[str, Path],
                         converter_type: str = 'soup') -> None:
        """
        将ENEX文件转换为Markdown文件
        
        Args:
            source: ENEX文件路径
            target: 输出目录路径
            converter_type: HTML转换器类型 ('soup' 或 'html2text')
        """
        try:
            source_path = Path(source)
            target_path = Path(target)
            
            # 验证
            if not source_path.exists():
                raise FileNotFoundError(f"文件不存在: {source_path}")
            if source_path.suffix.lower() != '.enex':
                raise ValueError(f"不是ENEX文件: {source_path}")
            
            # 解析
            logger.info(f"开始解析: {source_path}")
            parser = EnexParser(source_path)
            notes = parser.parse()
            
            # 写入
            logger.info(f"开始写入Markdown文件")
            writer = MarkdownWriter(target_path, converter_type)
            writer.write_all(notes)
            
            logger.info(f"转换完成: {len(notes)} 个笔记")
            
        except Exception as e:
            logger.error(f"转换失败: {e}")
            raise
    
    @classmethod
    def markdown_to_enex(cls,
                        source: Union[str, Path],
                        target: Union[str, Path],
                        resource_paths: Optional[List[Union[str, Path]]] = None) -> None:
        """
        将Markdown文件转换为ENEX格式
        
        Args:
            source: Markdown文件目录
            target: ENEX输出文件路径
            resource_paths: 额外的资源搜索路径
        """
        try:
            source_path = Path(source)
            target_path = Path(target)
            
            # 验证
            if not source_path.exists():
                raise FileNotFoundError(f"目录不存在: {source_path}")
            
            # 准备资源路径
            res_paths = [Path(p) for p in resource_paths] if resource_paths else []
            
            # 初始化写入器
            writer = EnexWriter(target_path)
            
            # 处理所有Markdown文件
            md_files = list(source_path.rglob('*.md'))
            if not md_files:
                raise ValueError(f"未找到Markdown文件: {source_path}")
            
            logger.info(f"找到 {len(md_files)} 个Markdown文件")
            
            for md_file in md_files:
                try:
                    parser = MarkdownParser(md_file, res_paths)
                    note = parser.parse()
                    if note:
                        writer.write(note)
                except Exception as e:
                    logger.warning(f"处理失败 {md_file.name}: {e}")
            
            # 保存
            writer.save()
            logger.info(f"转换完成")
            
        except Exception as e:
            logger.error(f"转换失败: {e}")
            raise
    
    @classmethod
    def convert(cls, 
                source: Union[str, Path],
                target: Union[str, Path],
                **kwargs) -> None:
        """
        根据文件扩展名自动选择转换方向
        
        Args:
            source: 源文件/目录
            target: 目标文件/目录
            **kwargs: 其他参数
        """
        source_path = Path(source)
        
        if source_path.suffix.lower() == '.enex':
            cls.enex_to_markdown(source, target, **kwargs)
        elif source_path.suffix.lower() == '.md':
            if not str(target).lower().endswith('.enex'):
                target = Path(target) / 'output.enex'
            cls.markdown_to_enex(source_path.parent, target, **kwargs)
        else:
            raise ValueError("不支持的文件格式，仅支持 .enex 和 .md")

__all__ = ['Converter', 'Config']