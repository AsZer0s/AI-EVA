# AI-EVA 模块化架构说明

## 📁 目录结构

```
Project_Root/
│
├── launcher.py               # [Launcher] 核心启动脚本 (总指挥)
├── config.yaml               # [配置] 全局配置文件
├── requirements.txt          # [依赖] 项目基础依赖
├── README.md                 # 项目说明文档
│
├── bin/                      # 启动脚本
│   ├── start_windows.bat
│   └── start_linux.sh
│
├── modules/                  # [核心组件] 各个功能模块的代码
│   ├── __init__.py
│   │
│   ├── asr/                  # [SenseVoice] 语音转文字模块
│   │   ├── asr_worker.py     # SenseVoice 的推理代码
│   │   ├── utils.py
│   │   └── requirements.txt  # 该模块特有的依赖
│   │
│   ├── llm/                  # [Ollama] 大语言模型连接器
│   │   ├── ollama_client.py  # 调用 Ollama API 的客户端代码
│   │   ├── prompt_templates.py # 存储 System Prompts
│   │   └── requirements.txt
│   │
│   ├── tts/                  # [IndexTTS2] 文字转语音模块
│   │   ├── tts_worker.py     # IndexTTS2 的推理代码
│   │   └── requirements.txt
│   │
│   └── webui/                # [WebUI] 前端交互界面
│       ├── app.py            # FastAPI 服务管理器
│       └── requirements.txt
│
├── models/                   # [模型权重] 集中存放模型文件
│   ├── sense_voice/        
│   └── index_tts/
│
├── voices/                   # [TTS参考音频] 存放用于克隆的参考音色
│
├── temp/                     # [数据交换] 存放管道流转中的临时文件
│
└── logs/                     # [日志] 系统运行日志
```

## 🔑 核心设计理念

### 1. 模块化分离
- **代码与模型分离**: 模型文件存放在 `models/` 目录，代码存放在 `modules/` 目录
- **功能模块解耦**: 每个模块独立运行，通过 HTTP API 通信
- **统一配置管理**: 所有配置集中在 `config.yaml`

### 2. 数据流转
- **临时文件**: `temp/` 目录用于存放处理过程中的临时文件
- **日志文件**: `logs/` 目录集中管理所有日志
- **模型文件**: `models/` 目录统一存放模型权重

### 3. 启动方式
- **统一启动器**: `launcher.py` 负责启动和管理所有模块
- **独立启动**: 每个模块也可以独立运行（用于调试）

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 安装各模块依赖（可选，如果需要独立运行模块）
pip install -r modules/asr/requirements.txt
pip install -r modules/tts/requirements.txt
pip install -r modules/llm/requirements.txt
pip install -r modules/webui/requirements.txt
```

### 2. 配置设置

编辑 `config.yaml` 文件，配置各模块的参数：

```yaml
modules:
  asr:
    enabled: true
    device: "cuda:0"
    port: 50000
    
  tts:
    enabled: true
    port: 9966
    
  webui:
    enabled: true
    port: 8000
    manager_port: 9000
```

### 3. 启动服务

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

### 4. 访问服务

- **服务管理器**: http://localhost:9000
- **前端界面**: http://localhost:8000
- **ASR API**: http://localhost:50000
- **TTS API**: http://localhost:9966

## 📝 模块说明

### ASR 模块 (modules/asr/)
- **功能**: 语音转文字
- **技术**: SenseVoice
- **端口**: 50000 (可配置)
- **独立启动**: `python -m modules.asr.asr_worker`

### TTS 模块 (modules/tts/)
- **功能**: 文字转语音
- **技术**: IndexTTS2
- **端口**: 9966 (可配置)
- **独立启动**: `python -m modules.tts.tts_worker`

### LLM 模块 (modules/llm/)
- **功能**: 大语言模型交互
- **技术**: Ollama
- **说明**: Ollama 需要单独安装和启动

### WebUI 模块 (modules/webui/)
- **功能**: 服务管理和前端界面
- **技术**: FastAPI
- **端口**: 8000 (前端), 9000 (管理器)
- **独立启动**: `python -m modules.webui.app`

## ⚙️ 配置说明

### config.yaml 结构

```yaml
system:
  temp_dir: "./temp"      # 临时文件目录
  log_dir: "./logs"       # 日志目录

modules:
  asr:
    enabled: true         # 是否启用
    device: "cuda:0"      # 设备
    port: 50000           # 端口
    
  tts:
    enabled: true
    port: 9966
    
  llm:
    base_url: "http://localhost:11434"
    model_name: "qwen2.5:7b"
    
  webui:
    enabled: true
    port: 8000
    manager_port: 9000

logging:
  level: "INFO"
  save_to_file: true

performance:
  use_gpu: true
  enable_audio_cache: true
```

## 🔧 开发指南

### 添加新模块

1. 在 `modules/` 下创建新目录
2. 创建模块代码和 `requirements.txt`
3. 在 `config.yaml` 中添加配置
4. 在 `launcher.py` 中添加启动逻辑

### 调试模块

每个模块都可以独立运行：

```bash
# ASR 模块
python -m modules.asr.asr_worker

# TTS 模块
python -m modules.tts.tts_worker

# WebUI 模块
python -m modules.webui.app
```

## 📊 性能优化建议

1. **临时文件目录**: 建议将 `temp/` 目录挂载到 RAM Disk 或 SSD
2. **GPU 加速**: 在 `config.yaml` 中启用 GPU
3. **音频缓存**: 启用音频缓存以减少重复生成
4. **并发控制**: 根据硬件配置调整 `max_concurrent_requests`

## 🐛 故障排查

### 模块启动失败
1. 检查端口是否被占用
2. 检查依赖是否安装完整
3. 查看 `logs/` 目录下的日志文件

### 模型加载失败
1. 检查模型文件是否存在
2. 检查模型路径配置是否正确
3. 检查 GPU 是否可用（如果使用 GPU）

## 📚 更多信息

- 各模块的详细文档请查看 `modules/*/README.md`
- 配置文件示例请参考 `config.yaml`
- 问题反馈请查看项目 Issues

