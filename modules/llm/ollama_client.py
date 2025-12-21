#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM 模块 - Ollama 客户端
负责与大语言模型交互
"""
import sys
from pathlib import Path
import httpx
import yaml
import logging
from typing import Optional, Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger("ollama_client")

# 加载配置
def load_config():
    """加载配置文件"""
    config_path = project_root / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

config = load_config()
llm_config = config.get('modules', {}).get('llm', {})


class OllamaClient:
    """Ollama API 客户端"""
    
    def __init__(self):
        self.base_url = llm_config.get('base_url', 'http://localhost:11434')
        self.model_name = llm_config.get('model_name', 'qwen2.5:7b')
        self.keep_alive = llm_config.get('keep_alive', '5m')
        self.timeout = llm_config.get('timeout', 300)
        self.temperature = llm_config.get('temperature', 0.7)
        self.max_tokens = llm_config.get('max_tokens', 2048)
        self.client = httpx.AsyncClient(timeout=self.timeout)
        logger.info(f"初始化 Ollama 客户端: {self.base_url}, 模型: {self.model_name}")
    
    async def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get('temperature', self.temperature),
                    "num_predict": kwargs.get('max_tokens', self.max_tokens),
                },
                "keep_alive": self.keep_alive
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('message', {}).get('content', '')
            
        except Exception as e:
            logger.error(f"生成文本失败: {e}")
            raise
    
    async def generate_stream(self, prompt: str, system_prompt: str = None, **kwargs):
        """
        流式生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 其他参数
            
        Yields:
            生成的文本片段
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": kwargs.get('temperature', self.temperature),
                    "num_predict": kwargs.get('max_tokens', self.max_tokens),
                },
                "keep_alive": self.keep_alive
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                import json
                                data = json.loads(line)
                                if 'message' in data and 'content' in data['message']:
                                    yield data['message']['content']
                            except json.JSONDecodeError:
                                continue
                            
        except Exception as e:
            logger.error(f"流式生成文本失败: {e}")
            raise
    
    async def check_health(self) -> bool:
        """检查 Ollama 服务健康状态"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """列出可用的模型"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局客户端实例
_client: Optional[OllamaClient] = None

def get_client() -> OllamaClient:
    """获取 Ollama 客户端实例"""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client

