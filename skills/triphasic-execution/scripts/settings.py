#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Settings UI for Triphasic Execution Framework
============================================
启动本地 HTTP 服务器，提供 HTML 设置界面，处理表单提交，
写入 config.json 和 SKILL.md，在系统默认浏览器中打开设置页面。

用法:
  python settings.py                         # 打开设置界面
  python settings.py --skill-dir /path/to/skill  # 指定技能目录
  python settings.py --home /path/to/home        # 指定数据目录
  python settings.py --port 8080                  # 指定端口
"""

import os
import sys
import json
import time
import webbrowser
import threading
import argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 全局标志：设置是否完成
SETTINGS_DONE = False
SERVER_INSTANCE = None

# 默认端口范围
DEFAULT_PORT_MIN = 8080
DEFAULT_PORT_MAX = 8999


def get_skill_dir(args) -> Path:
    """获取技能目录路径"""
    if args.skill_dir:
        return Path(args.skill_dir).expanduser().resolve()
    # 自动检测：scripts/settings.py → ../（技能根目录）
    return Path(__file__).parent.parent


def get_home_dir(args, skill_dir) -> Path:
    """获取数据目录路径"""
    if args.home:
        return Path(args.home).expanduser().resolve()
    # 从 config.json 读取
    config_file = skill_dir / "assets" / "default_config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if "_triphasic_home" in cfg:
                return Path(cfg["_triphasic_home"]).expanduser()
        except Exception:
            pass
    # 从环境变量读取
    env_home = os.environ.get("TRIPHASIC_HOME")
    if env_home:
        return Path(env_home).expanduser()
    # 默认值
    return Path.home() / ".workbuddy" / "triphasic"


def find_available_port(min_port=DEFAULT_PORT_MIN, max_port=DEFAULT_PORT_MAX) -> int:
    """查找可用端口"""
    import socket
    for port in range(min_port, max_port + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("localhost", port))
            sock.close()
            return port
        except OSError:
            continue
    raise RuntimeError(f"无法找到可用端口（范围 {min_port}-{max_port}）")


def update_skill_md(skill_dir: Path, config: dict):
    """更新 SKILL.md 中的配置值"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"   ⚠️  SKILL.md 不存在：{skill_md}")
        return False

    try:
        # 备份
        backup = skill_dir / "SKILL.md.bak"
        with open(skill_md, "r", encoding="utf-8") as f:
            original_content = f.read()
        with open(backup, "w", encoding="utf-8") as f:
            f.write(original_content)
        print(f"   ✅ 已备份 SKILL.md → SKILL.md.bak")

        # 读取内容
        content = original_content
        mode = config.get("mode", "on_demand")
        triphasic_home = config.get("_triphasic_home", "~/.workbuddy/triphasic/")
        require_confirm = config.get("hooks", {}).get("require_task_confirmation", True)

        # 更新「双模式设计」章节开头
        mode_text = "🔵 全局自动模式" if mode == "global" else "🟢 按需调用模式（默认）"
        mode_marker = "### 核心理念：用户习惯决定启动方式"
        if mode_marker in content:
            # 在章节开头添加当前配置
            lines = content.split("\n")
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                new_lines.append(line)
                if line.strip() == mode_marker:
                    # 检查下一行是否已经是"当前配置"注释
                    if i + 1 < len(lines) and "**当前配置" in lines[i + 1]:
                        # 替换现有注释
                        new_lines.append(f"> **当前配置：{mode_text}**")
                        i += 2
                        continue
                    else:
                        # 插入新注释
                        new_lines.append(f"> **当前配置：{mode_text}**")
                i += 1
            content = "\n".join(new_lines)

        # 更新「数据目录」章节的表格
        # 替换 TRIPHASIC_HOME 默认值说明
        home_marker = "**默认值**：`~/.workbuddy/triphasic/`"
        content = content.replace(home_marker, f"**当前配置**：`{triphasic_home}`")

        # 更新「配置」章节的示例代码
        # 替换 mode 示例
        if mode == "global":
            content = content.replace('"mode": "on_demand"', '"mode": "global"')
        # 替换 require_task_confirmation 示例
        if not require_confirm:
            content = content.replace(
                '"require_task_confirmation": true',
                '"require_task_confirmation": false'
            )

        # 写回
        with open(skill_md, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"   ✅ 已更新 SKILL.md 配置值")
        return True

    except Exception as e:
        print(f"   ❌ 更新 SKILL.md 失败：{e}")
        # 恢复备份
        if backup.exists():
            with open(backup, "r", encoding="utf-8") as f:
                original = f.read()
            with open(skill_md, "w", encoding="utf-8") as f:
                f.write(original)
            print(f"   ✅ 已恢复 SKILL.md 备份")
        return False

