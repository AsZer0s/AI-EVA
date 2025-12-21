"""
音频缓存管理工具
用于优化 TTS 音频的缓存和复用
"""
import hashlib
import json
import os
import time
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from utils.logger import get_logger

# 加载配置
def _load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}

_config = _load_config()
performance_config = _config.get('performance', {})
tts_config = _config.get('modules', {}).get('tts', {})

logger = get_logger("audio_cache")

class AudioCache:
    """音频缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache/audio", max_size_mb: int = None):
        """
        初始化音频缓存
        
        Args:
            cache_dir: 缓存目录
            max_size_mb: 最大缓存大小（MB）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置最大缓存大小
        default_cache_size = tts_config.get('audio_cache_size', 100)
        self.max_size_mb = max_size_mb or default_cache_size
        self.max_size_bytes = self.max_size_mb * 1024 * 1024
        
        # 缓存索引文件
        self.index_file = self.cache_dir / "index.json"
        self.index = self._load_index()
        
        logger.info(f"音频缓存初始化完成，最大大小: {self.max_size_mb}MB")
    
    def _load_index(self) -> Dict[str, Any]:
        """加载缓存索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载缓存索引失败: {e}")
        return {}
    
    def _save_index(self):
        """保存缓存索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存索引失败: {e}")
    
    def _generate_key(self, text: str, voice: str, speed: float = 1.0) -> str:
        """
        生成缓存键
        
        Args:
            text: 文本内容
            voice: 音色
            speed: 语速
            
        Returns:
            缓存键
        """
        # 创建包含所有参数的字符串
        key_string = f"{text}|{voice}|{speed}"
        # 生成 MD5 哈希
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.mp3"
    
    def _get_cache_size(self) -> int:
        """获取当前缓存大小"""
        total_size = 0
        for file_path in self.cache_dir.glob("*.mp3"):
            total_size += file_path.stat().st_size
        return total_size
    
    def _cleanup_cache(self):
        """清理缓存（LRU 策略）"""
        current_size = self._get_cache_size()
        
        if current_size <= self.max_size_bytes:
            return
        
        logger.info(f"缓存大小超限，开始清理... 当前: {current_size/1024/1024:.1f}MB")
        
        # 按访问时间排序，删除最旧的
        items = []
        for key, info in self.index.items():
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                items.append((key, info, cache_path.stat().st_size))
        
        # 按最后访问时间排序
        items.sort(key=lambda x: x[1].get('last_accessed', 0))
        
        # 删除最旧的文件直到满足大小限制
        for key, info, size in items:
            if current_size <= self.max_size_bytes * 0.8:  # 清理到80%
                break
            
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
                current_size -= size
                del self.index[key]
                logger.debug(f"删除缓存文件: {key}")
        
        self._save_index()
        logger.info(f"缓存清理完成，当前大小: {current_size/1024/1024:.1f}MB")
    
    def get(self, text: str, voice: str, speed: float = 1.0) -> Optional[bytes]:
        """
        获取缓存的音频
        
        Args:
            text: 文本内容
            voice: 音色
            speed: 语速
            
        Returns:
            音频数据，如果未找到则返回 None
        """
        key = self._generate_key(text, voice, speed)
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        # 更新访问时间
        if key in self.index:
            self.index[key]['last_accessed'] = time.time()
            self._save_index()
        
        try:
            with open(cache_path, 'rb') as f:
                audio_data = f.read()
            logger.debug(f"命中缓存: {key[:8]}...")
            return audio_data
        except Exception as e:
            logger.error(f"读取缓存文件失败: {e}")
            return None
    
    def set(self, text: str, voice: str, speed: float, audio_data: bytes):
        """
        设置缓存音频
        
        Args:
            text: 文本内容
            voice: 音色
            speed: 语速
            audio_data: 音频数据
        """
        key = self._generate_key(text, voice, speed)
        cache_path = self._get_cache_path(key)
        
        try:
            # 保存音频文件
            with open(cache_path, 'wb') as f:
                f.write(audio_data)
            
            # 更新索引
            self.index[key] = {
                'text': text,
                'voice': voice,
                'speed': speed,
                'size': len(audio_data),
                'created_at': time.time(),
                'last_accessed': time.time()
            }
            
            self._save_index()
            logger.debug(f"缓存音频: {key[:8]}... ({len(audio_data)} bytes)")
            
            # 检查是否需要清理缓存
            self._cleanup_cache()
            
        except Exception as e:
            logger.error(f"保存缓存文件失败: {e}")
    
    def clear(self):
        """清空所有缓存"""
        try:
            # 删除所有音频文件
            for file_path in self.cache_dir.glob("*.mp3"):
                file_path.unlink()
            
            # 清空索引
            self.index = {}
            self._save_index()
            
            logger.info("缓存已清空")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        current_size = self._get_cache_size()
        file_count = len(self.index)
        
        return {
            'file_count': file_count,
            'total_size_mb': round(current_size / 1024 / 1024, 2),
            'max_size_mb': self.max_size_mb,
            'usage_percent': round((current_size / self.max_size_bytes) * 100, 1),
            'cache_dir': str(self.cache_dir)
        }
    
    def cleanup_expired(self, max_age_hours: int = 24):
        """
        清理过期缓存
        
        Args:
            max_age_hours: 最大保存时间（小时）
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        expired_keys = []
        for key, info in self.index.items():
            if current_time - info.get('created_at', 0) > max_age_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
            del self.index[key]
        
        if expired_keys:
            self._save_index()
            logger.info(f"清理过期缓存: {len(expired_keys)} 个文件")

# 全局缓存实例
audio_cache = AudioCache()
