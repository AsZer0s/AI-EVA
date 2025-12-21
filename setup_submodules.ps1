# 设置 Git 子模块脚本
# 用于将 IndexTTS2 和 SenseVoice 添加为子模块

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "设置 Git 子模块" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否已有子模块
$hasIndexTTS = Test-Path ".gitmodules"
if ($hasIndexTTS) {
    Write-Host "检测到已有 .gitmodules 文件" -ForegroundColor Yellow
    git submodule status
    Write-Host ""
    $continue = Read-Host "是否继续设置子模块？(y/n)"
    if ($continue -ne "y") {
        Write-Host "已取消" -ForegroundColor Yellow
        exit
    }
}

Write-Host "步骤 1: 移除现有目录（如果存在）..." -ForegroundColor Yellow

# 移除 index-tts（如果存在且不是子模块）
if (Test-Path "index-tts") {
    $isSubmodule = Test-Path "index-tts\.git"
    if (-not $isSubmodule) {
        Write-Host "  移除 index-tts 目录..." -ForegroundColor Gray
        try {
            Remove-Item -Recurse -Force "index-tts" -ErrorAction Stop
            Write-Host "  ✅ index-tts 已移除" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️ 无法完全移除 index-tts，部分文件可能被占用" -ForegroundColor Yellow
            Write-Host "  💡 提示: 请手动关闭可能占用文件的程序后重试" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ✅ index-tts 已经是子模块" -ForegroundColor Green
    }
}

# 移除 SenseVoice（如果存在且不是子模块）
if (Test-Path "SenseVoice") {
    $isSubmodule = Test-Path "SenseVoice\.git"
    if (-not $isSubmodule) {
        Write-Host "  移除 SenseVoice 目录..." -ForegroundColor Gray
        try {
            Remove-Item -Recurse -Force "SenseVoice" -ErrorAction Stop
            Write-Host "  ✅ SenseVoice 已移除" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️ 无法完全移除 SenseVoice，部分文件可能被占用" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ✅ SenseVoice 已经是子模块" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "步骤 2: 添加子模块..." -ForegroundColor Yellow

# 添加 IndexTTS2 子模块
if (-not (Test-Path "index-tts\.git")) {
    Write-Host "  添加 IndexTTS2 子模块..." -ForegroundColor Gray
    git submodule add https://github.com/index-tts/index-tts.git index-tts
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ IndexTTS2 子模块添加成功" -ForegroundColor Green
    } else {
        Write-Host "  ❌ IndexTTS2 子模块添加失败" -ForegroundColor Red
    }
} else {
    Write-Host "  ✅ IndexTTS2 子模块已存在" -ForegroundColor Green
}

# 添加 SenseVoice 子模块
if (-not (Test-Path "SenseVoice\.git")) {
    Write-Host "  添加 SenseVoice 子模块..." -ForegroundColor Gray
    git submodule add https://github.com/FunAudioLLM/SenseVoice.git SenseVoice
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ SenseVoice 子模块添加成功" -ForegroundColor Green
    } else {
        Write-Host "  ❌ SenseVoice 子模块添加失败" -ForegroundColor Red
    }
} else {
    Write-Host "  ✅ SenseVoice 子模块已存在" -ForegroundColor Green
}

Write-Host ""
Write-Host "步骤 3: 初始化子模块..." -ForegroundColor Yellow
git submodule update --init --recursive
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ 子模块初始化成功" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ 子模块初始化可能有问题，请检查" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "子模块设置完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "1. 下载 IndexTTS2 模型文件:" -ForegroundColor White
Write-Host "   cd index-tts" -ForegroundColor Gray
Write-Host "   modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 提交子模块配置:" -ForegroundColor White
Write-Host "   git add .gitmodules index-tts SenseVoice" -ForegroundColor Gray
Write-Host "   git commit -m 'Add IndexTTS2 and SenseVoice as submodules'" -ForegroundColor Gray
Write-Host ""

