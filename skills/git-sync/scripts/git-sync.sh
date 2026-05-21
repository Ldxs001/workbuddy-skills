#!/bin/bash
# git-sync.sh - 一键同步skill到码云、GitHub并生成ZIP包
# 用法: bash git-sync.sh <skill-name> [version]
# 示例: bash git-sync.sh color-toolkit 1.0.0

set -euo pipefail

SKILL_NAME="${1:-}"
VERSION="${2:-1.0.0}"

if [ -z "$SKILL_NAME" ]; then
    echo "用法: bash $0 <skill-name> [version]"
    echo "示例: bash $0 color-toolkit 1.0.0"
    exit 1
fi

# ── 路径定义 ──────────────────────────────────────────
SKILLS_DIR="$HOME/.workbuddy/skills"
WORK_REPO="$HOME/.workbuddy/workbuddy-skills"
README_FILE="$WORK_REPO/README.md"
PACK_DIR="$SKILLS_DIR/.${SKILL_NAME}-pack"
ZIP_FILE="$SKILLS_DIR/${SKILL_NAME}-v${VERSION}.zip"

echo "============================================"
echo "  git-sync: $SKILL_NAME v$VERSION"
echo "============================================"

# ── 0. 前置检查 ──────────────────────────────────────
if [ ! -d "$SKILLS_DIR/$SKILL_NAME" ]; then
    echo "❌ 错误: ~/.workbuddy/skills/$SKILL_NAME 不存在"
    exit 1
fi

if [ ! -d "$WORK_REPO/.git" ]; then
    echo "❌ 错误: 工作仓库 $WORK_REPO 不是git仓库"
    exit 1
fi

