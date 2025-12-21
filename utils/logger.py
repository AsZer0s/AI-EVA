"""
AI-EVA Demo 日志工具
"""
import logging
import sys
import yaml
from pathlib import Path
from datetime import datetime

# 加载配置
def _load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}

_config = _load_config()
logging_config = _config.get('logging', {})

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m', # 黄色
        'ERROR': '\033[31m',   # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'     # 重置
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

def setup_logger(name: str = "ai-eva", level: str = None) -> logging.Logger:
    """
    设置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
    
    Returns:
        配置好的日志器
    """
    if level is None:
        level = logging_config.get('level', 'INFO')
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # 控制台格式化器（彩色）
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果启用）
    save_to_file = logging_config.get('save_to_file', True)
    if save_to_file:
        log_file_path = logging_config.get('file_path', 'logs/ai-eva.log')
        file_handler = logging.FileHandler(
            log_file_path,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 文件格式化器（无颜色）
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

# 创建默认日志器
logger = setup_logger()

def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器"""
    return setup_logger(name)
