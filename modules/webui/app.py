#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebUI 模块 - 前端交互界面
基于 FastAPI 的服务管理界面
"""
import subprocess
import time
import os
import sys
import socket
import psutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import webbrowser
import threading
import yaml

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
except ImportError:
    print("正在安装 FastAPI 和 uvicorn...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'fastapi', 'uvicorn[standard]', 'websockets', '--quiet'])
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 加载配置
def load_config():
    """加载配置文件"""
    config_path = project_root / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

config = load_config()
webui_config = config.get('modules', {}).get('webui', {})
asr_config = config.get('modules', {}).get('asr', {})
tts_config = config.get('modules', {}).get('tts', {})
llm_config = config.get('modules', {}).get('llm', {})

class ServiceManager:
    """服务管理器"""
    def __init__(self):
        self.processes = {}
        self.ports = {
            'TTS': tts_config.get('port', 9966),
            'ASR': asr_config.get('port', 50000),
            'Frontend': webui_config.get('port', 8000),
            'Ollama': 11434
        }
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="AI-EVA")
        
    def check_port(self, port):
        """检查端口是否被占用"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    
    def kill_port_process(self, port):
        """终止占用指定端口的进程"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    for conn in proc.connections():
                        if conn.laddr.port == port:
                            proc.kill()
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            print(f"终止端口 {port} 的进程失败: {e}")
        return False
    
    def start_tts(self):
        """启动 TTS 服务"""
        port = self.ports['TTS']
        if self.check_port(port):
            self.kill_port_process(port)
            time.sleep(1)
        
        try:
            proc = subprocess.Popen(
                [sys.executable, '-m', 'modules.tts.tts_worker'],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.processes['TTS'] = proc
            return True
        except Exception as e:
            print(f"启动 TTS 失败: {e}")
            return False
    
    def start_asr(self):
        """启动 ASR 服务"""
        if 'ASR' in self.processes:
            proc = self.processes['ASR']
            if proc.poll() is None:
                self.stop_service('ASR')
                time.sleep(1)
        
        port = self.ports['ASR']
        if self.check_port(port):
            self.kill_port_process(port)
            time.sleep(1)
        
        try:
            proc = subprocess.Popen(
                [sys.executable, '-m', 'modules.asr.asr_worker'],
                cwd=str(project_root),
                stdout=None,
                stderr=subprocess.STDOUT,
                creationflags=0 if sys.platform == 'win32' else 0
            )
            self.processes['ASR'] = proc
            return True
        except Exception as e:
            print(f"启动 ASR 失败: {e}")
            return False
    
    def start_frontend(self):
        """启动前端服务"""
        if 'Frontend' in self.processes:
            proc = self.processes['Frontend']
            if proc.poll() is None:
                self.stop_service('Frontend')
                time.sleep(1)
        
        port = self.ports['Frontend']
        if self.check_port(port):
            self.kill_port_process(port)
            time.sleep(1)
        
        try:
            html_file = webui_config.get('html_file', 'index.html')
            proc = subprocess.Popen(
                [sys.executable, '-m', 'http.server', str(port)],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.processes['Frontend'] = proc
            return True
        except Exception as e:
            print(f"启动前端服务失败: {e}")
            return False
    
    def start_ollama(self):
        """启动 Ollama 服务"""
        if 'Ollama' in self.processes:
            proc = self.processes['Ollama']
            if proc.poll() is None:
                self.stop_service('Ollama')
                time.sleep(1)
        
        port = self.ports['Ollama']
        if self.check_port(port):
            return True
        
        try:
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, 
                                  timeout=2)
            if result.returncode == 0:
                proc = subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                self.processes['Ollama'] = proc
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        except Exception as e:
            print(f"启动 Ollama 失败: {e}")
        return False
    
    def stop_service(self, name):
        """停止指定服务"""
        if name in self.processes:
            try:
                proc = self.processes[name]
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                del self.processes[name]
                return True
            except Exception as e:
                print(f"停止 {name} 失败: {e}")
        return False
    
    def stop_all(self):
        """停止所有服务"""
        results = {}
        for name in list(self.processes.keys()):
            results[name] = self.stop_service(name)
        
        for name, port in self.ports.items():
            if self.check_port(port):
                self.kill_port_process(port)
        
        return results
    
    def get_status(self):
        """获取所有服务状态"""
        status = {}
        for name, port in self.ports.items():
            if name in self.processes:
                proc = self.processes[name]
                if proc.poll() is None:
                    status[name] = 'running'
                else:
                    status[name] = 'stopped'
            else:
                if self.check_port(port):
                    status[name] = 'running'
                else:
                    status[name] = 'stopped'
        return status


# 创建 FastAPI 应用
app = FastAPI(title="AI-EVA 服务管理器")
service_manager = ServiceManager()

# HTML 界面模板（简化版，实际应该从文件读取）
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-EVA 服务管理器</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Microsoft YaHei UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .controls {
            padding: 30px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
            background: #f7fafc;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            color: white;
            min-width: 120px;
        }
        .btn-start { background: #48bb78; }
        .btn-stop { background: #f56565; }
        .btn-refresh { background: #4299e1; }
        .btn-browser { background: #9f7aea; }
        .services {
            padding: 30px;
        }
        .service-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .service-table th, .service-table td {
            padding: 15px;
            text-align: left;
        }
        .service-table thead {
            background: #e2e8f0;
        }
        .status-running { color: #48bb78; font-weight: bold; }
        .status-stopped { color: #f56565; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI-EVA 服务管理器</h1>
        </div>
        <div class="controls">
            <button class="btn btn-start" onclick="startAll()">🚀 一键启动</button>
            <button class="btn btn-stop" onclick="stopAll()">⏹️ 一键停止</button>
            <button class="btn btn-refresh" onclick="refreshStatus()">🔄 刷新状态</button>
            <button class="btn btn-browser" onclick="openBrowser()">🌐 打开浏览器</button>
        </div>
        <div class="services">
            <h2>服务状态</h2>
            <table class="service-table">
                <thead>
                    <tr>
                        <th>服务名称</th>
                        <th>状态</th>
                        <th>端口</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="services-tbody">
                    <tr><td colspan="4" style="text-align: center;">加载中...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function refreshStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateServicesTable(data.status);
            } catch (error) {
                console.error('刷新状态失败:', error);
            }
        }
        
        function updateServicesTable(status) {
            const tbody = document.getElementById('services-tbody');
            tbody.innerHTML = '';
            
            const ports = {
                'TTS': """ + str(tts_config.get('port', 9966)) + """,
                'ASR': """ + str(asr_config.get('port', 50000)) + """,
                'Frontend': """ + str(webui_config.get('port', 8000)) + """,
                'Ollama': 11434
            };
            
            for (const [name, state] of Object.entries(status)) {
                const row = document.createElement('tr');
                const isRunning = state === 'running';
                
                row.innerHTML = `
                    <td><strong>${name}</strong></td>
                    <td class="${isRunning ? 'status-running' : 'status-stopped'}">
                        ${isRunning ? '✅ 运行中' : '❌ 已停止'}
                    </td>
                    <td>${ports[name] || 'N/A'}</td>
                    <td>
                        ${isRunning 
                            ? `<button class="btn btn-stop" style="padding: 6px 12px; font-size: 12px;" onclick="stopService('${name}')">⏹️ 停止</button>`
                            : `<button class="btn btn-start" style="padding: 6px 12px; font-size: 12px;" onclick="startService('${name}')">▶️ 启动</button>`
                        }
                    </td>
                `;
                tbody.appendChild(row);
            }
        }
        
        async function startAll() {
            try {
                const response = await fetch('/api/start-all', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    setTimeout(refreshStatus, 2000);
                }
            } catch (error) {
                console.error('启动失败:', error);
            }
        }
        
        async function stopAll() {
            if (!confirm('确定要停止所有服务吗？')) return;
            try {
                const response = await fetch('/api/stop-all', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    refreshStatus();
                }
            } catch (error) {
                console.error('停止失败:', error);
            }
        }
        
        async function startService(name) {
            try {
                const response = await fetch(`/api/start/${name}`, { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    setTimeout(refreshStatus, 2000);
                }
            } catch (error) {
                console.error('启动失败:', error);
            }
        }
        
        async function stopService(name) {
            if (!confirm(`确定要停止 ${name} 服务吗？`)) return;
            try {
                const response = await fetch(`/api/stop/${name}`, { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    refreshStatus();
                }
            } catch (error) {
                console.error('停止失败:', error);
            }
        }
        
        function openBrowser() {
            window.open('http://localhost:' + """ + str(webui_config.get('port', 8000)) + """, '_blank');
        }
        
        refreshStatus();
        setInterval(refreshStatus, 5000);
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_TEMPLATE

@app.get("/api/status")
async def get_status():
    status = service_manager.get_status()
    return JSONResponse({"status": status})

@app.post("/api/start-all")
async def start_all():
    try:
        def start_services():
            results = {}
            services = [
                ('TTS', service_manager.start_tts),
                ('ASR', service_manager.start_asr),
                ('Frontend', service_manager.start_frontend),
                ('Ollama', service_manager.start_ollama)
            ]
            for name, start_func in services:
                results[name] = start_func()
                time.sleep(1)
            return results
        
        results = service_manager.executor.submit(start_services).result(timeout=60)
        return JSONResponse({"success": True, "results": results})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@app.post("/api/stop-all")
async def stop_all():
    try:
        results = service_manager.stop_all()
        return JSONResponse({"success": True, "results": results})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@app.post("/api/start/{service_name}")
async def start_service(service_name: str):
    try:
        success = False
        if service_name == 'TTS':
            success = service_manager.start_tts()
        elif service_name == 'ASR':
            success = service_manager.start_asr()
        elif service_name == 'Frontend':
            success = service_manager.start_frontend()
        elif service_name == 'Ollama':
            success = service_manager.start_ollama()
        else:
            return JSONResponse({"success": False, "message": "未知服务"}, status_code=400)
        
        return JSONResponse({"success": success})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@app.post("/api/stop/{service_name}")
async def stop_service(service_name: str):
    try:
        success = service_manager.stop_service(service_name)
        return JSONResponse({"success": success})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

def main():
    """主函数"""
    try:
        import psutil
    except ImportError:
        print("正在安装 psutil...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'psutil', '--quiet'])
        import psutil
    
    def open_browser():
        time.sleep(2)
        manager_port = webui_config.get('manager_port', 9000)
        webbrowser.open(f'http://localhost:{manager_port}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    manager_port = webui_config.get('manager_port', 9000)
    print("=" * 50)
    print("AI-EVA 服务管理器")
    print("=" * 50)
    print(f"服务管理界面: http://localhost:{manager_port}")
    print(f"前端界面: http://localhost:{webui_config.get('port', 8000)}")
    print("=" * 50)
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    uvicorn.run(app, host="127.0.0.1", port=manager_port, log_level="info")

if __name__ == '__main__':
    main()

