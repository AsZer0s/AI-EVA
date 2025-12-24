"""
API测试脚本
用于测试AI陪伴对话服务的各个接口
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查接口"""
    print("=" * 50)
    print("测试健康检查接口")
    print("=" * 50)
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_chat():
    """测试文本对话接口"""
    print("=" * 50)
    print("测试文本对话接口")
    print("=" * 50)
    data = {
        "text": "你好，请介绍一下你自己",
        "conversation_history": None
    }
    response = requests.post(f"{BASE_URL}/api/chat", json=data)
    print(f"状态码: {response.status_code}")
    print(f"用户输入: {data['text']}")
    print(f"AI回复: {response.json().get('text', '')}")
    print()

def test_transcribe(audio_file_path):
    """测试音频转文本接口"""
    print("=" * 50)
    print("测试音频转文本接口")
    print("=" * 50)
    try:
        with open(audio_file_path, "rb") as f:
            files = {"audio": f}
            response = requests.post(f"{BASE_URL}/api/audio/transcribe", files=files)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"识别文本: {result.get('text', '')}")
        print(f"检测到语音: {result.get('has_speech', False)}")
    except FileNotFoundError:
        print(f"文件不存在: {audio_file_path}")
    except Exception as e:
        print(f"错误: {e}")
    print()

def test_tts():
    """测试文本转语音接口"""
    print("=" * 50)
    print("测试文本转语音接口")
    print("=" * 50)
    data = {
        "text": "你好，这是TTS测试"
    }
    response = requests.post(f"{BASE_URL}/api/audio/tts", json=data)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        # 保存音频文件
        with open("test_output.wav", "wb") as f:
            f.write(response.content)
        print("音频已保存到: test_output.wav")
    else:
        print(f"错误: {response.text}")
    print()

def test_complete(audio_file_path):
    """测试完整流程接口"""
    print("=" * 50)
    print("测试完整流程接口（音频->文本->AI->文本）")
    print("=" * 50)
    try:
        with open(audio_file_path, "rb") as f:
            files = {"audio": f}
            data = {"conversation_history": "[]"}
            response = requests.post(f"{BASE_URL}/api/complete", files=files, data=data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"用户语音识别: {result.get('text', '')}")
        print(f"AI回复: {result.get('ai_reply', '')}")
        print(f"音频可用: {result.get('audio_available', False)}")
    except FileNotFoundError:
        print(f"文件不存在: {audio_file_path}")
    except Exception as e:
        print(f"错误: {e}")
    print()

def test_complete_with_audio(audio_file_path):
    """测试完整流程并返回音频接口"""
    print("=" * 50)
    print("测试完整流程接口（音频->文本->AI->音频）")
    print("=" * 50)
    try:
        with open(audio_file_path, "rb") as f:
            files = {"audio": f}
            data = {"conversation_history": "[]"}
            response = requests.post(f"{BASE_URL}/api/complete/audio", files=files, data=data)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            # 保存音频文件
            with open("complete_output.wav", "wb") as f:
                f.write(response.content)
            print("音频已保存到: complete_output.wav")
            print(f"用户文本: {response.headers.get('X-User-Text', '')}")
            print(f"AI回复: {response.headers.get('X-AI-Reply', '')}")
        else:
            print(f"错误: {response.text}")
    except FileNotFoundError:
        print(f"文件不存在: {audio_file_path}")
    except Exception as e:
        print(f"错误: {e}")
    print()

if __name__ == "__main__":
    print("开始测试AI陪伴对话服务API")
    print()
    
    # 1. 健康检查
    test_health()
    
    # 2. 文本对话
    test_chat()
    
    # 3. TTS测试（不需要音频文件）
    test_tts()
    
    # 4. 音频转文本（需要音频文件）
    # 如果有测试音频文件，取消下面的注释
    # test_transcribe("test_audio.wav")
    
    # 5. 完整流程（需要音频文件）
    # 如果有测试音频文件，取消下面的注释
    # test_complete("test_audio.wav")
    # test_complete_with_audio("test_audio.wav")
    
    print("测试完成！")

