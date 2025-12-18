import asyncio
import hashlib
import io
import os
import re
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

from config import config
from utils.audio_cache import audio_cache
from utils.logger import get_logger

# 初始化日志
logger = get_logger("indextts")

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
CONCURRENCY_LIMIT = max(1, config.MAX_CONCURRENT_REQUESTS)
_generation_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
_voice_cache = {}  # 存储音色文件路径
_voice_cache_lock = threading.RLock()

# IndexTTS2 配置路径
INDEXTTS_BASE_DIR = Path("index-tts")
INDEXTTS_CHECKPOINTS_DIR = INDEXTTS_BASE_DIR / "checkpoints"
INDEXTTS_CONFIG_PATH = INDEXTTS_CHECKPOINTS_DIR / "config.yaml"


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
                # 添加 index-tts 目录到 Python 路径
                import sys
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
            logger.info(f"🔄 [Model] 配置文件: {INDEXTTS_CONFIG_PATH}")
            logger.info(f"🔄 [Model] 模型目录: {INDEXTTS_CHECKPOINTS_DIR}")
            
            try:
                tts = IndexTTS2(
                    cfg_path=str(INDEXTTS_CONFIG_PATH),
                    model_dir=str(INDEXTTS_CHECKPOINTS_DIR),
                    use_fp16=False,
                    use_cuda_kernel=False,
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
            logger.error(f"❌ [Model] 错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"❌ [Model] 详细堆栈:\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"模型加载失败: {str(e)}"
            )


class TTSRequest(BaseModel):
    text: str
    voice: str = "default"  # 默认音色，可以是音频文件路径或标识符


def sanitize_text(raw_text: str) -> str:
    """标准化文本，提升缓存命中率并避免异常字符"""
    if not raw_text or not raw_text.strip():
        logger.warning("⚠️ [Sanitize] 文本为空，返回原始文本")
        return raw_text
    
    # 移除 emoji 和特殊符号
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
        "\U00002600-\U000026FF"  # miscellaneous symbols
        "\U00002700-\U000027BF"  # dingbats
        "]+", flags=re.UNICODE
    )
    
    # 移除 emoji
    cleaned = emoji_pattern.sub('', raw_text)
    
    # 规范化空白字符（多个空格/换行合并为单个空格）
    cleaned = re.sub(r"\s+", " ", cleaned)
    
    # 去除首尾空白
    cleaned = cleaned.strip()
    
    # 如果清理后为空，返回一个默认文本
    if not cleaned:
        logger.warning(f"⚠️ [Sanitize] 清理后文本为空，使用默认文本")
        cleaned = "你好"  # 默认文本
    
    logger.debug(f"🔍 [Sanitize] 文本清理: {len(raw_text)} -> {len(cleaned)} 字符")
    if len(raw_text) != len(cleaned):
        logger.debug(f"🔍 [Sanitize] 移除了 {len(raw_text) - len(cleaned)} 个特殊字符")
    
    return cleaned


def _get_voice_audio_path(voice: str) -> str:
    """
    获取音色音频文件路径
    
    Args:
        voice: 音色标识符或文件路径
        
    Returns:
        音频文件路径
    """
    # 如果 voice 是文件路径且存在，直接返回
    if os.path.exists(voice):
        return voice
    
    # 检查缓存
    with _voice_cache_lock:
        cached_path = _voice_cache.get(voice)
        if cached_path and os.path.exists(cached_path):
            return cached_path
    
    # 默认音色路径（如果存在）
    default_voice_paths = [
        INDEXTTS_BASE_DIR / "examples" / "voice_01.wav",
        INDEXTTS_BASE_DIR / "examples" / "voice_07.wav",
        INDEXTTS_BASE_DIR / "examples" / "voice_10.wav",
        INDEXTTS_BASE_DIR / "examples" / "voice_12.wav",
    ]
    
    # 尝试找到第一个存在的默认音色文件
    for default_path in default_voice_paths:
        if default_path.exists():
            with _voice_cache_lock:
                _voice_cache[voice] = str(default_path)
            logger.info(f"✅ [Voice] 使用默认音色: {default_path}")
            return str(default_path)
    
    # 如果没有找到默认音色，返回 None（将使用随机音色）
    logger.warning(f"⚠️ [Voice] 未找到音色文件: {voice}，将使用随机音色")
    return None


