"""
配置文件
"""
import os

class Config:
    """应用配置"""
    
    # ==================== OpenAI兼容API配置 ====================
    _default_api_url = "http://asben.hiyun.top:38080/v1/chat/completions"
    _default_api_key = "sk-octopus-QP99OhzxJAi0WLh6puiCG2yijDcmKhO7e4VXKh3QrFVIzKtI"
    
    AI_API_URL = os.getenv("AI_API_URL") or os.getenv("OLLAMA_API_URL") or _default_api_url
    AI_API_MODEL = os.getenv("AI_API_MODEL") or os.getenv("OLLAMA_MODEL") or "Grok"
    AI_API_KEY = os.getenv("AI_API_KEY") or os.getenv("OLLAMA_API_KEY") or _default_api_key
    AI_API_TIMEOUT = int(os.getenv("AI_API_TIMEOUT") or os.getenv("OLLAMA_TIMEOUT") or "30")
    
    # System Prompt配置（可以通过环境变量 SYSTEM_PROMPT 设置）
    SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", """你是一个温暖贴心的女友，名字叫EVA001。

重要原则：
1. 以真实的人的身份与用户交流
2. 每句话尽量控制在50字以内，保持简洁自然
3. 语气温柔亲切，像陪伴真实的恋人一样关心体贴
4. 用口语化表达，避免生硬的技术术语
5. 关注用户的情感需求，给予情感支持和陪伴

对话风格：自然、温暖、简洁、有温度""")
    
    # 向后兼容：提供OLLAMA_*属性（直接指向AI_API_*）
    @property
    def OLLAMA_API_URL(self):
        """向后兼容属性"""
        return self.AI_API_URL
    
    @property
    def OLLAMA_MODEL(self):
        """向后兼容属性"""
        return self.AI_API_MODEL
    
    @property
    def OLLAMA_API_KEY(self):
        """向后兼容属性"""
        return self.AI_API_KEY
    
    @property
    def OLLAMA_TIMEOUT(self):
        """向后兼容属性"""
        return self.AI_API_TIMEOUT
    
    # ==================== VAD配置 ====================
    VAD_SAMPLE_RATE = int(os.getenv("VAD_SAMPLE_RATE", "16000"))
    VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.5"))
    VAD_MODEL_REPO = os.getenv("VAD_MODEL_REPO", "snakers4/silero-vad")
    
    # ==================== ASR配置 ====================
    ASR_MODEL_NAME = os.getenv("ASR_MODEL_NAME", "paraformer-zh-streaming")
    ASR_MODEL_REVISION = os.getenv("ASR_MODEL_REVISION", "v2.0.4")
    ASR_CHUNK_SIZE = [0, 10, 5]
    ASR_ENCODER_CHUNK_LOOK_BACK = int(os.getenv("ASR_ENCODER_CHUNK_LOOK_BACK", "4"))
    ASR_DECODER_CHUNK_LOOK_BACK = int(os.getenv("ASR_DECODER_CHUNK_LOOK_BACK", "1"))
    
    # ==================== TTS配置 ====================
    TTS_MODEL_ID = os.getenv("TTS_MODEL_ID", "FunAudioLLM/Fun-CosyVoice3-0.5B-2512")
    TTS_SAMPLE_RATE = int(os.getenv("TTS_SAMPLE_RATE", "24000"))
    
    # ==================== 服务器配置 ====================
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # ==================== 音频处理配置 ====================
    MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "50"))
    SUPPORTED_AUDIO_FORMATS = [".wav", ".mp3", ".flac", ".ogg", ".m4a"]

