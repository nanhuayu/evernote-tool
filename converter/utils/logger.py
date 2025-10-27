"""日志工具"""
import logging
from pathlib import Path
from ..config import Config

_logger_initialized = False

def setup_logger(name: str = 'converter', 
                 level: str = None,
                 log_file: str = None) -> logging.Logger:
    """配置日志记录器"""
    global _logger_initialized
    
    logger = logging.getLogger(name)
    
    if _logger_initialized:
        return logger
    
    level = level or Config.LOG_LEVEL
    log_file = log_file or Config.LOG_FILE
    
    logger.setLevel(getattr(logging, level.upper()))
    
    formatter = logging.Formatter(Config.LOG_FORMAT)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    _logger_initialized = True
    return logger

def get_logger(name: str = 'converter') -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)