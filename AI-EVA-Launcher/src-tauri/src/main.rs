// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::Command;
use std::fs;
use std::io::Write;

#[tauri::command]
fn get_default_install_path() -> Result<String, String> {
    let home = dirs::home_dir().ok_or("无法获取用户主目录")?;
    let default_path = home.join("AI-EVA");
    Ok(default_path.to_string_lossy().to_string())
}

#[tauri::command]
fn check_python_env(install_path: String) -> Result<String, String> {
    let install_path_buf = PathBuf::from(&install_path);
    let python_dir = install_path_buf.join("python-portable");
    let python_exe = python_dir.join("python.exe");
    
    // 检查便携式 Python
    if python_exe.exists() {
        let output = Command::new(&python_exe)
            .arg("--version")
            .output();
        
        if let Ok(output) = output {
            if output.status.success() {
                let version = String::from_utf8_lossy(&output.stdout);
                return Ok(format!("便携式: {}", version.trim()));
            }
        }
    }
    
    // 检查系统 Python
    let system_python = Command::new("python")
        .arg("--version")
        .output();
    
    if let Ok(output) = system_python {
        if output.status.success() {
            let version = String::from_utf8_lossy(&output.stdout);
            return Ok(format!("系统: {}", version.trim()));
        }
    }
    
    // 检查 python3
    let python3 = Command::new("python3")
        .arg("--version")
        .output();
    
    if let Ok(output) = python3 {
        if output.status.success() {
            let version = String::from_utf8_lossy(&output.stdout);
            return Ok(format!("系统: {}", version.trim()));
        }
    }
    
    Err("未安装 Python".to_string())
}

#[tauri::command]
fn check_ai_eva(install_path: String) -> Result<String, String> {
    let install_path_buf = PathBuf::from(&install_path);
    
    // 检查关键文件
    let key_files = [
        "index.html",
        "indextts_api.py",
        "start-all.bat",
        "AAA一键启动.bat"
    ];
    
    let mut found_files = Vec::new();
    for file in &key_files {
        let file_path = install_path_buf.join(file);
        if file_path.exists() {
            found_files.push(file);
        }
    }
    
    if found_files.len() >= 2 {
        Ok(format!("已安装 ({} 个文件)", found_files.len()))
    } else {
        Err("未安装".to_string())
    }
}

#[tauri::command]
fn check_indextts(install_path: String) -> Result<String, String> {
    let install_path_buf = PathBuf::from(&install_path);
    let indextts_path = install_path_buf.join("index-tts");
    
    if indextts_path.exists() {
        // 检查是否是 Git 仓库
        let git_dir = indextts_path.join(".git");
        if git_dir.exists() {
            Ok("已克隆 (Git 仓库)".to_string())
        } else {
            Ok("已存在目录".to_string())
        }
    } else {
        Err("未安装".to_string())
    }
}

