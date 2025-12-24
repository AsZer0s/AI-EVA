# CosyVoice TTS 安装指南

CosyVoice不能直接通过modelscope pipeline使用，需要从GitHub安装。

## 安装步骤

### 1. 克隆CosyVoice仓库

```bash
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice

# 如果子模块克隆失败，运行以下命令直到成功
git submodule update --init --recursive
```

### 2. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 如果遇到sox兼容性问题（Windows通常不需要）
# Ubuntu:
# sudo apt-get install sox libsox-dev
# CentOS:
# sudo yum install sox sox-devel
```

### 3. 配置CosyVoice路径

有两种方式让项目找到CosyVoice：

**方式1：将CosyVoice放在项目目录下**
```bash
# 在项目根目录下
cd C:\Users\AsZero\Desktop\project\Text2A
# 将CosyVoice目录复制到这里
```

**方式2：设置PYTHONPATH环境变量**
```powershell
# Windows PowerShell
$env:PYTHONPATH = "C:\path\to\CosyVoice;$env:PYTHONPATH"

# 或者在系统环境变量中添加
```

### 4. 下载模型

模型会在首次使用时自动下载，或者手动下载：

```python
from modelscope import snapshot_download

# 下载Fun-CosyVoice3-0.5B模型（推荐）
snapshot_download('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', 
                  local_dir='pretrained_models/Fun-CosyVoice3-0.5B')
```

## 验证安装

启动服务器后，如果看到以下日志，说明TTS已成功加载：

```
✓ TTS模型加载成功（CosyVoice Synthesizer）
```

## 故障排除

### 问题1：ImportError: No module named 'cosyvoice'

**解决方法：**
- 确保CosyVoice目录在Python路径中
- 检查CosyVoice目录下是否有`cosyvoice`模块
- 尝试设置PYTHONPATH环境变量

### 问题2：模型下载失败

**解决方法：**
- 检查网络连接
- 尝试使用镜像源
- 手动下载模型到指定目录

### 问题3：依赖冲突

**解决方法：**
- 创建独立的conda环境
- 按照CosyVoice官方文档安装依赖

## 参考链接

- CosyVoice GitHub: https://github.com/FunAudioLLM/CosyVoice
- 模型下载: https://www.modelscope.cn/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512

