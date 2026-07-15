"""GitHub + Gitee Release 创建器 — git-sync 子模块"""
import subprocess, sys, json, os
from _paths import WORK_REPO, CONFIG_FILE

WORK_REPO_STR = str(WORK_REPO)

GITEE_REPO = "wUwproject/workbuddy-skills"
GITHUB_REPO = "Ldxs001/workbuddy-skills"

def _get_gitee_token() -> str:
    """从 config.json 或环境变量获取 Gitee token"""
    token = os.environ.get("GITEE_TOKEN", "")
    if token:
        return token
    try:
        cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
        return cfg.get("gitee_token", "")
    except Exception:
        return ""

def _get_github_token() -> str:
    """从 remote URL 提取 GitHub token"""
    remote_url = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=WORK_REPO_STR, capture_output=True, text=True
    ).stdout.strip()
    token = ""
    if ":" in remote_url and "@" in remote_url:
        token_part = remote_url.split("//")[1].split("@")[0]
        if ":" in token_part:
            token = token_part.split(":")[1]
    elif "token" in remote_url:
        token = remote_url.split("token=")[1].split("&")[0]
    return token

def main():
    if len(sys.argv) < 4:
        print("用法: release_creator.py <name> <type> <version>")
        sys.exit(1)
    name, typ, version = sys.argv[1], sys.argv[2], sys.argv[3]
    tag = f"v{version}" if typ == "agent" else f"{name}-v{version}"
    body = f"## {name} v{version}\n\n自动发布 by git-sync"

    # 1. 创建本地 tag
    subprocess.run(["git", "tag", tag, "-f"], cwd=WORK_REPO_STR, capture_output=True)

    # 2. 推送到 GitHub
    subprocess.run(["git", "push", "origin", tag, "-f"], cwd=WORK_REPO_STR, capture_output=True)

    # 3. 推送到 Gitee
    subprocess.run(["git", "push", "gitee", tag, "-f"], cwd=WORK_REPO_STR, capture_output=True)

    # 4. 创建 GitHub Release
    gh_token = _get_github_token()
    if gh_token:
        data = json.dumps({
            "tag_name": tag, "name": f"{name} v{version}",
            "body": body, "draft": False, "prerelease": False
        })
        curl_cmd = [
            "curl", "-s", "-X", "POST",
            f"https://api.github.com/repos/{GITHUB_REPO}/releases",
            "-H", f"Authorization: token {gh_token}",
            "-H", "Content-Type: application/json",
            "-d", data
        ]
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        try:
            r = json.loads(result.stdout)
            print(f"  ✅ GitHub Release: {r.get('html_url', 'unknown')}")
        except json.JSONDecodeError:
            print(f"  ⚠️  GitHub Release 创建响应异常: {result.stdout[:200]}")
    else:
        print("  ⚠️  无法获取 GitHub token，跳过 GitHub Release")
        print("  ✅ tag 已推送: git push origin " + tag)

    # 5. 创建 Gitee 发行版
    gitee_token = _get_gitee_token()
    if gitee_token:
        data = json.dumps({
            "access_token": gitee_token,
            "tag_name": tag,
            "target_commitish": "main",
            "name": f"{name} v{version}",
            "body": body,
            "prerelease": False
        })
        curl_cmd = [
            "curl", "-s", "-X", "POST",
            f"https://gitee.com/api/v5/repos/{GITEE_REPO}/releases",
            "-H", "Content-Type: application/json;charset=UTF-8",
            "-d", data
        ]
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        try:
            r = json.loads(result.stdout)
            if "id" in r:
                print(f"  ✅ Gitee 发行版: https://gitee.com/{GITEE_REPO}/releases/{tag}")
            elif "message" in r and "已存在" in r.get("message", ""):
                print(f"  ✅ Gitee 发行版已存在（跳过）")
            else:
                print(f"  ⚠️  Gitee 创建响应: {r.get('message', result.stdout[:200])[:80]}")
        except json.JSONDecodeError:
            print(f"  ⚠️  Gitee 创建响应异常: {result.stdout[:200]}")
    else:
        print("  ⚠️  未配置 GITEE_TOKEN，跳过 Gitee 发行版创建")

if __name__ == "__main__":
    main()
