# Set the device with environment, default is cuda:0
# export SENSEVOICE_DEVICE=cuda:1

import os, re
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing_extensions import Annotated
from typing import List
from enum import Enum
import torchaudio
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
    files: Annotated[List[UploadFile], File(description="wav or mp3 audios in 16KHz")],
    keys: Annotated[str, Form(description="name of each audio joined with comma")] = None,
    lang: Annotated[Language, Form(description="language of audio content")] = "auto",
):
    audios = []
    for file in files:
        file_io = BytesIO(await file.read())
        data_or_path_or_list, audio_fs = torchaudio.load(file_io)

        # transform to target sample
        if audio_fs != TARGET_FS:
            resampler = torchaudio.transforms.Resample(orig_freq=audio_fs, new_freq=TARGET_FS)
            data_or_path_or_list = resampler(data_or_path_or_list)

        data_or_path_or_list = data_or_path_or_list.mean(0)
        audios.append(data_or_path_or_list)

    if lang == "":
        lang = "auto"

    if not keys:
        key = [f.filename for f in files]
    else:
        key = keys.split(",")

    res = m.inference(
        data_in=audios,
        language=lang,  # "zh", "en", "yue", "ja", "ko", "nospeech"
        use_itn=False,
        ban_emo_unk=False,
        key=key,
        fs=TARGET_FS,
        **kwargs,
    )
    if len(res) == 0:
        return {"result": []}
    for it in res[0]:
        it["raw_text"] = it["text"]
        it["clean_text"] = re.sub(regex, "", it["text"], 0, re.MULTILINE)
        it["text"] = rich_transcription_postprocess(it["text"])
    return {"result": res[0]}


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
