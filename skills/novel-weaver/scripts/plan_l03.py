#!/usr/bin/env python3
"""Plan L03 substructures for 赛博搏杀记"""

import sys, json
sys.path.insert(0, 'scripts')

from novel_workflow_engine import NovelWorkflowEngine
from _path_utils import DATA_DIR
from pathlib import Path

PROJECT = '赛博搏杀记'
CHAPTER = 'L03'

# L03 子结构规划：索赔链调查 + 李梅联合维权 + 世界冲突开始
SUB_STRUCTURES = [
    {
        "s_key": "S01", 
        "title": "线索浮现", 
        "summary": "整理父母遗物，发现恒达机电义肢配件出厂合格证。铁心询问最近是否有心事，'你走神了三次'。", 
        "tone": "沉静内省", 
        "emotions": ["疑惑", "不安"]
    },
    {
        "s_key": "S02", 
        "title": "李梅介入", 
        "summary": "铁线巷黑作坊老板的儿子李梅出现，声称知道真相——恒达诊所与黑市部件链，父亲是被压榨的受害者而非意外死亡。两人决定联合维权。", 
        "tone": "紧张对峙", 
        "emotions": ["愤怒", "决心"]
    },
    {
        "s_key": "S03", 
        "title": "维权联盟形成", 
        "summary": "整理索赔材料：购买记录、安装记录、出厂编号。李梅分享她姐姐因劣质义肢致残的遭遇。世界冲突开始：个人维权 vs 资本帝国。", 
        "tone": "坚定推进", 
        "emotions": ["愤怒", "团结"]
    },
    {
        "s_key": "S04", 
        "title": "索赔信发送", 
        "summary": "将索赔材料邮寄给恒达机电法务部。收到回复：'您的索赔已被拒绝，证据不足'。老陈建议不要硬碰硬，但主角意识到必须战斗。", 
        "tone": "对抗升级", 
        "emotions": ["愤怒", "绝望", "反击"]
    },
    {
        "s_key": "S05", 
        "title": "世界冲突", 
        "summary": "铁心问哥你到底想做什么，主角回答：'不是我要做，是这个世界逼我做的'。从结构力训练转向系统性反抗，为后续归元会埋下伏笔。", 
        "tone": "觉醒宣言", 
        "emotions": ["愤怒", "决心", "悲剧感"]
    }
]

def main():
    engine = NovelWorkflowEngine()
    
    state_path = DATA_DIR / PROJECT / 'data' / 'novel_state.json'
    
    # 步骤 1: 子结构因果链验证
    print("[规划 L03 子结构]")
    result = engine.validate_sub_causality(CHAPTER, SUB_STRUCTURES)
    if not result.get('passed'):
        print(f"[失败] 因果链未通过：{result}")
        return False
    
    print("[✓] 子结构因果链验证通过")
    
    # 步骤 2: 注册到 state
    print("\n[注册 L03 子结构]")
    engine.register_sub_structures_to_state(PROJECT, CHAPTER, SUB_STRUCTURES)
    
    # 步骤 3: 检查门禁并推进阶段
    print("[检查门]")
    gate_result = engine.check_and_advance_phase(CHAPTER, 'outline_causality', 'sub_causality')
    if not gate_result.get('passed'):
        print(f"[失败] 门禁未通过：{gate_result}")
        return False
    
    print("[✓] L03 规划完成，状态已更新为 writing")
    
    # 打印结果
    with open(state_path, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    for ch in state['chapters']:
        if ch['id'] == CHAPTER and ch.get('sub_structures'):
            print("\n=== L03 子结构清单 ===")
            for skey, sval in ch['sub_structures'].items():
                print(f"{skey}: {sval['title']} [{sval['tone']}]")
            
            return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