def save_config_from_json(skill_dir: Path, home_dir: Path, config_json: str) -> int:
    """
    从 JSON 字符串保存配置（用于对话式设置）
    
    Args:
        skill_dir: 技能目录
        home_dir: 数据目录
        config_json: JSON 字符串，包含配置
        
    Returns:
        int: 0 表示成功，1 表示失败
    """
    try:
        # 解析 JSON
        config = json.loads(config_json)
        print(f"   📝 解析配置 JSON 成功")
        
        # 确保数据目录存在
        home_dir = Path(config.get("_triphasic_home", str(home_dir))).expanduser()
        home_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入 config.json
        config_file = home_dir / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"   ✅ 已写入 config.json：{config_file}")
        
        # 更新 SKILL.md
        update_skill_md(skill_dir, config)
        
        print(f"✅ 配置保存成功")
        return 0
        
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON 解析失败：{e}")
        return 1
    except Exception as e:
        print(f"   ❌ 保存配置失败：{e}")
        return 1


class SettingsHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def log_message(self, format, *args):
        """禁用默认日志输出"""
        pass

    def do_GET(self):
        """处理 GET 请求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/" or parsed_path.path == "/index.html":
            # 返回设置页面
            self.serve_settings_html()

        elif parsed_path.path == "/config":
            # 返回当前配置（JSON）
            self.send_config()

        elif parsed_path.path == "/done":
            # 返回"设置已完成"页面
            self.send_done_page()

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """处理 POST 请求"""
        if self.path == "/save":
            self.handle_save()
        else:
            self.send_error(404, "Not Found")

    def serve_settings_html(self):
        """返回 settings.html"""
        html_file = self.server.skill_dir / "assets" / "settings.html"
        if not html_file.exists():
            self.send_error(404, "settings.html not found")
            return

        try:
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
        except Exception as e:
            self.send_error(500, f"Error reading settings.html: {e}")

    def send_config(self):
        """返回当前配置 JSON"""
        config_file = self.server.home_dir / "config.json"
        if not config_file.exists():
            # 使用默认配置
            config_file = self.server.skill_dir / "assets" / "default_config.json"

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 添加 _triphasic_home 字段（方便前端使用）
            config["_triphasic_home"] = str(self.server.home_dir)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(config, indent=2, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.send_error(500, f"Error reading config: {e}")

    def handle_save(self):
        """处理保存请求"""
        global SETTINGS_DONE

        try:
            # 读取请求体
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            form_data = json.loads(post_data.decode("utf-8"))

            # 更新 config.json
            config_file = self.server.home_dir / "config.json"
            if not config_file.exists():
                config_file = self.server.skill_dir / "assets" / "default_config.json"

            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 更新字段
            config["mode"] = form_data.get("mode", "on_demand")
            config["_triphasic_home"] = form_data.get("triphasic_home", "~/.workbuddy/triphasic/")
            config["problems_file"] = form_data.get("problems_file", "PROBLEMS.md")
            config["risks_file"] = form_data.get("risks_file", "RISKS.md")
            config["lessons_file"] = form_data.get("lessons_file", "LESSONS_REGISTER.md")
            config["logs_dir"] = form_data.get("logs_dir", ".problem_logs")

            if "hooks" not in config:
                config["hooks"] = {}
            config["hooks"]["require_task_confirmation"] = form_data.get("require_confirmation", True)

            # 确保数据目录存在
            home_dir = Path(form_data.get("triphasic_home", "~/.workbuddy/triphasic/")).expanduser()
            home_dir.mkdir(parents=True, exist_ok=True)

            # 写入 config.json
            with open(home_dir / "config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # 更新 SKILL.md
            update_skill_md(self.server.skill_dir, config)

            # 创建 .settings_done 标志文件
            done_flag = self.server.skill_dir / ".settings_done"
            done_flag.touch()

            # 设置全局标志
            SETTINGS_DONE = True

            # 返回成功响应
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))

        except Exception as e:
            print(f"   ❌ 保存设置失败：{e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

    def send_done_page(self):
        """返回"设置已完成"页面"""
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>设置已完成</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #1a1a2e; color: #4ecdc4; }
        .message { text-align: center; }
        .message h1 { font-size: 48px; }
        .message p { font-size: 18px; color: #e0e0e0; }
    </style>
</head>
<body>
    <div class="message">
        <h1>✅</h1>
        <p>设置已保存！可关闭此页面。</p>
    </div>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def start_server(skill_dir: Path, home_dir: Path, port: int) -> HTTPServer:
    """启动 HTTP 服务器"""
    server = HTTPServer(("localhost", port), SettingsHandler)
    server.skill_dir = skill_dir
    server.home_dir = home_dir
    return server


def main():
    global SERVER_INSTANCE

    parser = argparse.ArgumentParser(description="Triphasic Execution - 设置界面")
    parser.add_argument("--skill-dir", type=str, default=None, help="技能目录路径")
    parser.add_argument("--home", type=str, default=None, help="数据目录路径")
    parser.add_argument("--port", type=int, default=None, help="指定端口（默认随机 8080-8999）")
    parser.add_argument("--save-config", type=str, default=None, help="保存配置（JSON 字符串），不启动服务器")
    args = parser.parse_args()

    # 确定路径
    skill_dir = get_skill_dir(args)
    home_dir = get_home_dir(args, skill_dir)

    # 如果提供了 --save-config，直接保存并退出
    if args.save_config:
        return save_config_from_json(skill_dir, home_dir, args.save_config)

    print(f"⚙️  启动 Triphasic Execution 设置界面...")
    print(f"   📂 技能目录：{skill_dir}")
    print(f"   📁 数据目录：{home_dir}")

    # 清理旧的标志文件
    done_flag = skill_dir / ".settings_done"
    if done_flag.exists():
        done_flag.unlink()
        print(f"   🧹 已清理旧的标志文件")

    # 查找可用端口
    if args.port:
        port = args.port
    else:
        try:
            port = find_available_port()
        except RuntimeError as e:
            print(f"   ❌ {e}")
            sys.exit(1)

    # 启动 HTTP 服务器
    server = start_server(skill_dir, home_dir, port)
    SERVER_INSTANCE = server

    print(f"   🌐 服务器已启动：http://localhost:{port}/")

    # 在后台线程中运行服务器
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # 打开浏览器
    url = f"http://localhost:{port}/"
    success = webbrowser.open(url)
    if not success:
        print(f"   ❌ 无法打开浏览器（webbrowser.open 返回 False）")
        print(f"   💡 请手动打开：{url}")
        print(f"\n⚠️  BROWSER_UNAVAILABLE - 浏览器不可用，请使用对话式设置")
        # 返回特定退出码 2 表示浏览器不可用
        sys.exit(2)

    print(f"   ✅ 已在浏览器中打开设置页面")

    # 阻塞等待用户完成设置
    print(f"\n⏳ 等待用户完成设置...")
    try:
        while not SETTINGS_DONE:
            # 检查标志文件
            if done_flag.exists():
                print(f"   ✅ 检测到设置已完成标志")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n   ⚠️  用户中断")

    # 停止服务器
    print(f"\n🛑 正在关闭服务器...")
    server.shutdown()
    server.server_close()

    print(f"✅ 设置界面已关闭")
    return 0


if __name__ == "__main__":
    sys.exit(main())
