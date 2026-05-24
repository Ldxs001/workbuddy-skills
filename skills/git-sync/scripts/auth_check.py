# -*- coding: utf-8 -*-
"""
授权检查模块 - 由 skill-standardization 自动生成 - DO NOT EDIT
技能: git-sync
"""

import json
import sys
from pathlib import Path

AUTH_STATE_FILE = Path(__file__).resolve().parent.parent / ".auth_state.json"

# 权限列表（自动生成，请勿手动修改）
_PERMISSIONS_RAW = [
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "sensitive_access",
    "desc": "检测到敏感信息访问（memory/credentials/token）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "subprocess_call",
    "desc": "检测到 subprocess 调用（os.system/subprocess等）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "critical_write",
    "desc": "检测到关键位置写入（skills/.workbuddy/系统目录）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  },
  {
    "serial": 0,
    "name": "file_delete",
    "desc": "检测到文件删除操作（os.remove/shutil.rmtree等）"
  }
]

PERMISSIONS = _PERMISSIONS_RAW  # list[dict]

_initialized = False


def _load_state():
    """加载授权状态字典。"""
    if not AUTH_STATE_FILE.exists():
        return {}
    try:
        with open(AUTH_STATE_FILE, "r", encoding="utf-8") as _f:
            return json.load(_f)
    except Exception:
        return {}


def _save_state(state):
    """保存授权状态字典。"""
    AUTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTH_STATE_FILE, "w", encoding="utf-8") as _f:
        json.dump(state, _f, indent=2, ensure_ascii=False)


def _all_unauthorized():
    """返回 True 当且仅当所有权限均未授权。"""
    st = _load_state()
    for p in PERMISSIONS:
        if st.get(p["name"], {}).get("authorized", False):
            return False
    return True


def _show_auth_table():
    """
    弹出授权表（全部未授权时调用）。
    用户可选择「全部授权」「输入序号」「拒绝」。
    """
    print("=" * 70)
    print(" 授权表 — 请选择需要授权的操作")
    print("=" * 70)
    print(f"{'序号':<6}  {'权限名称':<38}  简述")
    print("-" * 70)
    for p in PERMISSIONS:
        print(f"{p['serial']:<6}  {p['name']:<38}  {p['desc'][:40]}")
    print("-" * 70)
    print(" 选项：")
    print("   all        — 全部授权")
    print("   1,3,5      — 输入序号（逗号分隔）")
    print("   r          — 拒绝所有（退出）")
    print("=" * 70)

    try:
        choice = input("请选择: ").strip().lower()
    except EOFError:
        print("[非交互环境] 默认全部授权")
        choice = "all"

    st = _load_state()

    if choice == "all":
        for p in PERMISSIONS:
            st[p["name"]] = {"authorized": True, "mode": "unified"}
        _save_state(st)
        print("[✓] 已授权全部操作")
    elif choice == "r":
        print("[✗] 用户拒绝授权，技能将退出")
        sys.exit(1)
    else:
        try:
            serials = [int(x.strip()) for x in choice.split(",")]
        except ValueError:
            print("[!] 输入格式错误，已跳过")
            return
        serial_map = {p['serial']: p['name'] for p in PERMISSIONS}
        for s in serials:
            if s in serial_map:
                st[serial_map[s]] = {"authorized": True, "mode": "unified"}
        _save_state(st)
        print(f"[✓] 已授权序号: {serials}")


def _prompt_immediate(perm_name, perm_desc):
    """
    对单个未授权权限弹出即时授权对话框。
    选项：1=永久授权  2=仅本次  3=拒绝
    返回: "permanent" / "once" / "reject"
    """
    print()
    print("=" * 60)
    print(f" [授权询问] {perm_desc}")
    print("=" * 60)
    print("   1. 永久授权（不再询问）")
    print("   2. 仅本次（本次执行生效，下次再问）")
    print("   3. 拒绝授权（跳过此操作）")
    print("=" * 60)
    try:
        choice = input("请选择 (1/2/3): ").strip()
    except EOFError:
        print("[非交互环境] 默认：仅本次授权")
        return "once"
    if choice == "1":
        return "permanent"
    elif choice == "2":
        return "once"
    else:
        return "reject"


def authorize(perm_name, perm_desc=''):
    """
    检查并请求授权。在每次高风险操作前调用。
    返回 True（已授权）/ False（已拒绝，调用方应跳过操作）。
    """
    global _initialized
    if not _initialized:
        initialize()
        _initialized = True

    st = _load_state()
    if st.get(perm_name, {}).get("authorized", False):
        return True

    decision = _prompt_immediate(perm_name, perm_desc)

    if decision == "permanent":
        st[perm_name] = {"authorized": True, "mode": "immediate"}
        _save_state(st)
        return True
    elif decision == "once":
        return True  # 仅本次，不落盘
    else:
        print(f"[✗] 权限 {perm_name} 被拒绝，跳过此操作")
        return False


def initialize():
    """
    在技能入口处调用一次。
    若全部未授权则弹出授权表；否则不干预。
    """
    if not _all_unauthorized():
        return
    if not PERMISSIONS:
        return
    _show_auth_table()
    # 重新检查：若仍全部未授权说明用户选了 r
    if _all_unauthorized():
        print("[✗] 未授权任何操作，技能退出")
        sys.exit(1)


def reset():
    """重置授权状态（调试用）。"""
    if AUTH_STATE_FILE.exists():
        AUTH_STATE_FILE.unlink()
    print("[*] 授权状态已重置")


def status():
    """打印当前授权状态。"""
    st = _load_state()
    print("授权状态：")
    for p in PERMISSIONS:
        ok = st.get(p["name"], {}).get("authorized", False)
        marker = "✓" if ok else "✗"
        auth_str = "已授权" if ok else "未授权"
        print(f"  [{marker}] {p['name']}: {auth_str}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            status()
        elif cmd == "reset":
            reset()
        elif cmd == "init":
            initialize()
        else:
            print("Usage: python auth_check.py [status|reset|init]")
    else:
        initialize()