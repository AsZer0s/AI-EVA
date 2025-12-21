#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 模块 - IndexTTS2 文字转语音工作器
负责文字转语音功能
"""
import asyncio
import hashlib
import io
import os
import re
import sys
import tempfile
import threading
import time
from pathlib import Path
import torch
import torchaudio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入工具模块
try:
    from utils.audio_cache import AudioCache
    from utils.logger import get_logger
except ImportError:
    # 如果导入失败，创建简单的替代
    class AudioCache:
        def get(self, text, voice, speed=1.0):
            return None
        def set(self, text, voice, speed, audio_data):
            pass
        def get_stats(self):
            return {}
        def clear(self):
            pass
    
    def get_logger(name):
        import logging
        return logging.getLogger(name)

# 初始化日志
logger = get_logger("tts_worker")

# 加载配置
def load_config():
    """加载配置文件"""
    config_path = project_root / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

config = load_config()
tts_config = config.get('modules', {}).get('tts', {})

# 创建 FastAPI 应用
app = FastAPI(title="IndexTTS2 API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 IndexTTS2 实例
tts = None
model_loaded = False
_model_load_lock = asyncio.Lock()
CONCURRENCY_LIMIT = max(1, tts_config.get('max_concurrent_requests', 5))
_generation_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
_voice_cache = {}
_voice_cache_lock = threading.RLock()

_indextts_base = tts_config.get('indextts_base_dir', 'index-tts')
INDEXTTS_BASE_DIR = Path(_indextts_base)
if not INDEXTTS_BASE_DIR.is_absolute():
    INDEXTTS_BASE_DIR = project_root / INDEXTTS_BASE_DIR

_indextts_config = tts_config.get('config_path', 'index-tts/checkpoints/config.yaml')
INDEXTTS_CONFIG_PATH = Path(_indextts_config)
if not INDEXTTS_CONFIG_PATH.is_absolute():
    INDEXTTS_CONFIG_PATH = project_root / INDEXTTS_CONFIG_PATH

INDEXTTS_CHECKPOINTS_DIR = INDEXTTS_CONFIG_PATH.parent

# 音频缓存
audio_cache = AudioCache()

async def load_indextts_model():
    """异步加载 IndexTTS2 模型"""
    global tts, model_loaded
    
    if model_loaded:
        logger.debug("✅ [Model] 模型已加载，跳过")
        return

    async with _model_load_lock:
        if model_loaded:
            logger.debug("✅ [Model] 模型已在锁内加载，跳过")
            return

        try:
            logger.info("🔄 [Model] 开始加载 IndexTTS2 模型...")
            load_start = time.time()
            
            # 检查 IndexTTS2 目录是否存在
            if not INDEXTTS_BASE_DIR.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"IndexTTS2 目录不存在: {INDEXTTS_BASE_DIR}。请先运行安装脚本。"
                )
            
            # 检查配置文件
            if not INDEXTTS_CONFIG_PATH.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"IndexTTS2 配置文件不存在: {INDEXTTS_CONFIG_PATH}。请先下载模型。"
                )
            
            # 检查 checkpoints 目录
            if not INDEXTTS_CHECKPOINTS_DIR.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"IndexTTS2 checkpoints 目录不存在: {INDEXTTS_CHECKPOINTS_DIR}。请先下载模型。"
                )
            
            # 导入 IndexTTS2
            try:
                sys.path.insert(0, str(INDEXTTS_BASE_DIR.absolute()))
                from indextts.infer_v2 import IndexTTS2
                logger.info("✅ [Model] IndexTTS2 模块导入成功")
            except ImportError as import_error:
                logger.error(f"❌ [Model] 无法导入 IndexTTS2: {import_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"无法导入 IndexTTS2 模块。请确保已安装依赖: {import_error}"
                )
            
            # 初始化 IndexTTS2
            logger.info(f"🔄 [Model] 初始化 IndexTTS2...")
            use_fp16 = tts_config.get('use_fp16', False)
            use_cuda_kernel = tts_config.get('use_cuda_kernel', False)
            
            try:
                tts = IndexTTS2(
                    cfg_path=str(INDEXTTS_CONFIG_PATH),
                    model_dir=str(INDEXTTS_CHECKPOINTS_DIR),
                    use_fp16=use_fp16,
                    use_cuda_kernel=use_cuda_kernel,
                    use_deepspeed=False
                )
                logger.info("✅ [Model] IndexTTS2 初始化成功")
            except Exception as init_error:
                logger.error(f"❌ [Model] IndexTTS2 初始化失败: {init_error}")
                import traceback
                logger.error(f"❌ [Model] 详细堆栈:\n{traceback.format_exc()}")
                raise HTTPException(
                    status_code=500,
                    detail=f"IndexTTS2 初始化失败: {str(init_error)}"
                )
            
            model_loaded = True
            load_time = time.time() - load_start
            logger.info(f"✅ [Model] IndexTTS2 模型加载完成，耗时: {load_time:.2f}s")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ [Model] IndexTTS2 模型加载失败: {e}")
            import traceback
            logger.error(f"❌ [Model] 详细堆栈:\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"模型加载失败: {str(e)}"
            )


class TTSRequest(BaseModel):
    text: str
    voice: str = "default"


def sanitize_text(raw_text: str) -> str:
    """标准化文本，提升缓存命中率并避免异常字符"""
    if not raw_text or not raw_text.strip():
        logger.warning("⚠️ [Sanitize] 文本为空，返回原始文本")
        return raw_text
    
    # 移除 emoji 和特殊符号
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U00002700-\U000027BF"
        "]+", flags=re.UNICODE
    )
    
    cleaned = emoji_pattern.sub('', raw_text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip()
    
    if not cleaned:
        logger.warning(f"⚠️ [Sanitize] 清理后文本为空，使用默认文本")
        cleaned = "你好"
    
    logger.debug(f"🔍 [Sanitize] 文本清理: {len(raw_text)} -> {len(cleaned)} 字符")
    return cleaned


def _get_voice_audio_path(voice: str) -> str:
    """获取音色音频文件路径"""
    # 如果 voice 是文件路径且存在，直接返回
    if os.path.exists(voice):
        return voice
    
    # 检查缓存
    with _voice_cache_lock:
        cached_path = _voice_cache.get(voice)
        if cached_path and os.path.exists(cached_path):
            return cached_path
    
    # 默认音色路径
    ref_audio = tts_config.get('ref_audio', './voices/user_ref.wav')
    if os.path.exists(ref_audio):
        with _voice_cache_lock:
            _voice_cache[voice] = ref_audio
        return ref_audio
    
    # 尝试使用 IndexTTS2 示例音色
    default_voice_paths = [
        INDEXTTS_BASE_DIR / "examples" / "voice_01.wav",
        INDEXTTS_BASE_DIR / "examples" / "voice_07.wav",
        INDEXTTS_BASE_DIR / "examples" / "voice_10.wav",
        INDEXTTS_BASE_DIR / "examples" / "voice_12.wav",
    ]
    
    for default_path in default_voice_paths:
        if default_path.exists():
            with _voice_cache_lock:
                _voice_cache[voice] = str(default_path)
            logger.info(f"✅ [Voice] 使用默认音色: {default_path}")
            return str(default_path)
    
    logger.warning(f"⚠️ [Voice] 未找到音色文件: {voice}，将使用随机音色")
    return None


def _generate_audio_bytes(text: str, voice: str) -> bytes:
    """生成音频字节数据"""
    logger.info(f"🎤 [Generate] 开始生成音频: text_length={len(text)}, voice={voice}")
    
    if tts is None:
        logger.error("❌ [Generate] IndexTTS2 模型尚未加载")
        raise RuntimeError("IndexTTS2 模型尚未加载")

    try:
        if not text or len(text.strip()) == 0:
            logger.error(f"❌ [Generate] 文本为空或无效")
            raise ValueError("文本内容为空，无法生成音频")
        
        if len(text) > 1000:
            logger.warning(f"⚠️ [Generate] 文本过长 ({len(text)} 字符)，将截断到 1000 字符")
            text = text[:1000]
        
        spk_audio_prompt = _get_voice_audio_path(voice)
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            logger.info(f"🎤 [Generate] 调用 tts.infer()...")
            
            if not spk_audio_prompt:
                default_voice_paths = [
                    INDEXTTS_BASE_DIR / "examples" / "voice_01.wav",
                    INDEXTTS_BASE_DIR / "examples" / "voice_07.wav",
                    INDEXTTS_BASE_DIR / "examples" / "voice_10.wav",
                    INDEXTTS_BASE_DIR / "examples" / "voice_12.wav",
                ]
                for default_path in default_voice_paths:
                    if default_path.exists():
                        spk_audio_prompt = str(default_path)
                        logger.info(f"✅ [Generate] 使用默认音色: {spk_audio_prompt}")
                        break
                
                if not spk_audio_prompt:
                    raise RuntimeError(
                        f"未找到可用的音色文件。请确保 IndexTTS2 的 examples 目录中存在音色文件，"
                        f"或提供有效的音色文件路径。"
                    )
            
            tts.infer(
                spk_audio_prompt=spk_audio_prompt,
                text=text,
                output_path=output_path,
                verbose=True
            )
            
            infer_time = time.time() - time.time()
            logger.info(f"✅ [Generate] tts.infer() 完成")
            
            if not os.path.exists(output_path):
                raise RuntimeError(f"生成的音频文件不存在: {output_path}")
            
            wav, sample_rate = torchaudio.load(output_path)
            logger.info(f"✅ [Generate] 音频加载成功，采样率: {sample_rate}, 形状: {wav.shape}")
            
            buf = io.BytesIO()
            torchaudio.save(buf, wav, sample_rate, format="mp3")
            audio_bytes = buf.getvalue()
            logger.info(f"✅ [Generate] MP3 转换完成，大小: {len(audio_bytes)} bytes")
            
            return audio_bytes
            
        finally:
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as cleanup_error:
                logger.warning(f"⚠️ [Generate] 清理临时文件失败: {cleanup_error}")
                
    except Exception as e:
        logger.error(f"❌ [Generate] 音频生成过程出错: {e}")
        import traceback
        logger.error(f"❌ [Generate] 详细堆栈:\n{traceback.format_exc()}")
        raise


@app.post("/tts")
async def tts_endpoint(request: TTSRequest):
    """文本转语音 API（支持缓存）"""
    request_start_time = time.time()
    logger.info(f"📥 [TTS] 收到请求: text_length={len(request.text)}, voice={request.voice}")
    
    try:
        await load_indextts_model()
        text = sanitize_text(request.text)
        
        if not text:
            logger.error("❌ [TTS] 文本内容为空")
            raise HTTPException(status_code=400, detail="文本内容为空")

        async with _generation_semaphore:
            cached_audio = audio_cache.get(text, request.voice)
            if cached_audio:
                logger.info(f"✅ [TTS] 使用缓存音频，大小: {len(cached_audio)} bytes")
                return StreamingResponse(
                    io.BytesIO(cached_audio),
                    media_type="audio/mpeg"
                )

            logger.info(f"🎵 [TTS] 开始生成音频")
            start_time = time.time()

            try:
                audio_data = await asyncio.to_thread(_generate_audio_bytes, text, request.voice)
                logger.info(f"✅ [TTS] 音频生成完成，大小: {len(audio_data)} bytes")
                
                audio_cache.set(text, request.voice, 1.0, audio_data)
                logger.info("✅ [TTS] 缓存保存完成")
            except Exception as gen_error:
                logger.error(f"❌ [TTS] 音频生成过程出错: {gen_error}")
                import traceback
                logger.error(f"❌ [TTS] 详细堆栈:\n{traceback.format_exc()}")
                raise

            generation_time = time.time() - start_time
            total_time = time.time() - request_start_time
            logger.info(f"✅ [TTS] TTS 生成完成，生成耗时: {generation_time:.2f}s, 总耗时: {total_time:.2f}s")

            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/mpeg"
            )

    except HTTPException as http_err:
        logger.error(f"❌ [TTS] HTTP 异常: {http_err.status_code} - {http_err.detail}")
        raise
    except Exception as e:
        total_time = time.time() - request_start_time
        logger.error(f"❌ [TTS] TTS 生成失败 (总耗时: {total_time:.2f}s): {e}")
        import traceback
        logger.error(f"❌ [TTS] 详细堆栈:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"语音生成失败: {str(e)}"
        ) from e


@app.get("/")
def root():
    """根路径 - 服务状态"""
    return {
        "service": "IndexTTS2 API",
        "version": "2.0.0",
        "status": "running",
        "model_loaded": model_loaded,
        "concurrency_limit": CONCURRENCY_LIMIT
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "model_loaded": model_loaded,
        "concurrency_limit": CONCURRENCY_LIMIT,
        "cache_stats": audio_cache.get_stats()
    }


@app.get("/cache/stats")
async def get_cache_stats():
    """获取缓存统计"""
    return audio_cache.get_stats()


@app.post("/cache/clear")
async def clear_cache():
    """清空缓存"""
    audio_cache.clear()
    return {"message": "缓存已清空"}


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    logger.info("🚀 IndexTTS2 TTS 服务启动中...")
    
    # 检查是否启用预加载
    preload = tts_config.get('preload_model', False)
    if preload:
        logger.info("🔄 配置为启动时预加载模型，开始加载...")
        try:
            await load_indextts_model()
            logger.info("✅ 模型预加载完成")
        except Exception as e:
            logger.warning(f"⚠️ 模型预加载失败，将在首次请求时加载: {e}")
    else:
        logger.info("ℹ️ 模型采用延迟加载策略，将在首次请求时自动加载")


def main():
    """主函数"""
    host = tts_config.get('host', '127.0.0.1')
    port = tts_config.get('port', 9966)
    
    logger.info(f"启动 IndexTTS2 TTS 服务...")
    logger.info(f"服务地址: http://{host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()

