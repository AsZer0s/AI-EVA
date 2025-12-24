# AI陪伴对话后端服务

完整的AI语音对话系统，整合了VAD声音检测、ASR语音识别、AI对话和TTS语音合成功能。

## 功能特性

- 🎤 **VAD声音检测**：使用silero-vad检测语音活动
- 🗣️ **ASR语音识别**：使用FunASR进行中文语音识别
- 🤖 **AI对话**：集成Ollama/Grok API进行智能对话
- 🔊 **TTS语音合成**：使用CosyVoice进行文本转语音

## 系统要求

- Python 3.8+
- PyTorch 2.2.0+ (CPU或GPU版本)
- CUDA (可选，用于GPU加速)

## 安装步骤

### 1. 安装PyTorch

**GPU版本（推荐）：**
```bash
# CUDA 11.8
pip install torch==2.2.0 torchaudio==2.2.0 --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch==2.2.0 torchaudio==2.2.0 --index-url https://download.pytorch.org/whl/cu121
```

**CPU版本：**
```bash
pip install torch==2.2.0+cpu torchaudio==2.2.0+cpu --index-url https://download.pytorch.org/whl/cpu
```

### 2. 安装其他依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（可选）

创建 `.env` 文件或设置环境变量：

```bash
# Ollama/Grok API配置（重要：如果API需要认证，必须配置API密钥）
OLLAMA_API_URL=http://asben.hiyun.top:38080/v1/chat/completions
OLLAMA_MODEL=grok
OLLAMA_API_KEY=your_api_key_here  # 如果API需要认证，请设置此值

# VAD配置
VAD_THRESHOLD=0.5

# TTS配置
TTS_MODEL_ID=FunAudioLLM/Fun-CosyVoice3-0.5B-2512

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

**注意**：如果AI对话返回"API认证失败"，请设置 `OLLAMA_API_KEY` 环境变量。

## 使用方法

### 启动服务

```bash
python app.py
```

或者使用uvicorn：

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

服务启动后，访问 `http://localhost:8000/docs` 查看API文档。

### API接口说明

#### ⭐ 推荐接口（统一流程）

**1. 文本输入接口（文本 -> AI -> 音频）**
```
POST /api/chat/text
Content-Type: application/json

{
  "text": "你好，请介绍一下你自己",
  "conversation_history": [可选]
}

返回: 音频流（WAV格式）
响应头:
  X-User-Text: 用户输入的文本
  X-AI-Reply: AI回复的文本
  X-Audio-Sample-Rate: 音频采样率
```

**2. 音频输入接口（音频 -> 文本 -> AI -> 音频）**
```
POST /api/chat/audio
Content-Type: multipart/form-data

file: [音频文件]
conversation_history: [可选，JSON字符串格式的对话历史]

返回: 音频流（WAV格式）
响应头:
  X-User-Text: 识别出的用户文本
  X-AI-Reply: AI回复的文本
  X-Audio-Sample-Rate: 音频采样率
```

#### 其他接口（高级用法）

**3. 健康检查**
```
GET /api/health
```

**4. 文本对话（仅返回文本，不包含TTS）**
```
POST /api/chat
Content-Type: application/json

{
  "text": "你好",
  "conversation_history": [可选]
}
```

**5. 音频转文本**
```
POST /api/audio/transcribe
Content-Type: multipart/form-data

file: [音频文件]
```

**6. 文本转语音**
```
POST /api/audio/tts
Content-Type: application/json

{
  "text": "你好，我是AI助手"
}
```

### 使用示例

#### Python示例

```python
import requests

# ⭐ 推荐：文本输入接口（文本 -> AI -> 音频）
response = requests.post(
    "http://localhost:8000/api/chat/text",
    json={"text": "你好，请介绍一下你自己"}
)
# 保存音频
with open("ai_reply.wav", "wb") as f:
    f.write(response.content)
# 获取文本信息
user_text = response.headers.get("X-User-Text")
ai_reply = response.headers.get("X-AI-Reply")
print(f"用户: {user_text}")
print(f"AI: {ai_reply}")

# ⭐ 推荐：音频输入接口（音频 -> 文本 -> AI -> 音频）
with open("user_audio.wav", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/chat/audio",
        files={"audio": f},
        data={"conversation_history": "[]"}
    )
# 保存音频
with open("ai_reply.wav", "wb") as f:
    f.write(response.content)
# 获取文本信息
user_text = response.headers.get("X-User-Text")
ai_reply = response.headers.get("X-AI-Reply")
print(f"识别文本: {user_text}")
print(f"AI回复: {ai_reply}")

# 健康检查
response = requests.get("http://localhost:8000/api/health")
print(response.json())
```

