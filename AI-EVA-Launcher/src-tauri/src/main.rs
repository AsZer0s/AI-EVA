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
        "chattts_api.py",
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

    // 克隆仓库
    let output = Command::new("git")
        .arg("clone")
        .arg("https://github.com/index-tts/index-tts.git")
        .arg(&indextts_path)
        .current_dir(&install_path_buf)
        .output()
        .map_err(|e| format!("执行 git clone 失败: {}", e))?;

    if !output.status.success() {
        let error_msg = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Git clone 失败: {}", error_msg));
    }

    Ok("IndexTTS2 克隆完成".to_string())
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

