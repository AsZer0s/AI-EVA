#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ASR 模块 - SenseVoice 语音识别工作器
负责语音转文字功能
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, List
import torch
import torchaudio
import numpy as np
from io import BytesIO
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import yaml

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        # 如果已经是 TextIOWrapper，跳过
        pass

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 添加 SenseVoice 目录到路径（确保能正确导入 utils）
sensevoice_dir = project_root / "SenseVoice"
if sensevoice_dir.exists():
    sys.path.insert(0, str(sensevoice_dir))

# 导入 SenseVoice 相关模块
try:
    # 保存原始工作目录
    original_cwd = os.getcwd()
    
    # 临时切换到 SenseVoice 目录以便正确导入 utils
    if sensevoice_dir.exists():
        os.chdir(str(sensevoice_dir))
    
    # 导入模块
    from model import SenseVoiceSmall
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    
    # 恢复工作目录
    os.chdir(original_cwd)
    
    SENSEVOICE_AVAILABLE = True
except ImportError as e:
    SENSEVOICE_AVAILABLE = False
    # 恢复工作目录
    try:
        os.chdir(original_cwd)
    except:
        pass
    import logging
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger("asr_worker")
    logger.warning(f"SenseVoice 模块未找到，语音识别功能将不可用: {e}")
except Exception as e:
    SENSEVOICE_AVAILABLE = False
    # 恢复工作目录
    try:
        os.chdir(original_cwd)
    except:
        pass
    import logging
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger("asr_worker")
    logger.error(f"导入 SenseVoice 模块时出错: {e}")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger("asr_worker")

# 加载配置
def load_config():
    """加载配置文件"""
    config_path = project_root / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

config = load_config()
asr_config = config.get('modules', {}).get('asr', {})

# 目标采样率
TARGET_FS = asr_config.get('target_sample_rate', 16000)

# 创建 FastAPI 应用
app = FastAPI(
    title="SenseVoice ASR API",
    description="AI-EVA 语音识别服务",
    version="2.0.0"
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

class SenseVoiceWorker:
    """SenseVoice 工作器"""
    
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
        
        if self.is_loaded:
            logger.debug("✅ 模型已加载，跳过")
            return
        
        try:
            logger.info("🔄 正在加载 SenseVoice 模型...")
            
            # 获取设备配置
            device_config = asr_config.get('device', 'cuda:0')
            use_gpu = config.get('performance', {}).get('use_gpu', True)
            
            # 自动检测可用设备
            if use_gpu and torch.cuda.is_available():
                self.device = device_config
                logger.info(f"✅ 使用 GPU 设备: {self.device}")
            else:
                self.device = "cpu"
                if use_gpu and not torch.cuda.is_available():
                    logger.warning("⚠️  CUDA 不可用，降级到 CPU")
                else:
                    logger.info("使用 CPU 设备")
            
            # 加载模型
            model_path = asr_config.get('model_path', 'iic/SenseVoiceSmall')
            self.model, kwargs = SenseVoiceSmall.from_pretrained(
                model=model_path, 
                device=self.device
            )
            self.model.eval()
            
            self.is_loaded = True
            logger.info("✅ SenseVoice 模型加载完成")
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"语音识别失败: {str(e)}"
            )

# 创建工作器实例
worker = SenseVoiceWorker()

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    logger.info("🚀 SenseVoice ASR 服务启动中...")
    
    # 预加载模型（如果启用）
    if config.get('performance', {}).get('use_gpu', True):
        try:
            await worker.load_model()
            logger.info("✅ 模型预加载完成")
        except Exception as e:
            logger.warning(f"模型预加载失败，将在首次请求时加载: {e}")

@app.get("/")
async def root():
    """根路径 - 服务状态"""
    return {
        "service": "SenseVoice ASR API",
        "version": "2.0.0",
        "status": "running",
        "model_loaded": worker.is_loaded,
        "device": worker.device if worker.device else "unknown"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "model_available": SENSEVOICE_AVAILABLE,
        "model_loaded": worker.is_loaded
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
        text = await worker.transcribe_audio(audio_data, language)
        
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
        import traceback
        logger.error(traceback.format_exc())
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
    """
    try:
        results = []
        
        for i, file in enumerate(files):
            try:
                audio_data = await file.read()
                text = await worker.transcribe_audio(audio_data, language)
                
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
        "loaded": worker.is_loaded,
        "device": worker.device,
        "supported_languages": ["auto", "zh", "en", "yue", "ja", "ko"],
        "supported_formats": ["wav", "mp3", "m4a", "flac"]
    }

def main():
    """主函数"""
    host = asr_config.get('host', '127.0.0.1')
    port = asr_config.get('port', 50000)
    
    logger.info(f"启动 SenseVoice ASR 服务...")
    logger.info(f"服务地址: http://{host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()

