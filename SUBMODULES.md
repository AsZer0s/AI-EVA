# 子模块设置说明

## 📦 子模块配置

本项目使用 Git 子模块来管理第三方依赖：
- **IndexTTS2**: 从官方仓库拉取
- **SenseVoice**: 从官方仓库拉取

## 🚀 首次克隆项目后初始化子模块

```bash
# 克隆项目（包含子模块）
git clone --recursive <your-repo-url>

# 或者如果已经克隆了项目，初始化子模块
git submodule update --init --recursive
```

## 📥 添加子模块（如果还没有）

如果子模块还没有设置，可以使用以下命令添加：

```bash
# 添加 IndexTTS2 子模块
git submodule add https://github.com/index-tts/index-tts.git index-tts

# 添加 SenseVoice 子模块
git submodule add https://github.com/FunAudioLLM/SenseVoice.git SenseVoice

# 初始化子模块
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

## 📋 子模块信息

### IndexTTS2
- **仓库地址**: https://github.com/index-tts/index-tts
- **本地路径**: `index-tts/`
- **用途**: 文字转语音（TTS）引擎

### SenseVoice
- **仓库地址**: https://github.com/FunAudioLLM/SenseVoice
- **本地路径**: `SenseVoice/`
- **用途**: 语音识别（ASR）引擎

## ⚠️ 注意事项

1. **模型文件**: 子模块中的模型文件（checkpoints）不会被提交，需要单独下载
2. **更新子模块**: 更新子模块后需要提交 `.gitmodules` 文件
3. **删除子模块**: 如果需要移除子模块：
   ```bash
   git submodule deinit -f index-tts
   git rm -f index-tts
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