# 从 _meta.json 或 SKILL.md 提取描述（供README更新用）
SKILL_DESC=""
if [ -f "$SKILLS_DIR/$SKILL_NAME/_meta.json" ]; then
    SKILL_DESC=$(python -c "
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(d.get('description',''))
except: pass
" "$SKILLS_DIR/$SKILL_NAME/_meta.json" 2>/dev/null || true)
fi
if [ -z "$SKILL_DESC" ] && grep -q "^description:" "$SKILLS_DIR/$SKILL_NAME/SKILL.md" 2>/dev/null; then
    SKILL_DESC=$(grep "^description:" "$SKILLS_DIR/$SKILL_NAME/SKILL.md" | head -1 | sed 's/^description: *//')
fi
if [ -z "$SKILL_DESC" ]; then
    SKILL_DESC="$SKILL_NAME 技能"
fi

echo "技能描述: $SKILL_DESC"

# ── 0.5 _meta.json 标准化校验 ─────────────────────────
echo ""
echo "[0/5] 校验 _meta.json 标准字段..."

normalize_meta_json() {
    local meta_file="$SKILLS_DIR/$SKILL_NAME/_meta.json"

    if [ ! -f "$meta_file" ]; then
        echo "  ⚠️  _meta.json 不存在，自动创建..."
    fi

    python "$SKILLS_DIR/git-sync/scripts/normalize_meta.py" "$meta_file" "$SKILL_NAME" "$VERSION" "$SKILL_DESC"

    # 确保 _meta.json 也复制到 scripts 同级（以防被忽略）
    cp "$meta_file" "$SKILLS_DIR/git-sync/scripts/../_meta.json" 2>/dev/null || true
}

normalize_meta_json

# ── 1. 同步文件到工作仓库 ────────────────────────────
echo ""
echo "[1/5] 同步文件到工作仓库..."

DST="$WORK_REPO/skills/$SKILL_NAME"
rm -rf "$DST"
mkdir -p "$DST"

copy_dir() {
    local src="$1" dst="$2"
    if [ -d "$src" ]; then
        mkdir -p "$dst"
        # 用find复制，排除__pycache__
        find "$src" -type f ! -path "*/__pycache__/*" ! -name "*.pyc" \
            ! -name "*.html" ! -name "*.log" \
            -exec sh -c 'mkdir -p "$2/$(dirname "$1")" && cp "$1" "$2/$(dirname "$1")/"' _ {} "$dst" \;
        # 上面的方式太复杂，改用简单方式
    fi
}

# 简单可靠的复制方式
sync_skill() {
    local src="$SKILLS_DIR/$SKILL_NAME"
    local dst="$WORK_REPO/skills/$SKILL_NAME"

    # SKILL.md + _meta.json（必需）
    cp "$src/SKILL.md" "$dst/" 2>/dev/null || true
    cp "$src/_meta.json" "$dst/" 2>/dev/null || true

    # 根目录配置文件（非py，非md）
    for f in "$src"/*.json "$src"/*.yaml "$src"/*.yml; do
        [ -f "$f" ] || continue
        local bn=$(basename "$f")
        [ "$bn" = "_meta.json" ] && continue
        cp "$f" "$dst/"
    done

    # scripts/ 目录
    if [ -d "$src/scripts" ]; then
        mkdir -p "$dst/scripts"
        for f in "$src/scripts/"*.py "$src/scripts/"*.sh; do
            [ -f "$f" ] && cp "$f" "$dst/scripts/"
        done
    fi

    # references/ 目录
    if [ -d "$src/references" ]; then
        mkdir -p "$dst/references"
        find "$src/references" -type f ! -path "*/__pycache__/*" \
            -exec cp {} "$dst/references/" \; 2>/dev/null || \
        cp -r "$src/references/." "$dst/references/" 2>/dev/null || true
    fi

    # assets/ 目录
    if [ -d "$src/assets" ]; then
        mkdir -p "$dst/assets"
        cp -r "$src/assets/." "$dst/assets/" 2>/dev/null || true
    fi

    # data/ 目录
    if [ -d "$src/data" ]; then
        mkdir -p "$dst/data"
        cp -r "$src/data/." "$dst/data/" 2>/dev/null || true
    fi

    # 清理__pycache__
    find "$dst" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$dst" -name "*.pyc" -delete 2>/dev/null || true
}

sync_skill

echo "  已同步文件:"
find "$DST" -type f | sed "s|$WORK_REPO/skills/$SKILL_NAME/|  - |" | head -20

# ── 2. 更新 README.md ────────────────────────────────
echo ""
echo "[2/5] 更新 README.md..."

if [ ! -f "$README_FILE" ]; then
    echo "  ⚠️  README.md 不存在，跳过"
else
    # 检查技能是否已存在于README（表格 或 目录树）
    ALREADY_IN_TABLE=false
    ALREADY_IN_TREE=false

    # README格式: | `skill-name` | description | (注意|后有空格)
    if grep -qE "\| \`$SKILL_NAME\` \|" "$README_FILE" 2>/dev/null; then
        ALREADY_IN_TABLE=true
    fi
    if grep -q "│   ├── $SKILL_NAME/" "$README_FILE" 2>/dev/null || \
       grep -q "│   └── $SKILL_NAME/" "$README_FILE" 2>/dev/null; then
        ALREADY_IN_TREE=true
    fi

    if [ "$ALREADY_IN_TABLE" = true ] && [ "$ALREADY_IN_TREE" = true ]; then
        echo "  ℹ️  $SKILL_NAME 已存在于README，跳过更新"
    else
        echo "  📝 添加 $SKILL_NAME 到 README.md..."

        # --- 更新技能列表表格 ---
        if [ "$ALREADY_IN_TABLE" = false ]; then
            # 检查 awk 插入行是否已存在（防止重复）
            AWK_LINE="| \`$SKILL_NAME\` |"
            if grep -F "$AWK_LINE" "$README_FILE" >/dev/null 2>&1; then
                echo "  ℹ️  表格中已存在 $SKILL_NAME，跳过表格插入"
            else
                # 在表格分隔行 |------|------| 后插入新行
                awk -v name="$SKILL_NAME" -v desc="$SKILL_DESC" '
                    /^|------|------|/ {
                        print $0
                        print "| `" name "` | " desc " |"
                        next
                    }
                    { print }
                ' "$README_FILE" > "${README_FILE}.tmp" && mv "${README_FILE}.tmp" "$README_FILE"
                echo "  ✅ 已添加到技能列表表格"
            fi

        fi

        # --- 更新目录结构 ---
        if [ "$ALREADY_IN_TREE" = false ]; then
            # 双重检查（防止脚本重复运行）
            if grep -q "├── $SKILL_NAME/" "$README_FILE" 2>/dev/null || \
               grep -q "└── $SKILL_NAME/" "$README_FILE" 2>/dev/null; then
                echo "  ℹ️  目录树中已存在 $SKILL_NAME，跳过"
            else
                # 通过sys.argv传递参数，避免heredoc中bash变量展开混乱
                python - "$SKILL_NAME" "$README_FILE" << 'PYEOF'
import re, sys
skill_name = sys.argv[1]
readme_path = sys.argv[2]

with open(readme_path, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

in_skills_block = False
last_entry_idx = -1
indent = "│   "

for i, line in enumerate(lines):
    stripped = line.rstrip()
    if "├── skills/" in stripped or "└── skills/" in stripped:
        in_skills_block = True
    if in_skills_block:
        if re.match(r"│   ├── .+", stripped) or re.match(r"│   └── .+", stripped):
            last_entry_idx = i

if last_entry_idx >= 0:
    last_line = lines[last_entry_idx].rstrip()
    if "└──" in last_line:
        lines[last_entry_idx] = last_line.replace("└──", "├──", 1)
        lines.insert(last_entry_idx + 1, indent + "└── " + skill_name + "/")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("  ✅ 已更新目录结构")
    else:
        print("  ⚠️  最后一个条目不是└──，请手动添加")
else:
    print("  ⚠️  未找到skills目录树，请手动添加")
PYEOF
            fi
        fi
    fi
fi

# ── 3. 提交到工作仓库 ────────────────────────────────
echo ""
echo "[3/5] 提交代码..."

cd "$WORK_REPO"

# 确保remote配置正确
git config user.email "workbuddy@local" 2>/dev/null || true
git config user.name "WorkBuddy" 2>/dev/null || true

git add "skills/$SKILL_NAME/"
git add "README.md" 2>/dev/null || true

if git diff --cached --quiet; then
    echo "  ℹ️  没有变更需要提交"
else
    COMMIT_MSG="feat: sync $SKILL_NAME v$VERSION"
    # 检查是否已有pending的未推送commit，有的话amend，否则新commit
    # 简单策略：始终新建commit
    git commit -m "$COMMIT_MSG"
    echo "  ✅ 已提交: $COMMIT_MSG"
fi

# ── 4. 推送到双平台 ──────────────────────────────────
echo ""
echo "[4/5] 推送到码云..."

git pull gitee main --rebase 2>/dev/null || echo "  ⚠️  码云pull失败（可能无网络），继续..."
if git push gitee main 2>&1; then
    echo "  ✅ 码云推送成功"
else
    echo "  ❌ 码云推送失败（请检查网络或凭据）"
fi

echo ""
echo "[5/5] 推送到 GitHub..."

git pull origin main --rebase 2>/dev/null || echo "  ⚠️  GitHub pull失败（可能无网络），继续..."
if git push origin main 2>&1; then
    echo "  ✅ GitHub推送成功"
else
    echo "  ❌ GitHub推送失败（请检查网络或凭据）"
fi

# ── 5. 生成 ZIP 安装包 ───────────────────────────────
echo ""
echo "[额外] 生成 ZIP 安装包..."

cd "$SKILLS_DIR"
rm -rf "$PACK_DIR" "$ZIP_FILE"

mkdir -p "$PACK_DIR/$SKILL_NAME"

# 复制与上传仓库一致的目录结构
sync_skill_for_zip() {
    local src="$SKILLS_DIR/$SKILL_NAME"
    local dst="$PACK_DIR/$SKILL_NAME"

    cp "$src/SKILL.md" "$dst/" 2>/dev/null || true
    cp "$src/_meta.json" "$dst/" 2>/dev/null || true

    for f in "$src"/*.json "$src"/*.yaml "$src"/*.yml; do
        [ -f "$f" ] || continue
        [ "$(basename "$f")" = "_meta.json" ] && continue
        cp "$f" "$dst/" 2>/dev/null || true
    done

    if [ -d "$src/scripts" ]; then
        mkdir -p "$dst/scripts"
        for f in "$src/scripts/"*.py "$src/scripts/"*.sh; do
            [ -f "$f" ] && cp "$f" "$dst/scripts/"
        done
    fi

    if [ -d "$src/references" ]; then
        mkdir -p "$dst/references"
        cp -r "$src/references/." "$dst/references/" 2>/dev/null || true
    fi

    if [ -d "$src/assets" ]; then
        mkdir -p "$dst/assets"
        cp -r "$src/assets/." "$dst/assets/" 2>/dev/null || true
    fi

    if [ -d "$src/data" ]; then
        mkdir -p "$dst/data"
        cp -r "$src/data/." "$dst/data/" 2>/dev/null || true
    fi

    find "$dst" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$dst" -name "*.pyc" -delete 2>/dev/null || true
}

sync_skill_for_zip

# 打包（ZIP根目录为 skill-name/）
cd "$PACK_DIR"
zip -r "$ZIP_FILE" "$SKILL_NAME/" 2>/dev/null
cd "$SKILLS_DIR"
rm -rf "$PACK_DIR"

echo "  ✅ ZIP包已生成:"
unzip -l "$ZIP_FILE" | head -20
echo "  📦 路径: $ZIP_FILE"

# ── 完成 ──────────────────────────────────────────────
echo ""
echo "============================================"
echo "  ✅ 全部完成"
echo "============================================"
echo "  ZIP: $ZIP_FILE"
echo "  码云: https://gitee.com/wUwproject/workbuddy-skills/tree/main/skills/$SKILL_NAME"
echo "  GitHub: https://github.com/Ldxs001/workbuddy-skills/tree/main/skills/$SKILL_NAME"
