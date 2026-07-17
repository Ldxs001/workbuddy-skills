"""
local-rag-builder NLI 三向分类器
v0.1.0

用 cross-encoder（3-class）对 (query, doc) pair 做蕴含/中立/矛盾标注。
模型从 data/models/ 加载，与 reranker 同一套路径解析逻辑，local_files_only。
"""
import os
import torch
import torch.nn.functional as F

from config import load_config
from utils import MODELS_DIR, safe_json_load


class NLIClassifier:
    """NLI 三向分类器"""

    LABEL_NAMES = ["contradiction", "neutral", "entailment"]

    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """加载 NLI 模型（路径解析逻辑与 ModelReranker 一致）"""
        if self._model is not None:
            return

        if not self.model_path:
            cfg = load_config()
            self.model_path = cfg.get("nli", {}).get("model_path", "")

        # 路径解析：HuggingFace ID → 本地路径
        if self.model_path and not os.path.exists(self.model_path):
            index_path = os.path.join(MODELS_DIR, "model_index.json")
            idx = safe_json_load(index_path, {})
            if self.model_path in idx:
                actual = idx[self.model_path].get("path", "")
                if actual and os.path.exists(actual):
                    self.model_path = actual
                else:
                    dirname = self.model_path.replace("/", "_")
                    local_path = os.path.join(MODELS_DIR, dirname)
                    if os.path.exists(local_path):
                        self.model_path = local_path

        # 兜底：扫描 MODELS_DIR
        if not self.model_path or not os.path.exists(self.model_path):
            from utils import find_model_dirs
            models = find_model_dirs(MODELS_DIR)
            if not models:
                raise ValueError("未找到 NLI 模型。请先在 Web 面板下载 NLI 模型")
            self.model_path = models[0]["path"]

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, local_files_only=True
            )
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_path, local_files_only=True
            ).to(device).eval()
        except Exception as e:
            raise RuntimeError(f"加载 NLI 模型失败 ({self.model_path}): {e}")

    def classify(self, query: str, docs: list, top_k: int = 0) -> list:
        """
        对每个 doc 做 NLI 三向分类。

        参数:
            query: 查询关键词（slice 短语，如 "茅台 制作工艺"）
            docs: Document 或 dict 列表
            top_k: 0=全部分类，>0 只分类前 top_k 个

        返回:
            [
                {"doc": doc, "contradiction": 0.03, "neutral": 0.12, "entailment": 0.85},
                ...
            ]
        """
        if not docs:
            return []

        self._load_model()

        # 截断
        classify_docs = docs[:top_k] if top_k > 0 else docs

        # 提取文本内容
        contents = []
        for doc in classify_docs:
            c = doc.page_content if hasattr(doc, "page_content") else (
                doc.get("content", "") if isinstance(doc, dict) else str(doc)
            )
            contents.append(c)

        # (query, doc) 作为 pair 输入
        pairs = [[query, c] for c in contents]
        inputs = self._tokenizer(
            pairs, padding=True, truncation=True,
            max_length=512, return_tensors="pt",
        ).to(self._model.device)

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits  # (N, 3)
            probs = F.softmax(logits, dim=-1)  # (N, 3)

        results = []
        for i, doc in enumerate(classify_docs):
            prob = probs[i].tolist()
            label_dict = {
                self.LABEL_NAMES[j]: round(prob[j], 4)
                for j in range(3)
            }
            results.append({"doc": doc, **label_dict})

        return results

    def classify_batch(self, query: str, doc_batches: list[list], top_k: int = 0) -> list[list]:
        """
        批量分类（用于多个 slice 各自独立的 docs）

        参数:
            query: 单个 query（此方法对每个 batch 用同一 query）
            doc_batches: [[doc, doc, ...], [doc, ...], ...]
            top_k: 0=全部分类

        返回:
            [[{doc, labels}, ...], [{doc, labels}, ...], ...]
        """
        results = []
        for docs in doc_batches:
            results.append(self.classify(query, docs, top_k))
        return results

    def verify(self, key: str, value: str) -> dict:
        """evidence 语义一致性验证 — 查询输出 NLI

        用同一 NLI 模型判断 entity/attr key 和 evidence value 语义是否一致。
        (premise=value, hypothesis=key)

        参数:
            key:   entity/attr，LLM 提炼的概念词（如"定义"、"引力波"）
            value: evidence 值，原文出处子串（如"什么是"、"主涉引力波"）

        返回:
            {"is_valid": bool,
             "entailment": float,    # 蕴含概率
             "neutral": float,       # 中立概率
             "contradiction": float} # 矛盾概率

        判定标准：
            entailment > max(neutral, contradiction) → is_valid=True
            否则 → is_valid=False
        """
        self._load_model()
        pairs = [[value, key]]  # [premise, hypothesis]
        inputs = self._tokenizer(
            pairs, padding=True, truncation=True,
            max_length=512, return_tensors="pt",
        ).to(self._model.device)

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits
            probs = F.softmax(logits, dim=-1)

        prob = probs[0].tolist()
        label_dict = {
            self.LABEL_NAMES[j]: round(prob[j], 4) for j in range(3)
        }
        is_valid = (
            label_dict["entailment"] > label_dict["neutral"] and
            label_dict["entailment"] > label_dict["contradiction"]
        )
        return {"is_valid": is_valid, **label_dict}


# ==================== 全局单例 ====================

_NLI_INSTANCE = None

def get_nli_classifier(model_path: str = None) -> NLIClassifier:
    """获取 NLI 分类器单例（rag_core 和 agent 共享同一个模型实例）"""
    global _NLI_INSTANCE
    if _NLI_INSTANCE is None:
        _NLI_INSTANCE = NLIClassifier(model_path)
    return _NLI_INSTANCE


# ==================== CLI ====================

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="NLI 分类器测试工具")
    parser.add_argument("--query", type=str, required=True, help="查询文本")
    parser.add_argument("--docs", type=str, nargs="+", help="待分类文档")
    parser.add_argument("--model", type=str, default="", help="模型路径或 HuggingFace ID")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()

    if args.query and args.docs:
        from langchain_core.documents import Document
        docs = [Document(page_content=d) for d in args.docs]

        clf = NLIClassifier(args.model or None)
        results = clf.classify(args.query, docs)

        if args.json:
            output = []
            for r in results:
                output.append({
                    "content": r["doc"].page_content[:100] if hasattr(r["doc"], "page_content") else str(r["doc"])[:100],
                    "labels": {k: v for k, v in r.items() if k != "doc"},
                })
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(f"NLI 分类结果 (model: {clf.model_path}):")
            for i, r in enumerate(results):
                text = (r["doc"].page_content[:80] if hasattr(r["doc"], "page_content") else str(r["doc"])[:80])
                max_label = max(["entailment", "neutral", "contradiction"], key=lambda k: r.get(k, 0))
                conf = r.get(max_label, 0)
                print(f"  #{i + 1} [{max_label}, {conf:.1%}] {text}...")
    else:
        parser.print_help()
