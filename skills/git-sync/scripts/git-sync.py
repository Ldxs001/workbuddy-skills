#!/usr/bin/env python3
"""
git-sync.py v2.6.22 - 完整 Python 版 git-sync
跨平台兼容（Windows/Linux/macOS），不依赖 rsync
用法: python git-sync.py <skill-name> [version] [--skip-scan]
"""
import os
import sys
import json
import shutil
import subprocess
import argparse
import tempfile
from pathlib import Path
from datetime import datetime

# ── 强制 UTF-8 输出（Windows 终端兼容）────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── 路径配置 ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
SKILLS_DIR = SCRIPT_DIR.parents[1]  # skills/<skill-name>/scripts/ → skills/
WORK_REPO  = Path.home() / ".workbuddy" / "workbuddy-skills"
DIST_DIR   = SKILLS_DIR / ".dist"
MANIFEST_FILE = (
    SKILLS_DIR / ".standardization" / "git-sync" / "data" / "manifest.json"
)
README_FILE = WORK_REPO / "README.md"

# ── 颜色输出 ──────────────────────────────────────────────────────────────────
class C:
    R = "\033[0;31m"; G = "\033[0;32m"; Y = "\033[1;33m"
    B = "\033[0;34m"; C = "\033[0;36m"; W = "\033[1;37m"; N = "\033[0m"

def log(step, total, msg, level="info"):
    tag = {"info":"[i]","ok":"[OK]","warn":"[!]","err":"[X]","skip":"[-]"}.get(level,"[i]")
    color = {"info":C.C,"ok":C.G,"warn":C.Y,"err":C.R,"skip":C.W}.get(level,"")
    print(f"{color}[{step}/{total}] {tag} {msg}{C.N}")

def _git_env(base_env: dict = None) -> dict:
    """
    构造一个完全静默的 git 环境变量字典。
    用 GIT_CONFIG_COUNT 注入 credential.helper=（空=禁用），
    优先级高于所有配置文件，覆盖所有子进程（含 Python 脚本内调 git）。
    """
    env = base_env.copy() if base_env else os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "credential.helper"
    env["GIT_CONFIG_VALUE_0"] = ""
    return env


def run_python(script: Path, *args, capture=False, check=True):
    """运行 scripts/ 下的 Python 辅助脚本"""
    env = _git_env()
    env["PYTHONUTF8"] = "1"
    cmd = [sys.executable, str(script), *[str(a) for a in args]]
    return subprocess.run(cmd, capture_output=capture, encoding="utf-8",
                         check=check, env=env,
                         stdin=subprocess.DEVNULL)

def run_git(*args, workdir=None, check=True):
    """
    运行 git 命令，完全静默不弹 UI。
    用 _git_env() 注入 GIT_CONFIG_COUNT，彻底阻止所有子进程弹窗。
    """
    env = _git_env()
    si = None
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
    cmd = ["git",
           "-c", "credential.helper=",
           "-c", "credential.https://gitee.com.provider=",
           "-c", "credential.https://github.com.provider=",
           *[str(a) for a in args]]
    return subprocess.run(cmd, cwd=str(workdir or WORK_REPO),
                         capture_output=True, encoding="utf-8",
                         check=check, env=env,
                         stdin=subprocess.DEVNULL,
                         startupinfo=si)

# ── 步骤 1：检查维护清单 ─────────────────────────────────────────────────────
def step_manifest(skill_name: str, version: str, repo_name="workbuddy-skills"):
    log(1, 8, "检查维护清单...")
    manifest_py = SCRIPT_DIR / "manifest.py"
    if not manifest_py.exists():
        log(1, 8, "manifest.py 不存在，跳过", "skip")
        return
    # manifest.py 用 exit code 2 表示 NOT_FOUND，不能用 check=True
    r = run_python(manifest_py, "check", repo_name, skill_name,
                   capture=True, check=False)
    status = r.stdout.strip()
    if status == "NOT_FOUND":
        log(1, 8, "不在清单中，自动添加...", "warn")
        run_python(manifest_py, "add", repo_name, skill_name,
                   check=False)
    elif status == "FOUND:not-uploaded":
        log(1, 8, "在清单中，未上传（正常）", "ok")
    else:
        log(1, 8, "在清单中，已上传", "ok")

