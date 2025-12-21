# 子模块设置指南

## 📦 关于子模块

本项目使用 Git 子模块来管理第三方依赖库：
- **IndexTTS2**: https://github.com/index-tts/index-tts
- **SenseVoice**: https://github.com/FunAudioLLM/SenseVoice

这样可以：
- ✅ 保持第三方库的更新
- ✅ 减少仓库大小
- ✅ 避免版本冲突

## 🚀 快速设置

### 方法一：使用脚本（推荐）

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File setup_submodules.ps1
```

### 方法二：手动设置

```bash
# 1. 添加 IndexTTS2 子模块
git submodule add https://github.com/index-tts/index-tts.git index-tts

# 2. 添加 SenseVoice 子模块
git submodule add https://github.com/FunAudioLLM/SenseVoice.git SenseVoice

# 3. 初始化子模块
git submodule update --init --recursive
```

## 📥 首次克隆项目

如果克隆项目时没有包含子模块：

```bash
# 克隆项目（包含子模块）
git clone --recursive <your-repo-url>

# 或者克隆后初始化子模块
git clone <your-repo-url>
cd AI-EVA
git submodule update --init --recursive
```

## 🔄 更新子模块

```bash
# 更新所有子模块到最新版本
git submodule update --remote

# 更新特定子模块
git submodule update --remote index-tts
git submodule update --remote SenseVoice
```

## 📝 下载模型文件

子模块初始化后，还需要下载模型文件：

### IndexTTS2 模型
```bash
cd index-tts
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

### SenseVoice 模型
SenseVoice 模型会在首次使用时自动从 ModelScope 下载。

## ⚠️ 注意事项

1. **不要直接修改子模块代码**：如果需要修改，应该 fork 仓库或提交 PR
2. **提交子模块更新**：更新子模块后需要提交 `.gitmodules` 文件
3. **模型文件**：子模块中的模型文件不会被提交，需要单独下载

## 🔧 故障排查

### 子模块显示为空目录

```bash
git submodule update --init --recursive
```

### 移除子模块

```bash
git submodule deinit -f index-tts
git rm -f index-tts
rm -rf .git/modules/index-tts
```

### 检查子模块状态

```bash
git submodule status
```

