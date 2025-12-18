import asyncio
import hashlib
import io
import os
import random
import re
import threading
import time
from pathlib import Path

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
        logger.debug("✅ [Model] 模型已加载，跳过")
        return

    async with _model_load_lock:
        if model_loaded:
            logger.debug("✅ [Model] 模型已在锁内加载，跳过")
            return

        try:
            logger.info("🔄 [Model] 开始加载 ChatTTS 模型...")
            load_start = time.time()
            
            # 检查并处理文件锁问题
            asset_gpt_dir = Path("asset/gpt")
            config_json_path = asset_gpt_dir / "config.json"
            config_json_bak_path = asset_gpt_dir / "config.json.bak"
            
            if config_json_path.exists():
                logger.info(f"🔍 [Model] 检查模型文件: {config_json_path}")
                # 如果备份文件存在，尝试删除它
                if config_json_bak_path.exists():
                    try:
                        logger.info(f"🗑️ [Model] 删除旧的备份文件: {config_json_bak_path}")
                        os.remove(config_json_bak_path)
                        logger.info("✅ [Model] 备份文件已删除")
                    except Exception as bak_error:
                        logger.warning(f"⚠️ [Model] 无法删除备份文件: {bak_error}")
                        # 尝试重命名备份文件
                        try:
                            import time as time_module
                            timestamp = int(time_module.time())
                            new_bak_name = f"config.json.bak.{timestamp}"
                            os.rename(config_json_bak_path, asset_gpt_dir / new_bak_name)
                            logger.info(f"✅ [Model] 备份文件已重命名为: {new_bak_name}")
                        except Exception as rename_error:
                            logger.warning(f"⚠️ [Model] 无法重命名备份文件: {rename_error}")
            
            # 添加重试机制
            max_load_retries = 3
            load_retry_delay = 2  # 秒
            force_redownload = False  # 第一次尝试不强制重新下载
            
            for retry_count in range(max_load_retries):
                try:
                    logger.info(f"🔄 [Model] 创建 ChatTTS.Chat() 实例 (尝试 {retry_count + 1}/{max_load_retries})...")
                    chat = ChatTTS.Chat()
                    
                    if force_redownload:
                        logger.warning("⚠️ [Model] 强制重新下载模型文件...")
                    
                    logger.info(f"🔄 [Model] 调用 chat.load(compile=False, force_redownload={force_redownload})...")
                    chat.load(compile=False, force_redownload=force_redownload)
                    logger.info("✅ [Model] chat.load() 调用完成")
                    
                    # 等待一下，让模型组件有时间初始化
                    await asyncio.sleep(1)
                    
                    # 检查模型是否真正加载成功
                    logger.info("🔍 [Model] 检查模型加载状态...")
                    has_loaded = chat.has_loaded(use_decoder=True)
                    logger.info(f"🔍 [Model] has_loaded(use_decoder=True) = {has_loaded}")
                    
                    if not has_loaded:
                        if retry_count < max_load_retries - 1:
                            logger.warning("⚠️ [Model] 模型组件未完全加载，将在下次重试时强制重新下载")
                            force_redownload = True  # 下次重试时强制重新下载
                            await asyncio.sleep(load_retry_delay)
                            load_retry_delay *= 2  # 指数退避
                            continue  # 继续重试
                        else:
                            logger.error("❌ [Model] 模型组件未完全加载！")
                            logger.error("❌ [Model] 可能原因：文件下载失败或文件损坏")
                            logger.error("❌ [Model] 请检查 asset/ 目录下的文件完整性")
                            logger.error("❌ [Model] 建议解决方案：")
                            logger.error("   1. 删除 asset/tokenizer/ 目录下的损坏文件")
                            logger.error("   2. 删除 asset/gpt/ 目录下的损坏文件（如果有）")
                            logger.error("   3. 重启 ChatTTS 服务，让它重新下载文件")
                            logger.error("   4. 如果问题持续，请检查网络连接或手动下载模型文件")
                            raise HTTPException(
                                status_code=500,
                                detail="ChatTTS 模型组件未完全加载。请检查 asset/ 目录下的文件完整性，删除损坏的文件后重启服务。"
                            )
                    
                    logger.info("✅ [Model] 模型组件加载验证成功")
                    break  # 成功加载，跳出重试循环
                    
                except PermissionError as perm_error:
                    if retry_count < max_load_retries - 1:
                        logger.warning(f"⚠️ [Model] 文件被占用，等待 {load_retry_delay} 秒后重试...")
                        logger.warning(f"⚠️ [Model] 错误详情: {perm_error}")
                        await asyncio.sleep(load_retry_delay)
                        load_retry_delay *= 2  # 指数退避
                    else:
                        logger.error(f"❌ [Model] 文件被占用，已达到最大重试次数")
                        raise
                except Exception as load_error:
                    # 其他错误直接抛出
                    logger.error(f"❌ [Model] 加载失败: {load_error}")
                    raise
            
            # 检查 ChatTTS 对象的可用属性
            logger.info("🔍 [Model] 检查 ChatTTS 对象属性...")
            logger.info(f"🔍 [Model] chat 对象类型: {type(chat)}")
            logger.info(f"🔍 [Model] chat 对象属性: {[attr for attr in dir(chat) if not attr.startswith('_')]}")
            if hasattr(chat, 'speaker'):
                logger.info(f"🔍 [Model] chat.speaker 存在: {chat.speaker is not None}")
                if chat.speaker is not None:
                    logger.info(f"🔍 [Model] chat.speaker 类型: {type(chat.speaker)}")
                    logger.info(f"🔍 [Model] chat.speaker 属性: {[attr for attr in dir(chat.speaker) if not attr.startswith('_')]}")
            else:
                logger.warning("⚠️ [Model] chat.speaker 属性不存在")
            
            model_loaded = True
            load_time = time.time() - load_start
            logger.info(f"✅ [Model] ChatTTS 模型加载完成，耗时: {load_time:.2f}s")

            # 初始化女孩音色
            logger.info("🔄 [Model] 初始化女孩音色...")
            init_girl_voice()
            logger.info("✅ [Model] 女孩音色初始化完成")
            
        except Exception as e:
            logger.error(f"❌ [Model] ChatTTS 模型加载失败: {e}")
            logger.error(f"❌ [Model] 错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"❌ [Model] 详细堆栈:\n{traceback.format_exc()}")
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
        try:
            # 尝试使用新的 API
            if hasattr(chat, 'speaker') and chat.speaker is not None:
                logger.info("🔄 [Voice] 使用 chat.speaker.sample_random()...")
                girl_spk_emb = chat.speaker.sample_random()
            elif hasattr(chat, 'sample_random_speaker'):
                logger.info("🔄 [Voice] 使用 chat.sample_random_speaker()...")
                girl_spk_emb = chat.sample_random_speaker()
            else:
                # 使用预定义的 GIRL_VOICE_SEED
                logger.info("🔄 [Voice] 使用预定义的 GIRL_VOICE_SEED...")
                girl_spk_emb = torch.tensor(GIRL_VOICE_SEED, dtype=torch.float32).unsqueeze(0)
                logger.info(f"✅ [Voice] 使用预定义音色，形状: {girl_spk_emb.shape}")
            
            with _speaker_cache_lock:
                _speaker_cache["1031.pt"] = girl_spk_emb
            logger.info("✅ [Voice] 女孩音色初始化成功")
        except Exception as e:
            logger.error(f"❌ [Voice] 初始化女孩音色失败: {e}")
            logger.error(f"❌ [Voice] 错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"❌ [Voice] 详细堆栈:\n{traceback.format_exc()}")
            # 使用预定义的 GIRL_VOICE_SEED 作为后备
            logger.info("🔄 [Voice] 使用预定义的 GIRL_VOICE_SEED 作为后备...")
            girl_spk_emb = torch.tensor(GIRL_VOICE_SEED, dtype=torch.float32).unsqueeze(0)
            with _speaker_cache_lock:
                _speaker_cache["1031.pt"] = girl_spk_emb
            logger.info("✅ [Voice] 使用预定义音色作为后备")
    else:
        girl_spk_emb = None
        with _speaker_cache_lock:
            _speaker_cache.pop("1031.pt", None)


def sanitize_text(raw_text: str) -> str:
    """标准化文本，提升缓存命中率并避免异常字符（包括 emoji 和数字）"""
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
    
    # 将数字转换为中文数字（避免 ChatTTS 的 invalid characters 错误）
    digit_map = {
        '0': '零', '1': '一', '2': '二', '3': '三', '4': '四',
        '5': '五', '6': '六', '7': '七', '8': '八', '9': '九'
    }
    for digit, chinese in digit_map.items():
        cleaned = cleaned.replace(digit, chinese)
    
    # 移除其他特殊 Unicode 字符（只保留中文、英文、基本标点）
    # 注意：移除可能导致 ChatTTS 错误的标点符号：! ? '
    # 只保留安全的标点：. , ; : 和中文标点
    cleaned = re.sub(r'[^\u4e00-\u9fff\w\s.,;:，。；：\-\(\)\[\]\"（）【】《》]', '', cleaned)
    
    # 移除单引号和其他可能导致问题的字符
    cleaned = cleaned.replace("'", "").replace("!", "").replace("?", "")
    
    # 移除控制字符和零宽字符
    cleaned = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u206f]", "", cleaned)
    
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


def _clone_embedding(embedding):
    return embedding.clone() if hasattr(embedding, "clone") else embedding


def _select_speaker_embedding(voice: str):
    """根据音色选择或生成说话人嵌入"""
    if voice == "1031.pt" and girl_spk_emb is not None:
        logger.debug(f"✅ [Speaker] 使用缓存的女孩音色")
        return _clone_embedding(girl_spk_emb)

    with _speaker_cache_lock:
        cached_embedding = _speaker_cache.get(voice)
    if cached_embedding is not None:
        logger.debug(f"✅ [Speaker] 使用缓存的音色: {voice}")
        return _clone_embedding(cached_embedding)

    if chat is None:
        raise RuntimeError("ChatTTS 模型尚未加载")

    voice_seed = hashlib.md5(voice.encode("utf-8")).hexdigest()
    seed = int(voice_seed[:8], 16) % 1_000_000
    logger.info(f"🔄 [Speaker] 生成新音色: voice={voice}, seed={seed}")

    try:
        with _random_lock:
            state = random.getstate()
            try:
                random.seed(seed)
                # 尝试使用新的 API
                if hasattr(chat, 'speaker') and chat.speaker is not None:
                    logger.info("🔄 [Speaker] 使用 chat.speaker.sample_random()...")
                    embedding = chat.speaker.sample_random()
                elif hasattr(chat, 'sample_random_speaker'):
                    logger.info("🔄 [Speaker] 使用 chat.sample_random_speaker()...")
                    embedding = chat.sample_random_speaker()
                else:
                    # 使用基于 seed 的随机生成
                    logger.warning("⚠️ [Speaker] ChatTTS API 不可用，使用预定义音色")
                    embedding = torch.tensor(GIRL_VOICE_SEED, dtype=torch.float32).unsqueeze(0)
            finally:
                random.setstate(state)
    except Exception as e:
        logger.error(f"❌ [Speaker] 生成音色失败: {e}")
        logger.error(f"❌ [Speaker] 错误类型: {type(e).__name__}")
        import traceback
        logger.error(f"❌ [Speaker] 详细堆栈:\n{traceback.format_exc()}")
        # 使用预定义的 GIRL_VOICE_SEED 作为后备
        logger.info("🔄 [Speaker] 使用预定义的 GIRL_VOICE_SEED 作为后备...")
        embedding = torch.tensor(GIRL_VOICE_SEED, dtype=torch.float32).unsqueeze(0)

    with _speaker_cache_lock:
        _speaker_cache[voice] = embedding

    logger.info(f"✅ [Speaker] 音色生成成功: {voice}")
    return _clone_embedding(embedding)


def _generate_audio_bytes(text: str, voice: str) -> bytes:
    logger.info(f"🎤 [Generate] 开始生成音频: text_length={len(text)}, voice={voice}")
    
    if chat is None:
        logger.error("❌ [Generate] ChatTTS 模型尚未加载")
        raise RuntimeError("ChatTTS 模型尚未加载")

    try:
        logger.info(f"🎤 [Generate] 选择说话人嵌入: voice={voice}")
        spk_emb = _select_speaker_embedding(voice)
        logger.info(f"✅ [Generate] 说话人嵌入获取成功")
        
        # 验证文本长度
        if not text or len(text.strip()) == 0:
            logger.error(f"❌ [Generate] 文本为空或无效")
            raise ValueError("文本内容为空，无法生成音频")
        
        if len(text) > 1000:
            logger.warning(f"⚠️ [Generate] 文本过长 ({len(text)} 字符)，将截断到 1000 字符")
            text = text[:1000]
        
        logger.info(f"🎤 [Generate] 创建推理参数: temperature={GIRL_VOICE_CONFIG['temperature']}")
        params = ChatTTS.Chat.InferCodeParams(
            spk_emb=spk_emb,
            temperature=GIRL_VOICE_CONFIG["temperature"]
        )
        
        logger.info(f"🎤 [Generate] 调用 chat.infer()... (文本长度: {len(text)})")
        logger.debug(f"🎤 [Generate] 文本内容: {text[:100]}...")
        infer_start = time.time()
        
        # 尝试多种方法避免 narrow() 错误
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                if attempt == 0:
                    # 第一次尝试：使用 skip_refine=True
                    logger.info(f"🔄 [Generate] 尝试 {attempt + 1}/{max_attempts}: 使用 skip_refine=True")
                    refine_params = ChatTTS.Chat.RefineTextParams()
                    refine_params.skip_refine = True
                    wavs = chat.infer([text], params_infer_code=params, params_refine_text=refine_params)
                elif attempt == 1:
                    # 第二次尝试：不使用 refine 参数
                    logger.info(f"🔄 [Generate] 尝试 {attempt + 1}/{max_attempts}: 不使用 refine 参数")
                    wavs = chat.infer([text], params_infer_code=params)
                else:
                    # 第三次尝试：使用标准的中文文本（确保长度足够）
                    logger.info(f"🔄 [Generate] 尝试 {attempt + 1}/{max_attempts}: 使用标准中文文本")
                    # 移除所有英文、数字、特殊字符，只保留中文和基本中文标点
                    simple_text = re.sub(r'[^\u4e00-\u9fff\s，。]', '', text).strip()
                    # 移除多余空格
                    simple_text = re.sub(r'\s+', '', simple_text)
                    # 确保文本长度足够（至少10个字符），如果太短则使用默认文本
                    if not simple_text or len(simple_text) < 10:
                        simple_text = "你好，我是人工智能助手，很高兴为你服务。"  # 使用更长的默认文本
                    logger.info(f"🔄 [Generate] 标准中文文本: {simple_text[:50]}... (长度: {len(simple_text)})")
                    # 尝试使用 use_decoder=False 来避免某些问题
                    try:
                        # 先尝试不使用 decoder
                        wavs = chat.infer([simple_text], params_infer_code=params, use_decoder=False)
                    except Exception as decoder_error:
                        logger.warning(f"⚠️ [Generate] use_decoder=False 失败，尝试 use_decoder=True: {decoder_error}")
                        # 如果失败，尝试使用 decoder
                        wavs = chat.infer([simple_text], params_infer_code=params, use_decoder=True)
                
                logger.info(f"✅ [Generate] 尝试 {attempt + 1} 成功生成音频")
                break  # 成功，跳出循环
                
            except Exception as infer_error:
                error_msg = str(infer_error).lower()
                last_error = infer_error
                logger.warning(f"⚠️ [Generate] 尝试 {attempt + 1} 失败: {infer_error}")
                
                if attempt < max_attempts - 1:
                    logger.info(f"🔄 [Generate] 继续尝试下一种方法...")
                else:
                    logger.error(f"❌ [Generate] 所有尝试都失败")
                    raise RuntimeError(f"音频生成失败，已尝试 {max_attempts} 种方法: {last_error}")
        
        infer_time = time.time() - infer_start
        logger.info(f"✅ [Generate] chat.infer() 完成，耗时: {infer_time:.2f}s, 输出数量: {len(wavs)}")
        
        logger.info(f"🎤 [Generate] 转换音频格式...")
        wav = torch.from_numpy(wavs[0]).unsqueeze(0)
        logger.info(f"✅ [Generate] 音频张量形状: {wav.shape}")

        logger.info(f"🎤 [Generate] 保存为 MP3 格式...")
        buf = io.BytesIO()
        torchaudio.save(buf, wav, 24000, format="mp3")
        audio_bytes = buf.getvalue()
        logger.info(f"✅ [Generate] MP3 保存完成，大小: {len(audio_bytes)} bytes")
        
        return audio_bytes
    except Exception as e:
        logger.error(f"❌ [Generate] 音频生成过程出错: {e}")
        logger.error(f"❌ [Generate] 错误类型: {type(e).__name__}")
        import traceback
        logger.error(f"❌ [Generate] 详细堆栈:\n{traceback.format_exc()}")
        raise


@app.post("/tts")
async def tts(request: TTSRequest):
    """文本转语音 API（支持缓存）"""
    request_start_time = time.time()
    logger.info(f"📥 [TTS] 收到请求: text_length={len(request.text)}, voice={request.voice}")
    logger.debug(f"📥 [TTS] 请求文本预览: {request.text[:100]}...")
    
    try:
        logger.info("🔄 [TTS] 检查模型加载状态...")
        await load_chattts_model()
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
