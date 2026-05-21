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

# ── 路径定义 ──────────────────────────────────────
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

# ── 0.5 维护清单检查（v1.3.0 新增）────────────────────
echo ""
echo "[0.5/5] 检查维护清单..."

MANIFEST_CHECK=$(python "$SKILLS_DIR/git-sync/scripts/manifest.py" check workbuddy-skills "$SKILL_NAME" 2>&1)
CHECK_EXIT=$?

if [ $CHECK_EXIT -eq 0 ]; then
    echo "  ✅ 在清单中，已上传: $SKILL_NAME"
elif [ $CHECK_EXIT -eq 1 ]; then
    echo "  ⏳ 在清单中，但未上传: $SKILL_NAME"
    echo "  → 继续执行同步（完成后将标记为 uploaded）"
elif [ $CHECK_EXIT -eq 2 ]; then
    echo "  ❓ $SKILL_NAME 不在维护清单中"
    echo ""
    echo "  维护清单中未找到该技能。"
    echo "  请选择操作："
    echo "    1) 加入清单并标记为已上传（推荐，同步后加入）"
    echo "    2) 仅本次同步，不加入清单"
    echo "    3) 中止同步"
    echo ""
    read -p "  请输入选项 [1/2/3]: " MANIFEST_CHOICE
    case "$MANIFEST_CHOICE" in
        1)
            python "$SKILLS_DIR/git-sync/scripts/manifest.py" add workbuddy-skills "$SKILL_NAME" --type skill --uploaded --note "$SKILL_DESC"
            echo "  ✅ 已加入清单，继续同步..."
            ;;
        2)
            echo "  ⚠️  仅本次同步，未加入清单"
            ;;
        3)
            echo "  ❌ 同步已中止"
            exit 0
            ;;
        *)
            echo "  ❌ 无效选项，中止"
            exit 1
            ;;
    esac
fi

# ── 0. _meta.json 标准化校验 ────────────────────────
echo ""
echo "[0/5] 校验 _meta.json 标准字段..."

normalize_meta_json() {
    local meta_file="$SKILLS_DIR/$SKILL_NAME/_meta.json"

    if [ ! -f "$meta_file" ]; then
        echo "  ⚠️  _meta.json 不存在，自动创建..."
    fi

    python "$SKILLS_DIR/git-sync/scripts/normalize_meta.py" "$meta_file" "$SKILL_NAME" "$VERSION" "$SKILL_DESC"
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
        find "$src" -type f ! -path "*/__pycache__/*" ! -name "*.pyc" \
            ! -name "*.html" ! -name "*.log" \
            -exec sh -c 'mkdir -p "$2/$(dirname "$1")" && cp "$1" "$2/$(dirname "$1")/"' _ {} "$dst" \;
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
    # 全量重新生成 README.md（从仓库实际文件）
    echo "  🔄 全量重新生成 README.md（从仓库实际文件）..."
    python "$SKILLS_DIR/git-sync/scripts/update_readme.py" workbuddy-skills "$README_FILE"
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
    git commit -m "$COMMIT_MSG"
    echo "  ✅ 已提交: $COMMIT_MSG"
fi

# ── 3.5 同步成功后更新清单 uploaded 标记 ─────────────
# 如果技能在清单中但 uploaded=false，现在设为 true
python "$SKILLS_DIR/git-sync/scripts/manifest.py" check workbuddy-skills "$SKILL_NAME" 2>/dev/null
if [ $? -eq 1 ]; then
    echo ""
    echo "  ℹ️  将 $SKILL_NAME 标记为已上传..."
    # 直接修改 manifest.json 中该条目的 uploaded 字段
    python -c "
import json
with open('$SKILLS_DIR/git-sync/manifest.json', 'r') as f:
    data = json.load(f)
items = data.get('repos', {}).get('workbuddy-skills', {}).get('items', {})
if '$SKILL_NAME' in items and isinstance(items['$SKILL_NAME'], dict):
    items['$SKILL_NAME']['uploaded'] = True
with open('$SKILLS_DIR/git-sync/manifest.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write('\n')
print('  ✅ 已标记 $SKILL_NAME 为 uploaded')
" 2>/dev/null || true
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
