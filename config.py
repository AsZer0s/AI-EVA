"""
AI-EVA Demo 统一配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置类"""
    
    # ========== 基础配置 ==========
    PROJECT_NAME = "AI-EVA Demo"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # ========== 服务端口配置 ==========
    CHAT_TTS_PORT = int(os.getenv("CHAT_TTS_PORT", 9966))
    CHAT_TTS_HOST = os.getenv("CHAT_TTS_HOST", "127.0.0.1")
    
    SENSEVOICE_PORT = int(os.getenv("SENSEVOICE_PORT", 50000))
    SENSEVOICE_HOST = os.getenv("SENSEVOICE_HOST", "127.0.0.1")
    
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", 11434))
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
    
    FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 8000))
    FRONTEND_HOST = os.getenv("FRONTEND_HOST", "127.0.0.1")
    
    # ========== AI 模型配置 ==========
    DEFAULT_OLLAMA_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "gemma2:2b")
    DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "1031.pt")
    SENSEVOICE_DEVICE = os.getenv("SENSEVOICE_DEVICE", "cuda:0")
    
    # ========== 性能配置 ==========
    USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", 5))
    AUDIO_CACHE_SIZE = int(os.getenv("AUDIO_CACHE_SIZE", 100))  # MB
    
    # ========== 日志配置 ==========
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    SAVE_LOG_FILE = os.getenv("SAVE_LOG_FILE", "true").lower() == "true"
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/ai-eva.log")
    
    # ========== 路径配置 ==========
    BASE_DIR = Path(__file__).parent
    ASSETS_DIR = BASE_DIR / "asset"
    MODELS_DIR = BASE_DIR / "models"
    LOGS_DIR = BASE_DIR / "logs"
    
    # 确保必要目录存在
    LOGS_DIR.mkdir(exist_ok=True)
    
    # ========== API 端点配置 ==========
    @property
    def chat_tts_url(self):
        return f"http://{self.CHAT_TTS_HOST}:{self.CHAT_TTS_PORT}"
    
    @property
    def sensevoice_url(self):
        return f"http://{self.SENSEVOICE_HOST}:{self.SENSEVOICE_PORT}"
    
    @property
    def ollama_url(self):
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"
    
    @property
    def frontend_url(self):
        return f"http://{self.FRONTEND_HOST}:{self.FRONTEND_PORT}"

# 全局配置实例
config = Config()
