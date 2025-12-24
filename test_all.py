"""
完整流程测试脚本
使用统一接口测试AI陪伴对话服务的完整流程
"""
import requests
import json
import os
import sys
from pathlib import Path

class TestClient:
    """测试客户端"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.conversation_history = []
        self.test_results = []
    
    def log(self, message, status="INFO"):
        """记录日志"""
        status_symbol = {
            "INFO": "ℹ️",
            "SUCCESS": "✓",
            "ERROR": "✗",
            "WARNING": "⚠️"
        }.get(status, "•")
        print(f"{status_symbol} {message}")
        self.test_results.append({"status": status, "message": message})
    
    def check_service(self):
        """检查服务状态"""
        self.log("=" * 60)
        self.log("步骤1: 检查服务状态", "INFO")
        self.log("=" * 60)
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                self.log(f"服务状态: {health.get('status', 'unknown')}", "SUCCESS")
                self.log(f"  ASR模型: {'已加载' if health.get('asr_loaded') else '未加载'}", 
                        "SUCCESS" if health.get('asr_loaded') else "ERROR")
                self.log(f"  VAD模型: {'已加载' if health.get('vad_loaded') else '未加载'}", 
                        "SUCCESS" if health.get('vad_loaded') else "WARNING")
                self.log(f"  TTS模型: {'已加载' if health.get('tts_loaded') else '未加载'}", 
                        "SUCCESS" if health.get('tts_loaded') else "WARNING")
                
                # 检查关键功能
                if not health.get('asr_loaded'):
                    self.log("警告: ASR模型未加载，音频输入功能将不可用", "ERROR")
                    return False
                if not health.get('tts_loaded'):
                    self.log("警告: TTS模型未加载，语音合成功能将不可用", "WARNING")
                
                return True
            else:
                self.log(f"服务响应异常: {response.status_code}", "ERROR")
                return False
        except requests.exceptions.ConnectionError:
            self.log("无法连接到服务，请确保服务已启动", "ERROR")
            self.log(f"尝试启动服务: python app.py", "INFO")
            return False
        except Exception as e:
            self.log(f"检查服务失败: {e}", "ERROR")
            return False
    
    def test_text_input(self, text: str, output_file: str = None):
        """
        测试文本输入接口
        流程: 文本 -> AI对话 -> TTS -> 音频
        """
        self.log("")
        self.log("=" * 60)
        self.log("步骤2: 测试文本输入接口 (/api/chat/text)", "INFO")
        self.log("=" * 60)
        self.log(f"输入文本: {text}", "INFO")
        
        if output_file is None:
            output_file = "test_text_reply.wav"
        
        try:
            data = {
                "text": text,
                "conversation_history": self.conversation_history
            }
            
            self.log("发送请求到 /api/chat/text...", "INFO")
            response = requests.post(
                f"{self.base_url}/api/chat/text",
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                # 保存音频
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                # 获取文本信息
                user_text = response.headers.get("X-User-Text", "")
                ai_reply = response.headers.get("X-AI-Reply", "")
                sample_rate = response.headers.get("X-Audio-Sample-Rate", "未知")
                
                # 更新对话历史
                if user_text:
                    self.conversation_history.append({"role": "user", "content": user_text})
                if ai_reply:
                    self.conversation_history.append({"role": "assistant", "content": ai_reply})
                
                # 检查文件大小
                file_size = os.path.getsize(output_file)
                
                self.log("✓ 请求成功", "SUCCESS")
                self.log(f"  用户输入: {user_text}", "INFO")
                self.log(f"  AI回复: {ai_reply[:100]}{'...' if len(ai_reply) > 100 else ''}", "INFO")
                self.log(f"  音频文件: {output_file}", "SUCCESS")
                self.log(f"  文件大小: {file_size / 1024:.2f} KB", "INFO")
                self.log(f"  采样率: {sample_rate} Hz", "INFO")
                
                return True, user_text, ai_reply, output_file
            else:
                error_detail = response.text if hasattr(response, 'text') else str(response.status_code)
                self.log(f"✗ 请求失败: {response.status_code}", "ERROR")
                self.log(f"  错误详情: {error_detail[:200]}", "ERROR")
                return False, None, None, None
                
        except requests.exceptions.Timeout:
            self.log("✗ 请求超时（60秒）", "ERROR")
            return False, None, None, None
        except Exception as e:
            self.log(f"✗ 测试失败: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False, None, None, None
    
    def test_audio_input(self, audio_file_path: str, output_file: str = None):
        """
        测试音频输入接口
        流程: 音频 -> VAD -> ASR -> AI对话 -> TTS -> 音频
        """
        self.log("")
        self.log("=" * 60)
        self.log("步骤3: 测试音频输入接口 (/api/chat/audio)", "INFO")
        self.log("=" * 60)
        
        if not os.path.exists(audio_file_path):
            self.log(f"✗ 音频文件不存在: {audio_file_path}", "ERROR")
            self.log("跳过音频输入测试", "WARNING")
            return False, None, None, None
        
        self.log(f"输入音频: {audio_file_path}", "INFO")
        file_size = os.path.getsize(audio_file_path)
        self.log(f"文件大小: {file_size / 1024:.2f} KB", "INFO")
        
        if output_file is None:
            output_file = "test_audio_reply.wav"
        
        try:
            with open(audio_file_path, "rb") as f:
                files = {"audio": f}
                data = {"conversation_history": json.dumps(self.conversation_history)}
                
                self.log("发送请求到 /api/chat/audio...", "INFO")
                response = requests.post(
                    f"{self.base_url}/api/chat/audio",
                    files=files,
                    data=data,
                    timeout=120  # 音频处理可能需要更长时间
                )
            
            if response.status_code == 200:
                # 保存音频
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                # 获取文本信息
                user_text = response.headers.get("X-User-Text", "")
                ai_reply = response.headers.get("X-AI-Reply", "")
                sample_rate = response.headers.get("X-Audio-Sample-Rate", "未知")
                
                # 更新对话历史
                if user_text:
                    self.conversation_history.append({"role": "user", "content": user_text})
                if ai_reply:
                    self.conversation_history.append({"role": "assistant", "content": ai_reply})
                
                # 检查文件大小
                reply_file_size = os.path.getsize(output_file)
                
                self.log("✓ 请求成功", "SUCCESS")
                self.log(f"  识别文本: {user_text}", "INFO")
                self.log(f"  AI回复: {ai_reply[:100]}{'...' if len(ai_reply) > 100 else ''}", "INFO")
                self.log(f"  音频文件: {output_file}", "SUCCESS")
                self.log(f"  文件大小: {reply_file_size / 1024:.2f} KB", "INFO")
                self.log(f"  采样率: {sample_rate} Hz", "INFO")
                
                return True, user_text, ai_reply, output_file
            else:
                error_detail = response.text if hasattr(response, 'text') else str(response.status_code)
                self.log(f"✗ 请求失败: {response.status_code}", "ERROR")
                self.log(f"  错误详情: {error_detail[:200]}", "ERROR")
                return False, None, None, None
                
        except requests.exceptions.Timeout:
            self.log("✗ 请求超时（120秒）", "ERROR")
            return False, None, None, None
        except Exception as e:
            self.log(f"✗ 测试失败: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False, None, None, None
    
    def test_conversation_flow(self):
        """测试连续对话流程"""
        self.log("")
        self.log("=" * 60)
        self.log("步骤4: 测试连续对话流程", "INFO")
        self.log("=" * 60)
        
        test_messages = [
            "你好，请介绍一下你自己",
            "你刚才说了什么？",
            "你能帮我做什么？"
        ]
        
        for i, message in enumerate(test_messages, 1):
            self.log(f"\n对话轮次 {i}/{len(test_messages)}", "INFO")
            success, user_text, ai_reply, output_file = self.test_text_input(
                message,
                output_file=f"test_conversation_{i}.wav"
            )
            
            if not success:
                self.log(f"对话轮次 {i} 失败，停止测试", "ERROR")
                break
            
            self.log(f"对话轮次 {i} 完成", "SUCCESS")
    
    def print_summary(self):
        """打印测试总结"""
        self.log("")
        self.log("=" * 60)
        self.log("测试总结", "INFO")
        self.log("=" * 60)
        
        success_count = sum(1 for r in self.test_results if r["status"] == "SUCCESS")
        error_count = sum(1 for r in self.test_results if r["status"] == "ERROR")
        warning_count = sum(1 for r in self.test_results if r["status"] == "WARNING")
        
        self.log(f"总测试项: {len(self.test_results)}", "INFO")
        self.log(f"成功: {success_count}", "SUCCESS")
        self.log(f"失败: {error_count}", "ERROR" if error_count > 0 else "INFO")
        self.log(f"警告: {warning_count}", "WARNING" if warning_count > 0 else "INFO")
        
        self.log("")
        self.log("生成的音频文件:", "INFO")
        audio_files = [
            "test_text_reply.wav",
            "test_audio_reply.wav",
            "test_conversation_1.wav",
            "test_conversation_2.wav",
            "test_conversation_3.wav"
        ]
        for audio_file in audio_files:
            if os.path.exists(audio_file):
                file_size = os.path.getsize(audio_file)
                self.log(f"  ✓ {audio_file} ({file_size / 1024:.2f} KB)", "SUCCESS")
        
        self.log("")
        self.log("=" * 60)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("AI陪伴对话服务 - 完整流程测试")
    print("=" * 60 + "\n")
    
    # 创建测试客户端
    client = TestClient()
    
    # 1. 检查服务状态
    if not client.check_service():
        print("\n❌ 服务不可用，请先启动服务")
        sys.exit(1)
    
    # 2. 测试文本输入接口
    client.test_text_input("你好，请介绍一下你自己")
    
    # 3. 测试音频输入接口（如果存在测试音频文件）
    test_audio_files = [
        "test_input.wav",
        "input_audio.wav",
        "test_audio.wav"
    ]
    audio_file_found = False
    for audio_file in test_audio_files:
        if os.path.exists(audio_file):
            client.test_audio_input(audio_file)
            audio_file_found = True
            break
    
    if not audio_file_found:
        client.log("未找到测试音频文件，跳过音频输入测试", "WARNING")
        client.log("提示: 将音频文件命名为 test_input.wav 放在项目目录下即可测试", "INFO")
    
    # 4. 测试连续对话流程
    client.test_conversation_flow()
    
    # 5. 打印测试总结
    client.print_summary()
    
    print("\n✅ 测试完成！")
    print("\n提示:")
    print("  - 可以使用音频播放器播放生成的 .wav 文件")
    print("  - 检查响应头中的 X-User-Text 和 X-AI-Reply 获取文本信息")
    print("  - 对话历史已自动维护，支持多轮对话")


if __name__ == "__main__":
    main()

