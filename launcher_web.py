#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI-EVA Demo Web 启动器
基于 Web 的服务管理界面，无需 tkinter
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

class ServiceManager:
    """服务管理器"""
    def __init__(self):
        self.processes = {}
        self.ports = {
            'IndexTTS2': 9966,
            'SenseVoice': 50000,
            'Frontend': 8000,
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
    
    def start_chattts(self):
        """启动 IndexTTS2 服务"""
        if self.check_port(self.ports['ChatTTS']):
            self.kill_port_process(self.ports['ChatTTS'])
            time.sleep(1)
        
        try:
            proc = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', 'indextts_api:app', '--host', '0.0.0.0', '--port', '9966'],
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.processes['ChatTTS'] = proc
            return True
        except Exception as e:
            print(f"启动 IndexTTS2 失败: {e}")
            return False
    
    def start_sensevoice(self):
        """启动 SenseVoice 服务"""
        if 'SenseVoice' in self.processes:
            proc = self.processes['SenseVoice']
            if proc.poll() is None:
                self.stop_service('SenseVoice')
                time.sleep(1)
        
        if self.check_port(self.ports['SenseVoice']):
            self.kill_port_process(self.ports['SenseVoice'])
            time.sleep(1)
        
        sensevoice_path = Path('SenseVoice/api.py')
        if not sensevoice_path.exists():
            return False
        
        try:
            if sys.platform == 'win32':
                proc = subprocess.Popen(
                    [sys.executable, 'api.py'],
                    cwd=str(sensevoice_path.parent),
                    stdout=None,
                    stderr=subprocess.STDOUT,
                    creationflags=0
                )
            else:
                proc = subprocess.Popen(
                    [sys.executable, 'api.py'],
                    cwd=str(sensevoice_path.parent),
                    stdout=None,
                    stderr=subprocess.STDOUT
                )
            self.processes['SenseVoice'] = proc
            return True
        except Exception as e:
            print(f"启动 SenseVoice 失败: {e}")
            return False
    
    def start_frontend(self):
        """启动前端服务"""
        if 'Frontend' in self.processes:
            proc = self.processes['Frontend']
            if proc.poll() is None:
                self.stop_service('Frontend')
                time.sleep(1)
        
        if self.check_port(self.ports['Frontend']):
            self.kill_port_process(self.ports['Frontend'])
            time.sleep(1)
        
        try:
            proc = subprocess.Popen(
                [sys.executable, '-m', 'http.server', '8000'],
                cwd=os.getcwd(),
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
        
        if self.check_port(self.ports['Ollama']):
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

# HTML 界面
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-EVA 服务管理器</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei UI', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
        .banner {
            background: #fbbf24;
            color: #92400e;
            padding: 15px;
            text-align: center;
            font-size: 14px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
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
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .btn:active {
            transform: translateY(0);
        }
        .btn-start { background: #48bb78; }
        .btn-stop { background: #f56565; }
        .btn-refresh { background: #4299e1; }
        .btn-browser { background: #9f7aea; }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .services {
            padding: 30px;
        }
        .services h2 {
            margin-bottom: 20px;
            color: #2d3748;
        }
        .service-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .service-table thead {
            background: #e2e8f0;
        }
        .service-table th {
            padding: 15px;
            text-align: left;
            font-weight: bold;
            color: #2d3748;
        }
        .service-table td {
            padding: 15px;
            border-top: 1px solid #e2e8f0;
        }
        .service-table tr:hover {
            background: #f7fafc;
        }
        .status-running {
            color: #48bb78;
            font-weight: bold;
        }
        .status-stopped {
            color: #f56565;
            font-weight: bold;
        }
        .log-area {
            padding: 30px;
            background: #1a202c;
            color: #e2e8f0;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
            border-radius: 8px;
        }
        .log-entry {
            padding: 5px 0;
            border-bottom: 1px solid #2d3748;
        }
        .log-time {
            color: #718096;
        }
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="banner">
            ⚠️ Demo阶段：程序运行可能会不稳定，如有异常可即刻向我们反馈
        </div>
        <div class="header">
            <h1>AI-EVA Demo 服务管理器</h1>
            <p>基于 Web 的服务管理界面</p>
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
        <div class="log-area" id="log-area">
            <div class="log-entry"><span class="log-time">[系统]</span> AI-EVA Demo 服务管理器已就绪</div>
        </div>
    </div>

    <script>
        let statusInterval;
        
        function addLog(message) {
            const logArea = document.getElementById('log-area');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
            logArea.appendChild(entry);
            logArea.scrollTop = logArea.scrollHeight;
        }
        
        async function refreshStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateServicesTable(data.status);
            } catch (error) {
                addLog('刷新状态失败: ' + error.message);
            }
        }
        
        function updateServicesTable(status) {
            const tbody = document.getElementById('services-tbody');
            tbody.innerHTML = '';
            
            const ports = {
                'IndexTTS2': 9966,
                'SenseVoice': 50000,
                'Frontend': 8000,
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
            addLog('开始启动所有服务...');
            try {
                const response = await fetch('/api/start-all', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    addLog('所有服务启动完成！');
                    setTimeout(refreshStatus, 2000);
                } else {
                    addLog('启动失败: ' + (data.message || '未知错误'));
                }
            } catch (error) {
                addLog('启动失败: ' + error.message);
            }
        }
        
        async function stopAll() {
            if (!confirm('确定要停止所有服务吗？')) return;
            addLog('开始停止所有服务...');
            try {
                const response = await fetch('/api/stop-all', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    addLog('所有服务已停止');
                    refreshStatus();
                } else {
                    addLog('停止失败: ' + (data.message || '未知错误'));
                }
            } catch (error) {
                addLog('停止失败: ' + error.message);
            }
        }
        
        async function startService(name) {
            addLog(`开始启动 ${name} 服务...`);
            try {
                const response = await fetch(`/api/start/${name}`, { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    addLog(`${name} 服务启动成功`);
                    setTimeout(refreshStatus, 2000);
                } else {
                    addLog(`${name} 服务启动失败: ` + (data.message || '未知错误'));
                }
            } catch (error) {
                addLog(`启动 ${name} 失败: ` + error.message);
            }
        }
        
        async function stopService(name) {
            if (!confirm(`确定要停止 ${name} 服务吗？`)) return;
            addLog(`开始停止 ${name} 服务...`);
            try {
                const response = await fetch(`/api/stop/${name}`, { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    addLog(`${name} 服务已停止`);
                    refreshStatus();
                } else {
                    addLog(`${name} 服务停止失败: ` + (data.message || '未知错误'));
                }
            } catch (error) {
                addLog(`停止 ${name} 失败: ` + error.message);
            }
        }
        
        function openBrowser() {
            window.open('http://localhost:8000', '_blank');
            addLog('已打开浏览器');
        }
        
        // 页面加载时刷新状态
        refreshStatus();
        // 每5秒自动刷新状态
        statusInterval = setInterval(refreshStatus, 5000);
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
        # 异步启动服务
        def start_services():
            results = {}
            services = [
                ('IndexTTS2', service_manager.start_chattts),
                ('SenseVoice', service_manager.start_sensevoice),
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
        if service_name == 'IndexTTS2':
            success = service_manager.start_chattts()
        elif service_name == 'SenseVoice':
            success = service_manager.start_sensevoice()
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
    # 检查 psutil 是否安装
    try:
        import psutil
    except ImportError:
        print("正在安装 psutil...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'psutil', '--quiet'])
        import psutil
    
    # 延迟打开浏览器
    def open_browser():
        time.sleep(2)
        webbrowser.open('http://localhost:9000')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("=" * 50)
    print("AI-EVA Demo Web 启动器")
    print("=" * 50)
    print("服务管理界面: http://localhost:9000")
    print("前端界面: http://localhost:8000")
    print("=" * 50)
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="info")

if __name__ == '__main__':
    main()