# ── 步骤 2：版本号对比 ───────────────────────────────────────────────────────
def step_version_compare(skill_name: str, local_ver: str) -> str:
    log(2, 8, "版本号对比（仓库 vs 本地源文件）...")
    repo_meta = WORK_REPO / "skills" / skill_name / "_meta.json"
    repo_ver = ""
    if repo_meta.exists():
        try:
            repo_ver = json.load(open(repo_meta, encoding="utf-8"))["version"]
        except Exception:
            pass
    print(f"  仓库版本: {repo_ver or '（无）'}")
    print(f"  本地源文件版本: {local_ver}")

    if not repo_ver:
        log(2, 8, "仓库无版本记录，正常同步", "ok")
        return "normal"
    if repo_ver == local_ver:
        log(2, 8, f"版本相同 ({local_ver})，跳过文件同步", "skip")
        return "skip_sync"
    # 简单版本比较
    def ver_lt(a, b):
        na = [int(x) for x in a.split(".")]
        nb = [int(x) for x in b.split(".")]
        return na < nb
    if ver_lt(repo_ver, local_ver):
        log(2, 8, "仓库版本 < 本地版本，正常升级", "ok")
        return "normal"
    else:
        log(2, 8, f"版本异常：仓库({repo_ver}) > 本地({local_ver})", "err")
        print("  请手动处理版本冲突后重试。")
        sys.exit(1)

# ── 步骤 3：_meta.json 标准化校验 ──────────────────────────────────────────
def step_normalize_meta(meta_file: Path, skill_name: str, version: str):
    log(3, 8, "校验 _meta.json 标准字段...")
    normalize_py = SCRIPT_DIR / "normalize_meta.py"
    if not normalize_py.exists():
        log(3, 8, "normalize_meta.py 不存在，跳过", "skip")
        return
    desc = get_meta_desc(meta_file)
    run_python(normalize_py, str(meta_file), skill_name, version, desc)

# ── 步骤 3.5：SKILL.md 规范化审查（只读扫描，不修改、不阻断） ────────────────────────────────────────
def step_skill_audit(skill_name: str, skills_dir: Path, manifest_file: Path):
    """
    只读扫描 SKILL.md 规范性，不修改任何文件，不阻断同步流程。
    仅输出审计结论，不展开逐条细节。
    """
    log("3.5", 8, "SKILL.md 规范审查（只读扫描）...")
    skill_md = skills_dir / skill_name / "SKILL.md"
    if not skill_md.exists():
        log("3.5", 8, "SKILL.md 不存在，跳过审查", "skip")
        return
    # 读取清单中的版本号（用于审计参考，不影响流程）
    manifest_ver = ""
    try:
        m = json.load(open(manifest_file, encoding="utf-8"))
        items = m.get("repos", {}).get("workbuddy-skills", {}).get("items", {})
        manifest_ver = items.get(skill_name, {}).get("version", "")
    except Exception:
        pass
    audit_out = SCRIPT_DIR / f".audit_{skill_name}.json"
    # 调用本地 bundled skill_audit 包（python -m skill_audit）
    # 注意：只传 audit 子命令，不传任何 --fix / --refactor 等修改类参数
    env = _git_env()
    env["PYTHONUTF8"] = "1"
    cmd = [
        sys.executable, "-m", "skill_audit",
        "audit", str(skills_dir / skill_name),
        "--json", f"--manifest-version={manifest_ver}",
    ]
    r = subprocess.run(
        cmd,
        cwd=str(SCRIPT_DIR),   # skill_audit/ 包在 SCRIPT_DIR 下
        capture_output=True, encoding="utf-8",
        check=False, env=env,
        stdin=subprocess.DEVNULL,
    )
    # skill_audit --json 输出到 stdout，需要手动写入 audit_out
    if r.stdout and r.returncode == 0:
        try:
            import json as _json
            _d = _json.loads(r.stdout)
            audit_out.write_text(r.stdout, encoding="utf-8")
        except Exception:
            pass
    if audit_out.exists():
        d = json.load(open(audit_out, encoding="utf-8"))
        errors = d["summary"]["errors"]
        warns  = d["summary"]["warns"]
        verdict = d["verdict"]
        # 只输出结论，不展开细节
        if verdict == "pass":
            print(f"  ✅ 审查结论：PASS（ERROR={errors}, WARN={warns}）")
        elif verdict == "warn":
            print(f"  💡 审查结论：WARN（ERROR={errors}, WARN={warns}）—— 建议优化，不阻断同步")
        else:
            print(f"  ⚠️  审查结论：{verdict}（ERROR={errors}, WARN={warns}）—— 仅记录，不阻断同步")
        audit_out.unlink(missing_ok=True)
    else:
        log("3.5", 8, "审查执行失败，跳过", "warn")