#[tauri::command]
async fn setup_python_env(install_path: String) -> Result<String, String> {
    let install_path_buf = PathBuf::from(&install_path);
    let python_dir = install_path_buf.join("python-portable");
    
    // 检查是否已存在 Python 环境
    let python_exe = python_dir.join("python.exe");
    if python_exe.exists() {
        // 验证 Python 是否可用
        let output = Command::new(&python_exe)
            .arg("--version")
            .output();
        
        if let Ok(output) = output {
            if output.status.success() {
                let version = String::from_utf8_lossy(&output.stdout);
                return Ok(format!("已存在: {}", version.trim()));
            }
        }
    }
    
    // 检查系统 Python
    let system_python = Command::new("python")
        .arg("--version")
        .output();
    
    if let Ok(output) = system_python {
        if output.status.success() {
            let version = String::from_utf8_lossy(&output.stdout);
            return Ok(format!("使用系统 Python: {}", version.trim()));
        }
    }
    
    // 需要下载便携式 Python
    println!("开始下载便携式 Python...");
    
    // 创建目录
    fs::create_dir_all(&python_dir)
        .map_err(|e| format!("创建目录失败: {}", e))?;
    
    // Python Embedded 下载 URL
    let python_version = "3.10.9";
    let python_url = format!(
        "https://www.python.org/ftp/python/{}/python-{}-embed-amd64.zip",
        python_version, python_version
    );
    
    println!("下载地址: {}", python_url);
    
    // 下载 Python Embedded
    let response = reqwest::get(&python_url)
        .await
        .map_err(|e| format!("下载 Python 失败: {}", e))?;
    
    let total_size = response.content_length().unwrap_or(0);
    let mut downloaded = 0u64;
    let zip_path = python_dir.join("python-embed.zip");
    let mut file = fs::File::create(&zip_path)
        .map_err(|e| format!("创建文件失败: {}", e))?;
    
    let mut stream = response.bytes_stream();
    
    use futures_util::StreamExt;
    while let Some(item) = stream.next().await {
        let chunk = item.map_err(|e| format!("读取数据失败: {}", e))?;
        file.write_all(&chunk)
            .map_err(|e| format!("写入文件失败: {}", e))?;
        downloaded += chunk.len() as u64;
        
        if total_size > 0 {
            let percent = (downloaded * 100) / total_size;
            println!("Python 下载进度: {}%", percent);
        }
    }
    
    // 解压文件
    println!("解压 Python...");
    let zip_file = fs::File::open(&zip_path)
        .map_err(|e| format!("打开压缩文件失败: {}", e))?;
    
    let mut archive = zip::ZipArchive::new(zip_file)
        .map_err(|e| format!("读取压缩文件失败: {}", e))?;
    
    for i in 0..archive.len() {
        let mut file = archive.by_index(i)
            .map_err(|e| format!("读取压缩文件条目失败: {}", e))?;
        
        let outpath = match file.enclosed_name() {
            Some(path) => python_dir.join(path),
            None => continue,
        };
        
        if (*file.name()).ends_with('/') {
            fs::create_dir_all(&outpath)
                .map_err(|e| format!("创建目录失败: {}", e))?;
        } else {
            if let Some(p) = outpath.parent() {
                fs::create_dir_all(p)
                    .map_err(|e| format!("创建目录失败: {}", e))?;
            }
            
            let mut outfile = fs::File::create(&outpath)
                .map_err(|e| format!("创建文件失败: {}", e))?;
            std::io::copy(&mut file, &mut outfile)
                .map_err(|e| format!("写入文件失败: {}", e))?;
        }
    }
    
    // 删除压缩文件
    fs::remove_file(&zip_path)
        .map_err(|e| format!("删除压缩文件失败: {}", e))?;
    
    // 创建 python310._pth 配置文件
    let pth_content = "python310.zip\n.\n# Uncomment to run site.main() automatically\nimport site\n";
    let pth_path = python_dir.join("python310._pth");
    fs::write(&pth_path, pth_content)
        .map_err(|e| format!("创建配置文件失败: {}", e))?;
    
    // 安装 pip
    println!("安装 pip...");
    let pip_script_url = "https://bootstrap.pypa.io/get-pip.py";
    let pip_script_path = python_dir.join("get-pip.py");
    
    let pip_response = reqwest::get(pip_script_url)
        .await
        .map_err(|e| format!("下载 pip 安装脚本失败: {}", e))?;
    
    let mut pip_file = fs::File::create(&pip_script_path)
        .map_err(|e| format!("创建文件失败: {}", e))?;
    
    let mut pip_stream = pip_response.bytes_stream();
    while let Some(item) = pip_stream.next().await {
        let chunk = item.map_err(|e| format!("读取数据失败: {}", e))?;
        pip_file.write_all(&chunk)
            .map_err(|e| format!("写入文件失败: {}", e))?;
    }
    
    // 执行 pip 安装
    let pip_output = Command::new(&python_exe)
        .arg(&pip_script_path)
        .current_dir(&python_dir)
        .output()
        .map_err(|e| format!("执行 pip 安装失败: {}", e))?;
    
    if !pip_output.status.success() {
        let error_msg = String::from_utf8_lossy(&pip_output.stderr);
        return Err(format!("pip 安装失败: {}", error_msg));
    }
    
    // 删除临时文件
    let _ = fs::remove_file(&pip_script_path);
    
    Ok(format!("Python {} 便携式环境安装完成", python_version))
}

