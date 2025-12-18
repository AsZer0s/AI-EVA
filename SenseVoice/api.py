# Set the device with environment, default is cuda:0
# export SENSEVOICE_DEVICE=cuda:1

import os
import re
import sys
from pathlib import Path

# 添加当前目录到 Python 路径，确保可以导入 model
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing_extensions import Annotated
from typing import List
from enum import Enum
import torch
import torchaudio
import soundfile as sf
import numpy as np
from model import SenseVoiceSmall
from funasr.utils.postprocess_utils import rich_transcription_postprocess
from io import BytesIO

TARGET_FS = 16000


class Language(str, Enum):
    auto = "auto"
    zh = "zh"
    en = "en"
    yue = "yue"
    ja = "ja"
    ko = "ko"
    nospeech = "nospeech"


model_dir = "iic/SenseVoiceSmall"

# 自动检测可用设备
import torch
if torch.cuda.is_available():
    device = os.getenv("SENSEVOICE_DEVICE", "cuda:0")
    print(f"✅ 使用 GPU 设备: {device}")
else:
    device = "cpu"
    print(f"⚠️  CUDA 不可用，使用 CPU 设备")

try:
    print(f"📦 正在加载模型: {model_dir}")
    print(f"📂 当前工作目录: {os.getcwd()}")
    m, kwargs = SenseVoiceSmall.from_pretrained(model=model_dir, device=device)
    m.eval()
    print(f"✅ 模型加载成功")
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    import traceback
    print(f"详细错误信息:")
    traceback.print_exc()
    raise

regex = r"<\|.*\|>"

app = FastAPI()

# 添加 CORS 中间件，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset=utf-8>
            <title>Api information</title>
        </head>
        <body>
            <a href='./docs'>Documents of API</a>
        </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查模型是否已加载
        model_loaded = m is not None and hasattr(m, 'eval')
        return {
            "status": "healthy",
            "service": "SenseVoice",
            "model_loaded": model_loaded,
            "device": device
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "SenseVoice",
            "error": str(e)
        }


@app.post("/api/v1/asr")
async def turn_audio_to_text(
    files: Annotated[List[UploadFile], File(description="wav or mp3 audios in 16KHz")] = None,
    file: UploadFile = File(None, description="单个音频文件（兼容前端调用）"),
    keys: Annotated[str, Form(description="name of each audio joined with comma")] = None,
    lang: Annotated[str, Form(description="language of audio content")] = None,
    language: Annotated[str, Form(description="language of audio content (兼容前端)")] = None,
):
    # 兼容前端调用：支持单个 file 或多个 files
    if file is not None:
        files = [file]
    
    if files is None or len(files) == 0:
        return {"result": [], "text": "", "error": "未提供音频文件"}
    
    # 处理语言参数：兼容 lang 和 language
    if lang is None:
        if language is not None:
            lang = language
        else:
            lang = "auto"
    
    if lang == "" or lang is None:
        lang = "auto"
    
    # 将字符串转换为 Language 枚举（如果可能）
    try:
        lang_enum = Language(lang)
    except ValueError:
        lang_enum = Language.auto
    
    audios = []
    for file_item in files:
        file_io = BytesIO(await file_item.read())
        audio_fs = None
        data_or_path_or_list = None
        
        # 优先使用 soundfile 加载音频（避免 torchcodec 依赖）
        try:
            file_io.seek(0)
            audio_data, audio_fs = sf.read(file_io, dtype='float32')
            
            # 转换为 torch tensor
            if len(audio_data.shape) == 1:
                # 单声道
                data_or_path_or_list = torch.from_numpy(audio_data)
            else:
                # 多声道，取平均值
                data_or_path_or_list = torch.from_numpy(audio_data.mean(axis=1))
            
        except Exception as e:
            # 如果 soundfile 失败，尝试使用 torchaudio（可能需要 torchcodec）
            try:
                file_io.seek(0)
                data_or_path_or_list, audio_fs = torchaudio.load(file_io)
                # 如果是多声道，取平均值
                if len(data_or_path_or_list.shape) > 1:
                    data_or_path_or_list = data_or_path_or_list.mean(0)
            except Exception as e2:
                return {
                    "result": [],
                    "text": "",
                    "error": f"音频加载失败: soundfile错误={str(e)}, torchaudio错误={str(e2)}"
                }
        
        # 重采样到目标采样率
        if audio_fs and audio_fs != TARGET_FS:
            data_tensor = data_or_path_or_list.unsqueeze(0)  # 添加通道维度 [1, samples]
            resampler = torchaudio.transforms.Resample(orig_freq=audio_fs, new_freq=TARGET_FS)
            data_or_path_or_list = resampler(data_tensor).squeeze(0)  # 移除通道维度
        
        audios.append(data_or_path_or_list)

    if not keys:
        key = [f.filename or "audio.wav" for f in files]
    else:
        key = keys.split(",")

    res = m.inference(
        data_in=audios,
        language=lang_enum,  # "zh", "en", "yue", "ja", "ko", "nospeech"
        use_itn=False,
        ban_emo_unk=False,
        key=key,
        fs=TARGET_FS,
        **kwargs,
    )
    
    if len(res) == 0 or len(res[0]) == 0:
        return {"result": [], "text": ""}
    
    # 处理结果
    for it in res[0]:
        it["raw_text"] = it["text"]
        it["clean_text"] = re.sub(regex, "", it["text"], 0, re.MULTILINE)
        it["text"] = rich_transcription_postprocess(it["text"])
    
    # 兼容前端调用：返回单个文本结果
    first_result_text = res[0][0]["text"] if len(res[0]) > 0 else ""
    
    # 返回格式：同时支持批量格式和单个文本格式
    return {
        "result": res[0],
        "text": first_result_text,  # 前端期望的格式
        "success": True
    }


if __name__ == "__main__":
    import uvicorn
    
    try:
        print(f"🚀 启动 SenseVoice 服务...")
        print(f"📡 监听地址: 0.0.0.0:50000")
        uvicorn.run(app, host="0.0.0.0", port=50000)
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按 Enter 键退出...")