# ── 步骤 4：同步文件到工作仓库 ─────────────────────────────────────────────
EXCLUDE_PATTERNS = [
    "__pycache__", ".git", ".eggs", "eggs", "dist", "build",
    ".egg-info", ".pytest_cache", ".mypy_cache", "node_modules",
    ".standardization", "outputs", "test-outputs",
    "*.pyc", "*.pyo", "*.log", "*.zip", "*.bak*",
    "*.tmp", "._*", "*.decisions.json", "*.sensitive_scan_*.json",
    "zip_out", "preview_server.py", "*_fixed.py", "stderr.txt", "stdout.txt",
    "*.bat", "test_*.py", ".gitignore", ".ds_store", "thumbs.db",
    "config.json", "manifest.json", "pack_zip.py",
]

def _ignore_patterns(path, names):
    ignored = set()
    for name in names:
        for pat in EXCLUDE_PATTERNS:
            if pat.startswith("*"):
                if name.endswith(pat[1:]):
                    ignored.add(name); break
            elif pat.endswith("/"):
                if (Path(path) / name).is_dir() and name == pat.rstrip("/"):
                    ignored.add(name); break
            else:
                if name == pat:
                    ignored.add(name); break
    return ignored

def sync_files(skill_name: str, skills_dir: Path, work_repo: Path):
    """用 Python copytree 替代 rsync"""
    src = skills_dir / skill_name
    dst = work_repo / "skills" / skill_name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_ignore_patterns)
    # 二次保险：清理残留
    for root, dirs, _ in os.walk(dst):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(Path(root) / d, ignore_errors=True)
    count = sum(1 for _ in dst.rglob("*") if _.is_file())
    log(4, 8, f"已同步 {count} 个文件到 {dst}", "ok")
    return dst

# ── 步骤 4.5：敏感信息扫描 ────────────────────────────────────────────────
def step_sensitive_scan(skill_name: str, repo_skill_dir: Path,
                        skip_scan: bool = False):
    log("4.5", 8, "扫描敏感信息...")
    if skip_scan:
        log("4.5", 8, "已跳过敏感信息扫描（--skip-scan）", "skip")
        return
    scan_py = SCRIPT_DIR / "sensitive_scan.py"
    if not scan_py.exists():
        log("4.5", 8, "sensitive_scan.py 不存在，跳过", "skip")
        return

    scan_out = SCRIPT_DIR / f".sensitive_scan_{skill_name}.json"
    run_python(scan_py, "scan", str(repo_skill_dir),
               "--output", str(scan_out))

    if not scan_out.exists() or scan_out.stat().st_size == 0:
        log("4.5", 8, "未发现敏感信息", "ok")
        scan_out.unlink(missing_ok=True)
        return

    # ── 打印扫描结果详情 ──────────────────────────────────────────────────
    d = json.load(scan_out.open(encoding="utf-8"))
    total_findings = sum(len(e.get("findings", [])) for e in d)
    print(f"  ⚠️  发现敏感信息：共 {len(d)} 个文件，{total_findings} 处")
    for e in d:
        file_rel = e["file"]       # 已是相对路径，如 "references/faq.md"
        finds = e.get("findings", [])
        if not finds:
            continue
        print(f"  📄 {file_rel}（{len(finds)} 处）")
        for f in finds[:5]:          # 每文件最多显示 5 条
            label = f.get("label", "敏感信息")
            severity = f.get("severity", "")
            line = f.get("line", "?")
            replace = f.get("replace", "[redacted]")
            print(f"      [{severity}] 第 {line} 行 {label} → 替换为：{replace}")
        if len(finds) > 5:
            print(f"      ... 还有 {len(finds) - 5} 处未显示")

    # ── 默认全部脱敏 ──────────────────────────────────────────────────────
    decisions = SCRIPT_DIR / f".sensitive_scan_{skill_name}.json.decisions.json"
    make_py = SCRIPT_DIR / "make_all_sanitize.py"
    if make_py.exists():
        r = run_python(make_py, str(scan_out), capture=True)
        if r and r.stdout:
            Path(decisions).write_text(r.stdout, encoding="utf-8")

    if decisions.exists():
        log("4.5", 8, "正在执行脱敏...", "info")
        # 先备份脱敏前的文件哈希（用于对比）
        sanitized_files = set()
        for e in d:
            sanitized_files.add(repo_skill_dir / e["file"])

        run_python(scan_py, "apply", str(repo_skill_dir),
                   "--decisions", str(decisions),
                   "--scan-result", str(scan_out))

        # 脱敏后：显示脱敏结果
        print(f"  ✅ 脱敏完成，涉及 {len(sanitized_files)} 个文件：")
        for fp in sorted(sanitized_files):
            rel = fp.relative_to(repo_skill_dir)
            print(f"      - {file_rel}")
    else:
        log("4.5", 8, "无脱敏决策文件，跳过脱敏", "warn")

    scan_out.unlink(missing_ok=True)
    decisions.unlink(missing_ok=True)