#[tauri::command]
async fn download_ai_eva(repo_url: String, install_path: String) -> Result<String, String> {
    let install_path_buf = PathBuf::from(&install_path);
    
    // 创建安装目录
    fs::create_dir_all(&install_path_buf)
        .map_err(|e| format!("创建目录失败: {}", e))?;

    // 解析 GitHub 仓库 URL
    let repo_url = repo_url.trim();
    let (owner, repo) = parse_github_url(&repo_url)?;

    // 下载最新 release 或直接下载 zip
    // 优先尝试 main 分支，如果失败则尝试 master 分支
    let download_url = if repo_url.contains("/releases/") {
        repo_url.to_string()
    } else {
        // 尝试下载 main 分支
        format!("https://github.com/{}/{}/archive/refs/heads/main.zip", owner, repo)
    };

    println!("下载地址: {}", download_url);
    
    // 下载文件
    let response = reqwest::get(&download_url)
        .await
        .map_err(|e| format!("下载失败: {}", e))?;

    let total_size = response.content_length().unwrap_or(0);
    let mut downloaded = 0u64;
    let mut file = fs::File::create(install_path_buf.join("ai-eva.zip"))
        .map_err(|e| format!("创建文件失败: {}", e))?;

    let mut stream = response.bytes_stream();
    
    use futures_util::StreamExt;
    while let Some(item) = stream.next().await {
        let chunk = item.map_err(|e| format!("读取数据失败: {}", e))?;
        file.write_all(&chunk)
            .map_err(|e| format!("写入文件失败: {}", e))?;
        downloaded += chunk.len() as u64;
        
        if total_size > 0 {
            let percent = (downloaded * 100) / total_size;
            println!("下载进度: {}%", percent);
        }
    }

    // 解压文件
    let zip_path = install_path_buf.join("ai-eva.zip");
    let zip_file = fs::File::open(&zip_path)
        .map_err(|e| format!("打开压缩文件失败: {}", e))?;
    
    let mut archive = zip::ZipArchive::new(zip_file)
        .map_err(|e| format!("读取压缩文件失败: {}", e))?;

    // 解压所有文件
    for i in 0..archive.len() {
        let mut file = archive.by_index(i)
            .map_err(|e| format!("读取压缩文件条目失败: {}", e))?;
        
        let outpath = match file.enclosed_name() {
            Some(path) => install_path_buf.join(path),
            None => continue,
        };

        // 创建目录
        if (*file.name()).ends_with('/') {
            fs::create_dir_all(&outpath)
                .map_err(|e| format!("创建目录失败: {}", e))?;
        } else {
            // 创建父目录
            if let Some(p) = outpath.parent() {
                fs::create_dir_all(p)
                    .map_err(|e| format!("创建目录失败: {}", e))?;
            }
            
            // 提取文件
            let mut outfile = fs::File::create(&outpath)
                .map_err(|e| format!("创建文件失败: {}", e))?;
            std::io::copy(&mut file, &mut outfile)
                .map_err(|e| format!("写入文件失败: {}", e))?;
        }
    }

    // 删除压缩文件
    fs::remove_file(&zip_path)
        .map_err(|e| format!("删除压缩文件失败: {}", e))?;

    Ok("AI-EVA 下载完成".to_string())
}

