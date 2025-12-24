"""
AI陪伴对话后端服务
整合：VAD声音检测 -> ASR语音识别 -> AI对话 -> TTS语音合成
"""
import os
import io
import logging
from typing import Optional, Tuple
import numpy as np
import soundfile as sf
import torch
import torchaudio
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import requests
import json
from config import Config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI陪伴对话服务", description="VAD + ASR + AI对话 + TTS完整流程")

# 使用配置
config = Config()

# ==================== 全局模型实例 ====================
asr_model = None
vad_model = None
tts_model = None

# ==================== VAD声音检测模块 ====================
def init_vad_model():
    """初始化VAD模型"""
    global vad_model
    max_retries = 3
    retry_delay = 2  # 秒
    
    for attempt in range(max_retries):
        try:
            logger.info(f"正在加载VAD模型（尝试 {attempt + 1}/{max_retries}）...")
            # 使用silero-vad
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            vad_model = model
            logger.info("VAD模型加载成功")
            return True
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"VAD模型加载失败（尝试 {attempt + 1}/{max_retries}）: {error_msg}")
            
            # 如果是网络错误，等待后重试
            if "connection" in error_msg.lower() or "timeout" in error_msg.lower() or "remote" in error_msg.lower():
                if attempt < max_retries - 1:
                    import time
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    continue
            
            # 最后一次尝试失败
            if attempt == max_retries - 1:
                logger.error(f"VAD模型加载失败，已重试 {max_retries} 次")
                logger.warning("VAD功能将不可用，但系统会继续运行（默认认为所有音频都有语音）")
                return False
    
    return False

def detect_speech(audio_data: np.ndarray, sample_rate: int = 16000) -> bool:
    """检测音频中是否有语音活动"""
    global vad_model
    if vad_model is None:
        logger.warning("VAD模型未初始化，跳过检测")
        return True  # 如果没有VAD，默认认为有语音
    
    try:
        # 确保音频是单声道
        if len(audio_data.shape) > 1:
            audio_data = audio_data[:, 0]
        
        # 转换为torch tensor
        audio_tensor = torch.from_numpy(audio_data).float()
        
        # 如果采样率不匹配，需要重采样
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            audio_tensor = resampler(audio_tensor)
        
        # VAD检测
        speech_prob = vad_model(audio_tensor, 16000).item()
        return speech_prob > config.VAD_THRESHOLD
    except Exception as e:
        logger.error(f"VAD检测失败: {e}")
        return True  # 出错时默认认为有语音

# ==================== ASR语音识别模块 ====================
def init_asr_model():
    """初始化ASR模型"""
    global asr_model
    try:
        from funasr import AutoModel
        asr_model = AutoModel(
            model=config.ASR_MODEL_NAME,
            model_revision=config.ASR_MODEL_REVISION
        )
        logger.info("ASR模型加载成功")
        return True
    except Exception as e:
        logger.error(f"ASR模型加载失败: {e}")
        return False

def transcribe_audio(audio_data: np.ndarray, sample_rate: int = 16000) -> str:
    """将音频转换为文本"""
    global asr_model
    if asr_model is None:
        raise RuntimeError("ASR模型未初始化")
    
    try:
        cache = {}
        chunk_stride = config.ASR_CHUNK_SIZE[1] * 960  # 600ms
        total_chunk_num = int((len(audio_data) - 1) / chunk_stride + 1)
        
        full_text = ""
        for i in range(total_chunk_num):
            speech_chunk = audio_data[i * chunk_stride:(i + 1) * chunk_stride]
            is_final = i == total_chunk_num - 1
            res = asr_model.generate(
                input=speech_chunk,
                cache=cache,
                is_final=is_final,
                chunk_size=config.ASR_CHUNK_SIZE,
                encoder_chunk_look_back=config.ASR_ENCODER_CHUNK_LOOK_BACK,
                decoder_chunk_look_back=config.ASR_DECODER_CHUNK_LOOK_BACK
            )
            
            if res and len(res) > 0:
                text = res[0].get('text', '')
                if text:
                    full_text += text
        
        return full_text.strip()
    except Exception as e:
        logger.error(f"ASR识别失败: {e}")
        raise

