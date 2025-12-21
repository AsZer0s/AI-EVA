#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI-EVA 项目一键安装依赖脚本
自动安装整个项目所需的所有依赖包，包括：
- 项目基础依赖
- ASR 模块依赖（SenseVoice）
- TTS 模块依赖（IndexTTS2）
- LLM 模块依赖
- WebUI 模块依赖
"""
import sys
import io
import subprocess
import re
from pathlib import Path
from collections import defaultdict

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 使用清华源加速下载
TSINGHUA_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"

# IndexTTS2 特殊依赖（必须精确版本）
indextts_special_deps = [
    "accelerate==1.8.1",
    "cn2an==0.5.22",
    "cython==3.0.7",
    "descript-audiotools==0.7.2",
    "einops>=0.8.1",
    "ffmpeg-python==0.2.0",
    "g2p-en==2.1.0",
    "jieba==0.42.1",
    "json5==0.10.0",
    "keras==2.9.0",
    "librosa==0.10.2.post1",
    "matplotlib==3.8.2",
    "modelscope==1.27.0",
    "munch==4.0.0",
    "numba==0.58.1",
    "numpy==1.26.2",  # 重要：必须使用 1.26.2
    "omegaconf>=2.3.0",
    "opencv-python==4.9.0.80",
    "pandas==2.3.2",
    "safetensors==0.5.2",
    "sentencepiece>=0.2.1",
    "tensorboard==2.9.1",
    "textstat>=0.7.10",
    "tokenizers==0.21.0",
    "tqdm>=4.67.1",
    "transformers==4.52.1",  # 重要：必须使用 4.52.1
    "wetext>=0.0.9",  # Windows/Mac
]

def parse_requirements_file(file_path):
    """解析 requirements.txt 文件"""
    dependencies = []
    if not file_path.exists():
        return dependencies
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            # 移除行内注释
            if '#' in line:
                line = line.split('#')[0].strip()
            if line:
                dependencies.append(line)
    
    return dependencies

def merge_dependencies(all_deps):
    """合并依赖，处理版本冲突"""
    merged = {}
    
    # IndexTTS2 特殊版本要求（优先级最高）
    special_versions = {
        'transformers': '4.52.1',
        'numpy': '1.26.2',
    }
    
    for dep in all_deps:
        # 提取包名
        name = None
        if '==' in dep:
            name = dep.split('==')[0].strip()
        elif '>=' in dep:
            name = dep.split('>=')[0].strip()
        elif '<=' in dep:
            name = dep.split('<=')[0].strip()
        elif '<' in dep and '>' not in dep:
            name = dep.split('<')[0].strip()
        elif '>' in dep and '<' not in dep:
            name = dep.split('>')[0].strip()
        else:
            name = dep.split()[0].strip()
        
        if not name:
            continue
        
        # 如果是指定的特殊包，使用特殊版本
        if name in special_versions:
            merged[name] = f"{name}=={special_versions[name]}"
            continue
        
        # 普通合并逻辑
        if name not in merged:
            merged[name] = dep
        else:
            existing = merged[name]
            # 如果已有精确版本（==），保留
            if '==' in existing:
                # 除非新的是特殊版本要求
                if name in special_versions and '==' in dep:
                    merged[name] = dep
            # 如果新的是精确版本，优先使用
            elif '==' in dep:
                merged[name] = dep
            # 否则保留更严格的版本要求
            else:
                # 简单策略：保留第一个非精确版本要求
                pass
    
    return list(merged.values())

def compare_versions(v1, v2):
    """比较版本号"""
    def normalize_version(v):
        return [int(x) for x in re.sub(r'[^\d.]', '', v).split('.')]
    
    v1_parts = normalize_version(v1)
    v2_parts = normalize_version(v2)
    
    for i in range(max(len(v1_parts), len(v2_parts))):
        v1_val = v1_parts[i] if i < len(v1_parts) else 0
        v2_val = v2_parts[i] if i < len(v2_parts) else 0
        if v1_val > v2_val:
            return 1
        elif v1_val < v2_val:
            return -1
    return 0

def print_step(step_num, message):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {message}")
    print('='*60)

def check_and_install_package(package, force_reinstall=False):
    """检查并安装包（使用清华源）"""
    package_name = package.split('==')[0].split('>=')[0].split('>')[0]
    
    try:
        # 检查是否已安装
        __import__(package_name.replace('-', '_'))
        if force_reinstall:
            print(f"   重新安装 {package}...")
            subprocess.run([sys.executable, "-m", "pip", "install", package, 
                          "--force-reinstall", "-i", TSINGHUA_MIRROR, "-q"], 
                         check=True, capture_output=True)
            print(f"   ✅ {package_name} 重新安装成功")
        else:
            print(f"   ✅ {package_name} 已安装，跳过")
        return True
    except ImportError:
        print(f"   安装 {package}...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package, 
                          "-i", TSINGHUA_MIRROR, "-q"], 
                         check=True, capture_output=True)
            print(f"   ✅ {package_name} 安装成功")
            return True
        except subprocess.CalledProcessError:
            print(f"   ⚠️ {package_name} 安装失败")
            return False

def main():
    """主函数"""
    print("="*60)
    print("AI-EVA 项目依赖一键安装脚本")
    print("="*60)
    print(f"📦 使用镜像源: {TSINGHUA_MIRROR}")
    print()
    
    # 步骤 0: 收集所有依赖文件
    print_step(0, "收集项目依赖文件")
    
    requirements_files = [
        ("项目基础依赖", PROJECT_ROOT / "requirements.txt"),
        ("ASR 模块依赖", PROJECT_ROOT / "modules" / "asr" / "requirements.txt"),
        ("TTS 模块依赖", PROJECT_ROOT / "modules" / "tts" / "requirements.txt"),
        ("LLM 模块依赖", PROJECT_ROOT / "modules" / "llm" / "requirements.txt"),
        ("WebUI 模块依赖", PROJECT_ROOT / "modules" / "webui" / "requirements.txt"),
        ("SenseVoice 依赖", PROJECT_ROOT / "SenseVoice" / "requirements.txt"),
    ]
    
    all_dependencies = []
    found_files = []
    
    for name, file_path in requirements_files:
        deps = parse_requirements_file(file_path)
        if deps:
            print(f"   ✅ {name}: {file_path.name} ({len(deps)} 个依赖)")
            all_dependencies.extend(deps)
            found_files.append((name, file_path, deps))
        else:
            if file_path.exists():
                print(f"   ⚠️ {name}: {file_path.name} (空文件)")
            else:
                print(f"   ⚠️ {name}: {file_path.name} (文件不存在)")
    
    # 添加 IndexTTS2 特殊依赖
    print(f"   ✅ IndexTTS2 特殊依赖: {len(indextts_special_deps)} 个")
    all_dependencies.extend(indextts_special_deps)
    
    # 合并依赖
    print(f"\n   合并依赖中...")
    merged_deps = merge_dependencies(all_dependencies)
    print(f"   合并后共 {len(merged_deps)} 个依赖")
    
    # 步骤 1: 检查并调整关键依赖版本
    print_step(1, "检查并调整关键依赖版本")
    
    # 检查 transformers
    print("   检查 transformers...")
    try:
        import transformers
        if transformers.__version__ != "4.52.1":
            print(f"   当前版本: {transformers.__version__}，需要降级到 4.52.1")
            subprocess.run([sys.executable, "-m", "pip", "install", "transformers==4.52.1", 
                          "--force-reinstall", "-i", TSINGHUA_MIRROR], 
                         check=True)
            print("   ✅ transformers 已降级到 4.52.1")
        else:
            print("   ✅ transformers 版本正确")
    except ImportError:
        print("   安装 transformers==4.52.1...")
        subprocess.run([sys.executable, "-m", "pip", "install", "transformers==4.52.1", 
                      "-i", TSINGHUA_MIRROR], check=True)
        print("   ✅ transformers 安装成功")
    
    # 检查 numpy
    print("   检查 numpy...")
    try:
        import numpy
        if numpy.__version__ != "1.26.2":
            print(f"   当前版本: {numpy.__version__}，需要降级到 1.26.2")
            subprocess.run([sys.executable, "-m", "pip", "install", "numpy==1.26.2", 
                          "--force-reinstall", "-i", TSINGHUA_MIRROR], 
                         check=True)
            print("   ✅ numpy 已降级到 1.26.2")
        else:
            print("   ✅ numpy 版本正确")
    except ImportError:
        print("   安装 numpy==1.26.2...")
        subprocess.run([sys.executable, "-m", "pip", "install", "numpy==1.26.2", 
                      "-i", TSINGHUA_MIRROR], check=True)
        print("   ✅ numpy 安装成功")
    
    # 检查并升级 protobuf
    print("   检查 protobuf...")
    try:
        import google.protobuf
        # 检查版本是否 >= 3.20.3
        protobuf_version = google.protobuf.__version__
        version_parts = [int(x) for x in protobuf_version.split('.')]
        if version_parts < [3, 20, 3]:
            print(f"   当前版本: {protobuf_version}，需要升级到 >= 3.20.3")
            subprocess.run([sys.executable, "-m", "pip", "install", "protobuf>=3.20.3", 
                          "--upgrade", "-i", TSINGHUA_MIRROR], 
                         check=True)
            print("   ✅ protobuf 已升级")
        else:
            print(f"   ✅ protobuf 版本: {protobuf_version}")
    except ImportError:
        print("   安装 protobuf>=3.20.3...")
        subprocess.run([sys.executable, "-m", "pip", "install", "protobuf>=3.20.3", 
                      "-i", TSINGHUA_MIRROR], check=True)
        print("   ✅ protobuf 安装成功")
    
    # 步骤 2: 安装项目依赖
    print_step(2, "安装项目所有依赖")
    
    # 按优先级排序：先安装基础依赖，再安装特殊依赖
    priority_deps = []
    normal_deps = []
    
    for dep in merged_deps:
        dep_lower = dep.lower()
        # 优先安装的包
        if any(keyword in dep_lower for keyword in ['fastapi', 'uvicorn', 'pydantic', 'pyyaml', 'torch', 'torchaudio']):
            priority_deps.append(dep)
        elif dep.startswith("numpy") or dep.startswith("transformers"):
            # 已处理，跳过
            continue
        else:
            normal_deps.append(dep)
    
    print(f"   优先安装依赖: {len(priority_deps)} 个")
    print(f"   普通依赖: {len(normal_deps)} 个")
    
    failed = []
    
    # 安装优先依赖
    if priority_deps:
        print("\n   安装优先依赖...")
        for dep in priority_deps:
            if not check_and_install_package(dep):
                failed.append(dep)
    
    # 安装普通依赖
    if normal_deps:
        print("\n   安装普通依赖...")
        for dep in normal_deps:
            if not check_and_install_package(dep):
                failed.append(dep)
    
    # 步骤 3: 验证安装
    print_step(3, "验证核心依赖")
    
    # 项目核心依赖
    core_deps = {
        # Web 框架
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'pydantic': 'pydantic',
        # 配置管理
        'pyyaml': 'yaml',
        # PyTorch
        'torch': 'torch',
        'torchaudio': 'torchaudio',
        # IndexTTS2 核心
        'json5': 'json5',
        'cn2an': 'cn2an',
        'einops': 'einops',
        'jieba': 'jieba',
        'librosa': 'librosa',
        'omegaconf': 'omegaconf',
        'sentencepiece': 'sentencepiece',
        'accelerate': 'accelerate',
        'munch': 'munch',
        # ASR 相关
        'funasr': 'funasr',
        'modelscope': 'modelscope',
        # HTTP 客户端
        'httpx': 'httpx',
        # 系统监控
        'psutil': 'psutil',
    }
    
    all_ok = True
    for name, module in core_deps.items():
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} 未安装")
            all_ok = False
    
    # 步骤 4: 测试 IndexTTS2 导入
    print_step(4, "测试 IndexTTS2 模块导入")
    
    try:
        import sys
        from pathlib import Path
        index_tts_path = Path(__file__).parent / "index-tts"
        if index_tts_path.exists():
            sys.path.insert(0, str(index_tts_path))
            from indextts.infer_v2 import IndexTTS2
            print("   ✅ IndexTTS2 模块导入成功")
        else:
            print("   ⚠️ index-tts 目录不存在，跳过导入测试")
            print("   💡 提示: 请确保 index-tts 目录在项目根目录下")
    except ImportError as e:
        print(f"   ⚠️ IndexTTS2 导入失败: {e}")
        print("   💡 提示: 可能还需要安装其他依赖或下载模型文件")
    
    # 总结
    print("\n" + "="*60)
    print("安装总结")
    print("="*60)
    
    if failed:
        print(f"\n⚠️ 以下依赖安装失败 ({len(failed)} 个):")
        for dep in failed:
            print(f"   - {dep}")
        print("\n💡 提示: 可以稍后手动安装这些依赖")
    else:
        print("\n✅ 所有依赖安装成功！")
    
    if all_ok:
        print("\n✅ 核心依赖验证通过")
    else:
        print("\n⚠️ 部分核心依赖验证失败，请检查安装日志")
    
    print("\n" + "="*60)
    print("下一步操作:")
    print("="*60)
    print("1. 下载模型文件（如果还没有）:")
    print("   # IndexTTS2 模型")
    print("   cd index-tts")
    print("   modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints")
    print()
    print("   # SenseVoice 模型会自动下载（首次使用时）")
    print()
    print("2. 启动服务:")
    print("   # 方式一：使用启动器（推荐）")
    print("   python launcher.py")
    print()
    print("   # 方式二：单独启动各模块")
    print("   python -m modules.asr.asr_worker    # ASR 服务")
    print("   python -m modules.tts.tts_worker    # TTS 服务")
    print("   python -m modules.webui.app          # WebUI 服务")
    print()
    print("3. 访问服务:")
    print("   - 服务管理器: http://localhost:9000")
    print("   - 前端界面: http://localhost:8000")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 安装过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

