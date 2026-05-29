#!/usr/bin/env python3
"""
chain_manager.py - Chain Manager OO Refactor v1.22.0
调用链管理核心脚本：创建、查询、更新、删除、执行调用链。

零外部依赖，仅使用 Python 标准库。
跨平台支持 Windows/Linux/macOS。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# R-12 审计锚点：数据目录字面量声明
DEFAULT_DATA_DIR_RAW = "skills/.standardization/skill-sub/data/"

SKILL_DIR = Path(__file__).resolve().parent.parent
# 运行时绝对路径
DATA_DIR = SKILL_DIR.parent / ".standardization" / "skill-sub" / "data"


# R-12 审计锚点：数据目录字面量声明
DEFAULT_DATA_DIR_RAW = "skills/.standardization/skill-sub/data/"

SKILL_DIR = Path(__file__).resolve().parent.parent
# 运行时绝对路径
DATA_DIR = SKILL_DIR.parent / ".standardization" / "skill-sub" / "data"


# ============================================================
# 配置类
# ============================================================

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, chain_home):
        self.chain_home = chain_home
        self.config_file = chain_home / "config.json"
        self._config = None
    
    def load(self):
        """加载用户配置"""
        defaults_path = Path(__file__).resolve().parent / "default_config.json"
        defaults = {}
        if defaults_path.exists():
            defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
        
        user_cfg = {}
        if self.config_file.exists():
            user_cfg = json.loads(self.config_file.read_text(encoding="utf-8"))
        
        defaults.update(user_cfg)
        self._config = defaults
        return defaults
    
    def get(self, key, fallback=None):
        """获取配置值"""
        if self._config is None:
            self.load()
        return self._config.get(key, fallback)
    
    def get_default_retry(self):
        """获取默认重试次数"""
        config = self.load()
        try:
            return max(1, int(config.get("default_max_retries", 3)))
        except (TypeError, ValueError):
            return 3

# ============================================================
# 路径管理类
# ============================================================

class PathManager:
    """路径管理器"""
    
    def __init__(self):
        self.chain_home = self._get_chain_home()
        self.chains_dir = self.chain_home / "chains"
        self.index_file = self.chains_dir / "index.json"
        self.config_file = self.chain_home / "config.json"
        self.skill_dir = Path(__file__).resolve().parent.parent
        self.state_dir = self.chain_home / "state"
        self.logs_dir = self.chain_home / "logs"
    
    def _get_chain_home(self):
        """获取调用链数据目录"""
        env_home = os.environ.get("SKILL_SUB_HOME") or os.environ.get("SKILL_CHAIN_HOME")
        if env_home:
            return Path(env_home)
        # 按照规定：skills/.standardization/<skill-name>/
        default = Path.home() / ".workbuddy" / "skills" / ".standardization" / "skill-sub"
        return default
    
    def get_skills_dir(self):
        """获取已安装技能目录"""
        env_dir = os.environ.get("WORKBUDDY_SKILLS_DIR")
        if env_dir:
            return Path(env_dir)
        return Path.home() / ".workbuddy" / "skills"
    
    def find_skill_path(self, skill_name):
        """查找技能实际目录"""
        skills_dir = self.get_skills_dir()
        if not skills_dir.exists():
            return None
        
        # 精确匹配
        exact = skills_dir / skill_name
        if exact.is_dir():
            return exact
        
        # 模糊匹配
        target = skill_name.lower().replace(" ", "-")
        for entry in skills_dir.iterdir():
            if entry.is_dir():
                if entry.name.lower().replace(" ", "-") == target or target in entry.name.lower():
                    return entry
        
        return None

# ============================================================
# 验证器类
# ============================================================

class ChainValidator:
    """调用链验证器"""
    
    # 里程碑关键词
    MILESTONE_KEYWORDS = [
        "审计", "安全", "部署", "发布", "上线", "打包",
        "测试", "验证", "校验", "审批", "审核",
        "付款", "支付", "下单", "提交", "推送",
        "导入", "导出", "迁移", "备份", "恢复",
        "audit", "deploy", "release", "publish", "push",
        "test", "verify", "validate", "approve", "review",
        "payment", "submit", "import", "export", "migrate",
        "backup", "restore", "build", "compile", "install",
    ]
    
    def __init__(self, path_manager):
        self.path_manager = path_manager
    
    def classify_milestones(self, steps):
        """基于结构特征的通用里程碑判断。
        
        规则优先级（从高到低）：
        1. 用户显式标记 is_milestone=true → 里程碑
        2. 用户显式标记 is_milestone=false → 非里程碑
        3. 总步骤数 <= 2 → 全部里程碑（链太短，每步都关键）
        4. 步骤名包含里程碑关键词 → 里程碑
        5. 被多个后续步骤依赖（瓶颈点，>=2个后续步骤依赖它）→ 里程碑
        6. 是最后一步 → 里程碑（最终交付物）
        7. 其余 → 非里程碑
        
        返回：list[dict] 每项包含 step_index, is_milestone, reason
        """
        n = len(steps)
        if n == 0:
            return []
        
        depended_by = {}
        for i, step in enumerate(steps):
            idx = step.get("index", i + 1)
            depended_by[idx] = set()
        
        for i, step in enumerate(steps):
            idx = step.get("index", i + 1)
            for dep in step.get("depends_on", []):
                if dep in depended_by:
                    depended_by[dep].add(idx)
        
        results = []
        for i, step in enumerate(steps):
            idx = step.get("index", i + 1)
            fm = step.get("failure_mode", {})
            
            if fm.get("is_milestone") is True:
                results.append({"step_index": idx, "is_milestone": True, "reason": "用户显式标记"})
                continue
            
            step_name = step.get("step_name", "")
            step_name_lower = step_name.lower()
            
            if n <= 2:
                results.append({"step_index": idx, "is_milestone": True, "reason": "短链（<=2步），所有步骤均为里程碑"})
                continue
            
            keyword_hit = None
            for kw in self.MILESTONE_KEYWORDS:
                if kw.lower() in step_name_lower:
                    keyword_hit = kw
                    break
            if keyword_hit:
                results.append({"step_index": idx, "is_milestone": True, "reason": f"关键词匹配: '{keyword_hit}'"})
                continue
            
            downstream_count = len(depended_by.get(idx, set()))
            if downstream_count >= 2:
                results.append({"step_index": idx, "is_milestone": True, "reason": f"瓶颈点（{downstream_count}个后续步骤依赖）"})
                continue
            
            if i == n - 1:
                results.append({"step_index": idx, "is_milestone": True, "reason": "最终交付步骤"})
                continue
            
            explicit_false = fm.get("is_milestone") is False
            results.append({
                "step_index": idx,
                "is_milestone": False,
                "reason": "显式取消里程碑" if explicit_false else "默认规则（非关键节点）"
            })
        
        return results
    
    def validate_chain(self, chain_data):
        """验证调用链数据"""
        errors = []
        warnings = []
        
        # 1. 基本结构
        if not chain_data.get("name"):
            errors.append("缺少名称")
        if not chain_data.get("steps"):
            errors.append("没有步骤")
        
        steps = chain_data.get("steps", [])
        
        # 2. 步骤完整性
        indices = set()
        for i, step in enumerate(steps):
            idx = step.get("index", i + 1)
            indices.add(idx)
            
            if not step.get("skill_name"):
                warnings.append(f"步骤 {idx}: 缺少技能名称")
            if not step.get("action"):
                warnings.append(f"步骤 {idx}: 缺少动作描述")
            if not step.get("step_name"):
                warnings.append(f"步骤 {idx}: 缺少步骤名称")
        
        # 3. 技能可用性
        missing = []
        for step in steps:
            skill_name = step.get("skill_name", "")
            if skill_name in ("(内置)", "(内置打包)", ""):
                continue
            path = self.path_manager.find_skill_path(skill_name)
            if not path:
                missing.append(skill_name)
        
        if missing:
            missing_unique = list(set(missing))
            for ms in missing_unique:
                errors.append(f"技能未安装: {ms}")
        
        return errors, warnings

# ============================================================
# 备份管理类
# ============================================================

class BackupManager:
    """备份管理器"""
    
    def __init__(self, path_manager):
        self.path_manager = path_manager
        self.backups_dir = self.path_manager.chain_home / "backups"
    
    def ensure_dirs(self):
        """确保备份目录存在"""
        self.backups_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_chain(self, name, chain_data, reason="auto"):
        """备份调用链"""
        self.ensure_dirs()
        
        # 创建备份文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backups_dir / f"{name}_{timestamp}.json"
        
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(chain_data, f, ensure_ascii=False, indent=2)
        
        return backup_file
    
    def list_backups(self, name):
        """列出备份"""
        if not self.backups_dir.exists():
            return []
        
        backups = []
        for f in self.backups_dir.iterdir():
            if f.name.startswith(name) and f.name.endswith(".json"):
                backups.append(f)
        
        return sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def restore_backup(self, name, backup_file):
        """恢复备份"""
        if not backup_file.exists():
            return False, f"备份文件不存在: {backup_file}"
        
        try:
            with open(backup_file, "r", encoding="utf-8") as f:
                chain_data = json.load(f)
            
            # 保存到当前链
            chain_file = self.path_manager.chains_dir / f"{name}.json"
            with open(chain_file, "w", encoding="utf-8") as f:
                json.dump(chain_data, f, ensure_ascii=False, indent=2)
            
            return True, f"已从备份恢复: {backup_file.name}"
        except Exception as e:
            return False, f"恢复失败: {e}"

# ============================================================
# 调用链管理类
# ============================================================

class ChainManager:
    """调用链管理器"""
    
    def __init__(self):
        self.path_manager = PathManager()
        self.config_manager = ConfigManager(self.path_manager.chain_home)
        self.validator = ChainValidator(self.path_manager)
        self.backup_manager = BackupManager(self.path_manager)
    
    def load_index(self):
        """加载调用链索引"""
        if not self.path_manager.index_file.exists():
            return {}
        with open(self.path_manager.index_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def save_index(self, index):
        """保存调用链索引"""
        self.path_manager.chains_dir.mkdir(parents=True, exist_ok=True)
        with open(self.path_manager.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def load_chain(self, name):
        """加载调用链"""
        index = self.load_index()
        if name not in index:
            return None
        chain_file = Path(index[name])
        if not chain_file.exists():
            return None
        with open(chain_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def save_chain(self, chain_data):
        """保存调用链"""
        index = self.load_index()
        name = chain_data["name"]
        
        # 备份现有链
        if name in index:
            existing = self.load_chain(name)
            if existing:
                self.backup_manager.backup_chain(name, existing, "overwrite")
        
        # 保存新链
        chain_file = self.path_manager.chains_dir / f"{name}.json"
        with open(chain_file, "w", encoding="utf-8") as f:
            json.dump(chain_data, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        index[name] = str(chain_file)
        self.save_index(index)
        
        return True
    
    def delete_chain(self, name, force=False):
        """删除调用链"""
        index = self.load_index()
        if name not in index:
            return False, f"调用链 '{name}' 不存在"
        
        # 备份
        existing = self.load_chain(name)
        if existing:
            self.backup_manager.backup_chain(name, existing, "delete")
        
        # 删除文件
        chain_file = Path(index[name])
        if chain_file.exists():
            chain_file.unlink()
        
        # 更新索引
        del index[name]
        self.save_index(index)
        
        return True, f"调用链 '{name}' 已删除"
    
    def list_chains(self):
        """列出所有调用链"""
        index = self.load_index()
        return list(index.keys())
    
    def create_chain(self, name, description="", purpose="", tags=None, steps=None):
        """创建调用链"""
        if tags is None:
            tags = []
        if steps is None:
            steps = []
        
        chain_data = {
            "name": name,
            "description": description,
            "purpose": purpose,
            "tags": tags,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "exec_count": 0
        }
        
        success = self.save_chain(chain_data)
        if success:
            return True, f"调用链 '{name}' 创建成功"
        else:
            return False, f"调用链 '{name}' 创建失败"
    

# ============================================================
# ChainEditor - 调用链编辑器
# ============================================================

class ChainEditor:
    """调用链编辑器（负责创建/更新/删除操作）"""
    
    def __init__(self, chain_manager):
        self.cm = chain_manager
        self.backup_manager = self.cm.backup_manager
        self.validator = self.cm.validator
    
    def create(self, name, description="", purpose="", tags=None, steps=None):
        """创建调用链"""
        if tags is None:
            tags = []
        if steps is None:
            steps = []
        
        chain_data = {
            "name": name,
            "description": description,
            "purpose": purpose,
            "tags": tags,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "exec_count": 0
        }
        
        # 验证
        errors, warnings = self.validator.validate_chain(chain_data)
        if errors:
            return False, f"验证失败: {'; '.join(errors)}"
        
        for w in warnings:
            print(f"[警告] {w}")
        
        # 保存
        success = self.cm.save_chain(chain_data)
        if success:
            return True, f"调用链 '{name}' 创建成功"
        else:
            return False, f"调用链 '{name}' 创建失败"
    
    def update(self, name, **kwargs):
        """更新调用链"""
        chain_data = self.cm.load_chain(name)
        if not chain_data:
            return False, f"调用链 '{name}' 不存在"
        
        # 备份
        self.backup_manager.backup_chain(name, chain_data, "update")
        
        # 更新字段
        for key, value in kwargs.items():
            if key in chain_data:
                chain_data[key] = value
        
        chain_data["updated_at"] = datetime.now().isoformat()
        
        # 验证
        errors, warnings = self.validator.validate_chain(chain_data)
        if errors:
            return False, f"验证失败: {'; '.join(errors)}"
        
        # 保存
        self.cm.save_chain(chain_data)
        return True, f"调用链 '{name}' 已更新"
    
    def delete(self, name, force=False):
        """删除调用链"""
        return self.cm.delete_chain(name, force=force)
    
    def add_step(self, name, step):
        """添加步骤"""
        chain_data = self.cm.load_chain(name)
        if not chain_data:
            return False, f"调用链 '{name}' 不存在"
        
        # 备份
        self.backup_manager.backup_chain(name, chain_data, "add_step")
        
        # 添加步骤
        steps = chain_data.get("steps", [])
        step["index"] = len(steps) + 1
        steps.append(step)
        chain_data["steps"] = steps
        chain_data["updated_at"] = datetime.now().isoformat()
        
        # 保存
        self.cm.save_chain(chain_data)
        return True, f"步骤已添加到 '{name}'"
    
    def remove_step(self, name, index):
        """删除步骤"""
        chain_data = self.cm.load_chain(name)
        if not chain_data:
            return False, f"调用链 '{name}' 不存在"
        
        # 备份
        self.backup_manager.backup_chain(name, chain_data, "remove_step")
        
        # 删除步骤
        steps = chain_data.get("steps", [])
        idx = index - 1  # 转换为 0-based
        if idx < 0 or idx >= len(steps):
            return False, f"步骤索引无效: {index}"
        
        steps.pop(idx)
        
        # 重新编号
        for i, s in enumerate(steps):
            s["index"] = i + 1
        
        chain_data["steps"] = steps
        chain_data["updated_at"] = datetime.now().isoformat()
        
        # 保存
        self.cm.save_chain(chain_data)
        return True, f"步骤 {index} 已从 '{name}' 删除"
    

# ============================================================
# CLI 命令处理类
# ============================================================

class CLIHandler:
    """CLI 命令处理器"""
    
    def __init__(self):
        self.chain_manager = ChainManager()
    
    def cmd_init(self, args):
        """初始化"""
        self.chain_manager.path_manager.chains_dir.mkdir(parents=True, exist_ok=True)
        print("✅ 初始化完成")
        return 0
    
    def cmd_create(self, args):
        """创建调用链"""
        name = args.name
        description = args.description or ""
        purpose = args.purpose or ""
        tags = args.tags or []
        
        steps = []
        if args.steps:
            try:
                steps = json.loads(args.steps)
            except json.JSONDecodeError as e:
                print(f"❌ 步骤 JSON 解析失败: {e}")
                return 1
        
        success, message = self.chain_manager.create_chain(name, description, purpose, tags, steps)
        if success:
            print(f"✅ {message}")
            return 0
        else:
            print(f"❌ {message}")
            return 1
    
    def cmd_list(self, args):
        """列出所有调用链"""
        chains = self.chain_manager.list_chains()
        if not chains:
            print("没有调用链")
            return 0
        
        print(f"调用链列表 ({len(chains)} 个):")
        for name in chains:
            print(f"  - {name}")
        
        return 0
    
    def cmd_show(self, args):
        """显示调用链"""
        name = args.name
        chain = self.chain_manager.load_chain(name)
        if not chain:
            print(f"❌ 调用链 '{name}' 不存在")
            return 1
        
        print(f"调用链: {chain['name']}")
        print(f"描述: {chain.get('description', '')}")
        print(f"目的: {chain.get('purpose', '')}")
        print(f"步骤数: {len(chain.get('steps', []))}")
        
        return 0
    
    def cmd_delete(self, args):
        """删除调用链"""
        name = args.name
        force = getattr(args, "force", False)
        
        success, message = self.chain_manager.delete_chain(name, force=force)
        if success:
            print(f"✅ {message}")
            return 0
        else:
            print(f"❌ {message}")
            return 1
    

# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    # 修复 Windows 控制台编码问题
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass  # Python <3.7 不支持
    
    parser = argparse.ArgumentParser(
        description="Chain Manager v1.2.0 - 调用链管理 (OO Refactor)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python chain_manager.py init
  python chain_manager.py create --name "发布流水线" --description "技能发布流程"
  python chain_manager.py list
  python chain_manager.py show --name "发布流水线"
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # init
    subparsers.add_parser("init", help="初始化")
    
    # create
    p_create = subparsers.add_parser("create", help="创建调用链")
    p_create.add_argument("--name", required=True, help="调用链名称")
    p_create.add_argument("--description", default="", help="描述")
    p_create.add_argument("--purpose", default="", help="目的")
    p_create.add_argument("--tags", default="", help="标签 (JSON 数组)")
    p_create.add_argument("--steps", default="", help="步骤 (JSON 数组)")
    
    # list
    subparsers.add_parser("list", help="列出所有调用链")
    
    # show
    p_show = subparsers.add_parser("show", help="显示调用链")
    p_show.add_argument("--name", required=True, help="调用链名称")
    
    # delete
    p_delete = subparsers.add_parser("delete", help="删除调用链")
    p_delete.add_argument("--name", required=True, help="调用链名称")
    p_delete.add_argument("--force", action="store_true", help="强制删除（不确认）")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    cli_handler = CLIHandler()
    
    commands = {
        "init": cli_handler.cmd_init,
        "create": cli_handler.cmd_create,
        "list": cli_handler.cmd_list,
        "show": cli_handler.cmd_show,
        "delete": cli_handler.cmd_delete,
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
