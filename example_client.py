"""
客户端示例
展示如何与AI陪伴对话服务交互
"""
import requests
import json
import time

class AIChatClient:
    """AI对话客户端"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.conversation_history = []
    
    def check_health(self):
        """检查服务健康状态"""
        try:
            response = requests.get(f"{self.base_url}/api/health")
            return response.json()
        except Exception as e:
            print(f"健康检查失败: {e}")
            return None
    
    def chat(self, text: str):
        """文本对话"""
        data = {
            "text": text,
            "conversation_history": self.conversation_history
        }
        try:
            response = requests.post(f"{self.base_url}/api/chat", json=data)
            if response.status_code == 200:
                result = response.json()
                ai_reply = result.get("text", "")
                
                # 更新对话历史
                self.conversation_history.append({"role": "user", "content": text})
                self.conversation_history.append({"role": "assistant", "content": ai_reply})
                
                return ai_reply
            else:
                return f"错误: {response.status_code}"
        except Exception as e:
            return f"请求失败: {e}"
    
    def transcribe_audio(self, audio_file_path: str):
        """音频转文本"""
        try:
            with open(audio_file_path, "rb") as f:
                files = {"audio": f}
                response = requests.post(f"{self.base_url}/api/audio/transcribe", files=files)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("text", "")
            else:
                return f"错误: {response.status_code}"
        except Exception as e:
            return f"请求失败: {e}"
    
    def text_to_speech(self, text: str, output_file: str = "output.wav"):
        """文本转语音"""
        data = {"text": text}
        try:
            response = requests.post(f"{self.base_url}/api/audio/tts", json=data)
            if response.status_code == 200:
                with open(output_file, "wb") as f:
                    f.write(response.content)
                return output_file
            else:
                error_detail = response.text if hasattr(response, 'text') else str(response.status_code)
                return f"错误: {response.status_code} - {error_detail}"
        except Exception as e:
            return f"请求失败: {e}"
    
    def complete_flow(self, audio_file_path: str):
        """完整流程：音频 -> 文本 -> AI -> 文本"""
        try:
            with open(audio_file_path, "rb") as f:
                files = {"audio": f}
                data = {"conversation_history": json.dumps(self.conversation_history)}
                response = requests.post(f"{self.base_url}/api/complete", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                user_text = result.get("text", "")
                ai_reply = result.get("ai_reply", "")
                
                # 更新对话历史
                if user_text:
                    self.conversation_history.append({"role": "user", "content": user_text})
                if ai_reply:
                    self.conversation_history.append({"role": "assistant", "content": ai_reply})
                
                return user_text, ai_reply
            else:
                return None, f"错误: {response.status_code}"
        except Exception as e:
            return None, f"请求失败: {e}"
    
    def complete_flow_with_audio(self, audio_file_path: str, output_file: str = "ai_reply.wav"):
        """完整流程：音频 -> 文本 -> AI -> 音频"""
        try:
            with open(audio_file_path, "rb") as f:
                files = {"audio": f}
                data = {"conversation_history": json.dumps(self.conversation_history)}
                response = requests.post(f"{self.base_url}/api/complete/audio", files=files, data=data)
            
            if response.status_code == 200:
                # 保存音频
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                # 获取文本信息
                user_text = response.headers.get("X-User-Text", "")
                ai_reply = response.headers.get("X-AI-Reply", "")
                
                # 更新对话历史
                if user_text:
                    self.conversation_history.append({"role": "user", "content": user_text})
                if ai_reply:
                    self.conversation_history.append({"role": "assistant", "content": ai_reply})
                
                return user_text, ai_reply, output_file
            else:
                return None, None, f"错误: {response.status_code}"
        except Exception as e:
            return None, None, f"请求失败: {e}"
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
    
    def chat_with_text(self, text: str, output_file: str = "text_reply.wav"):
        """
        统一接口：文本输入 -> AI对话 -> TTS -> 返回音频
        推荐使用此接口
        """
        data = {"text": text, "conversation_history": self.conversation_history}
        try:
            response = requests.post(f"{self.base_url}/api/chat/text", json=data)
            if response.status_code == 200:
                # 保存音频
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                # 获取文本信息
                user_text = response.headers.get("X-User-Text", "")
                ai_reply = response.headers.get("X-AI-Reply", "")
                
                # 更新对话历史
                if user_text:
                    self.conversation_history.append({"role": "user", "content": user_text})
                if ai_reply:
                    self.conversation_history.append({"role": "assistant", "content": ai_reply})
                
                return user_text, ai_reply, output_file
            else:
                error_detail = response.text if hasattr(response, 'text') else str(response.status_code)
                return None, None, f"错误: {response.status_code} - {error_detail}"
        except Exception as e:
            return None, None, f"请求失败: {e}"
    
    def chat_with_audio(self, audio_file_path: str, output_file: str = "audio_reply.wav"):
        """
        统一接口：音频输入 -> VAD -> ASR -> AI对话 -> TTS -> 返回音频
        推荐使用此接口
        """
        try:
            with open(audio_file_path, "rb") as f:
                files = {"audio": f}
                data = {"conversation_history": json.dumps(self.conversation_history)}
                response = requests.post(f"{self.base_url}/api/chat/audio", files=files, data=data)
            
            if response.status_code == 200:
                # 保存音频
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                # 获取文本信息
                user_text = response.headers.get("X-User-Text", "")
                ai_reply = response.headers.get("X-AI-Reply", "")
                
                # 更新对话历史
                if user_text:
                    self.conversation_history.append({"role": "user", "content": user_text})
                if ai_reply:
                    self.conversation_history.append({"role": "assistant", "content": ai_reply})
                
                return user_text, ai_reply, output_file
            else:
                error_detail = response.text if hasattr(response, 'text') else str(response.status_code)
                return None, None, f"错误: {response.status_code} - {error_detail}"
        except Exception as e:
            return None, None, f"请求失败: {e}"


# 使用示例
if __name__ == "__main__":
    # 创建客户端
    client = AIChatClient()
    
    # 检查服务状态
    print("检查服务状态...")
    health = client.check_health()
    if health:
        print(f"服务状态: {health}")
        print(f"  ASR: {'✓' if health.get('asr_loaded') else '✗'}")
        print(f"  VAD: {'✓' if health.get('vad_loaded') else '✗'}")
        print(f"  TTS: {'✓' if health.get('tts_loaded') else '✗'}")
    print()
    
    # 示例1: 文本输入 -> AI -> TTS -> 音频（推荐）
    print("=" * 60)
    print("示例1: 文本输入接口（文本 -> AI -> 音频）")
    print("=" * 60)
    user_text, ai_reply, result = client.chat_with_text("你好，请介绍一下你自己")
    if result and not result.startswith("错误"):
        print(f"用户输入: {user_text}")
        print(f"AI回复: {ai_reply}")
        print(f"音频已保存到: {result}")
    else:
        print(f"失败: {result}")
    print()
    
    # 示例2: 继续对话（带历史）
    print("=" * 60)
    print("示例2: 继续对话（文本 -> AI -> 音频）")
    print("=" * 60)
    user_text, ai_reply, result = client.chat_with_text("你刚才说了什么？")
    if result and not result.startswith("错误"):
        print(f"用户输入: {user_text}")
        print(f"AI回复: {ai_reply}")
        print(f"音频已保存到: {result}")
    else:
        print(f"失败: {result}")
    print()
    
    # 示例3: 音频输入（需要音频文件）
    # print("=" * 60)
    # print("示例3: 音频输入接口（音频 -> 文本 -> AI -> 音频）")
    # print("=" * 60)
    # user_text, ai_reply, result = client.chat_with_audio("input_audio.wav")
    # if result and not result.startswith("错误"):
    #     print(f"用户语音识别: {user_text}")
    #     print(f"AI回复: {ai_reply}")
    #     print(f"音频已保存到: {result}")
    # else:
    #     print(f"失败: {result}")
    # print()
    
    print("示例完成！")
    print("\n提示：")
    print("  - 使用 chat_with_text() 进行文本对话（推荐）")
    print("  - 使用 chat_with_audio() 进行音频对话（需要音频文件）")
    print("  - 音频文件可以直接在前端播放")

