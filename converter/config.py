"""配置文件"""
from pathlib import Path

class Config:
    """全局配置"""
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'converter.log'
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    
    # 资源配置
    ASSETS_DIR_NAME = 'assets'
    DEFAULT_RESOURCE_DIRS = ['assets', 'images', 'attachments']
    
    # HTML转换配置
    HTML_PARSER = 'xml'  # 'xml' 或 'html.parser'
    
    # Markdown配置
    MARKDOWN_EXTENSIONS = [
        'extra',
        'tables', 
        'fenced_code',
        'nl2br'
    ]
    
    # 时间格式
    TIMESTAMP_FORMAT = '%Y%m%dT%H%M%SZ'
    
    # 文件名非法字符
    INVALID_FILENAME_CHARS = '<>:"/\\|?*'