# ── 步骤 5：更新 README.md ─────────────────────────────────────────────────
def step_update_readme(repo_name="workbuddy-skills"):
    log(5, 8, "更新 README.md...")
    readme = WORK_REPO / "README.md"
    if not readme.exists():
        log(5, 8, "README.md 不存在，跳过", "skip")
        return
    update_py = SCRIPT_DIR / "update_readme.py"
    if not update_py.exists():
        log(5, 8, "update_readme.py 不存在，跳过", "skip")
        return
    run_python(update_py, repo_name, str(readme))
    log(5, 8, "README.md 已更新", "ok")

# ── 步骤 6：提交并推送到双平台 ────────────────────────────────────────────
def _detect_remote(url_pattern: str) -> str:
    """根据 URL 关键字检测远程名，找不到返回空字符串"""
    r = run_git("remote", "-v",
                 workdir=WORK_REPO, check=False)
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and url_pattern in parts[1]:
            return parts[0]
    return ""


def _get_cred_url(host: str) -> str:
    """从 ~/.git-credentials 读取含凭证的 URL，精确匹配 host"""
    cred_file = Path.home() / ".git-credentials"
    if not cred_file.exists():
        return ""
    best = ""
    for line in cred_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        # 精确匹配：解析凭证 URL 的 host，与 target host 对比
        from urllib.parse import urlparse
        try:
            line_host = urlparse(line).hostname or ""
        except Exception:
            continue
        if line_host == host:
            best = line
            break  # 精确匹配，直接用
    return best


def _push_with_cred_url(remote_name: str, branch: str = "main") -> tuple:
    """
    用凭证嵌入 URL 直接 push，完全绕开 CredentialHelperSelector。
    返回 (success: bool, error_msg: str)
    """
    # 用 run_git 读取 remote URL（带 -c credential.helper= 覆盖）
    r = run_git("remote", "get-url", remote_name,
                 workdir=WORK_REPO, check=False)
    if r.returncode != 0:
        return False, f"获取 remote URL 失败: {r.stderr.strip()}"
    raw_url = r.stdout.strip()

    # 从 raw_url 提取 host（如 github.com）
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(raw_url)
    host = parsed.hostname or ""

    cred_url = _get_cred_url(host)
    if not cred_url:
        return False, f"找不到 {host} 的凭证，请检查 ~/.git-credentials"

    # 如果 cred_url 缺少路径（只有主机名），从 raw_url 补全
    parsed_cred = urlparse(cred_url)
    if not parsed_cred.path or parsed_cred.path == '/':
        parsed_raw = urlparse(raw_url)
        cred_url = f"{parsed_cred.scheme}://{parsed_cred.netloc}{parsed_raw.path}"

    # 临时覆盖 remote URL（含凭证），push 完立刻恢复
    run_git("remote", "set-url", remote_name, cred_url,
             workdir=WORK_REPO, check=False)
    try:
        r = run_git("push", remote_name, branch,
                     workdir=WORK_REPO, check=False)
        if r.returncode == 0:
            return True, ""
        return False, r.stderr.strip() or r.stdout.strip()
    finally:
        run_git("remote", "set-url", remote_name, raw_url,
                 workdir=WORK_REPO, check=False)


