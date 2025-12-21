#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI-EVA 核心启动脚本 (总指挥)
模块化架构启动器，负责启动和管理各个功能模块
"""
import os
import sys
import subprocess
import time
import signal
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import logging

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'logs' / 'launcher.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("launcher")


class ModuleLauncher:
    """模块启动器"""
    
    def __init__(self, config_path: Path = None):
        """
        初始化启动器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or (PROJECT_ROOT / "config.yaml")
        self.config = self._load_config()
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        
        # 确保必要目录存在
        self._ensure_directories()
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ 配置文件加载成功: {self.config_path}")
            return config or {}
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            return {}
    
    def _ensure_directories(self):
        """确保必要目录存在"""
        system_config = self.config.get('system', {})
        temp_dir = Path(system_config.get('temp_dir', './temp'))
        log_dir = Path(system_config.get('log_dir', './logs'))
        
        temp_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✅ 目录检查完成: temp={temp_dir}, logs={log_dir}")
    
    def start_module(self, module_name: str) -> bool:
        """
        启动指定模块
        
        Args:
            module_name: 模块名称 (asr, tts, llm, webui)
            
        Returns:
            是否启动成功
        """
        if module_name in self.processes:
            proc = self.processes[module_name]
            if proc.poll() is None:
                logger.warning(f"⚠️  {module_name} 模块已在运行")
                return True
        
        modules_config = self.config.get('modules', {})
        module_config = modules_config.get(module_name, {})
        
        if not module_config.get('enabled', True):
            logger.info(f"⏭️  {module_name} 模块已禁用，跳过")
            return False
        
        try:
            # 根据模块类型选择启动方式
            if module_name == 'asr':
                cmd = [sys.executable, '-m', 'modules.asr.asr_worker']
            elif module_name == 'tts':
                cmd = [sys.executable, '-m', 'modules.tts.tts_worker']
            elif module_name == 'webui':
                cmd = [sys.executable, '-m', 'modules.webui.app']
            elif module_name == 'llm':
                # LLM (Ollama) 通常作为外部服务，这里只检查
                logger.info("ℹ️  LLM (Ollama) 需要单独启动，请确保 Ollama 服务正在运行")
                return True
            else:
                logger.error(f"❌ 未知模块: {module_name}")
                return False
            
            logger.info(f"🚀 启动模块: {module_name}")
            logger.debug(f"   命令: {' '.join(cmd)}")
            
            # 启动进程
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            self.processes[module_name] = proc
            
            # 等待一下，检查进程是否正常启动
            time.sleep(2)
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                logger.error(f"❌ {module_name} 模块启动失败")
                logger.error(f"   标准输出: {stdout.decode('utf-8', errors='ignore')}")
                logger.error(f"   错误输出: {stderr.decode('utf-8', errors='ignore')}")
                return False
            
            logger.info(f"✅ {module_name} 模块启动成功 (PID: {proc.pid})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动 {module_name} 模块失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def stop_module(self, module_name: str) -> bool:
        """
        停止指定模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            是否停止成功
        """
        if module_name not in self.processes:
            logger.warning(f"⚠️  {module_name} 模块未运行")
            return False
        
        try:
            proc = self.processes[module_name]
            if proc.poll() is None:
                logger.info(f"🛑 停止模块: {module_name}")
                proc.terminate()
                
                # 等待进程结束
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"⚠️  {module_name} 模块未响应，强制终止")
                    proc.kill()
                    proc.wait()
                
                logger.info(f"✅ {module_name} 模块已停止")
            
            del self.processes[module_name]
            return True
            
        except Exception as e:
            logger.error(f"❌ 停止 {module_name} 模块失败: {e}")
            return False
    
    def start_all(self) -> Dict[str, bool]:
        """
        启动所有启用的模块
        
        Returns:
            各模块启动结果
        """
        logger.info("=" * 60)
        logger.info("🚀 AI-EVA 模块化架构启动器")
        logger.info("=" * 60)
        
        results = {}
        modules_config = self.config.get('modules', {})
        
        # 按顺序启动模块
        startup_order = ['asr', 'tts', 'llm', 'webui']
        
        for module_name in startup_order:
            if module_name in modules_config:
                results[module_name] = self.start_module(module_name)
                time.sleep(1)  # 模块间延迟
        
        self.running = True
        
        logger.info("=" * 60)
        logger.info("✅ 所有模块启动完成")
        logger.info("=" * 60)
        
        return results
    
    def stop_all(self) -> Dict[str, bool]:
        """
        停止所有模块
        
        Returns:
            各模块停止结果
        """
        logger.info("🛑 正在停止所有模块...")
        
        results = {}
        for module_name in list(self.processes.keys()):
            results[module_name] = self.stop_module(module_name)
        
        self.running = False
        logger.info("✅ 所有模块已停止")
        
        return results
    
    def get_status(self) -> Dict[str, str]:
        """
        获取所有模块状态
        
        Returns:
            各模块状态字典
        """
        status = {}
        for module_name, proc in self.processes.items():
            if proc.poll() is None:
                status[module_name] = 'running'
            else:
                status[module_name] = 'stopped'
        return status
    
    def wait(self):
        """等待所有进程结束"""
        try:
            while self.running:
                # 检查进程状态
                for module_name in list(self.processes.keys()):
                    proc = self.processes[module_name]
                    if proc.poll() is not None:
                        logger.warning(f"⚠️  {module_name} 模块意外退出")
                        del self.processes[module_name]
                
                if not self.processes:
                    logger.info("所有模块已退出")
                    break
                
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n收到中断信号，正在停止所有模块...")
            self.stop_all()


def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"\n收到信号 {signum}，正在优雅退出...")
    if launcher:
        launcher.stop_all()
    sys.exit(0)


# 全局启动器实例
launcher: Optional[ModuleLauncher] = None


def main():
    """主函数"""
    global launcher
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建启动器
    launcher = ModuleLauncher()
    
    # 启动所有模块
    results = launcher.start_all()
    
    # 显示启动结果
    print("\n" + "=" * 60)
    print("模块启动状态:")
    for module_name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {module_name:10s}: {status}")
    print("=" * 60)
    
    # 显示服务地址
    modules_config = launcher.config.get('modules', {})
    webui_config = modules_config.get('webui', {})
    asr_config = modules_config.get('asr', {})
    tts_config = modules_config.get('tts', {})
    
    print("\n服务地址:")
    print(f"  服务管理器: http://localhost:{webui_config.get('manager_port', 9000)}")
    print(f"  前端界面:   http://localhost:{webui_config.get('port', 8000)}")
    print(f"  ASR API:    http://localhost:{asr_config.get('port', 50000)}")
    print(f"  TTS API:    http://localhost:{tts_config.get('port', 9966)}")
    print("\n按 Ctrl+C 停止所有服务")
    print("=" * 60 + "\n")
    
    # 等待进程
    try:
        launcher.wait()
    except KeyboardInterrupt:
        pass
    finally:
        launcher.stop_all()


if __name__ == '__main__':
    main()