# ==================== AI对话模块 ====================
def chat_with_ai(user_text: str, conversation_history: list = None) -> str:
    """与AI对话，返回AI回复（使用OpenAI标准格式）"""
    try:
        # 构建消息历史（OpenAI标准格式）
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        
        # 添加用户消息
        messages.append({
            "role": "user",
            "content": user_text
        })
        
        # OpenAI标准格式的请求体
        payload = {
            "model": config.AI_API_MODEL,
            "messages": messages,
            "stream": False
        }
        
        # OpenAI标准格式的请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.AI_API_KEY}"  # OpenAI标准格式
        }
        
        logger.debug(f"AI API请求: URL={config.AI_API_URL}, Model={config.AI_API_MODEL}")
        
        response = requests.post(
            config.AI_API_URL,
            json=payload,
            headers=headers,
            timeout=config.AI_API_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # OpenAI标准响应格式: {"choices": [{"message": {"role": "assistant", "content": "..."}}]}
            if 'choices' in result and len(result['choices']) > 0:
                ai_reply = result['choices'][0].get('message', {}).get('content', '')
                if ai_reply:
                    return ai_reply
            
            # 兼容其他可能的格式
            if 'content' in result:
                return result['content']
            elif 'message' in result:
                if isinstance(result['message'], str):
                    return result['message']
                elif isinstance(result['message'], dict):
                    return result['message'].get('content', '')
            
            logger.error(f"AI API响应格式未知: {result}")
            return "抱歉，API响应格式异常，请检查配置。"
            
        elif response.status_code == 401:
            logger.error(f"AI API认证失败（401）: {response.text}")
            logger.error("提示：请检查API密钥配置（AI_API_KEY环境变量）")
            return "抱歉，API认证失败，请检查API密钥配置。"
        elif response.status_code == 404:
            logger.error(f"AI API端点不存在（404）: {response.text}")
            return "抱歉，API端点不存在，请检查API地址配置。"
        else:
            logger.error(f"AI API调用失败: {response.status_code}")
            logger.error(f"响应内容: {response.text}")
            return f"抱歉，API调用失败（状态码: {response.status_code}），请检查API地址和配置。"
            
    except requests.exceptions.Timeout:
        logger.error(f"AI API请求超时（超过{config.AI_API_TIMEOUT}秒）")
        return "抱歉，API请求超时，请稍后再试。"
    except requests.exceptions.ConnectionError:
        logger.error("AI API连接失败，请检查网络连接和API地址")
        return "抱歉，无法连接到API服务器，请检查网络连接。"
    except Exception as e:
        logger.error(f"AI对话失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return "抱歉，发生了错误，请稍后再试。"

# ==================== TTS语音合成模块 ====================
def init_tts_model():
    """初始化TTS模型（CosyVoice）"""
    global tts_model
    
    model_id = config.TTS_MODEL_ID
    
    # 方法1: 尝试使用CosyVoice AutoModel（推荐）
    try:
        logger.info("尝试方法1: 使用CosyVoice AutoModel（GitHub版本）...")
        
        # 尝试导入CosyVoice
        import sys
        import os
        
        cosyvoice_path = os.path.join(os.path.dirname(__file__), 'CosyVoice')
        matcha_path = os.path.join(cosyvoice_path, 'third_party', 'Matcha-TTS')
        
        # 添加CosyVoice路径
        if os.path.exists(cosyvoice_path):
            sys.path.insert(0, cosyvoice_path)
            logger.info(f"添加CosyVoice路径: {cosyvoice_path}")
        
        # 添加Matcha-TTS路径（CosyVoice需要）
        if os.path.exists(matcha_path):
            sys.path.insert(0, matcha_path)
            logger.info(f"添加Matcha-TTS路径: {matcha_path}")
        
        # 导入CosyVoice AutoModel
        try:
            from cosyvoice.cli.cosyvoice import AutoModel
        except ImportError as e:
            raise ImportError(f"CosyVoice未正确安装: {e}")
        
        # 使用modelscope下载的模型路径
        from modelscope import snapshot_download
        
        # 模型已经下载到了这个路径（根据日志）
        model_dir = snapshot_download(model_id)
        logger.info(f"使用模型路径: {model_dir}")
        
        # 初始化CosyVoice AutoModel
        logger.info("正在初始化CosyVoice AutoModel...")
        tts_model = AutoModel(model_dir=model_dir)
        logger.info("✓ TTS模型加载成功（CosyVoice AutoModel）")
        return True
        
    except ImportError as e:
        logger.warning(f"CosyVoice未安装: {e}")
        logger.warning("提示：CosyVoice需要从GitHub安装")
        logger.warning("安装步骤：")
        logger.warning("  1. git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git")
        logger.warning("  2. cd CosyVoice && pip install -r requirements.txt")
        logger.warning("  3. 将CosyVoice目录放在项目目录下")
    except Exception as e:
        logger.error(f"CosyVoice AutoModel初始化失败: {e}")
        import traceback
        logger.error("详细错误信息：")
        logger.error(traceback.format_exc())
    
    # 方法2: 尝试使用modelscope pipeline（备用，通常不工作）
    try:
        logger.info("尝试方法2: 使用modelscope pipeline（备用方法）...")
        from modelscope import snapshot_download
        from modelscope.pipelines import pipeline
        
        logger.info(f"正在下载模型: {model_id}")
        model_dir = snapshot_download(model_id)
        logger.info(f"模型路径: {model_dir}")
        
        # 尝试pipeline初始化
        tts_model = pipeline(
            task="text-to-speech",
            model=model_dir,
            trust_remote_code=True
        )
        logger.info("✓ TTS模型加载成功（modelscope pipeline）")
        return True
        
    except Exception as e:
        logger.warning(f"modelscope pipeline方法失败: {e}")
    
    logger.warning("=" * 60)
    logger.info("TTS功能将不可用，但其他功能（VAD、ASR、AI对话）正常")
    return False

def text_to_speech(text: str) -> Tuple[np.ndarray, int]:
    """将文本转换为语音，返回音频数据和采样率"""
    global tts_model
    if tts_model is None:
        logger.error("TTS模型未初始化")
        raise RuntimeError("TTS模型未初始化，请检查模型加载状态")
    
    try:
        # 检查是否是CosyVoice模型
        model_type = type(tts_model).__name__
        
        # 方法1: 检查类型名称
        is_cosyvoice_by_type = 'CosyVoice' in model_type
        
        # 方法2: 检查是否有inference_zero_shot方法
        has_inference_method = hasattr(tts_model, 'inference_zero_shot')
        if has_inference_method:
            inference_method = getattr(tts_model, 'inference_zero_shot', None)
            is_callable = callable(inference_method)
        else:
            is_callable = False
        
        # 方法3: 检查是否有sample_rate属性（CosyVoice特有）
        has_sample_rate = hasattr(tts_model, 'sample_rate')
        
        # 综合判断：是CosyVoice模型
        is_cosyvoice_model = (is_cosyvoice_by_type or (has_inference_method and is_callable)) and has_sample_rate
        
        logger.info(f"TTS模型检查: 类型={model_type}, 类型匹配={is_cosyvoice_by_type}, 有inference_zero_shot={has_inference_method}, 方法可调用={is_callable}, 有sample_rate={has_sample_rate}, 判断结果={is_cosyvoice_model}")
        
        if is_cosyvoice_model:
            # CosyVoice AutoModel的调用方式
            # CosyVoice3使用inference_zero_shot方法
            # 需要提供：文本、系统提示、参考音频路径
            import os
            
            # 查找参考音频文件（CosyVoice目录下的asset/zero_shot_prompt.wav）
            cosyvoice_path = os.path.join(os.path.dirname(__file__), 'CosyVoice')
            ref_audio = os.path.join(cosyvoice_path, 'asset', 'zero_shot_prompt.wav')
            
            # 如果参考音频不存在，尝试使用相对路径
            if not os.path.exists(ref_audio):
                ref_audio = os.path.join('CosyVoice', 'asset', 'zero_shot_prompt.wav')
                if not os.path.exists(ref_audio):
                    # 如果还是不存在，使用默认路径（CosyVoice会处理）
                    ref_audio = './asset/zero_shot_prompt.wav'
            
            # CosyVoice3的调用方式
            # inference_zero_shot(text, system_prompt, ref_audio_path, stream=False)
            system_prompt = "You are a helpful assistant.<|endofprompt|>希望你以后能够做的比我还好呦。"
            
            # 调用inference_zero_shot
            logger.info(f"TTS合成: 文本长度={len(text)}, 参考音频={ref_audio}")
            
            # 检查参考音频是否存在
            if not os.path.exists(ref_audio):
                logger.warning(f"参考音频不存在: {ref_audio}，将尝试使用默认路径")
                # 尝试使用CosyVoice目录下的默认路径
                default_ref = os.path.join(cosyvoice_path, 'asset', 'zero_shot_prompt.wav')
                if os.path.exists(default_ref):
                    ref_audio = default_ref
                else:
                    logger.error(f"找不到参考音频文件，请确保CosyVoice/asset/zero_shot_prompt.wav存在")
                    raise FileNotFoundError(f"参考音频文件不存在: {ref_audio}")
            
            results = list(tts_model.inference_zero_shot(
                text, 
                system_prompt, 
                ref_audio,
                stream=False
            ))
            
            # 获取第一个结果
            if results and len(results) > 0:
                result = results[0]
                audio_data = result.get('tts_speech')
                sample_rate = tts_model.sample_rate
                
                if audio_data is None:
                    raise ValueError("CosyVoice返回结果中没有tts_speech字段")
                
                # 确保audio_data是numpy数组
                if isinstance(audio_data, torch.Tensor):
                    audio_data = audio_data.cpu().numpy()
                
                logger.info(f"TTS合成成功: 音频长度={len(audio_data)}, 采样率={sample_rate}")
            else:
                raise ValueError("CosyVoice未返回音频数据")
        else:
            # 如果不是CosyVoice模型，尝试其他方式
            logger.warning(f"TTS模型类型 {model_type} 不是CosyVoice模型，尝试其他调用方式")
            
            # 检查是否有__call__方法（pipeline方式）
            if callable(tts_model):
                logger.info("尝试使用pipeline方式调用TTS模型")
                # modelscope pipeline的调用方式（备用）
                output = tts_model(text)
                
                # 提取音频数据
                if isinstance(output, dict):
                    audio_data = output.get('audio') or output.get('wav') or output.get('output_wav')
                    sample_rate = output.get('sample_rate', config.TTS_SAMPLE_RATE)
                elif isinstance(output, (list, tuple)) and len(output) >= 2:
                    audio_data, sample_rate = output[0], output[1]
                else:
                    audio_data = output
                    sample_rate = config.TTS_SAMPLE_RATE
            else:
                # 无法识别的TTS模型类型
                model_type = type(tts_model).__name__
                raise RuntimeError(f"无法识别的TTS模型类型: {model_type}，请检查模型初始化")
        
        if audio_data is None:
            raise ValueError("TTS输出中没有找到音频数据")
        
        # 确保是numpy数组
        if isinstance(audio_data, torch.Tensor):
            audio_data = audio_data.cpu().numpy()
        elif not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data)
        
        # 确保是单声道
        if len(audio_data.shape) > 1:
            if audio_data.shape[0] == 1 or audio_data.shape[1] == 1:
                audio_data = audio_data.flatten()
            else:
                audio_data = audio_data.mean(axis=1) if audio_data.shape[1] < audio_data.shape[0] else audio_data.mean(axis=0)
        
        # 确保数据类型正确
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # 归一化到[-1, 1]
        max_val = np.abs(audio_data).max()
        if max_val > 1.0:
            audio_data = audio_data / max_val
        
        return audio_data, int(sample_rate)
    except Exception as e:
        logger.error(f"TTS合成失败: {e}")
        logger.error(f"输入文本: {text[:50]}...")
        import traceback
        logger.error(traceback.format_exc())
        raise RuntimeError(f"TTS合成失败: {str(e)}")

# ==================== API接口 ====================
@app.on_event("startup")
async def startup_event():
    """启动时初始化所有模型"""
    logger.info("=" * 60)
    logger.info("正在初始化AI陪伴对话服务...")
    logger.info("=" * 60)
    
    init_status = {}
    
    # 初始化ASR
    logger.info("\n[1/3] 初始化ASR语音识别模型...")
    if init_asr_model():
        init_status['ASR'] = "✓ 成功"
        logger.info("✓ ASR模型加载成功")
    else:
        init_status['ASR'] = "✗ 失败"
        logger.error("✗ ASR模型初始化失败 - 这是核心功能，服务可能无法正常工作")
    
    # 初始化VAD
    logger.info("\n[2/3] 初始化VAD声音检测模型...")
    if init_vad_model():
        init_status['VAD'] = "✓ 成功"
        logger.info("✓ VAD模型加载成功")
    else:
        init_status['VAD'] = "✗ 失败（可选）"
        logger.warning("✗ VAD模型初始化失败 - 将跳过VAD检测（默认认为所有音频都有语音）")
    
    # 初始化TTS
    logger.info("\n[3/3] 初始化TTS语音合成模型...")
    if init_tts_model():
        init_status['TTS'] = "✓ 成功"
        logger.info("✓ TTS模型加载成功")
    else:
        init_status['TTS'] = "✗ 失败（可选）"
        logger.warning("✗ TTS模型初始化失败 - TTS功能将不可用，但其他功能正常")
    
    # 显示初始化总结
    logger.info("\n" + "=" * 60)
    logger.info("模型初始化完成！")
    logger.info("=" * 60)
    logger.info("初始化状态:")
    for module, status in init_status.items():
        logger.info(f"  {module:6s}: {status}")
    logger.info("=" * 60)
    
    # 检查关键功能
    if asr_model is None:
        logger.error("\n⚠️  警告：ASR模型未加载，语音识别功能将不可用！")
    else:
        logger.info("\n✓ 核心功能（ASR + AI对话）已就绪，服务可以正常使用")

class ChatRequest(BaseModel):
    text: str
    conversation_history: Optional[list] = None

class ChatResponse(BaseModel):
    text: str
    audio_url: Optional[str] = None

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """文本对话接口（不包含ASR和TTS）"""
    try:
        ai_reply = chat_with_ai(request.text, request.conversation_history)
        return ChatResponse(text=ai_reply)
    except Exception as e:
        logger.error(f"对话接口错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audio/transcribe")
async def transcribe_endpoint(audio: UploadFile = File(...)):
    """音频转文本接口"""
    try:
        # 读取音频文件
        audio_bytes = await audio.read()
        audio_io = io.BytesIO(audio_bytes)
        
        # 使用soundfile读取音频
        audio_data, sample_rate = sf.read(audio_io)
        
        # VAD检测
        has_speech = detect_speech(audio_data, sample_rate)
        if not has_speech:
            return JSONResponse(content={"text": "", "has_speech": False})
        
        # ASR识别
        text = transcribe_audio(audio_data, sample_rate)
        
        return JSONResponse(content={"text": text, "has_speech": True})
    except Exception as e:
        logger.error(f"转录接口错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audio/tts")
async def tts_endpoint(request: ChatRequest):
    """文本转语音接口"""
    try:
        if tts_model is None:
            raise HTTPException(status_code=503, detail="TTS模型未初始化")
        
        # 生成语音
        audio_data, sample_rate = text_to_speech(request.text)
        
        # 转换为WAV格式
        audio_io = io.BytesIO()
        sf.write(audio_io, audio_data, sample_rate, format='WAV')
        audio_io.seek(0)
        
        return StreamingResponse(
            audio_io,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=output.wav"}
        )
    except Exception as e:
        logger.error(f"TTS接口错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/complete")
async def complete_endpoint(
    audio: UploadFile = File(...), 
    conversation_history: Optional[str] = Form(None)
):
    """完整流程：音频输入 -> VAD -> ASR -> AI对话 -> TTS -> 音频输出"""
    try:
        # 1. 读取音频
        audio_bytes = await audio.read()
        audio_io = io.BytesIO(audio_bytes)
        audio_data, sample_rate = sf.read(audio_io)
        
        # 2. VAD检测
        has_speech = detect_speech(audio_data, sample_rate)
        if not has_speech:
            return JSONResponse(content={
                "text": "",
                "ai_reply": "",
                "has_speech": False,
                "message": "未检测到语音活动"
            })
        
        # 3. ASR识别
        user_text = transcribe_audio(audio_data, sample_rate)
        if not user_text:
            return JSONResponse(content={
                "text": "",
                "ai_reply": "",
                "has_speech": True,
                "message": "未能识别出文本"
            })
        
        # 4. AI对话
        history = None
        if conversation_history:
            try:
                history = json.loads(conversation_history)
            except:
                logger.warning("对话历史格式错误，将忽略")
        ai_reply = chat_with_ai(user_text, history)
        
        # 5. TTS合成（可选）
        audio_available = False
        if tts_model is not None:
            try:
                tts_audio_data, tts_sample_rate = text_to_speech(ai_reply)
                audio_available = True
            except Exception as tts_error:
                logger.error(f"TTS合成失败: {tts_error}")
                audio_available = False
        
        return JSONResponse(content={
            "text": user_text,
            "ai_reply": ai_reply,
            "has_speech": True,
            "audio_available": audio_available,
            "message": "TTS功能不可用" if not audio_available else "处理完成"
        })
            
    except Exception as e:
        logger.error(f"完整流程错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/complete/audio")
async def complete_with_audio_endpoint(
    audio: UploadFile = File(...), 
    conversation_history: Optional[str] = Form(None)
):
    """完整流程并返回音频：音频输入 -> VAD -> ASR -> AI对话 -> TTS -> 返回音频文件"""
    try:
        # 1. 读取音频
        audio_bytes = await audio.read()
        audio_io = io.BytesIO(audio_bytes)
        audio_data, sample_rate = sf.read(audio_io)
        
        # 2. VAD检测
        has_speech = detect_speech(audio_data, sample_rate)
        if not has_speech:
            return JSONResponse(content={
                "error": "未检测到语音活动"
            })
        
        # 3. ASR识别
        user_text = transcribe_audio(audio_data, sample_rate)
        if not user_text:
            return JSONResponse(content={
                "error": "未能识别出文本"
            })
        
        # 4. AI对话
        history = None
        if conversation_history:
            try:
                history = json.loads(conversation_history)
            except:
                pass
        ai_reply = chat_with_ai(user_text, history)
        
        # 5. TTS合成
        if tts_model is None:
            return JSONResponse(content={
                "error": "TTS模型未初始化",
                "text": user_text,
                "ai_reply": ai_reply
            })
        
        tts_audio_data, tts_sample_rate = text_to_speech(ai_reply)
        
        # 转换为WAV
        tts_audio_io = io.BytesIO()
        sf.write(tts_audio_io, tts_audio_data, tts_sample_rate, format='WAV')
        tts_audio_io.seek(0)
        
        return StreamingResponse(
            tts_audio_io,
            media_type="audio/wav",
            headers={
                "X-User-Text": user_text,
                "X-AI-Reply": ai_reply
            }
        )
            
    except Exception as e:
        logger.error(f"完整流程错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 统一接口：简化流程 ====================

@app.post("/api/chat/audio")
async def chat_with_audio(
    audio: UploadFile = File(...),
    conversation_history: Optional[str] = Form(None)
):
    """
    统一接口：音频输入 -> VAD -> ASR -> AI对话 -> TTS -> 返回音频
    流程：用户音频 -> 语音识别 -> AI回复 -> 语音合成 -> 返回音频流
    """
    try:
        # 1. 读取音频
        audio_bytes = await audio.read()
        audio_io = io.BytesIO(audio_bytes)
        audio_data, sample_rate = sf.read(audio_io)
        
        logger.info(f"收到音频输入: {len(audio_data)} 采样点, 采样率={sample_rate}Hz")
        
        # 2. VAD检测
        has_speech = detect_speech(audio_data, sample_rate)
        if not has_speech:
            logger.warning("未检测到语音活动")
            return JSONResponse(
                status_code=400,
                content={"error": "未检测到语音活动", "message": "请确保音频中包含语音"}
            )
        
        # 3. ASR识别
        if asr_model is None:
            return JSONResponse(
                status_code=503,
                content={"error": "ASR模型未初始化"}
            )
        
        user_text = transcribe_audio(audio_data, sample_rate)
        if not user_text or not user_text.strip():
            logger.warning("未能识别出文本")
            return JSONResponse(
                status_code=400,
                content={"error": "未能识别出文本", "message": "请确保音频清晰"}
            )
        
        logger.info(f"ASR识别结果: {user_text}")
        
        # 4. AI对话
        history = None
        if conversation_history:
            try:
                history = json.loads(conversation_history)
            except Exception as e:
                logger.warning(f"对话历史格式错误: {e}")
        
        ai_reply = chat_with_ai(user_text, history)
        logger.info(f"AI回复: {ai_reply[:100]}...")
        
        # 5. TTS合成
        if tts_model is None:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "TTS模型未初始化",
                    "user_text": user_text,
                    "ai_reply": ai_reply
                }
            )
        
        tts_audio_data, tts_sample_rate = text_to_speech(ai_reply)
        
        # 6. 转换为WAV格式并返回音频流
        tts_audio_io = io.BytesIO()
        sf.write(tts_audio_io, tts_audio_data, tts_sample_rate, format='WAV')
        tts_audio_io.seek(0)
        
        logger.info(f"返回音频: {len(tts_audio_io.getvalue())} bytes, 采样率={tts_sample_rate}Hz")
        
        return StreamingResponse(
            tts_audio_io,
            media_type="audio/wav",
            headers={
                "X-User-Text": user_text,
                "X-AI-Reply": ai_reply,
                "X-Audio-Sample-Rate": str(tts_sample_rate),
                "Content-Disposition": "inline; filename=ai_reply.wav"
            }
        )
            
    except Exception as e:
        logger.error(f"音频对话接口错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/api/chat/text")
