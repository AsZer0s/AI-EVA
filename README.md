# AI-EVA Demo

<div align="center">

🎭 **AI 虚拟女友对话系统** 

基于 VRM 3D 模型的智能交互 Demo

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Demo-orange.svg)](LICENSE)

[快速开始](#-快速开始) • [功能特性](#-功能特性) • [使用指南](#-使用指南) • [配置说明](#-配置说明) • [常见问题](#-常见问题)

</div>

---

## 📖 项目简介

AI-EVA 是一个集成了 **语音合成**、**AI 对话**、**语音识别** 的 3D 虚拟角色交互系统。通过整合 ChatTTS、Ollama、SenseVoice 等开源技术，实现了完整的多模态对话体验。

**适用场景：** 作为付费项目的免费 Demo 展示，演示 AI 虚拟角色的核心交互能力。

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 🎨 前端渲染 | Three.js + three-vrm | VRM 3D 模型展示 |
| 🧠 AI 对话 | Ollama | 本地大语言模型 |
| 🎵 语音合成 | ChatTTS | 高质量 TTS 引擎 |
| 🎤 语音识别 | SenseVoice | 高精度 ASR 服务 |
| ⚡ 后端框架 | FastAPI | 异步 Web 服务 |

---

## ✨ 功能特性

### 🎯 核心功能

<table>
<tr>
<td width="50%">

**💬 智能对话**
- 多轮对话上下文记忆
- 支持 Gemma2/Llama2/Qwen 等模型
- 实时流式响应（打字机效果）
- 本地部署，数据隐私安全

**🎵 语音交互**
- ChatTTS 40+ 种音色可选
- SenseVoice 高精度语音识别
- 浏览器原生语音识别降级
- 音频智能缓存机制

</td>
<td width="50%">

**🎭 3D 角色动画**
- VRM 1.0 标准格式支持
- 口型同步（TTS 播放时）
- 情感表情（开心/悲伤/惊讶等）
- 手势动作（挥手/点头/摇头等）
- 视线追踪（鼠标跟随）
- 自然待机动画（呼吸/眨眼）

**🚀 性能优化**
- GPU/CPU 自动降级
- 音频缓存（LRU 策略）
- 异步并发处理
- 实时性能监控面板

</td>
</tr>
</table>

### 🎨 交互体验

- ✅ **对话历史管理**：本地存储，支持导出 TXT/JSON
- ✅ **音色实时预览**：切换音色前可预先试听
- ✅ **双模式语音识别**：SenseVoice ↔ 浏览器原生
- ✅ **TTS 队列管理**：多条消息按序播放，可随时停止
- ✅ **性能监控**：FPS、内存、API 响应时间实时显示
- ✅ **引导教程**：首次使用的交互式引导
- ✅ **分享功能**：支持截图分享对话

---

## 🚀 快速开始

### 📋 环境要求

```
✅ Python 3.8+
✅ 8GB+ 内存（推荐 16GB）
✅ 现代浏览器（Chrome/Firefox/Edge）
⚠️ CUDA 11.8+（可选，用于 GPU 加速）
⚠️ Ollama 已安装并运行
```

### ⚡ 一键启动（推荐）

```bash
# 1️⃣ 克隆项目
git clone <your-repo-url>
cd AI-EVA

# 2️⃣ 安装依赖
pip install -r requirements.txt

# 💡 如需 GPU 加速（可选）
# pip uninstall torch torchaudio
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
# pip install -r requirements-gpu.txt

# 3️⃣ 一键启动
start-all.bat  # Windows
# ./start-all.sh  # Linux/Mac

# 4️⃣ 访问界面
# 打开浏览器访问: http://localhost:8000
```

### 🔧 手动启动（可选）

如果需要分别启动各个服务：

```bash
# 终端 1 - ChatTTS 服务（必需）
uvicorn chattts_api:app --host 0.0.0.0 --port 9966

# 终端 2 - SenseVoice 服务（可选）
cd SenseVoice && python api.py

# 终端 3 - Ollama 服务（必需）
ollama serve

# 终端 4 - 前端服务（必需）
python -m http.server 8000
```

### 📡 服务端口

| 服务 | 端口 | 状态检查 | 必需性 |
|------|------|---------|--------|
| 🌐 前端界面 | 8000 | http://localhost:8000 | ✅ 必需 |
| 🎵 ChatTTS | 9966 | http://localhost:9966/ | ✅ 必需 |
| 🧠 Ollama | 11434 | http://localhost:11434/api/tags | ✅ 必需 |
| 🎤 SenseVoice | 50000 | http://localhost:50000/ | ⚠️ 可选 |

---

## 🎮 使用指南

### 🌟 首次使用

1. **启动服务**
   ```bash
   start-all.bat
   ```

2. **上传 VRM 模型**
   - 拖拽 `.vrm` 文件到浏览器窗口
   - 或点击设置 ⚙️ → 上传模型

3. **配置 AI 模型**
   - 设置 → Ollama 模型选择（如 `gemma2:2b`）
   - 设置 → ChatTTS 音色选择（如 `1031.pt`）

4. **开始对话**
   - 输入框输入文字，按 Enter 发送
   - 点击 🎤 按钮使用语音输入

### 🎛️ 功能面板

<table>
<tr>
<td width="33%">

**⚙️ 设置面板**
- Ollama 模型配置
- ChatTTS 音色切换
- 语速调节（0.5x-2.0x）
- SenseVoice 开关
- 音色实时预览

</td>
<td width="33%">

**🎭 骨骼控制**
- 头部旋转
- 眼睛位置
- 手臂姿态
- 表情强度
- 动画速度

</td>
<td width="33%">

**📊 性能监控**
- FPS 显示
- 内存使用
- API 响应时间
- 缓存命中率
- 清空统计

</td>
</tr>
</table>

### 🔥 高级功能

**对话历史管理**
- 💾 自动保存到 LocalStorage
- 📤 导出为 TXT 文本
- 📊 导出为 JSON 格式
- 🗑️ 清空历史记录

**TTS 控制**
- ▶️ 队列播放（多条消息按序）
- ⏸️ 随时停止当前播放
- 🔊 音色预览（切换前试听）
- 💾 智能缓存（重复文本不重新生成）

**语音识别**
- 🎤 SenseVoice 高精度识别
- 🌐 浏览器原生识别降级
- 🔄 一键切换识别模式

---

## 🔧 配置说明

### 📝 环境变量

创建 `.env` 文件（复制 `.env.example`）：

```bash
# ========== 服务端口 ==========
CHAT_TTS_PORT=9966
SENSEVOICE_PORT=50000
OLLAMA_PORT=11434

# ========== AI 模型 ==========
DEFAULT_OLLAMA_MODEL=gemma2:2b
DEFAULT_VOICE=1031.pt

# ========== 性能配置 ==========
USE_GPU=true                     # 自动降级到 CPU
MAX_CONCURRENT_REQUESTS=5        # 最大并发请求数
AUDIO_CACHE_SIZE=100             # 音频缓存大小（MB）

# ========== 日志配置 ==========
LOG_LEVEL=INFO
LOG_FILE=ai-eva.log
```

### 🎨 VRM 模型要求

- **格式**：VRM 1.0 标准
- **大小**：建议 < 50MB
- **骨骼**：标准人形骨骼
- **表情**：支持 VRM BlendShape

**推荐模型来源：**
- [VRoid Hub](https://hub.vroid.com/)
- [Booth.pm](https://booth.pm/)
- [Sketchfab](https://sketchfab.com/)

### 🧠 Ollama 模型推荐

| 模型 | 大小 | 速度 | 质量 | 推荐场景 |
|------|------|------|------|---------|
| gemma2:2b | 1.6GB | ⚡⚡⚡ | ★★☆ | 快速测试 |
| qwen2.5:3b | 2.0GB | ⚡⚡☆ | ★★★ | 平衡选择 |
| llama3.2:3b | 2.0GB | ⚡⚡☆ | ★★★ | 英文对话 |
| qwen2.5:7b | 4.7GB | ⚡☆☆ | ★★★★ | 高质量 |

```bash
# 下载模型
ollama pull gemma2:2b
ollama pull qwen2.5:3b
```

---

## 📂 项目结构

```
AI-EVA/
├── 📄 test0037.html              # 前端主界面
├── 🐍 chattts_api.py             # ChatTTS API 服务
├── 🐍 sensevoice_api.py          # SenseVoice API 适配器
├── 🐍 config.py                  # 配置管理
├── 📝 start-all.bat              # 一键启动脚本
├── 📦 requirements.txt           # Python 依赖
├── 📦 requirements-gpu.txt       # GPU 版本依赖
├── 📋 .env.example               # 环境变量模板
├── 📖 README.md                  # 项目文档
├── 🔧 TROUBLESHOOTING.md         # 故障排除指南
├── 🗂️ SenseVoice/                # SenseVoice 模块
│   ├── api.py                   # SenseVoice API
│   ├── model.py                 # 模型定义
│   └── ...
└── 🛠️ utils/                     # 工具模块
    ├── logger.py                # 日志工具
    └── audio_cache.py           # 音频缓存
```

---

## ❓ 常见问题

### 🐛 安装与启动

<details>
<summary><b>Q: pip 安装依赖失败？</b></summary>

```bash
# 使用国内镜像加速
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或升级 pip
python -m pip install --upgrade pip
```
</details>

<details>
<summary><b>Q: CUDA 不可用错误？</b></summary>

**无需担心！** 程序会自动降级到 CPU 模式，不影响使用。

如需 GPU 加速：
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```
</details>

<details>
<summary><b>Q: 端口被占用？</b></summary>

```bash
# Windows 查看占用
netstat -ano | findstr :9966

# 杀死进程
taskkill /PID <进程ID> /F

# 或修改 .env 中的端口配置
```
</details>

### 🎯 功能使用

<details>
<summary><b>Q: 语音识别不准确？</b></summary>

1. **启用 SenseVoice**：设置 → SenseVoice: 开
2. **检查麦克风权限**：浏览器需要麦克风权限
3. **使用 HTTPS 或 localhost**：浏览器安全限制
</details>

<details>
<summary><b>Q: VRM 模型加载失败？</b></summary>

- ✅ 确保是 VRM 1.0 格式
- ✅ 文件大小 < 50MB
- ✅ 使用现代浏览器（Chrome/Firefox/Edge）
- ✅ 清除浏览器缓存（Ctrl+F5）
</details>

<details>
<summary><b>Q: AI 回复速度慢？</b></summary>

1. **使用小模型**：`gemma2:2b` 或 `qwen2.5:3b`
2. **启用 GPU**：安装 CUDA 版本 PyTorch
3. **减少上下文长度**：设置中调整历史记录数
</details>

### 🚀 性能优化

<details>
<summary><b>Q: 如何提升性能？</b></summary>

**GPU 加速：**
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**配置优化：**
```bash
# .env 文件
USE_GPU=true
AUDIO_CACHE_SIZE=200
MAX_CONCURRENT_REQUESTS=10
```

**模型选择：**
- 使用较小的 Ollama 模型
- 启用音频缓存
</details>

**更多问题？** 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 获取详细故障排除指南。

---

## 🛣️ 路线图

- [ ] 支持多角色切换
- [ ] 自定义表情和动作库
- [ ] 语音克隆功能
- [ ] 移动端适配
- [ ] Docker 一键部署
- [ ] WebRTC 实时通话

---

## 📄 许可证

本项目仅供 **学习和演示** 使用，作为付费项目的免费 Demo 展示。

**请遵守：**
- ✅ 个人学习和研究
- ✅ 技术交流和分享
- ❌ 商业用途
- ❌ 二次销售

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

**贡献指南：**
1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 🙏 致谢

感谢以下开源项目：

- [ChatTTS](https://github.com/2noise/ChatTTS) - 高质量 TTS 引擎
- [Ollama](https://ollama.com/) - 本地大语言模型
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) - 语音识别
- [three-vrm](https://github.com/pixiv/three-vrm) - VRM 模型支持
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架

---

<div align="center">

**AI-EVA Demo** - 让 AI 对话更有温度 🎭✨

⭐ 如果这个项目对你有帮助，欢迎 Star！

</div>
