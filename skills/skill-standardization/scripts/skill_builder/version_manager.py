#!/usr/bin/env python3
"""
VersionManager — 负责版本号管理
"""

import re
from pathlib import Path


class VersionManager:
    """版本号管理器"""

    @staticmethod
    def bump_version(skill_dir, bump_type):
        """自动升级版本号（SemVer）

        只更新 SKILL.md 和 _meta.json，不自修改其他 .py 文件
        """
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            print(f"⚠️  SKILL.md 不存在，无法升级版本号")
            return None

        # 1. 读取并解析当前版本
        content = skill_md.read_text(encoding="utf-8")
        m = re.search(r'^version:\s*([\d.]+)', content, re.MULTILINE)
        if not m:
            print(f"⚠️  SKILL.md 中未找到 version 字段")
            return None

        old_ver = m.group(1).strip()
        parts = old_ver.split(".")
        if len(parts) < 3:
            parts = (parts + ["0", "0"])[:3]
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if bump_type == "patch":
            patch += 1
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        else:
            print(f"⚠️  未知版本号类型: {bump_type}")
            return None

        new_ver = f"{major}.{minor}.{patch}"
        print(f"📌 版本号: {old_ver} → {new_ver} ({bump_type})")

        # 2. 更新 SKILL.md frontmatter version
        new_content = re.sub(
            r'(^version:\s*)[\d.]+',
            rf'\1{new_ver}',
            content,
            count=1,
            flags=re.MULTILINE
        )
        # 同时更新正文中版本号引用（如 "# skill-standardization vX.Y.Z"）
        new_content = re.sub(
            rf'(?<=v){re.escape(old_ver)}',
            new_ver,
            new_content,
            count=1
        )
        skill_md.write_text(new_content, encoding="utf-8")

        # 3. 更新 _meta.json version
        meta_file = skill_dir / "_meta.json"
        if meta_file.exists():
            try:
                import json
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                meta["version"] = new_ver
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                print(f"✅  _meta.json 版本已更新: {new_ver}")
            except Exception as e:
                print(f"⚠️  _meta.json 版本更新失败: {e}")
        else:
            print(f"⚠️  _meta.json 不存在，跳过版本更新")

        return new_ver

    @staticmethod
    def get_version_from_meta(skill_dir):
        """从 _meta.json 读取版本号（权威来源）"""
        meta_file = skill_dir / "_meta.json"
        if not meta_file.exists():
            return None
        try:
            import json
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            return meta.get("version")
        except Exception:
            return None

    @staticmethod
    def check_version_consistency(skill_dir):
        """检查版本号一致性（SKILL.md vs _meta.json）"""
        skill_md = skill_dir / "SKILL.md"
        meta_file = skill_dir / "_meta.json"

        if not skill_md.exists():
            return None, None, False

        # 从 SKILL.md 读取
        content = skill_md.read_text(encoding="utf-8")
        m = re.search(r'^version:\s*([\d.]+)', content, re.MULTILINE)
        md_ver = m.group(1).strip() if m else None

        # 从 _meta.json 读取
        meta_ver = VersionManager.get_version_from_meta(skill_dir)

        consistent = (md_ver == meta_ver) if (md_ver and meta_ver) else False

        return md_ver, meta_ver, consistent
