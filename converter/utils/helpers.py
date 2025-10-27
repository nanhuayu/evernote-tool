"""辅助函数"""
import re
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import Union, Optional
from ..config import Config

def sanitize_filename(filename: str) -> str:
    """清理文件名中的非法字符"""
    safe_name = ''.join(
        c if c not in Config.INVALID_FILENAME_CHARS else '_' 
        for c in filename
    )
    return safe_name.strip()

def calculate_hash(data: bytes, algorithm: str = 'md5') -> str:
    """计算数据哈希值"""
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()

def parse_timestamp(timestamp: str, default: datetime = None) -> datetime:
    """解析时间戳"""
    if not timestamp:
        return default or datetime.now()
    
    try:
        return datetime.strptime(timestamp, Config.TIMESTAMP_FORMAT)
    except ValueError:
        return default or datetime.now()

def format_timestamp(dt: datetime) -> str:
    """格式化时间戳"""
    return dt.strftime(Config.TIMESTAMP_FORMAT)

def guess_extension(mime_type: str) -> str:
    """根据MIME类型猜测文件扩展名"""
    ext = mimetypes.guess_extension(mime_type)
    return ext or '.bin'

def find_file(filename: str, search_paths: list[Path]) -> Optional[Path]:
    """在多个路径中查找文件"""
    for base_path in search_paths:
        file_path = base_path / filename
        if file_path.exists() and file_path.is_file():
            return file_path
    return None
