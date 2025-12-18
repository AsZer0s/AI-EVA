#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI-EVA Demo GUI 启动器
支持一键启动和一键停止所有服务
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import time
import os
import sys
import socket
import psutil
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

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
        # 如果已经在运行，先停止
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
            # 使用控制台窗口显示输出，方便查看错误信息
            if sys.platform == 'win32':
                # Windows: 创建新窗口显示输出
                proc = subprocess.Popen(
                    [sys.executable, 'api.py'],
                    cwd=str(sensevoice_path.parent),
                    stdout=None,  # 输出到控制台
                    stderr=subprocess.STDOUT,  # 错误也输出到控制台
                    creationflags=0  # 显示窗口
                )
            else:
                # Linux/Mac: 输出到当前终端
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
            import traceback
            traceback.print_exc()
            return False
    
    def start_frontend(self):
        """启动前端服务"""
        # 如果已经在运行，先停止
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
        # 如果已经在运行，先停止
        if 'Ollama' in self.processes:
            proc = self.processes['Ollama']
            if proc.poll() is None:
                self.stop_service('Ollama')
                time.sleep(1)
        
        if self.check_port(self.ports['Ollama']):
            # Ollama 可能已经在运行，不重复启动
            return True
        
        try:
            # 检查 ollama 命令是否存在
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
                if proc.poll() is None:  # 进程还在运行
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
        
        # 强制终止端口进程
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