async def chat_with_text(
    request: ChatRequest
):
    """
    统一接口：文本输入 -> AI对话 -> TTS -> 返回音频
    流程：用户文本 -> AI回复 -> 语音合成 -> 返回音频流
    """
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        logger.info(f"收到文本输入: {request.text[:100]}...")
        
        # 1. AI对话
        ai_reply = chat_with_ai(request.text, request.conversation_history)
        logger.info(f"AI回复: {ai_reply[:100]}...")
        
        # 2. TTS合成
        if tts_model is None:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "TTS模型未初始化",
                    "user_text": request.text,
                    "ai_reply": ai_reply
                }
            )
        
        tts_audio_data, tts_sample_rate = text_to_speech(ai_reply)
        
        # 3. 转换为WAV格式并返回音频流
        tts_audio_io = io.BytesIO()
        sf.write(tts_audio_io, tts_audio_data, tts_sample_rate, format='WAV')
        tts_audio_io.seek(0)
        
        logger.info(f"返回音频: {len(tts_audio_io.getvalue())} bytes, 采样率={tts_sample_rate}Hz")
        
        return StreamingResponse(
            tts_audio_io,
            media_type="audio/wav",
            headers={
                "X-User-Text": request.text,
                "X-AI-Reply": ai_reply,
                "X-Audio-Sample-Rate": str(tts_sample_rate),
                "Content-Disposition": "inline; filename=ai_reply.wav"
            }
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本对话接口错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "asr_loaded": asr_model is not None,
        "vad_loaded": vad_model is not None,
        "tts_loaded": tts_model is not None
    }

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI陪伴对话服务",
        "version": "1.0.0",
        "endpoints": {
            "/api/health": "健康检查",
            "/api/chat/audio": "音频输入接口（音频->文本->AI->音频）",
            "/api/chat/text": "文本输入接口（文本->AI->音频）",
            "/api/chat": "文本对话（仅返回文本，不包含TTS）",
            "/api/audio/transcribe": "音频转文本",
            "/api/audio/tts": "文本转语音",
            "/api/complete": "完整流程（音频->文本->AI->文本）",
            "/api/complete/audio": "完整流程（音频->文本->AI->音频）"
        },
        "recommended": {
            "audio_input": "/api/chat/audio",
            "text_input": "/api/chat/text"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