def _pull_with_cred_url(remote_name: str, branch: str = "main") -> tuple:
    """用凭证嵌入 URL 直接 pull，完全绕开 CredentialHelperSelector"""
    r = run_git("remote", "get-url", remote_name,
                 workdir=WORK_REPO, check=False)
    if r.returncode != 0:
        return False, f"获取 remote URL 失败: {r.stderr.strip()}"
    raw_url = r.stdout.strip()

    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(raw_url)
    host = parsed.hostname or ""

    cred_url = _get_cred_url(host)
    if not cred_url:
        return False, f"找不到 {host} 的凭证，请检查 ~/.git-credentials"

    parsed_cred = urlparse(cred_url)
    if not parsed_cred.path or parsed_cred.path == '/':
        parsed_raw = urlparse(raw_url)
        cred_url = f"{parsed_cred.scheme}://{parsed_cred.netloc}{parsed_raw.path}"

    run_git("remote", "set-url", remote_name, cred_url,
             workdir=WORK_REPO, check=False)
    try:
        r = run_git("pull", remote_name, branch, "--rebase",
                     workdir=WORK_REPO, check=False)
        return True, ""
    finally:
        run_git("remote", "set-url", remote_name, raw_url,
                 workdir=WORK_REPO, check=False)


def step_commit_and_push(skill_name: str, version: str):
    log(6, 8, "提交并推送...")
    if not WORK_REPO.exists():
        log(6, 8, f"工作仓库不存在: {WORK_REPO}", "err")
        return False, False

    # git config
    run_git("config", "user.email", "workbuddy@local", check=False)
    run_git("config", "user.name",  "WorkBuddy",  check=False)

    # add
    run_git("add", f"skills/{skill_name}/")
    run_git("add", "README.md", check=False)

    # commit
    r = run_git("diff", "--cached", "--quiet", check=False)
    if r.returncode == 0:
        log(6, 8, "没有变更需要提交", "skip")
        return True, True

    msg = f"feat: sync {skill_name} v{version}"
    run_git("commit", "-m", msg)
    log(6, 8, f"已提交: {msg}", "ok")

    # 自动检测远程名
    remote_gitee  = _detect_remote("gitee.com")
    remote_github = _detect_remote("github.com")

    # push to Gitee（不再提前 pull，避免远程旧版本覆盖本地修改）
    gitee_ok = False
    if remote_gitee:
        log(6, 8, f"推送到码云 (remote: {remote_gitee})...", "info")
        ok, err = _push_with_cred_url(remote_gitee, "main")
        # push 失败时：pull --rebase 再重试一次
        if not ok:
            log(6, 8, f"首次推送失败，尝试 pull --rebase 后重试：{err}", "warn")
            _pull_with_cred_url(remote_gitee, "main")
            ok, err = _push_with_cred_url(remote_gitee, "main")
        if ok:
            log(6, 8, "码云推送成功", "ok")
            gitee_ok = True
        else:
            log(6, 8, f"码云推送失败: {err}", "err")
    else:
        log(6, 8, "未找到码云远程，跳过", "warn")

    # push to GitHub（不再提前 pull，避免远程旧版本覆盖本地修改）
    github_ok = False
    if remote_github:
        log(6, 8, f"推送到 GitHub (remote: {remote_github})...", "info")
        ok, err = _push_with_cred_url(remote_github, "main")
        # push 失败时：pull --rebase 再重试一次
        if not ok:
            log(6, 8, f"首次推送失败，尝试 pull --rebase 后重试：{err}", "warn")
            _pull_with_cred_url(remote_github, "main")
            ok, err = _push_with_cred_url(remote_github, "main")
        if ok:
            log(6, 8, "GitHub 推送成功", "ok")
            github_ok = True
        else:
            log(6, 8, f"GitHub 推送失败: {err}", "err")
    else:
        log(6, 8, "未找到 GitHub 远程，跳过", "warn")

    return gitee_ok, github_ok

