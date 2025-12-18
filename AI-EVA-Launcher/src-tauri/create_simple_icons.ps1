# 创建简单的占位符图标文件
$iconsDir = "icons"
if (-not (Test-Path $iconsDir)) {
    New-Item -ItemType Directory -Path $iconsDir | Out-Null
}

Write-Host "创建占位符图标文件..." -ForegroundColor Green

# 检查是否有 ImageMagick 或其他工具
$hasImageMagick = Get-Command magick -ErrorAction SilentlyContinue

if ($hasImageMagick) {
    Write-Host "使用 ImageMagick 创建图标..." -ForegroundColor Yellow
    
    # 创建 PNG 文件
    magick convert -size 32x32 xc:"#667eea" "$iconsDir\32x32.png"
    magick convert -size 128x128 xc:"#667eea" "$iconsDir\128x128.png"
    magick convert -size 256x256 xc:"#667eea" "$iconsDir\128x128@2x.png"
    
    # 创建 ICO 文件（包含多个尺寸）
    magick convert -size 256x256 xc:"#667eea" -define icon:auto-resize=256,128,64,48,32,16 "$iconsDir\icon.ico"
    
    Write-Host "✅ 图标创建完成！" -ForegroundColor Green
} else {
    Write-Host "⚠️  ImageMagick 未安装，尝试使用 Python..." -ForegroundColor Yellow
    
    # 检查 Python
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        Write-Host "使用 Python 创建图标..." -ForegroundColor Yellow
        python create_placeholder_icons.py
    } else {
        Write-Host "❌ 未找到 Python 或 ImageMagick" -ForegroundColor Red
        Write-Host ""
        Write-Host "请选择以下方法之一创建图标:" -ForegroundColor Yellow
        Write-Host "1. 安装 ImageMagick: https://imagemagick.org/script/download.php"
        Write-Host "2. 使用在线工具: https://www.icoconverter.com/"
        Write-Host "3. 手动创建图标文件到 icons/ 目录"
        Write-Host ""
        Write-Host "需要的文件:" -ForegroundColor Cyan
        Write-Host "  - icons/32x32.png"
        Write-Host "  - icons/128x128.png"
        Write-Host "  - icons/128x128@2x.png (256x256)"
        Write-Host "  - icons/icon.ico"
        Write-Host ""
        exit 1
    }
}

