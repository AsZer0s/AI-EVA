"""
创建占位符图标文件的脚本
运行此脚本可以创建简单的占位符图标，用于开发测试
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_icon(size, output_path):
    """创建占位符图标"""
    # 创建图像
    img = Image.new('RGBA', (size, size), (102, 126, 234, 255))  # 紫色背景
    draw = ImageDraw.Draw(img)
    
    # 绘制简单的文字或图形
    # 这里绘制一个简单的圆形
    margin = size // 4
    draw.ellipse([margin, margin, size - margin, size - margin], 
                 fill=(255, 255, 255, 255), outline=(118, 75, 162, 255), width=size//20)
    
    # 保存
    img.save(output_path)
    print(f"创建图标: {output_path} ({size}x{size})")

def create_ico_file():
    """创建 ICO 文件（Windows）"""
    try:
        from PIL import Image
        sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
        images = []
        
        for size in sizes:
            img = Image.new('RGBA', size, (102, 126, 234, 255))
            draw = ImageDraw.Draw(img)
            margin = size[0] // 4
            draw.ellipse([margin, margin, size[0] - margin, size[1] - margin],
                        fill=(255, 255, 255, 255), outline=(118, 75, 162, 255), width=max(1, size[0]//20))
            images.append(img)
        
        # 保存为 ICO
        ico_path = 'icons/icon.ico'
        images[0].save(ico_path, format='ICO', sizes=[(img.width, img.height) for img in images])
        print(f"创建 ICO 文件: {ico_path}")
    except Exception as e:
        print(f"创建 ICO 失败: {e}")
        print("提示: 需要安装 Pillow: pip install Pillow")

def create_icns_file():
    """创建 ICNS 文件（macOS，可选）"""
    try:
        # macOS ICNS 文件创建比较复杂，这里创建一个占位符
        # 实际使用时可以使用 iconutil 工具或在线转换
        print("提示: ICNS 文件需要 macOS 系统或在线工具生成")
        print("可以使用: https://cloudconvert.com/png-to-icns")
    except Exception as e:
        print(f"创建 ICNS 失败: {e}")

if __name__ == '__main__':
    os.makedirs('icons', exist_ok=True)
    
    # 创建 PNG 图标
    create_placeholder_icon(32, 'icons/32x32.png')
    create_placeholder_icon(128, 'icons/128x128.png')
    create_placeholder_icon(256, 'icons/128x128@2x.png')
    
    # 创建 ICO 文件
    try:
        create_ico_file()
    except ImportError:
        print("\n警告: 无法创建 ICO 文件，需要安装 Pillow")
        print("运行: pip install Pillow")
        print("\n或者手动创建图标文件，参考 icons/README.md")
    
    # 创建 ICNS 文件（可选）
    try:
        create_icns_file()
    except Exception as e:
        print(f"ICNS 文件创建跳过: {e}")
    
    print("\n✅ 图标创建完成！")
    print("注意: macOS 的 icon.icns 文件需要单独创建或使用在线工具")

