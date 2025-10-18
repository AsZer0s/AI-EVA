import asyncio
import hashlib
import io
import random
import re
import threading
import time

import ChatTTS
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
logger = get_logger("chattts")

app = FastAPI(title="ChatTTS API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 ChatTTS 实例
chat = None
model_loaded = False
_model_load_lock = asyncio.Lock()
CONCURRENCY_LIMIT = max(1, config.MAX_CONCURRENT_REQUESTS)
_generation_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
_speaker_cache = {}
_speaker_cache_lock = threading.RLock()
_random_lock = threading.Lock()


async def load_chattts_model():
    """异步加载 ChatTTS 模型"""
    global chat, model_loaded, girl_spk_emb
    
    if model_loaded:
        return

    async with _model_load_lock:
        if model_loaded:
            return

        try:
            logger.info("正在加载 ChatTTS 模型...")
            chat = ChatTTS.Chat()
            chat.load(compile=False)
            model_loaded = True

            # 初始化女孩音色
            init_girl_voice()

            logger.info("✅ ChatTTS 模型加载完成")
        except Exception as e:
            logger.error(f"❌ ChatTTS 模型加载失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"模型加载失败: {str(e)}"
            )

class TTSRequest(BaseModel):
    text: str
    voice: str = "1031.pt"  # 默认音色

GIRL_VOICE_SEED = [-4.741,0.419,-3.355,3.652,-1.682,-1.254,9.719,1.436,0.871,12.334,-0.175,-2.653,-3.132,0.525,1.573,-0.351,0.030,-3.154,0.935,-0.111,-6.306,-1.840,-0.818,9.773,-1.842,-3.433,-6.200,-4.311,1.162,1.023,11.552,2.769,-2.408,-1.494,-1.143,12.412,0.832,-1.203,5.425,-1.481,0.737,-1.487,6.381,5.821,0.599,6.186,5.379,-2.141,0.697,5.005,-4.944,0.840,-4.974,0.531,-0.679,2.237,4.360,0.438,2.029,1.647,-2.247,-1.716,6.338,1.922,0.731,-2.077,0.707,4.959,-1.969,5.641,2.392,-0.953,0.574,1.061,-9.335,0.658,-0.466,4.813,1.383,-0.907,5.417,-7.383,-3.272,-1.727,2.056,1.996,2.313,-0.492,3.373,0.844,-8.175,-0.558,0.735,-0.921,8.387,-7.800,0.775,1.629,-6.029,0.709,-2.767,-0.534,2.035,2.396,2.278,2.584,3.040,-6.845,7.649,-2.812,-1.958,8.794,2.551,3.977,0.076,-2.073,-4.160,0.806,3.798,-1.968,-4.690,5.702,-4.376,-2.396,1.368,-0.707,4.930,6.926,1.655,4.423,-1.482,-3.670,2.988,-3.296,0.767,3.306,1.623,-3.604,-2.182,-1.480,-2.661,-1.515,-2.546,3.455,-3.500,-3.163,-1.376,-12.772,1.931,4.422,6.434,-0.386,-0.704,-2.720,2.177,-0.666,12.417,4.228,0.823,-1.740,1.285,-2.173,-4.285,-6.220,2.479,3.135,-2.790,1.395,0.946,-0.052,9.148,-2.802,-5.604,-1.884,1.796,-0.391,-1.499,0.661,-2.691,0.680,0.848,3.765,0.092,7.978,3.023,2.450,-15.073,5.077,3.269,2.715,-0.862,2.187,13.048,-7.028,-1.602,-6.784,-3.143,-1.703,1.001,-2.883,0.818,-4.012,4.455,-1.545,-14.483,-1.008,-3.995,2.366,3.961,1.254,-0.458,-1.175,2.027,1.830,2.682,0.131,-1.839,-28.123,-1.482,16.475,2.328,-13.377,-0.980,9.557,0.870,-3.266,-3.214,3.577,2.059,1.676,-0.621,-6.370,-2.842,0.054,-0.059,-3.179,3.182,3.411,4.419,-1.688,-0.663,-5.189,-5.542,-1.146,2.676,2.224,-5.519,6.069,24.349,2.509,4.799,0.024,-2.849,-1.192,-16.989,1.845,6.337,-1.936,-0.585,1.691,-3.564,0.931,0.223,4.314,-2.609,0.544,-1.931,3.604,1.248,-0.852,2.991,-1.499,-3.836,1.774,-0.744,0.824,7.597,-1.538,-0.009,0.494,-2.253,-1.293,-0.475,-3.816,8.165,0.285,-3.348,3.599,-4.959,-1.498,-1.492,-0.867,0.421,-2.191,-1.627,6.027,3.667,-21.459,2.594,-2.997,5.076,0.197,-3.305,3.998,1.642,-6.221,3.177,-3.344,5.457,0.671,-2.765,-0.447,1.080,2.504,1.809,1.144,2.752,0.081,-3.700,0.215,-2.199,3.647,1.977,1.326,3.086,34.789,-1.017,-14.257,-3.121,-0.568,-0.316,11.455,0.625,-6.517,-0.244,-8.490,9.220,0.068,-2.253,-1.485,3.372,2.002,-3.357,3.394,1.879,16.467,-2.271,1.377,-0.611,-5.875,1.004,12.487,2.204,0.115,-4.908,-6.992,-1.821,0.211,0.540,1.239,-2.488,-0.411,2.132,2.130,0.984,-10.669,-7.456,0.624,-0.357,7.948,2.150,-2.052,3.772,-4.367,-11.910,-2.094,3.987,-1.565,0.618,1.152,1.308,-0.807,1.212,-4.476,0.024,-6.449,-0.236,5.085,1.265,-0.586,-2.313,3.642,-0.766,3.626,6.524,-1.686,-2.524,-0.985,-6.501,-2.558,0.487,-0.662,-1.734,0.275,-9.230,-3.785,3.031,1.264,15.340,2.094,1.997,0.408,9.130,0.578,-2.239,-1.493,11.034,2.201,6.757,3.432,-4.133,-3.668,2.099,-6.798,-0.102,2.348,6.910,17.910,-0.779,4.389,1.432,-0.649,5.115,-1.064,3.580,4.129,-4.289,-2.387,-0.327,-1.975,-0.892,5.327,-3.908,3.639,-8.247,-1.876,-10.866,2.139,-3.932,-0.031,-1.444,0.567,-5.543,-2.906,1.399,-0.107,-3.044,-4.660,-1.235,-1.011,9.577,2.294,6.615,-1.279,-2.159,-3.050,-6.493,-7.282,-8.546,5.393,2.050,10.068,3.494,8.810,2.820,3.063,0.603,1.965,2.896,-3.049,7.106,-0.224,-1.016,2.531,-0.902,1.436,-1.843,1.129,6.746,-2.184,0.801,-0.965,-7.555,-18.409,6.176,-3.706,2.261,4.158,-0.928,2.164,-3.248,-4.892,-0.008,-0.521,7.931,-10.693,4.320,-0.841,4.446,-1.591,-0.702,4.075,3.323,-3.406,-1.198,-5.518,-0.036,-2.247,-2.638,2.160,-9.644,-3.858,2.402,-2.640,1.683,-0.961,-3.076,0.226,5.106,0.712,0.669,2.539,-4.340,-0.892,0.732,0.775,-2.757,4.365,-2.368,5.368,0.342,-0.655,0.240,0.775,3.686,-4.008,16.296,4.973,1.851,4.747,0.652,-2.117,6.470,2.189,-8.467,3.236,3.745,-1.332,3.583,-2.504,5.596,-2.440,0.995,-2.267,-3.322,3.490,1.156,1.716,0.669,-3.640,-1.709,5.055,6.265,-3.963,2.863,14.129,5.180,-3.590,0.393,0.234,-3.978,6.946,-0.521,1.925,-1.497,-0.283,0.895,-3.969,5.338,-1.808,-3.578,2.699,2.728,-0.895,-2.175,-2.717,2.574,4.571,1.131,2.187,3.620,-0.388,-3.685,0.979,2.731,-2.164,1.628,-1.006,-7.766,-11.033,-10.985,-2.413,-1.967,0.790,0.826,-1.623,-1.783,3.021,1.598,-0.931,-0.605,-1.684,1.408,-2.771,-2.354,5.564,-2.296,-4.774,-2.830,-5.149,2.731,-3.314,-1.002,3.522,3.235,-1.598,1.923,-2.755,-3.900,-3.519,-1.673,-2.049,-10.404,6.773,1.071,0.247,1.120,-0.794,2.187,-0.189,-5.591,4.361,1.772,1.067,1.895,-5.649,0.946,-2.834,-0.082,3.295,-7.659,-0.128,2.077,-1.638,0.301,-0.974,4.331,11.711,4.199,1.545,-3.236,-4.404,-1.333,0.623,1.414,-0.240,-0.816,-0.808,-1.382,0.632,-5.238,0.120,10.634,-2.026,1.702,-0.469,1.252,1.173,3.015,-8.798,1.633,-5.323,2.149,-6.481,11.635,3.072,5.642,5.252,4.702,-3.523,-0.594,4.150,1.392,0.554,-4.377,3.646,-0.884,1.468,0.779,2.372,-0.101,-5.702,0.539,-0.440,5.149,-0.011,-1.899,-1.349,-0.355,0.076,-0.100,-0.004,5.346,6.276,0.966,-3.138,-2.633,-3.124,3.606,-3.793,-3.332,2.359,-0.739,-3.301,-2.775,-0.491,3.283,-1.394,-1.883,1.203,1.097,2.233,2.170,-2.980,-15.800,-6.791,-0.175,-4.600,-3.840,-4.179,6.568,5.935,-0.431,4.623,4.601,-1.726,0.410,2.591,4.016,8.169,1.763,-3.058,-1.340,6.276,4.682,-0.089,1.301,-4.817]

GIRL_VOICE_CONFIG = {
    "temperature": 0.05
}

girl_spk_emb = None

def init_girl_voice():
    global girl_spk_emb
    if chat is not None:
        girl_spk_emb = chat.sample_random_speaker()
        with _speaker_cache_lock:
            _speaker_cache["1031.pt"] = girl_spk_emb
    else:
        girl_spk_emb = None
        with _speaker_cache_lock:
            _speaker_cache.pop("1031.pt", None)


def sanitize_text(raw_text: str) -> str:
    """标准化文本，提升缓存命中率并避免异常字符"""
    cleaned = re.sub(r"[^\w\s\u4e00-\u9fff.,!?;:，。！？；：]", "", raw_text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _clone_embedding(embedding):
    return embedding.clone() if hasattr(embedding, "clone") else embedding


def _select_speaker_embedding(voice: str):
    """根据音色选择或生成说话人嵌入"""
    if voice == "1031.pt" and girl_spk_emb is not None:
        return _clone_embedding(girl_spk_emb)

    with _speaker_cache_lock:
        cached_embedding = _speaker_cache.get(voice)
    if cached_embedding is not None:
        return _clone_embedding(cached_embedding)

    if chat is None:
        raise RuntimeError("ChatTTS 模型尚未加载")

    voice_seed = hashlib.md5(voice.encode("utf-8")).hexdigest()
    seed = int(voice_seed[:8], 16) % 1_000_000

    with _random_lock:
        state = random.getstate()
        try:
            random.seed(seed)
            embedding = chat.sample_random_speaker()
        finally:
            random.setstate(state)

    with _speaker_cache_lock:
        _speaker_cache[voice] = embedding

    return _clone_embedding(embedding)


def _generate_audio_bytes(text: str, voice: str) -> bytes:
    if chat is None:
        raise RuntimeError("ChatTTS 模型尚未加载")

    spk_emb = _select_speaker_embedding(voice)
    params = ChatTTS.Chat.InferCodeParams(
        spk_emb=spk_emb,
        temperature=GIRL_VOICE_CONFIG["temperature"]
    )

    wavs = chat.infer([text], params_infer_code=params)
    wav = torch.from_numpy(wavs[0]).unsqueeze(0)

    buf = io.BytesIO()
    torchaudio.save(buf, wav, 24000, format="mp3")
    return buf.getvalue()


@app.post("/tts")
async def tts(request: TTSRequest):
    """文本转语音 API（支持缓存）"""
    try:
        await load_chattts_model()

        text = sanitize_text(request.text)
        if not text:
            raise HTTPException(status_code=400, detail="文本内容为空")

        async with _generation_semaphore:
            cached_audio = audio_cache.get(text, request.voice)
            if cached_audio:
                logger.debug(f"使用缓存音频: {text[:20]}...")
                return StreamingResponse(
                    io.BytesIO(cached_audio),
                    media_type="audio/mpeg"
                )

            logger.info(f"生成 TTS 音频: {text[:20]}...")
            start_time = time.time()

            audio_data = await asyncio.to_thread(_generate_audio_bytes, text, request.voice)
            audio_cache.set(text, request.voice, 1.0, audio_data)

            generation_time = time.time() - start_time
            logger.info(f"TTS 生成完成，耗时: {generation_time:.2f}s")

            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/mpeg"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS 生成失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"语音生成失败: {str(e)}"
        ) from e

@app.get("/")
def root():
    """根路径 - 服务状态"""
    return {
        "service": "ChatTTS API",
        "version": "1.0.0",
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
        await load_chattts_model()
        
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
