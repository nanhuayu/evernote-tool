import logging
from pathlib import Path 
from typing import Optional, List, Union

from .ever import EvernoteParser, EvernoteWriter
from .mark import MarkdownParser, MarkdownWriter
from .content import Content

class Converter:
    """在Evernote ENEX和Markdown格式之间进行转换"""
    
    def __init__(self):
        self._setup_logging()
        
    @staticmethod
    def _setup_logging():
        """配置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('converter.log', encoding='utf-8')
            ]
        )

    @classmethod
    def enex_to_markdown(cls, source: Union[str, Path], target: Union[str, Path]) -> None:
        """将ENEX文件转换为Markdown文件
        
        Args:
            source: ENEX文件路径
            target: 输出目录路径
        """
        try:
            source_path = Path(source)
            target_path = Path(target)
            
            # 验证输入
            if not source_path.exists():
                raise FileNotFoundError(f"ENEX文件不存在: {source_path}")
            if not source_path.suffix.lower() == '.enex':
                raise ValueError(f"无效的文件类型: {source_path.suffix}")
                
            # 解析ENEX文件
            logging.info(f"开始解析ENEX文件: {source_path}")
            parser = EvernoteParser(str(source_path))
            notes = parser.parse()
            logging.info(f"成功解析 {len(notes)} 个笔记")
            
            # 保存为Markdown
            writer = MarkdownWriter(str(target_path))
            writer.save_all(notes)
            logging.info(f"已保存Markdown文件到: {target_path}")
            
        except Exception as e:
            logging.error(f"转换失败: {str(e)}")
            raise

    @classmethod
    def markdown_to_enex(cls, 
                        source: Union[str, Path], 
                        target: Union[str, Path], 
                        resource_paths: Optional[List[Union[str, Path]]] = None
                        ) -> None:
        """将Markdown文件转换为ENEX格式
        
        Args:
            source: 包含Markdown文件的目录
            target: ENEX输出文件路径
            resource_paths: 可选的额外资源搜索路径列表
        """
        try:
            source_path = Path(source)
            target_path = Path(target)
            
            # 验证输入
            if not source_path.exists():
                raise FileNotFoundError(f"源目录不存在: {source_path}")
                
            # 规范化资源路径
            resource_paths = [] if not resource_paths else resource_paths
            resource_paths.append(source_path)
            normalized_resource_paths = cls._normalize_resource_paths(resource_paths)
            
            # 初始化写入器
            writer = EvernoteWriter()
            
            # 处理所有Markdown文件
            md_files = list(source_path.glob('**/*.md'))
            if not md_files:
                raise ValueError(f"未找到Markdown文件: {source_path}")
                
            logging.info(f"开始处理 {len(md_files)} 个Markdown文件")
            for file in md_files:
                try:
                    parser = MarkdownParser(str(file), normalized_resource_paths)
                    note = parser.parse()
                    if note:
                        writer.add_note(note)
                        logging.debug(f"已处理: {file.name}")
                except Exception as e:
                    logging.warning(f"处理文件失败 {file}: {e}")
                    continue
            
            # 保存ENEX文件
            writer.save(str(target_path))
            logging.info(f"已保存ENEX文件到: {target_path}")
            
        except Exception as e:
            logging.error(f"转换失败: {str(e)}")
            raise

    @staticmethod
    def _normalize_resource_paths(paths: Optional[List[Union[str, Path]]]) -> List[Path]:
        """规范化资源路径列表"""
        if not paths:
            return []
        return [Path(p) for p in paths]

    @classmethod
    def convert_file(cls, source: Union[str, Path], target: Union[str, Path]) -> None:
        """根据文件扩展名自动选择转换方向
        
        Args:
            source: 源文件/目录路径 (.enex或.md)
            target: 目标文件/目录路径
        """
        source_path = Path(source)
        target_path = Path(target)
        
        if source_path.suffix.lower() == '.enex':
            cls.enex_to_markdown(source_path, target_path)
        elif source_path.suffix.lower() == '.md':
            if not str(target_path).lower().endswith('.enex'):
                target_path = target_path / 'output.enex'
            cls.markdown_to_enex(source_path.parent, target_path)
        else:
            raise ValueError("不支持的文件格式，必须是.enex或.md")