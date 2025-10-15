"""
SenseVoice API 简化版 - 专为 AI-EVA Demo 优化
支持浏览器音频流上传和实时语音识别
"""
import os
import asyncio
import logging
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import torch
import torchaudio
import numpy as np
from io import BytesIO
import tempfile
from pathlib import Path

# 导入 SenseVoice 相关模块
try:
    from SenseVoice.model import SenseVoiceSmall
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    SENSEVOICE_AVAILABLE = True
except ImportError:
    SENSEVOICE_AVAILABLE = False
    print("⚠️  SenseVoice 模块未找到，语音识别功能将不可用")

from config import config
from utils.logger import get_logger

# 初始化日志
logger = get_logger("sensevoice")

# 创建 FastAPI 应用
app = FastAPI(
    title="SenseVoice API",
    description="AI-EVA Demo 语音识别服务",
    version="1.0.0"
)

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
model = None
device = None

# 目标采样率
TARGET_FS = 16000

class SenseVoiceAPI:
    """SenseVoice API 管理器"""
    
    def __init__(self):
        self.model = None
        self.device = None
        self.is_loaded = False
        
    async def load_model(self):
        """异步加载模型"""
        if not SENSEVOICE_AVAILABLE:
            raise HTTPException(
                status_code=500, 
                detail="SenseVoice 模块未安装，请检查依赖"
            )
        
        try:
            logger.info("正在加载 SenseVoice 模型...")
            
            # 自动检测可用设备
            import torch
            if config.USE_GPU and torch.cuda.is_available():
                self.device = config.SENSEVOICE_DEVICE
                logger.info(f"✅ 使用 GPU 设备: {self.device}")
            else:
                self.device = "cpu"
                if config.USE_GPU and not torch.cuda.is_available():
                    logger.warning("⚠️  CUDA 不可用，降级到 CPU")
                else:
                    logger.info(f"使用 CPU 设备")
            
            # 加载模型
            model_dir = "iic/SenseVoiceSmall"
            self.model, kwargs = SenseVoiceSmall.from_pretrained(
                model=model_dir, 
                device=self.device
            )
            self.model.eval()
            
            self.is_loaded = True
            logger.info("✅ SenseVoice 模型加载完成")
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"模型加载失败: {str(e)}"
            )
    
    async def transcribe_audio(self, audio_data: bytes, language: str = "auto") -> str:
        """转录音频为文本"""
        if not self.is_loaded:
            await self.load_model()
        
        try:
            # 将字节数据转换为音频张量
            audio_io = BytesIO(audio_data)
            waveform, sample_rate = torchaudio.load(audio_io)
            
            # 转换为单声道
            if waveform.shape[0] > 1:
                waveform = waveform.mean(0, keepdim=True)
            
            # 重采样到目标采样率
            if sample_rate != TARGET_FS:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate, 
                    new_freq=TARGET_FS
                )
                waveform = resampler(waveform)
            
            # 转换为 numpy 数组
            audio_array = waveform.squeeze().numpy()
            
            # 推理
            result = self.model.inference(
                data_in=[audio_array],
                language=language,
                use_itn=False,
                ban_emo_unk=False,
                key=["audio"],
                fs=TARGET_FS
            )
            
            if result and len(result) > 0 and len(result[0]) > 0:
                text = result[0][0]["text"]
                # 后处理
                text = rich_transcription_postprocess(text)
                return text.strip()
            else:
                return ""
                
        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"语音识别失败: {str(e)}"
            )

# 创建 API 实例
sensevoice_api = SenseVoiceAPI()

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    logger.info("🚀 SenseVoice API 启动中...")
    
    # 预加载模型（可选）
    if config.USE_GPU:
        try:
            await sensevoice_api.load_model()
            logger.info("✅ 模型预加载完成")
        except Exception as e:
            logger.warning(f"模型预加载失败，将在首次请求时加载: {e}")

@app.get("/")
async def root():
    """根路径 - 服务状态"""
    return {
        "service": "SenseVoice API",
        "version": "1.0.0",
        "status": "running",
        "model_loaded": sensevoice_api.is_loaded,
        "device": sensevoice_api.device if sensevoice_api.device else "unknown"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "model_available": SENSEVOICE_AVAILABLE,
        "model_loaded": sensevoice_api.is_loaded
    }

@app.post("/api/v1/asr")
async def speech_to_text(
    file: UploadFile = File(..., description="音频文件 (wav/mp3/m4a)"),
    language: str = Form(default="auto", description="语言代码 (auto/zh/en/yue/ja/ko)")
):
    """
    语音转文字 API
    
    Args:
        file: 音频文件
        language: 语言代码
        
    Returns:
        识别结果
    """
    try:
        # 检查文件类型
        if not file.content_type.startswith('audio/'):
            raise HTTPException(
                status_code=400,
                detail="文件类型错误，请上传音频文件"
            )
        
        # 读取音频数据
        audio_data = await file.read()
        if len(audio_data) == 0:
            raise HTTPException(
                status_code=400,
                detail="音频文件为空"
            )
        
        logger.info(f"收到音频文件: {file.filename}, 大小: {len(audio_data)} bytes")
        
        # 转录音频
        text = await sensevoice_api.transcribe_audio(audio_data, language)
        
        logger.info(f"识别结果: {text}")
        
        return {
            "success": True,
            "text": text,
            "language": language,
            "confidence": 1.0  # SenseVoice 不提供置信度
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API 错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"处理失败: {str(e)}"
        )

@app.post("/api/v1/asr/batch")
async def batch_speech_to_text(
    files: List[UploadFile] = File(..., description="音频文件列表"),
    language: str = Form(default="auto", description="语言代码")
):
    """
    批量语音转文字 API
    
    Args:
        files: 音频文件列表
        language: 语言代码
        
    Returns:
        批量识别结果
    """
    try:
        results = []
        
        for i, file in enumerate(files):
            try:
                audio_data = await file.read()
                text = await sensevoice_api.transcribe_audio(audio_data, language)
                
                results.append({
                    "index": i,
                    "filename": file.filename,
                    "text": text,
                    "success": True
                })
                
            except Exception as e:
                results.append({
                    "index": i,
                    "filename": file.filename,
                    "text": "",
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "results": results,
            "total": len(files)
        }
        
    except Exception as e:
        logger.error(f"批量处理错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"批量处理失败: {str(e)}"
        )

@app.get("/api/v1/models")
async def get_models():
    """获取可用模型信息"""
    return {
        "available": SENSEVOICE_AVAILABLE,
        "loaded": sensevoice_api.is_loaded,
        "device": sensevoice_api.device,
        "supported_languages": ["auto", "zh", "en", "yue", "ja", "ko"],
        "supported_formats": ["wav", "mp3", "m4a", "flac"]
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"启动 SenseVoice API 服务...")
    logger.info(f"服务地址: http://{config.SENSEVOICE_HOST}:{config.SENSEVOICE_PORT}")
    
    uvicorn.run(
        app,
        host=config.SENSEVOICE_HOST,
        port=config.SENSEVOICE_PORT,
        log_level=config.LOG_LEVEL.lower()
    )
