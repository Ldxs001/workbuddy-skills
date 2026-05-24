#!/usr/bin/env python3
from auth_check import authorize, initialize

"""
build_index.py - 为 dist/ 目录生成 HTML 索引页（含 file:// 超链接）

用法: python build_index.py <dist_dir>
示例: python build_index.py ~/.workbuddy/skills/.dist/
"""

import html
import os
import sys
from datetime import datetime


def build_index(dist_dir):
    if not os.path.isdir(dist_dir):
        print(f"❌ 目录不存在: {dist_dir}")
        sys.exit(1)

    # 收集 ZIP 文件
    zip_files = []
    for f in sorted(os.listdir(dist_dir)):
        if f.endswith(".zip") and os.path.isfile(os.path.join(dist_dir, f)):
            fpath = os.path.join(dist_dir, f)
            size = os.path.getsize(fpath)
            mtime = os.path.getmtime(fpath)
            zip_files.append((f, fpath, size, mtime))

    # 生成 file:// 链接
    def file_url(path):
        real = os.path.abspath(path)
        if os.sep == "\\":
            real = real.replace("\\", "/")
            if ":" in real:
                # C:/... -> /C:/...
                real = "/" + real
        return "file://" + html.escape(real, quote=True)

    def fmt_size(bytes_):
        if bytes_ < 1024:
            return f"{bytes_} B"
        elif bytes_ < 1024 * 1024:
            return f"{bytes_ / 1024:.1f} KB"
        else:
            return f"{bytes_ / (1024 * 1024):.1f} MB"

    rows = ""
    for f, fpath, size, mtime in zip_files:
        url = file_url(fpath)
        size_str = fmt_size(size)
        time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        rows += (
            f"  <tr>\n"
            f"    <td><a href=\"{url}\">{html.escape(f)}</a></td>\n"
            f"    <td>{size_str}</td>\n"
            f"    <td>{time_str}</td>\n"
            f"  </tr>\n"
        )

    if not rows:
        rows = "  <tr><td colspan=\"3\" style=\"text-align:center;color:#999\">暂无 ZIP 包，请先运行 git-sync</td></tr>\n"

    dist_real = os.path.abspath(dist_dir)
    page = (
        "<!DOCTYPE html>\n"
        "<html lang=\"zh-CN\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        "  <title>WorkBuddy Skills — ZIP 索引</title>\n"
        "  <style>\n"
        "    * { margin:0; padding:0; box-sizing:border-box; }\n"
        "    body {\n"
        "      font-family: -apple-system, \"Segoe UI\", Roboto, \"Helvetica Neue\", sans-serif;\n"
        "      background: #f5f7fa;\n"
        "      color: #333;\n"
        "      padding: 2rem;\n"
        "    }\n"
        "    h1 { font-size:1.4rem; margin-bottom:0.3rem; color:#1a1a1a; }\n"
        "    .subtitle { font-size:0.85rem; color:#888; margin-bottom:1.5rem; }\n"
        "    .subtitle code { background:#e8ecf1; padding:0.1rem 0.4rem; border-radius:3px; font-size:0.82rem; }\n"
        "    table { width:100%; border-collapse:collapse; background:#fff; border-radius:8px; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,0.08); }\n"
        "    thead { background:#4a6cf7; color:#fff; }\n"
        "    th, td { padding:0.75rem 1rem; text-align:left; }\n"
        "    tbody tr:hover { background:#f0f4ff; }\n"
        "    a { color:#4a6cf7; text-decoration:none; }\n"
        "    a:hover { text-decoration:underline; }\n"
        "    .footer { margin-top:1.5rem; font-size:0.78rem; color:#aaa; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>📦 WorkBuddy Skills — ZIP 索引</h1>\n"
        f"  <p class=\"subtitle\">统一输出目录：<code>{html.escape(dist_real)}</code><br>点击文件名即可跳转 / 下载（需浏览器允许 file:// 协议）</p>\n"
        "  <table>\n"
        "    <thead><tr><th>文件名</th><th>大小</th><th>修改时间</th></tr></thead>\n"
        "    <tbody>\n"
        f"{rows}"
        "    </tbody>\n"
        "  </table>\n"
        f"  <p class=\"footer\">由 git-sync v1.5.0 自动生成 · 最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n"
        "</body>\n"
        "</html>\n"
    )

    index_path = os.path.join(dist_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"  ✅ HTML 索引已生成: {index_path}")
    return index_path


if __name__ == "__main__":
        initialize()
    # 授权检查（R-15 合规：自治模式，不阻断执行）
    import subprocess
import hashlib
import json
    _skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _auth_script = os.path.join(_skill_dir, "skill-standardization", "scripts", "authorization_manager.py")
    # 完整性校验：检查 authorization_manager.py 是否被篡改
    if os.path.exists(_auth_script):
        try:
            import hashlib, json, pathlib
            _hash_file = pathlib.Path.home() / ".workbuddy" / "skills" / ".standardization" / "git-sync" / "script_hashes.json"
            with open(_auth_script, "rb") as _f:
                _auth_hash = hashlib.sha256(_f.read()).hexdigest()
            if _hash_file.exists():
                with open(_hash_file) as _f:
                    _records = json.load(_f)
                _rel = str(pathlib.Path(_auth_script).relative_to(pathlib.Path.home() / ".workbuddy" / "skills"))
                if _rel in _records and _records[_rel] != _auth_hash:
                    print(f"⚠️ 警告: authorization_manager.py 哈希不匹配（可能被篡改）: {_rel}")
                    print(f"  预期: {_records[_rel][:16]}...")
                    print(f"  实际: {_auth_hash[:16]}...")
                else:
                    _records[_rel] = _auth_hash
                    with open(_hash_file, "w") as _f:
                        json.dump(_records, _f, indent=2, ensure_ascii=False)
            else:
                _hash_file.parent.mkdir(parents=True, exist_ok=True)
                with open(_hash_file, "w") as _f:
                    json.dump({_rel: _auth_hash}, _f, indent=2, ensure_ascii=False)
        except Exception as _e:
            print(f"⚠️ 哈希校验失败: {_e}")
    if os.path.exists(_auth_script):
        _r = subprocess.run([sys.executable, _auth_script, "request", "--type", "immediate", "--reason", "build_index: 生成 .dist/ HTML 索引"], capture_output=True, text=True)
        if _r.returncode != 0:
            print(f"❌ 授权被拒绝: {_r.stderr.strip()}")
            sys.exit(1)
    if len(sys.argv) < 2:
        print("用法: python build_index.py <dist_dir>")
        sys.exit(1)
    build_index(sys.argv[1])