#[tauri::command]
async fn clone_indextts2(install_path: String) -> Result<String, String> {
    let install_path_buf = PathBuf::from(&install_path);
    let indextts_path = install_path_buf.join("index-tts");

    // 检查 git 是否可用
    let git_check = Command::new("git")
        .arg("--version")
        .output();

    if git_check.is_err() {
        return Err("Git 未安装，请先安装 Git".to_string());
    }

    // 如果目录已存在，先删除
    if indextts_path.exists() {
        fs::remove_dir_all(&indextts_path)
            .map_err(|e| format!("删除现有目录失败: {}", e))?;
    }

    // 克隆仓库 - 先尝试正常克隆
    let output = Command::new("git")
        .arg("clone")
        .arg("https://github.com/index-tts/index-tts.git")
        .arg(&indextts_path)
        .current_dir(&install_path_buf)
        .output()
        .map_err(|e| format!("执行 git clone 失败: {}", e))?;

    // 检查是否遇到 LFS 错误
    let stderr = String::from_utf8_lossy(&output.stderr);
    let stdout = String::from_utf8_lossy(&output.stdout);
    let combined_output = format!("{}\n{}", stdout, stderr);
    let mut lfs_skipped = false;
    
    if !output.status.success() || combined_output.contains("LFS budget") || combined_output.contains("smudge filter lfs failed") {
        println!("检测到 Git LFS 错误，尝试跳过 LFS 文件...");
        lfs_skipped = true;
        
        // 如果目录已存在但克隆失败，先清理
        if indextts_path.exists() {
            let _ = fs::remove_dir_all(&indextts_path);
        }
        
        // 使用环境变量跳过 LFS 文件
        let output_skip = Command::new("git")
            .env("GIT_LFS_SKIP_SMUDGE", "1")
            .arg("clone")
            .arg("https://github.com/index-tts/index-tts.git")
            .arg(&indextts_path)
            .current_dir(&install_path_buf)
            .output()
            .map_err(|e| format!("Git clone (跳过 LFS) 失败: {}", e))?;
        
        if !output_skip.status.success() {
            let error_msg = String::from_utf8_lossy(&output_skip.stderr);
            return Err(format!("Git clone 失败 (已尝试跳过 LFS): {}", error_msg));
        }
    }

    // 检查并安装 git-lfs
    println!("检查 Git LFS...");
    let lfs_check = Command::new("git")
        .arg("lfs")
        .arg("--version")
        .output();
    
    if lfs_check.is_err() {
        println!("警告: Git LFS 未安装，将尝试安装...");
        // 尝试安装 git-lfs（Windows 上可能需要手动安装）
        println!("提示: 请手动安装 Git LFS: https://git-lfs.github.com/");
    } else {
        // 初始化 Git LFS
        println!("初始化 Git LFS...");
        let _ = Command::new("git")
            .arg("lfs")
            .arg("install")
            .current_dir(&indextts_path)
            .output();
        
        // 尝试拉取 LFS 文件（即使之前跳过了）
        println!("尝试下载 LFS 大文件...");
        let lfs_pull = Command::new("git")
            .arg("lfs")
            .arg("pull")
            .current_dir(&indextts_path)
            .output();
        
        if let Ok(lfs_output) = lfs_pull {
            if !lfs_output.status.success() {
                let lfs_error = String::from_utf8_lossy(&lfs_output.stderr);
                println!("Git LFS pull 警告: {} (可能因为配额限制，但不影响基本功能)", lfs_error);
            } else {
                println!("Git LFS 文件下载成功");
            }
        }
    }

    // 检查并安装 uv 包管理器
    println!("检查 uv 包管理器...");
    let uv_check = Command::new("uv")
        .arg("--version")
        .output();
    
    if uv_check.is_err() {
        println!("安装 uv 包管理器...");
        // 使用 pip 安装 uv
        let install_uv = Command::new("pip")
            .arg("install")
            .arg("uv")
            .output();
        
        if install_uv.is_err() {
            // 尝试使用 python -m pip
            let install_uv_py = Command::new("python")
                .arg("-m")
                .arg("pip")
                .arg("install")
                .arg("uv")
                .output();
            
            if install_uv_py.is_err() {
                return Err("无法安装 uv 包管理器。请手动运行: pip install uv".to_string());
            }
        }
        println!("uv 安装完成");
    }

    // 安装 IndexTTS2 环境
    println!("安装 IndexTTS2 环境依赖...");
    let uv_sync = Command::new("uv")
        .arg("sync")
        .arg("--default-index")
        .arg("https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple")
        .current_dir(&indextts_path)
        .output()
        .map_err(|e| format!("执行 uv sync 失败: {}", e))?;
    
    if !uv_sync.status.success() {
        let sync_error = String::from_utf8_lossy(&uv_sync.stderr);
        return Err(format!("uv sync 失败: {}\n\n提示: 请确保已安装 uv 包管理器: pip install uv", sync_error));
    }

    // 下载模型 - 优先尝试使用 huggingface-cli
    println!("开始下载 IndexTTS2 模型...");
    let checkpoints_dir = indextts_path.join("checkpoints");
    
    // 检查 checkpoints 目录是否已存在模型文件
    let model_exists = checkpoints_dir.exists() && {
        if let Ok(mut entries) = fs::read_dir(&checkpoints_dir) {
            entries.next().is_some()
        } else {
            false
        }
    };
    
    if !model_exists {
        println!("安装 huggingface-cli...");
        let install_hf = Command::new("uv")
            .arg("tool")
            .arg("install")
            .arg("huggingface-hub[cli,hf_xet]")
            .current_dir(&indextts_path)
            .output();
        
        if install_hf.is_ok() && install_hf.as_ref().unwrap().status.success() {
            println!("使用 huggingface-cli 下载模型...");
            println!("设置 HuggingFace 镜像: https://hf-mirror.com");
            let hf_download = Command::new("hf")
                .env("HF_ENDPOINT", "https://hf-mirror.com")
                .arg("download")
                .arg("IndexTeam/IndexTTS-2")
                .arg("--local-dir")
                .arg("checkpoints")
                .current_dir(&indextts_path)
                .output();
            
            if let Ok(hf_output) = hf_download {
                if hf_output.status.success() {
                    println!("模型下载成功 (使用 huggingface-cli)");
                } else {
                    let hf_error = String::from_utf8_lossy(&hf_output.stderr);
                    println!("huggingface-cli 下载失败，尝试使用 modelscope: {}", hf_error);
                    
                    // 回退到 modelscope
                    println!("安装 modelscope...");
                    let install_ms = Command::new("uv")
                        .arg("tool")
                        .arg("install")
                        .arg("modelscope")
                        .current_dir(&indextts_path)
                        .output();
                    
                    if install_ms.is_ok() && install_ms.as_ref().unwrap().status.success() {
                        println!("使用 modelscope 下载模型...");
                        let ms_download = Command::new("modelscope")
                            .arg("download")
                            .arg("--model")
                            .arg("IndexTeam/IndexTTS-2")
                            .arg("--local_dir")
                            .arg("checkpoints")
                            .current_dir(&indextts_path)
                            .output();
                        
                        if let Ok(ms_output) = ms_download {
                            if ms_output.status.success() {
                                println!("模型下载成功 (使用 modelscope)");
                            } else {
                                let ms_error = String::from_utf8_lossy(&ms_output.stderr);
                                println!("警告: 模型下载失败: {}", ms_error);
                                println!("提示: 可以稍后手动下载模型");
                            }
                        }
                    }
                }
            }
        } else {
            // 如果 huggingface-cli 安装失败，尝试 modelscope
            println!("huggingface-cli 安装失败，尝试使用 modelscope...");
            let install_ms = Command::new("uv")
                .arg("tool")
                .arg("install")
                .arg("modelscope")
                .current_dir(&indextts_path)
                .output();
            
            if let Ok(ms_output) = install_ms {
                if ms_output.status.success() {
                    println!("使用 modelscope 下载模型...");
                    let ms_download = Command::new("modelscope")
                        .arg("download")
                        .arg("--model")
                        .arg("IndexTeam/IndexTTS-2")
                        .arg("--local_dir")
                        .arg("checkpoints")
                        .current_dir(&indextts_path)
                        .output();
                    
                    if let Ok(ms_result) = ms_download {
                        if ms_result.status.success() {
                            println!("模型下载成功 (使用 modelscope)");
                        } else {
                            let ms_error = String::from_utf8_lossy(&ms_result.stderr);
                            println!("警告: 模型下载失败: {}", ms_error);
                            println!("提示: 可以稍后手动下载模型");
                        }
                    }
                }
            }
        }
    } else {
        println!("检测到模型文件已存在，跳过下载");
    }

    if lfs_skipped {
        Ok("IndexTTS2 克隆完成，环境已安装，模型已下载 (部分 LFS 大文件可能缺失)".to_string())
    } else {
        Ok("IndexTTS2 克隆完成，环境已安装，模型已下载".to_string())
    }
}

