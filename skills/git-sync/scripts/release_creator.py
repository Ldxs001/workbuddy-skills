"""GitHub Release 创建器 — git-sync 子模块"""
import subprocess, sys, json, os
from _paths import WORK_REPO

WORK_REPO_STR = str(WORK_REPO)

def main():
    if len(sys.argv) < 4:
        print("用法: release_creator.py <name> <type> <version>")
        sys.exit(1)
    name, typ, version = sys.argv[1], sys.argv[2], sys.argv[3]
    repo = "Ldxs001/workbuddy-skills"
    tag = f"v{version}" if typ == "agent" else f"{name}-v{version}"

    # 1. 创建本地 tag
    subprocess.run(["git", "tag", tag], cwd=WORK_REPO_STR, capture_output=True)

    # 2. 推送到 GitHub
    subprocess.run(["git", "push", "origin", tag], cwd=WORK_REPO_STR, capture_output=True)

    # 3. 推送到 Gitee
    subprocess.run(["git", "push", "gitee", tag], cwd=WORK_REPO_STR, capture_output=True)

    # 4. 创建 GitHub Release
    token = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=WORK_REPO_STR,
        capture_output=True, text=True
    ).stdout.split("@")[0].split("//")[-1] if "@" in subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=WORK_REPO_STR,
        capture_output=True, text=True
    ).stdout else ""
    
    # 从 remote URL 提取 token
    remote_url = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=WORK_REPO_STR,
        capture_output=True, text=True
    ).stdout.strip()
    if ":" in remote_url and "@" in remote_url:
        # https://user:token@github.com/repo
        token_part = remote_url.split("//")[1].split("@")[0]
        if ":" in token_part:
            token = token_part.split(":")[1]
    elif "token" in remote_url:
        token = remote_url.split("token=")[1].split("&")[0]

    if token:
        body = f"## {name} v{version}\n\n自动发布 by git-sync"
        data = json.dumps({
            "tag_name": tag, "name": f"{name} v{version}",
            "body": body, "draft": False, "prerelease": False
        })
        curl_cmd = [
            "curl", "-s", "-X", "POST",
            f"https://api.github.com/repos/{repo}/releases",
            "-H", f"Authorization: token {token}",
            "-H", "Content-Type: application/json",
            "-d", data
        ]
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        try:
            r = json.loads(result.stdout)
            print(f"  ✅ Release: {r.get('html_url', 'unknown')}")
        except json.JSONDecodeError:
            print(f"  ⚠️  创建 Release 但无法解析响应: {result.stdout[:200]}")
    else:
        print("  ⚠️  无法获取 GitHub token，跳过 API Release 创建")
        print("  ✅ tag 已推送: git push origin " + tag)

if __name__ == "__main__":
    main()
