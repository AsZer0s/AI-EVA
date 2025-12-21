#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 模块测试脚本
"""
import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
import time
import os

def test_tts():
    """测试 TTS 模块"""
    base_url = "http://localhost:9966"
    
    print("=" * 60)
    print("TTS 模块测试")
    print("=" * 60)
    print()
    
    # 1. 检查服务状态
    print("1. 检查服务状态...")
    try:
        response = requests.get(f"{base_url}/")
        status = response.json()
        print(f"   ✅ 服务状态: {status['status']}")
        print(f"   {'✅' if status['model_loaded'] else '⚠️ '} 模型加载: {status['model_loaded']}")
        print(f"   ✅ 并发限制: {status['concurrency_limit']}")
    except Exception as e:
        print(f"   ❌ 无法连接到 TTS 服务: {e}")
        return
    print()
    
    # 2. 测试 TTS API
    print("2. 测试 TTS API（触发模型加载）...")
    try:
        payload = {
            "text": "你好，这是一个测试",
            "voice": "default"
        }
        
        print(f"   发送请求: text='{payload['text']}'")
        print("   正在生成音频（可能需要一些时间加载模型）...")
        
        response = requests.post(
            f"{base_url}/tts",
            json=payload,
            timeout=300  # 5分钟超时，因为首次加载模型需要时间
        )
        
        if response.status_code == 200:
            # 保存音频文件
            output_file = "test_output.mp3"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(output_file)
            print(f"   ✅ TTS 请求成功！")
            print(f"   ✅ 音频文件: {output_file} ({file_size / 1024:.2f} KB)")
        else:
            print(f"   ❌ TTS 请求失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            
    except requests.exceptions.Timeout:
        print("   ⚠️ 请求超时（模型可能正在加载，这是正常的）")
        print("   💡 提示: 首次加载模型可能需要较长时间")
    except Exception as e:
        print(f"   ❌ TTS 请求失败: {e}")
        import traceback
        print(f"   详细错误:\n{traceback.format_exc()}")
    print()
    
    # 3. 再次检查模型状态
    print("3. 检查模型加载状态...")
    time.sleep(2)
    try:
        response = requests.get(f"{base_url}/")
        status = response.json()
        model_loaded = status['model_loaded']
        
        print(f"   {'✅' if model_loaded else '⚠️ '} 模型加载: {model_loaded}")
        
        if model_loaded:
            print("   ✅ 模型已成功加载！")
        else:
            print("   ⚠️ 模型仍未加载")
            print("   💡 可能原因:")
            print("      - 模型加载失败（请查看日志）")
            print("      - IndexTTS2 目录或配置文件不存在")
            print("      - 依赖未正确安装")
            
    except Exception as e:
        print(f"   ❌ 无法获取状态: {e}")
    print()
    
    # 4. 检查健康状态
    print("4. 检查健康状态...")
    try:
        response = requests.get(f"{base_url}/health")
        health = response.json()
        print(f"   ✅ 状态: {health['status']}")
        print(f"   ✅ 缓存统计:")
        cache_stats = health.get('cache_stats', {})
        print(f"      - 文件数: {cache_stats.get('file_count', 0)}")
        print(f"      - 缓存大小: {cache_stats.get('total_size_mb', 0):.2f} MB")
        print(f"      - 使用率: {cache_stats.get('usage_percent', 0):.1f}%")
    except Exception as e:
        print(f"   ❌ 无法获取健康状态: {e}")
    print()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_tts()