class AIEVALauncher:
    """AI-EVA GUI 启动器"""
    def __init__(self, root):
        self.root = root
        self.root.title("AI-EVA Demo 启动器")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设置窗口图标（如果有）
        try:
            if sys.platform == 'win32':
                self.root.iconbitmap(default='')
        except:
            pass
        
        self.service_manager = ServiceManager()
        self.is_starting = False
        self.is_stopping = False
        
        # 创建线程池执行器用于异步操作
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="AI-EVA")
        
        self.setup_ui()
        
        # 异步更新状态，不阻塞UI
        self.root.after(100, lambda: self.async_update_status())
        
        # 定期更新状态（异步）
        self.root.after(2000, self.periodic_update)
    
    def setup_ui(self):
        """设置UI界面"""
        # Demo阶段提示横幅
        banner_frame = tk.Frame(self.root, bg='#fbbf24', height=40)
        banner_frame.pack(fill=tk.X)
        banner_frame.pack_propagate(False)
        
        banner_label = tk.Label(
            banner_frame,
            text="⚠️ Demo阶段：程序运行可能会不稳定，如有异常可即刻向我们反馈",
            font=('Microsoft YaHei UI', 10),
            bg='#fbbf24',
            fg='#92400e',
            wraplength=750
        )
        banner_label.pack(expand=True)
        
        # 主标题
        title_frame = tk.Frame(self.root, bg='#667eea', height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="AI-EVA Demo 服务管理器",
            font=('Microsoft YaHei UI', 16, 'bold'),
            bg='#667eea',
            fg='white'
        )
        title_label.pack(pady=15)
        
        # 控制按钮区域
        control_frame = tk.Frame(self.root, padx=20, pady=15)
        control_frame.pack(fill=tk.X)
        
        self.start_btn = tk.Button(
            control_frame,
            text="🚀 一键启动",
            command=self.start_all_services,
            bg='#48bb78',
            fg='white',
            font=('Microsoft YaHei UI', 12, 'bold'),
            width=15,
            height=2,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = tk.Button(
            control_frame,
            text="⏹️ 一键停止",
            command=self.stop_all_services,
            bg='#f56565',
            fg='white',
            font=('Microsoft YaHei UI', 12, 'bold'),
            width=15,
            height=2,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        self.refresh_btn = tk.Button(
            control_frame,
            text="🔄 刷新状态",
            command=self.update_status,
            bg='#4299e1',
            fg='white',
            font=('Microsoft YaHei UI', 12, 'bold'),
            width=15,
            height=2,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=10)
        
        self.open_browser_btn = tk.Button(
            control_frame,
            text="🌐 打开浏览器",
            command=self.open_browser,
            bg='#9f7aea',
            fg='white',
            font=('Microsoft YaHei UI', 12, 'bold'),
            width=15,
            height=2,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.open_browser_btn.pack(side=tk.LEFT, padx=10)
        
        # 服务状态区域
        status_frame = tk.LabelFrame(
            self.root,
            text="服务状态",
            font=('Microsoft YaHei UI', 11, 'bold'),
            padx=20,
            pady=15
        )
        status_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 创建服务状态表格（带操作按钮）
        table_frame = tk.Frame(status_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # 表头
        header_frame = tk.Frame(table_frame, bg='#e2e8f0')
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(header_frame, text='服务名称', font=('Microsoft YaHei UI', 10, 'bold'), 
                bg='#e2e8f0', width=15, anchor='w').pack(side=tk.LEFT, padx=5)
        tk.Label(header_frame, text='状态', font=('Microsoft YaHei UI', 10, 'bold'), 
                bg='#e2e8f0', width=12, anchor='w').pack(side=tk.LEFT, padx=5)
        tk.Label(header_frame, text='端口', font=('Microsoft YaHei UI', 10, 'bold'), 
                bg='#e2e8f0', width=10, anchor='w').pack(side=tk.LEFT, padx=5)
        tk.Label(header_frame, text='操作', font=('Microsoft YaHei UI', 10, 'bold'), 
                bg='#e2e8f0', width=20, anchor='w').pack(side=tk.LEFT, padx=5)
        
        # 服务列表容器（可滚动）
        canvas = tk.Canvas(table_frame, bg='white')
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.services_frame = tk.Frame(canvas, bg='white')
        
        self.services_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.services_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 存储服务行控件的字典
        self.service_rows = {}
        
        # 日志区域
        log_frame = tk.LabelFrame(
            self.root,
            text="运行日志",
            font=('Microsoft YaHei UI', 11, 'bold'),
            padx=20,
            pady=15
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            font=('Consolas', 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        self.log("AI-EVA Demo 启动器已就绪")
    
    def log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def async_update_status(self):
        """异步更新服务状态，不阻塞UI"""
        def _update():
            try:
                status = self.service_manager.get_status()
                # 在主线程更新UI
                self.root.after(0, lambda: self._update_ui(status))
            except Exception as e:
                self.log(f"更新状态失败: {e}")
        
        # 在线程池中执行
        self.executor.submit(_update)
    
    def _update_ui(self, status):
        """在主线程更新UI"""
        # 清空现有服务行（保留框架结构）
        for widget in self.services_frame.winfo_children():
            widget.destroy()
        self.service_rows = {}
        
        # 创建服务行
        for name, state in status.items():
            port = self.service_manager.ports[name]
            is_running = state == 'running'
            
            # 创建服务行框架
            row_frame = tk.Frame(self.services_frame, bg='white', relief=tk.RAISED, bd=1)
            row_frame.pack(fill=tk.X, padx=2, pady=2)
            
            # 服务名称
            name_label = tk.Label(
                row_frame,
                text=name,
                font=('Microsoft YaHei UI', 10),
                bg='white',
                width=15,
                anchor='w'
            )
            name_label.pack(side=tk.LEFT, padx=5, pady=5)
            
            # 状态标签
            status_text = "✅ 运行中" if is_running else "❌ 已停止"
            status_color = '#48bb78' if is_running else '#f56565'
            status_label = tk.Label(
                row_frame,
                text=status_text,
                font=('Microsoft YaHei UI', 9),
                bg='white',
                fg=status_color,
                width=12,
                anchor='w'
            )
            status_label.pack(side=tk.LEFT, padx=5, pady=5)
            
            # 端口标签
            port_label = tk.Label(
                row_frame,
                text=str(port),
                font=('Microsoft YaHei UI', 9),
                bg='white',
                width=10,
                anchor='w'
            )
            port_label.pack(side=tk.LEFT, padx=5, pady=5)
            
            # 操作按钮框架
            btn_frame = tk.Frame(row_frame, bg='white')
            btn_frame.pack(side=tk.LEFT, padx=5, pady=5)
            
            # 启动/停止按钮
            if is_running:
                stop_btn = tk.Button(
                    btn_frame,
                    text="⏹️ 停止",
                    command=lambda n=name: self.stop_single_service(n),
                    bg='#f56565',
                    fg='white',
                    font=('Microsoft YaHei UI', 8),
                    width=8,
                    relief=tk.FLAT,
                    cursor='hand2'
                )
                stop_btn.pack(side=tk.LEFT, padx=2)
            else:
                start_btn = tk.Button(
                    btn_frame,
                    text="▶️ 启动",
                    command=lambda n=name: self.start_single_service(n),
                    bg='#48bb78',
                    fg='white',
                    font=('Microsoft YaHei UI', 8),
                    width=8,
                    relief=tk.FLAT,
                    cursor='hand2'
                )
                start_btn.pack(side=tk.LEFT, padx=2)
            
            # 保存行控件引用
            self.service_rows[name] = {
                'frame': row_frame,
                'status_label': status_label,
                'name': name,
                'port': port
            }
    
    def start_all_services(self):
        """启动所有服务"""
        if self.is_starting:
            return
        
        self.is_starting = True
        self.start_btn.config(state=tk.DISABLED)
        self.log("开始启动所有服务...")
        
        def start_thread():
            try:
                # 检查 Python 环境（异步）
                self.log("检查 Python 环境...")
                python_check = self.executor.submit(self.check_python).result(timeout=5)
                if not python_check:
                    self.root.after(0, lambda: messagebox.showerror("错误", "未找到 Python 环境，请先安装 Python 3.8+"))
                    return
                
                # 检查依赖（异步）
                self.log("检查依赖包...")
                deps_check = self.executor.submit(self.check_dependencies).result(timeout=5)
                if not deps_check:
                    self.log("开始安装依赖...")
                    install_result = self.executor.submit(self.install_dependencies).result(timeout=300)
                    if not install_result:
                        self.root.after(0, lambda: messagebox.showerror("错误", "依赖安装失败，请检查网络连接"))
                        return
                
                # 启动服务（异步执行）
                services = [
                    ('IndexTTS2', self.service_manager.start_chattts),
                    ('SenseVoice', self.service_manager.start_sensevoice),
                    ('Frontend', self.service_manager.start_frontend),
                    ('Ollama', self.service_manager.start_ollama)
                ]
                
                for name, start_func in services:
                    self.log(f"启动 {name} 服务...")
                    # 在线程池中异步启动服务
                    try:
                        result = self.executor.submit(start_func).result(timeout=30)
                        if result:
                            self.log(f"✅ {name} 服务启动成功")
                            # SenseVoice 启动后检查是否立即退出
                            if name == 'SenseVoice':
                                time.sleep(3)
                                proc = self.service_manager.processes.get('SenseVoice')
                                if proc and proc.poll() is not None:
                                    return_code = proc.returncode
                                    self.log(f"❌ {name} 服务启动后立即退出，返回码: {return_code}")
                                    self.log(f"💡 请查看 SenseVoice 控制台窗口查看详细错误信息")
                                else:
                                    self.log(f"💡 SenseVoice 输出已显示在独立控制台窗口")
                            else:
                                time.sleep(2)
                        else:
                            if name == 'SenseVoice':
                                self.log(f"⚠️ {name} 服务未找到，跳过")
                            elif name == 'Ollama':
                                self.log(f"⚠️ {name} 未安装或已在运行")
                            else:
                                self.log(f"❌ {name} 服务启动失败")
                    except Exception as e:
                        self.log(f"❌ 启动 {name} 服务时出错: {e}")
                
                self.log("所有服务启动完成！")
                self.log("等待服务就绪...")
                time.sleep(3)
                
                self.root.after(0, lambda: messagebox.showinfo(
                    "启动完成",
                    "所有服务已启动！\n\n前端地址: http://localhost:8000\n\n点击'打开浏览器'按钮访问界面"
                ))
                
            except Exception as e:
                self.log(f"❌ 启动失败: {e}")
                import traceback
                error_detail = traceback.format_exc()
                self.log(f"详细错误:\n{error_detail}")
                self.root.after(0, lambda: messagebox.showerror("错误", f"启动失败: {e}"))
            finally:
                self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.async_update_status())
                self.is_starting = False
        
        # 在线程池中执行，不阻塞UI
        self.executor.submit(start_thread)
    
    def stop_all_services(self):
        """停止所有服务（全异步）"""
        if self.is_stopping:
            return
        
        result = messagebox.askyesno("确认", "确定要停止所有服务吗？")
        if not result:
            return
        
        self.is_stopping = True
        self.stop_btn.config(state=tk.DISABLED)
        self.log("开始停止所有服务...")
        
        def stop_thread():
            """在后台线程执行停止操作"""
            try:
                # 异步停止服务
                results = self.service_manager.stop_all()
                for name, success in results.items():
                    if success:
                        self.log(f"✅ {name} 服务已停止")
                    else:
                        self.log(f"⚠️ {name} 服务停止失败")
                
                # 异步强制终止端口进程
                for name, port in self.service_manager.ports.items():
                    port_check = self.executor.submit(self.service_manager.check_port, port).result(timeout=2)
                    if port_check:
                        self.log(f"强制终止占用端口 {port} 的进程...")
                        self.executor.submit(self.service_manager.kill_port_process, port)
                
                self.log("所有服务已停止")
                self.root.after(0, lambda: messagebox.showinfo("停止完成", "所有服务已停止"))
                
            except Exception as e:
                self.log(f"❌ 停止失败: {e}")
                import traceback
                error_detail = traceback.format_exc()
                self.log(f"详细错误:\n{error_detail}")
                self.root.after(0, lambda: messagebox.showerror("错误", f"停止失败: {e}"))
            finally:
                self.root.after(0, lambda: self.stop_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.async_update_status())
                self.is_stopping = False
        
        # 在线程池中执行，不阻塞UI
        self.executor.submit(stop_thread)
    
    def start_single_service(self, service_name):
        """启动单个服务"""
        self.log(f"开始启动 {service_name} 服务...")
        
        def start_thread():
            try:
                success = False
                if service_name == 'IndexTTS2':
                    success = self.service_manager.start_chattts()
                elif service_name == 'SenseVoice':
                    success = self.service_manager.start_sensevoice()
                elif service_name == 'Frontend':
                    success = self.service_manager.start_frontend()
                elif service_name == 'Ollama':
                    success = self.service_manager.start_ollama()
                
                if success:
                    self.log(f"✅ {service_name} 服务启动成功")
                    # SenseVoice 启动后检查是否立即退出
                    if service_name == 'SenseVoice':
                        time.sleep(3)
                        proc = self.service_manager.processes.get('SenseVoice')
                        if proc and proc.poll() is not None:
                            # 进程已退出，说明启动失败
                            return_code = proc.returncode
                            self.log(f"❌ {service_name} 服务启动后立即退出，返回码: {return_code}")
                            self.log(f"💡 请查看 SenseVoice 控制台窗口查看详细错误信息")
                            self.root.after(0, self.update_status)
                            return
                        else:
                            self.log(f"💡 SenseVoice 输出已显示在独立控制台窗口")
                    else:
                        time.sleep(2)  # 等待服务就绪
                else:
                    if service_name == 'SenseVoice':
                        self.log(f"⚠️ {service_name} 服务未找到，跳过")
                    elif service_name == 'Ollama':
                        self.log(f"⚠️ {service_name} 未安装或已在运行")
                    else:
                        self.log(f"❌ {service_name} 服务启动失败")
                
            except Exception as e:
                self.log(f"❌ 启动 {service_name} 失败: {e}")
                import traceback
                error_detail = traceback.format_exc()
                self.log(f"详细错误:\n{error_detail}")
            finally:
                self.root.after(0, lambda: self.async_update_status())
        
        # 在线程池中执行，不阻塞UI
        self.executor.submit(start_thread)
    
    def stop_single_service(self, service_name):
        """停止单个服务"""
        result = messagebox.askyesno("确认", f"确定要停止 {service_name} 服务吗？")
        if not result:
            return
        
        self.log(f"开始停止 {service_name} 服务...")
        
        def stop_thread():
            try:
                success = self.service_manager.stop_service(service_name)
                
                if success:
                    self.log(f"✅ {service_name} 服务已停止")
                else:
                    # 尝试强制终止端口进程（异步）
                    port = self.service_manager.ports[service_name]
                    port_check = self.executor.submit(self.service_manager.check_port, port).result(timeout=2)
                    if port_check:
                        self.log(f"强制终止占用端口 {port} 的进程...")
                        self.executor.submit(self.service_manager.kill_port_process, port)
                        self.log(f"✅ {service_name} 服务已停止")
                    else:
                        self.log(f"⚠️ {service_name} 服务停止失败或未运行")
                
            except Exception as e:
                self.log(f"❌ 停止 {service_name} 失败: {e}")
                import traceback
                error_detail = traceback.format_exc()
                self.log(f"详细错误:\n{error_detail}")
            finally:
                self.root.after(0, lambda: self.async_update_status())
        
        # 在线程池中执行，不阻塞UI
        self.executor.submit(stop_thread)
    
    def open_browser(self):
        """打开浏览器"""
        import webbrowser
        webbrowser.open('http://localhost:8000')
        self.log("已打开浏览器")
    
    def check_python(self):
        """检查 Python 环境"""
        try:
            result = subprocess.run([sys.executable, '--version'], 
                                  capture_output=True, 
                                  timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def check_dependencies(self):
        """检查依赖是否已安装"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'fastapi'],
                                  capture_output=True,
                                  timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def install_dependencies(self):
        """安装依赖"""
        try:
            requirements_file = Path('requirements.txt')
            if not requirements_file.exists():
                self.log("未找到 requirements.txt")
                return False
            
            self.log("正在安装依赖，请稍候...")
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--quiet'],
                timeout=300,
                capture_output=True
            )
            return result.returncode == 0
        except Exception as e:
            self.log(f"依赖安装失败: {e}")
            return False
    
    def periodic_update(self):
        """定期更新状态（异步）"""
        self.async_update_status()
        self.root.after(5000, self.periodic_update)
    
    def update_status(self):
        """同步更新状态（用于手动刷新按钮）"""
        self.async_update_status()


def main():
    """主函数"""
    # 检查 psutil 是否安装
    try:
        import psutil
    except ImportError:
        print("正在安装 psutil...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'psutil', '--quiet'])
        import psutil
    
    root = tk.Tk()
    app = AIEVALauncher(root)
    
    # 窗口关闭时清理资源
    def on_closing():
        try:
            if hasattr(app, 'executor'):
                app.executor.shutdown(wait=False)
        except:
            pass
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()

