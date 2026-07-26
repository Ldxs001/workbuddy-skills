"""rag-assistant: 独立智能体，封装 local-rag-builder 技能"""
__version__ = "2.2.8"

# 确保 vendor/ 在 sys.path（使 pypdf 等本地包可导入）
import os
import sys
_vendor = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vendor"))
if _vendor not in sys.path:
    sys.path.insert(0, _vendor)