# ── 步骤 6.7：更新清单中的上传状态 ──────────────────────────────────────
def step_update_manifest_uploaded(skill_name: str, version: str,
                                  gitee_ok: bool, github_ok: bool,
                                  repo_name="workbuddy-skills"):
    manifest_py = SCRIPT_DIR / "manifest.py"
    if not manifest_py.exists():
        return
    if gitee_ok:
        run_python(manifest_py, "version", repo_name, skill_name, version,
                   "--platform", "gitee")
        run_python(manifest_py, "set-uploaded", repo_name, skill_name,
                   "--platform", "gitee")
        log("6.7", 8, f"清单已更新 [码云]: {skill_name} → {version}", "ok")
    else:
        log("6.7", 8, "码云推送失败，保持 not-uploaded (gitee)", "warn")
    if github_ok:
        run_python(manifest_py, "version", repo_name, skill_name, version,
                   "--platform", "github")
        run_python(manifest_py, "set-uploaded", repo_name, skill_name,
                   "--platform", "github")
        log("6.7", 8, f"清单已更新 [GitHub]: {skill_name} → {version}", "ok")
    else:
        log("6.7", 8, "GitHub 推送失败，保持 not-uploaded (github)", "warn")

# ── 步骤 7：生成 ZIP 安装包 ───────────────────────────────────────────────
def step_pack_zip(skill_name: str, version: str, skills_dir: Path,
                   skip_scan: bool = False):
    log(7, 8, "生成 ZIP 安装包...")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    zip_name = f"{skill_name}-v{version}.zip"
    zip_file = DIST_DIR / zip_name

    # 打包前敏感扫描
    log("7.5", 8, "打包前敏感信息扫描...")
    zip_source = skills_dir / skill_name
    if not skip_scan:
        scan_py = SCRIPT_DIR / "sensitive_scan.py"
        if scan_py.exists():
            scan_out_zip = SCRIPT_DIR / f".sensitive_scan_{skill_name}_zip.json"
            run_python(scan_py, "scan", str(zip_source),
                       "--output", str(scan_out_zip))
            if scan_out_zip.exists() and scan_out_zip.stat().st_size > 0:
                log("7.5", 8, "发现敏感信息，将在副本中脱敏...", "warn")
                tmp_dir = Path(tempfile.gettempdir()) / f".tmp_zip_{os.getpid()}"
                if tmp_dir.exists(): shutil.rmtree(tmp_dir)
                tmp_dir.mkdir(parents=True)
                dst_tmp = tmp_dir / skill_name
                shutil.copytree(zip_source, dst_tmp, ignore=_ignore_patterns)
                # 脱敏
                decisions_zip = scan_out_zip.with_suffix(".json.decisions.json")
                make_py = SCRIPT_DIR / "make_all_sanitize.py"
                if make_py.exists():
                    r = run_python(make_py, str(scan_out_zip), capture=True)
                    if r and r.stdout:
                        Path(decisions_zip).write_text(r.stdout, encoding="utf-8")
                if decisions_zip.exists():
                    run_python(scan_py, "apply", str(dst_tmp),
                               "--decisions", str(decisions_zip),
                               "--scan-result", str(scan_out_zip))
                zip_source = dst_tmp
                scan_out_zip.unlink(missing_ok=True)
                decisions_zip.unlink(missing_ok=True)
            else:
                scan_out_zip.unlink(missing_ok=True)
                log("7.5", 8, "未发现敏感信息", "ok")
        else:
            log("7.5", 8, "sensitive_scan.py 不存在，跳过", "skip")
    else:
        log("7.5", 8, "已跳过（--skip-scan）", "skip")

    # 清理 ZIP 源目录中的临时文件
    clean_py = SCRIPT_DIR / "clean_zip_source.py"
    if clean_py.exists():
        run_python(clean_py, str(zip_source), check=False)

    # 调用 pack_zip.py 打包
    pack_py = SCRIPT_DIR / "pack_zip.py"
    if pack_py.exists():
        run_python(pack_py, str(zip_source), str(zip_file))
    else:
        # 内置打包逻辑
        import zipfile
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in zip_source.rglob("*"):
                if f.is_file():
                    arcname = f.relative_to(zip_source.parent)
                    zf.write(f, arcname)
    log(7, 8, f"ZIP 已生成: {zip_file}", "ok")

    # 清理临时目录（仅在定义了 tmp_dir 时）
    if 'tmp_dir' in locals() and tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return zip_file

