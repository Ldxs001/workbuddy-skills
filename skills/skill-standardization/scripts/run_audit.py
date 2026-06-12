#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_audit.py — skill-standardization 审计启动脚本
绕过「目录名带横杠」导致的 Python 包导入问题。
用法: python run_audit.py audit <skill_dir> [--json] [--fix]
"""
import sys
import logging

logger = logging.getLogger(__name__)
import os

# ── [GBK 兼容] ──
if sys.stdout.encoding and sys.stdout.encoding.upper() not in ('UTF-8', 'UTF8'):
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, errors='replace')

# 将 skill-standardization/ 的父目录加入 sys.path
# 使得 import scripts.skill_audit 可以正常工作
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL_DIR)

# 切换工作目录到 skill-standardization/
os.chdir(SKILL_DIR)

from scripts.skill_audit import main
sys.exit(main())