def _generate_audio_bytes(text: str, voice: str) -> bytes:
    """生成音频字节数据"""
    logger.info(f"🎤 [Generate] 开始生成音频: text_length={len(text)}, voice={voice}")
    
    if tts is None:
        logger.error("❌ [Generate] IndexTTS2 模型尚未加载")
        raise RuntimeError("IndexTTS2 模型尚未加载")

    try:
        # 验证文本长度
        if not text or len(text.strip()) == 0:
            logger.error(f"❌ [Generate] 文本为空或无效")
            raise ValueError("文本内容为空，无法生成音频")
        
        if len(text) > 1000:
            logger.warning(f"⚠️ [Generate] 文本过长 ({len(text)} 字符)，将截断到 1000 字符")
            text = text[:1000]
        
        # 获取音色音频路径
        spk_audio_prompt = _get_voice_audio_path(voice)
        
        # 创建临时文件保存生成的音频
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            logger.info(f"🎤 [Generate] 调用 tts.infer()... (文本长度: {len(text)})")
            logger.debug(f"🎤 [Generate] 文本内容: {text[:100]}...")
            logger.debug(f"🎤 [Generate] 音色文件: {spk_audio_prompt}")
            
            infer_start = time.time()
            
            # 调用 IndexTTS2 进行推理
            # 确保总是有一个有效的音色文件
            if not spk_audio_prompt:
                # 如果没有找到音色文件，尝试使用默认音色
                logger.warning("⚠️ [Generate] 未找到指定音色文件，尝试使用默认音色")
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
                
                # 如果仍然没有找到，抛出错误
                if not spk_audio_prompt:
                    raise RuntimeError(
                        f"未找到可用的音色文件。请确保 IndexTTS2 的 examples 目录中存在音色文件，"
                        f"或提供有效的音色文件路径。"
                    )
            
            # 使用指定的音色文件进行推理
            tts.infer(
                spk_audio_prompt=spk_audio_prompt,
                text=text,
                output_path=output_path,
                verbose=True
            )
            
            infer_time = time.time() - infer_start
            logger.info(f"✅ [Generate] tts.infer() 完成，耗时: {infer_time:.2f}s")
            
            # 读取生成的音频文件
            if not os.path.exists(output_path):
                raise RuntimeError(f"生成的音频文件不存在: {output_path}")
            
            logger.info(f"🎤 [Generate] 读取生成的音频文件...")
            wav, sample_rate = torchaudio.load(output_path)
            logger.info(f"✅ [Generate] 音频加载成功，采样率: {sample_rate}, 形状: {wav.shape}")
            
            # 转换为 MP3 格式
            logger.info(f"🎤 [Generate] 转换为 MP3 格式...")
            buf = io.BytesIO()
            torchaudio.save(buf, wav, sample_rate, format="mp3")
            audio_bytes = buf.getvalue()
            logger.info(f"✅ [Generate] MP3 转换完成，大小: {len(audio_bytes)} bytes")
            
            return audio_bytes
            
        finally:
            # 清理临时文件
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as cleanup_error:
                logger.warning(f"⚠️ [Generate] 清理临时文件失败: {cleanup_error}")
                
    except Exception as e:
        logger.error(f"❌ [Generate] 音频生成过程出错: {e}")
        logger.error(f"❌ [Generate] 错误类型: {type(e).__name__}")
        import traceback
        logger.error(f"❌ [Generate] 详细堆栈:\n{traceback.format_exc()}")
        raise


