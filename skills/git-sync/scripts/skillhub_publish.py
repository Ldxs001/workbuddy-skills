"""SkillHub 发布器 — git-sync 子模块"""
import sys, subprocess, json, os
from _paths import WORK_REPO

def main():
    if len(sys.argv) < 3:
        print("用法: skillhub_publish.py <name> <version>")
        sys.exit(1)
    name, version = sys.argv[1], sys.argv[2]

    work_repo = str(WORK_REPO)
    skill_dir = os.path.join(work_repo, "skills", name)

    if not os.path.isdir(skill_dir):
        print(f"  ❌ 未找到技能目录: {skill_dir}")
        sys.exit(1)

    # SkillHub CLI 路径
    skillhub_cli = os.path.expanduser("~/.skillhub/skills_store_cli.py")
    if not os.path.isfile(skillhub_cli):
        print(f"  ❌ 未找到 SkillHub CLI: {skillhub_cli}")
        sys.exit(1)

    # 获取 changelog
    changelog_line = f"v{version}: sync via git-sync"
    changelog_path = os.path.join(skill_dir, "references", "changelog.md")
    if os.path.isfile(changelog_path):
        with open(changelog_path, encoding="utf-8") as f:
            for line in f:
                if f"## [{version}]" in line:
                    changelog_line = f"v{version}"
                    break

    cmd = [
        sys.executable, skillhub_cli, "publish", skill_dir,
        "--changelog", changelog_line,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=work_repo)
    if result.returncode == 0:
        print(f"  ✅ SkillHub: {name}")
    else:
        print(f"  ⚠️  SkillHub 结果: {result.stderr[:300]}")

if __name__ == "__main__":
    main()
