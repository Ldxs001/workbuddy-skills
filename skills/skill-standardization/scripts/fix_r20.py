#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_r20.py - 稳定 R-20 修复脚本（最终版 v2.2）
用法：python fix_r20.py <skill_dir> [--dry-run] [-v]

改进：
  - 移除 COMMON_ABBREVS 排除逻辑（所有中英文混排一律修复）
  - AI助手 → AI 助手（缩写+中文也要加空格）
  - 添加 --fix-ambiguity 选项，自动修复模糊表述
"""
import os
import re
import sys
import codecs

# ── 配置 ─────────────────────────────────────────────────────────────────────

# 术语映射（非首选语 → 标准术语）
TERM_MAP = [
    ('设置', '配置'),
    ('新建', '创建'),
    ('建立', '创建'),
    ('修改', '更新'),
    ('变更', '更新'),
    ('移除', '删除'),
]

# 拼写修复
SPELL_FIXES = [
    ('tAsk_progress.py', 'task_progress.py'),
    ('tAsk_progress', 'task_progress'),
]

# ── 核心函数 ───────────────────────────────────────────────────────────────────

def fix_chinese_english_spacing(text):
    """修复中英文混排缺少空格（不排除任何缩写）"""
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        # 跳过代码块（``` ... ```）
        if line.strip().startswith('```'):
            new_lines.append(line)
            continue
        # 跳过行内代码（`...`）
        if '`' in line:
            new_lines.append(line)
            continue
        
        # 修复：中文 + 英文单词（中间没有空格）
        def repl_cn_en(m):
            cn_char = m.group(1)
            en_word = m.group(2)
            # 如果中间已经有空格，不修复
            if m.group(0) != cn_char + en_word:
                return m.group(0)
            return cn_char + ' ' + en_word
        
        # 修复：英文单词 + 中文（中间没有空格）
        def repl_en_cn(m):
            en_word = m.group(1)
            cn_char = m.group(2)
            if m.group(0) != en_word + cn_char:
                return m.group(0)
            return en_word + ' ' + cn_char
        
        # 应用修复
        line = re.sub(r'([一-鿿])([A-Za-z]+)', repl_cn_en, line)
        line = re.sub(r'([A-Za-z]+)([一-鿿])', repl_en_cn, line)
        new_lines.append(line)
    
    return '\n'.join(new_lines)

def fix_file(fpath, dry_run=False, fix_ambiguity=False):
    """修复单个文件，返回 (changes, original, fixed) 或 (None, None, None)"""
    with codecs.open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    changes = []
    
    # 1. 修复术语不一致
    for old, new in TERM_MAP:
        if old in content:
            content = content.replace(old, new)
            changes.append(('术语', old, new))
    
    # 2. 修复中英文混排缺少空格
    new_content = fix_chinese_english_spacing(content)
    if new_content != content:
        # 记录具体哪些地方被修复了
        orig_lines = content.split('\n')
        new_lines = new_content.split('\n')
        for i, (o, n) in enumerate(zip(orig_lines, new_lines)):
            if o != n:
                changes.append(('中英文混排', o.strip(), n.strip()))
        content = new_content
    
    # 3. 修复拼写错误
    for old, new in SPELL_FIXES:
        if old in content:
            content = content.replace(old, new)
            changes.append(('拼写', old, new))
    
    # 4. 修复模糊表述（可选）
    if fix_ambiguity:
        ambiguity_map = {
            '可能': '可能的原因包括',
            '应该': '建议',
            '大概': '大约',
            '差不多': '接近',
        }
        for old, new in ambiguity_map.items():
            if old in content:
                content = content.replace(old, new)
                changes.append(('模糊表述', old, new))
    
    # 5. 保存文件
    if content != original:
        if not dry_run:
            with codecs.open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)
        return changes, original, content
    return None, None, None

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='修复 R-20 问题（术语不一致、中英文混排、拼写错误）',
        epilog='示例：python fix_r20.py ~/.workbuddy/skills/triphasic-execution'
    )
    parser.add_argument('skill_dir', help='技能目录路径')
    parser.add_argument('--dry-run', action='store_true', help='检测模式（不修复，只输出报告）')
    parser.add_argument('--fix-ambiguity', action='store_true', help='自动修复模糊表述（可能、应该等）')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出（显示具体修复内容）')
    args = parser.parse_args()
    
    if not os.path.isdir(args.skill_dir):
        print(f'错误：目录不存在 {args.skill_dir}')
        sys.exit(1)
    
    mode = "检测" if args.dry_run else "修复"
    print(f'{mode}：{args.skill_dir}')
    print('-' * 60)
    
    fixed_files = []
    for root, dirs, files in os.walk(args.skill_dir):
        for fname in sorted(files):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            changes, original, fixed = fix_file(fpath, args.dry_run, args.fix_ambiguity)
            if changes:
                fixed_files.append((fpath, changes))
    
    if not fixed_files:
        print('✅ 没有需要修复的问题')
    else:
        print(f'✅ {"检测到" if args.dry_run else "修复了"} {len(fixed_files)} 个文件：')
        for fpath, changes in fixed_files:
            rel_path = os.path.relpath(fpath, args.skill_dir)
            print(f'\n  📄 {rel_path}')
            if args.verbose:
                for change_type, old, new in changes:
                    if change_type == '中英文混排':
                        print(f'     - 中英文混排：{old} → {new}')
                    else:
                        print(f'     - {change_type}：{old} → {new}')
            else:
                type_counts = {}
                for change_type, old, new in changes:
                    type_counts[change_type] = type_counts.get(change_type, 0) + 1
                for t, c in type_counts.items():
                    print(f'     - {t}（{c} 处）')
    
    if args.dry_run:
        print(f'\n💡 提示：去掉 --dry-run 参数可实际执行修复')
    else:
        print(f'\n✅ 修复完成，建议重新运行审计确认：')
        print(f'   cd ~/.workbuddy/skills/skill-standardization/scripts')
        print(f'   python -m skill_audit audit "{args.skill_dir}"')

if __name__ == '__main__':
    main()