#### cURL示例

```bash
# ⭐ 推荐：文本输入接口
curl -X POST http://localhost:8000/api/chat/text \
  -H "Content-Type: application/json" \
  -d '{"text": "你好"}' \
  --output ai_reply.wav

# ⭐ 推荐：音频输入接口
curl -X POST http://localhost:8000/api/chat/audio \
  -F "audio=@user_audio.wav" \
  -F "conversation_history=[]" \
  --output ai_reply.wav

# 健康检查
curl http://localhost:8000/api/health
```

#### 前端JavaScript示例

```javascript
// 文本输入接口
async function chatWithText(text) {
    const response = await fetch('http://localhost:8000/api/chat/text', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: text})
    });
    
    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    audio.play(); // 自动播放
    
    // 获取文本信息
    const userText = response.headers.get('X-User-Text');
    const aiReply = response.headers.get('X-AI-Reply');
    console.log('用户:', userText);
    console.log('AI:', aiReply);
}

// 音频输入接口
async function chatWithAudio(audioFile) {
    const formData = new FormData();
    formData.append('audio', audioFile);
    formData.append('conversation_history', '[]');
    
    const response = await fetch('http://localhost:8000/api/chat/audio', {
        method: 'POST',
        body: formData
    });
    
    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    audio.play(); // 自动播放
    
    // 获取文本信息
    const userText = response.headers.get('X-User-Text');
    const aiReply = response.headers.get('X-AI-Reply');
    console.log('识别文本:', userText);
    console.log('AI回复:', aiReply);
}
```

## 项目结构

```
Text2A/
├── app.py              # 主服务文件（FastAPI应用）
├── config.py           # 配置文件
├── start_server.py     # 启动脚本
├── test_api.py         # API测试脚本
├── example_client.py    # 客户端使用示例
├── main.py             # 原始测试文件
├── requirements.txt    # 依赖列表
├── README.md          # 说明文档
└── URL                # 相关链接
```

## 快速开始

### 1. 安装依赖

```bash
# 先安装PyTorch（根据您的系统选择）
pip install torch==2.2.0+cpu torchaudio==2.2.0+cpu --index-url https://download.pytorch.org/whl/cpu

# 安装其他依赖
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 方式1: 使用启动脚本
python start_server.py

# 方式2: 直接运行
python app.py

# 方式3: 使用uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 3. 测试服务

```bash
# 运行测试脚本
python test_api.py

# 或使用客户端示例
python example_client.py
```

服务启动后，访问 `http://localhost:8000/docs` 查看交互式API文档。

## 注意事项

1. **首次运行**：首次运行时会自动下载模型，可能需要较长时间
2. **内存要求**：建议至少8GB内存，GPU版本需要更多显存
3. **音频格式**：支持WAV、MP3、FLAC等常见格式
4. **采样率**：建议使用16kHz采样率的音频以获得最佳效果
5. **CosyVoice TTS**：
   - 如果CosyVoice加载失败，TTS功能将不可用，但其他功能（VAD、ASR、AI对话）正常
   - CosyVoice可能需要从GitHub直接安装，参考：https://github.com/FunAudioLLM/CosyVoice
   - 或者使用其他TTS服务替代
   - 已安装的依赖：`addict`, `librosa`, `phonemizer`, `datasets<3.0.0`

## 故障排除

### VAD模型加载失败
- 检查网络连接（需要从GitHub下载模型）
- 尝试手动下载：`torch.hub.load('snakers4/silero-vad', 'silero_vad')`

### ASR模型加载失败
- 检查modelscope连接
- 确保funasr已正确安装

### TTS模型加载失败
- CosyVoice可能需要额外的依赖，参考官方文档
- 可以暂时禁用TTS功能，使用其他TTS服务

### Ollama API调用失败
- 检查API地址是否正确
- 确认网络连接正常
- 检查API密钥（如果需要）

## 许可证

本项目使用的各个组件遵循各自的许可证：
- FunASR: Apache 2.0
- silero-vad: MIT
- CosyVoice: 参考官方许可证

## 相关链接

- [FunASR](https://github.com/modelscope/FunASR)
- [silero-vad](https://github.com/snakers4/silero-vad)
- [CosyVoice](https://github.com/FunAudioLLM/CosyVoice)

