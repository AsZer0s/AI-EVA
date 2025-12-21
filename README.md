# AI-EVA

<div align="center">

🎭 **AI 虚拟女友对话系统** 

基于 VRM 3D 模型的智能交互 Demo

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Demo-orange.svg)](LICENSE)

[快速开始](#-快速开始) • [功能特性](#-功能特性) • [架构说明](#-架构说明) • [配置指南](#-配置指南) • [常见问题](#-常见问题)

</div>

---

## 📖 项目简介

AI-EVA 是一个集成了 **语音合成**、**AI 对话**、**语音识别** 的 3D 虚拟角色交互系统。通过整合 IndexTTS2、Ollama、SenseVoice 等开源技术，实现了完整的多模态对话体验。

**核心特点：**
- 🏗️ **模块化架构**：代码与模型分离，功能模块解耦，易于维护和扩展
- 🚀 **统一启动器**：一键启动所有服务，自动管理模块生命周期
- ⚙️ **集中配置**：所有配置集中在 `config.yaml`，简单易用
- 📦 **子模块管理**：使用 Git 子模块管理第三方依赖，保持代码同步

**适用场景：** 作为付费项目的免费 Demo 展示，演示 AI 虚拟角色的核心交互能力。

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 🎨 前端渲染 | Three.js + three-vrm | VRM 3D 模型展示 |
| 🧠 AI 对话 | Ollama | 本地大语言模型 |
| 🎵 语音合成 | IndexTTS2 | 高质量 TTS 引擎，支持语音克隆 |
| 🎤 语音识别 | SenseVoice | 高精度 ASR 服务 |
| ⚡ 后端框架 | FastAPI | 异步 Web 服务 |
| 🔧 启动器 | Python Subprocess | 统一服务管理 |

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
- IndexTTS2 支持语音克隆和情感控制
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

### ⚡ 一键安装与启动

#### 1️⃣ 克隆项目（包含子模块）

```bash
# 克隆项目（包含子模块）
git clone --recursive <your-repo-url>
cd AI-EVA

# 如果已经克隆了项目，初始化子模块
git submodule update --init --recursive
```

#### 2️⃣ 安装依赖

```bash
# 使用一键安装脚本（推荐，自动处理依赖冲突，使用清华源）
python install_deps.py

# 或手动安装
pip install -r requirements.txt
pip install -r modules/asr/requirements.txt
pip install -r modules/tts/requirements.txt
pip install -r modules/llm/requirements.txt
pip install -r modules/webui/requirements.txt
```

#### 3️⃣ 下载模型文件

```bash
# IndexTTS2 模型（必需）
cd index-tts
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
cd ..

# SenseVoice 模型会在首次使用时自动下载
```

#### 4️⃣ 配置 Ollama

确保 Ollama 已安装并运行：

```bash
# 安装 Ollama（如果未安装）
# Windows: 下载 https://ollama.com/download
# Linux/Mac: curl https://ollama.ai/install.sh | sh

# 启动 Ollama 服务
ollama serve

# 下载模型（在另一个终端）
ollama pull qwen2.5:7b
# 或使用更小的模型
ollama pull qwen2.5:3b
```

#### 5️⃣ 配置项目

编辑 `config.yaml` 文件，配置各模块参数：

```yaml
modules:
  llm:
    model_name: "qwen2.5:7b"  # 修改为你下载的模型
  
  tts:
    ref_audio: "./voices/user_ref.wav"  # 设置参考音频路径（可选）
```

#### 6️⃣ 启动服务

**方式一：使用启动器（推荐）**

```bash
python launcher.py
```

**方式二：使用批处理脚本（Windows）**

```bash
bin\start_windows.bat
```

**方式三：使用 Shell 脚本（Linux/Mac）**

```bash
bash bin/start_linux.sh
```

#### 7️⃣ 访问界面

- **前端界面**: http://localhost:8000
- **服务管理器**: http://localhost:9000
- **TTS API**: http://localhost:9966
- **ASR API**: http://localhost:50000

### 📡 服务端口

| 服务 | 端口 | 状态检查 | 必需性 |
|------|------|---------|--------|
| 🌐 前端界面 | 8000 | http://localhost:8000 | ✅ 必需 |
| 🎵 IndexTTS2 | 9966 | http://localhost:9966/ | ✅ 必需 |
| 🧠 Ollama | 11434 | http://localhost:11434/api/tags | ✅ 必需 |
| 🎤 SenseVoice | 50000 | http://localhost:50000/ | ⚠️ 可选 |
| 🔧 服务管理器 | 9000 | http://localhost:9000 | ✅ 必需 |

---

## 🏗️ 架构说明

### 目录结构

```
AI-EVA/
├── launcher.py              # 🚀 统一启动器（核心）
├── config.yaml              # ⚙️ 全局配置文件
├── install_deps.py          # 📦 依赖安装脚本
├── requirements.txt        # 📋 基础依赖
│
├── bin/                     # 🔧 启动脚本
│   ├── start_windows.bat
│   └── start_linux.sh
│
├── modules/                 # 📦 功能模块
│   ├── asr/                 # 🎤 语音识别（SenseVoice）
│   │   ├── asr_worker.py
│   │   └── requirements.txt
│   ├── tts/                 # 🎵 语音合成（IndexTTS2）
│   │   ├── tts_worker.py
│   │   └── requirements.txt
│   ├── llm/                 # 🧠 大语言模型（Ollama）
│   │   ├── ollama_client.py
│   │   └── requirements.txt
│   └── webui/               # 🌐 Web 界面
│       ├── app.py
│       └── requirements.txt
│
├── models/                  # 💾 模型文件目录
│   ├── sense_voice/
│   └── index_tts/
│
├── voices/                  # 🎤 TTS 参考音频
├── temp/                    # 📁 临时文件
├── logs/                    # 📝 日志文件
│
├── index-tts/              # 📦 IndexTTS2 子模块
└── SenseVoice/             # 📦 SenseVoice 子模块
```

### 核心设计理念

1. **模块化分离**
   - 代码与模型分离：模型文件存放在 `models/` 目录
   - 功能模块解耦：每个模块独立运行，通过 HTTP API 通信
   - 统一配置管理：所有配置集中在 `config.yaml`

2. **数据流转**
   - 临时文件：`temp/` 目录用于存放处理过程中的临时文件
   - 日志文件：`logs/` 目录集中管理所有日志
   - 模型文件：`models/` 目录统一存放模型权重

3. **启动方式**
   - 统一启动器：`launcher.py` 负责启动和管理所有模块
   - 独立启动：每个模块也可以独立运行（用于调试）

详细架构说明请查看 [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 🎮 使用指南

### 🌟 首次使用

1. **启动服务**
   ```bash
   python launcher.py
   ```

2. **上传 VRM 模型**
   - 拖拽 `.vrm` 文件到浏览器窗口
   - 或点击设置 ⚙️ → 上传模型

3. **配置 AI 模型**
   - 设置 → Ollama 模型选择（如 `qwen2.5:7b`）
   - 设置 → IndexTTS2 音色选择（支持音频文件路径或默认音色）

4. **开始对话**
   - 输入框输入文字，按 Enter 发送
   - 点击 🎤 按钮使用语音输入

### 🎛️ 功能面板

<table>
<tr>
<td width="33%">

**⚙️ 设置面板**
- Ollama 模型配置
- IndexTTS2 音色切换（支持语音克隆）
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

## 🔧 配置指南

### config.yaml 配置说明

主要配置项：

```yaml
system:
  temp_dir: "./temp"      # 临时文件目录
  log_dir: "./logs"       # 日志目录

modules:
  asr:
    enabled: true         # 是否启用 ASR
    device: "cuda:0"      # 设备：cuda:0, cpu
    port: 50000           # API 端口
    
  tts:
    enabled: true         # 是否启用 TTS
    port: 9966            # API 端口
    preload_model: false  # 启动时预加载模型（true=启动加载，false=延迟加载）
    ref_audio: "./voices/user_ref.wav"  # 参考音频路径
    
  llm:
    base_url: "http://localhost:11434"  # Ollama API 地址
    model_name: "qwen2.5:7b"            # 模型名称
    
  webui:
    enabled: true
    port: 8000            # 前端端口
    manager_port: 9000    # 服务管理器端口
```

完整配置说明请查看 [config.yaml](config.yaml)

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
| qwen2.5:3b | 2.0GB | ⚡⚡☆ | ★★★ | 平衡选择 |
| qwen2.5:7b | 4.7GB | ⚡☆☆ | ★★★★ | 高质量 |
| gemma2:2b | 1.6GB | ⚡⚡⚡ | ★★☆ | 快速测试 |
| llama3.2:3b | 2.0GB | ⚡⚡☆ | ★★★ | 英文对话 |

```bash
# 下载模型
ollama pull qwen2.5:7b
ollama pull qwen2.5:3b
```

---

## 📦 子模块管理

本项目使用 Git 子模块管理第三方依赖：

- **IndexTTS2**: https://github.com/index-tts/index-tts
- **SenseVoice**: https://github.com/FunAudioLLM/SenseVoice

### 初始化子模块

```bash
# 克隆项目时包含子模块
git clone --recursive <your-repo-url>

# 或已克隆后初始化
git submodule update --init --recursive
```

### 更新子模块

```bash
# 更新所有子模块
git submodule update --remote

# 更新特定子模块
git submodule update --remote index-tts
git submodule update --remote SenseVoice
```

详细说明请查看 [SUBMODULES.md](SUBMODULES.md)

---

## ❓ 常见问题

### 🐛 安装与启动

<details>
<summary><b>Q: 子模块克隆失败？</b></summary>

```bash
# 如果克隆时子模块失败，可以手动初始化
git submodule update --init --recursive

# 如果 IndexTTS2 的 LFS 文件下载失败（仓库 LFS 预算超限），可以跳过 LFS
git config --global filter.lfs.smudge "git-lfs smudge --skip %f"
git submodule update --init --recursive index-tts
git config --global --unset filter.lfs.smudge
```
</details>

<details>
<summary><b>Q: pip 安装依赖失败？</b></summary>

```bash
# 使用一键安装脚本（自动使用清华源）
python install_deps.py

# 或手动使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 升级 pip
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

# 或修改 config.yaml 中的端口配置
```
</details>

<details>
<summary><b>Q: 模块启动失败？</b></summary>

1. 检查端口是否被占用
2. 检查依赖是否安装完整：`python install_deps.py`
3. 查看 `logs/` 目录下的日志文件
4. 检查 `config.yaml` 配置是否正确
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

1. **使用小模型**：`qwen2.5:3b` 或 `gemma2:2b`
2. **启用 GPU**：安装 CUDA 版本 PyTorch
3. **减少上下文长度**：设置中调整历史记录数
4. **预加载模型**：在 `config.yaml` 中设置 `tts.preload_model: true`
</details>

### 🚀 性能优化

<details>
<summary><b>Q: 如何提升性能？</b></summary>

**GPU 加速：**
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**配置优化：**
```yaml
# config.yaml
performance:
  use_gpu: true
  enable_audio_cache: true

modules:
  tts:
    preload_model: true  # 启动时预加载模型
    audio_cache_size: 200
  asr:
    max_concurrent_requests: 10
```

**模型选择：**
- 使用较小的 Ollama 模型
- 启用音频缓存
- 预加载 TTS 模型（如果内存充足）
</details>

---

## 🛣️ 路线图

- [ ] 支持多角色切换
- [ ] 自定义表情和动作库
- [ ] 语音克隆功能增强
- [ ] 移动端适配
- [ ] Docker 一键部署
- [ ] WebRTC 实时通话
- [ ] 插件系统支持

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

- [IndexTTS2](https://github.com/index-tts/index-tts) - 高质量 TTS 引擎，支持语音克隆和情感控制
- [Ollama](https://ollama.com/) - 本地大语言模型
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) - 语音识别
- [three-vrm](https://github.com/pixiv/three-vrm) - VRM 模型支持
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架

---

<div align="center">

**AI-EVA Demo** - 让 AI 对话更有温度 🎭✨

⭐ 如果这个项目对你有帮助，欢迎 Star！

</div>