# ── 步骤 8：刷新 index.html ────────────────────────────────────────────────
def step_build_index():
    log(8, 8, "刷新 .dist/index.html...")
    build_py = SCRIPT_DIR / "build_index.py"
    if not build_py.exists():
        log(8, 8, "build_index.py 不存在，跳过", "skip")
        return
    run_python(build_py, str(DIST_DIR))
    log(8, 8, "index.html 已刷新", "ok")

# ── 辅助：读取 description ───────────────────────────────────────────────────
def get_meta_desc(meta_file: Path) -> str:
    get_desc_py = SCRIPT_DIR / "get_meta_desc.py"
    if get_desc_py.exists():
        r = run_python(get_desc_py, str(meta_file), capture=True)
        return r.stdout.strip()
    return ""

# ── 主流程 ────────────────────────────────────────────────────────────────────
def main():
    # ── 0. 彻底阻止 CredentialHelperSelector 弹窗 ──────────────────────
    # 方案：在最早时机固化 credential.helper 配置，所有后续 git 命令直接继承
    # 同时用 GIT_CREDENTIAL_HELPER 环境变量双重保险
    import subprocess as _sp
    _env = os.environ.copy()
    _env["GIT_TERMINAL_PROMPT"] = "0"
    # 写入 repo 级配置（最高优先级，覆盖全局）
    _sp.run(
        ["git", "config", "credential.helper", "store"],
        cwd=str(WORK_REPO), capture_output=True, check=False, env=_env
    )
    # 写入全局配置（防止 repo 级失败）
    _sp.run(
        ["git", "config", "--global", "credential.helper", "store"],
        capture_output=True, check=False, env=_env
    )
    # 确保 .git-credentials 文件存在（避免 store helper 报错）
    _cred = Path.home() / ".git-credentials"
    if not _cred.exists():
        try:
            _cred.write_text("", encoding="utf-8")
        except Exception:
            pass
    # ────────────────────────────────────────────────────────────────────────

    parser = argparse.ArgumentParser(description="git-sync.py v2.6.22")
    parser.add_argument("skill_name", nargs="?", default="",
                        help="技能名称（如 skill-standardization）")
    parser.add_argument("version", nargs="?", default="",
                        help="版本号（如 2.26.0）")
    parser.add_argument("--skip-scan", action="store_true",
                        help="跳过敏感信息扫描")
    args = parser.parse_args()

    skill_name = args.skill_name
    version    = args.version
    skip_scan  = args.skip_scan

    if not skill_name:
        print(f"用法: python {sys.argv[0]} <skill-name> [version] [--skip-scan]")
        sys.exit(1)

    # 自动读取版本号
    meta_file = SKILLS_DIR / skill_name / "_meta.json"
    if not version:
        if meta_file.exists():
            try:
                version = json.load(open(meta_file, encoding="utf-8"))["version"]
            except Exception:
                pass
        if not version:
            print("❌ 无法读取版本号，请手动指定")
            sys.exit(1)

    print("=" * 50)
    print(f"  git-sync.py: {skill_name} v{version}")
    print("=" * 50)

    # 执行各步骤
    step_manifest(skill_name, version)
    compare_result = step_version_compare(skill_name, version)
    step_normalize_meta(meta_file, skill_name, version)
    step_skill_audit(skill_name, SKILLS_DIR, MANIFEST_FILE)

    # 步骤 4：同步文件（版本相同时跳过）
    if compare_result == "skip_sync":
        log(4, 8, "跳过文件同步（版本相同）", "skip")
        repo_skill_dir = WORK_REPO / "skills" / skill_name
    else:
        log(4, 8, "同步文件到工作仓库...")
        repo_skill_dir = sync_files(skill_name, SKILLS_DIR, WORK_REPO)

    step_sensitive_scan(skill_name, repo_skill_dir, skip_scan)
    step_update_readme()

    gitee_ok, github_ok = step_commit_and_push(skill_name, version)
    step_update_manifest_uploaded(skill_name, version, gitee_ok, github_ok)

    zip_file = step_pack_zip(skill_name, version, SKILLS_DIR, skip_scan)
    step_build_index()

    print()
    print("=" * 50)
    print(f"  ✅ 全部完成: {skill_name} v{version}")
    print(f"  📦 ZIP: {zip_file}")
    print("=" * 50)

if __name__ == "__main__":
    main()