@app.post("/tts")
async def tts_endpoint(request: TTSRequest):
    """文本转语音 API（支持缓存）"""
    request_start_time = time.time()
    logger.info(f"📥 [TTS] 收到请求: text_length={len(request.text)}, voice={request.voice}")
    logger.debug(f"📥 [TTS] 请求文本预览: {request.text[:100]}...")
    
    try:
        logger.info("🔄 [TTS] 检查模型加载状态...")
        await load_indextts_model()
        logger.info("✅ [TTS] 模型已加载")

        logger.info(f"🧹 [TTS] 清理文本: 原始长度={len(request.text)}")
        text = sanitize_text(request.text)
        logger.info(f"🧹 [TTS] 清理后长度={len(text)}")
        
        if not text:
            logger.error("❌ [TTS] 文本内容为空")
            raise HTTPException(status_code=400, detail="文本内容为空")

        logger.info(f"🔒 [TTS] 获取信号量 (并发限制: {CONCURRENCY_LIMIT})...")
        async with _generation_semaphore:
            logger.info("✅ [TTS] 已获取信号量，开始处理")
            
            logger.info(f"🔍 [TTS] 检查缓存: text_hash={hashlib.md5(text.encode()).hexdigest()[:8]}, voice={request.voice}")
            cached_audio = audio_cache.get(text, request.voice)
            if cached_audio:
                logger.info(f"✅ [TTS] 使用缓存音频，大小: {len(cached_audio)} bytes")
                return StreamingResponse(
                    io.BytesIO(cached_audio),
                    media_type="audio/mpeg"
                )

            logger.info(f"🎵 [TTS] 开始生成音频: text={text[:50]}..., voice={request.voice}")
            start_time = time.time()

            try:
                logger.info("🔄 [TTS] 调用 _generate_audio_bytes...")
                audio_data = await asyncio.to_thread(_generate_audio_bytes, text, request.voice)
                logger.info(f"✅ [TTS] 音频生成完成，大小: {len(audio_data)} bytes")
                
                logger.info("💾 [TTS] 保存到缓存...")
                audio_cache.set(text, request.voice, 1.0, audio_data)
                logger.info("✅ [TTS] 缓存保存完成")
            except Exception as gen_error:
                logger.error(f"❌ [TTS] 音频生成过程出错: {gen_error}")
                logger.error(f"❌ [TTS] 错误堆栈: {gen_error.__class__.__name__}: {str(gen_error)}")
                import traceback
                logger.error(f"❌ [TTS] 详细堆栈:\n{traceback.format_exc()}")
                raise

            generation_time = time.time() - start_time
            total_time = time.time() - request_start_time
            logger.info(f"✅ [TTS] TTS 生成完成，生成耗时: {generation_time:.2f}s, 总耗时: {total_time:.2f}s")

            logger.info("📤 [TTS] 返回音频流...")
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
        logger.error(f"❌ [TTS] 错误类型: {type(e).__name__}")
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


@app.post("/tts/batch")
async def batch_tts(requests: list[TTSRequest]):
    """批量 TTS 生成"""
    try:
        await load_indextts_model()
        
        results = []
        for i, request in enumerate(requests):
            try:
                text = sanitize_text(request.text)
                if not text:
                    results.append({
                        "index": i,
                        "success": False,
                        "error": "文本内容为空"
                    })
                    continue

                cached_audio = audio_cache.get(text, request.voice)
                if cached_audio:
                    results.append({
                        "index": i,
                        "success": True,
                        "cached": True,
                        "audio_size": len(cached_audio)
                    })
                else:
                    # 生成音频（简化版，实际需要完整处理）
                    results.append({
                        "index": i,
                        "success": True,
                        "cached": False,
                        "message": "需要单独生成"
                    })
            except Exception as e:
                results.append({
                    "index": i,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "results": results,
            "total": len(requests)
        }
        
    except Exception as e:
        logger.error(f"批量 TTS 失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"批量处理失败: {str(e)}"
        )