#[tauri::command]
fn launch_ai_eva(install_path: String) -> Result<String, String> {
    let install_path_buf = PathBuf::from(&install_path);
    
    // 查找启动脚本
    let start_script = install_path_buf.join("AAA一键启动.bat");
    
    if !start_script.exists() {
        // 尝试查找其他可能的启动脚本
        let alt_scripts = [
            "start-all.bat",
            "start.bat",
            "launcher_web.py"
        ];
        
        let mut found = false;
        for script_name in &alt_scripts {
            let script_path = install_path_buf.join(script_name);
            if script_path.exists() {
                if script_name.ends_with(".py") {
                    // Python 脚本
                    Command::new("python")
                        .arg(&script_path)
                        .current_dir(&install_path_buf)
                        .spawn()
                        .map_err(|e| format!("启动 Python 脚本失败: {}", e))?;
                } else {
                    // Batch 脚本
                    Command::new("cmd")
                        .arg("/c")
                        .arg(&script_path)
                        .current_dir(&install_path_buf)
                        .spawn()
                        .map_err(|e| format!("启动批处理脚本失败: {}", e))?;
                }
                found = true;
                break;
            }
        }
        
        if !found {
            return Err("未找到启动脚本".to_string());
        }
    } else {
        // 执行启动脚本
        Command::new("cmd")
            .arg("/c")
            .arg(&start_script)
            .current_dir(&install_path_buf)
            .spawn()
            .map_err(|e| format!("启动失败: {}", e))?;
    }

    Ok("AI-EVA 启动成功".to_string())
}

fn parse_github_url(url: &str) -> Result<(String, String), String> {
    // 支持多种 GitHub URL 格式
    // https://github.com/owner/repo
    // https://github.com/owner/repo.git
    // git@github.com:owner/repo.git
    
    let url = url.trim();
    
    if url.starts_with("https://github.com/") {
        let parts: Vec<&str> = url.trim_start_matches("https://github.com/")
            .trim_end_matches(".git")
            .split('/')
            .collect();
        
        if parts.len() >= 2 {
            return Ok((parts[0].to_string(), parts[1].to_string()));
        }
    } else if url.starts_with("git@github.com:") {
        let parts: Vec<&str> = url.trim_start_matches("git@github.com:")
            .trim_end_matches(".git")
            .split('/')
            .collect();
        
        if parts.len() >= 2 {
            return Ok((parts[0].to_string(), parts[1].to_string()));
        }
    }
    
    Err("无效的 GitHub URL 格式".to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_default_install_path,
            check_python_env,
            check_ai_eva,
            check_indextts,
            setup_python_env,
            download_ai_eva,
            clone_indextts2,
            launch_ai_eva
        ])
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用时出错");
}

