# 图标文件说明

此目录需要包含以下图标文件用于应用打包：

## 必需文件

- `32x32.png` - 32x32 像素 PNG 图标
- `128x128.png` - 128x128 像素 PNG 图标  
- `128x128@2x.png` - 256x256 像素 PNG 图标（Retina 显示）
- `icon.icns` - macOS 图标文件
- `icon.ico` - Windows 图标文件

## 图标规格

- **PNG 文件**: 透明背景，PNG-24 格式
- **ICO 文件**: 包含多个尺寸（16x16, 32x32, 48x48, 256x256）
- **ICNS 文件**: macOS 标准图标格式

## 生成图标

可以使用在线工具生成：
- https://www.icoconverter.com/ (ICO)
- https://cloudconvert.com/png-to-icns (ICNS)
- https://www.favicon-generator.org/ (多格式)

## 临时方案

如果没有图标文件，应用仍可正常运行，但打包后的应用会使用默认图标。

