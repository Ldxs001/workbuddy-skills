"""
RAG Assistant 外部接入 API（端口 8767）
独立于 Web UI（8765）和 RAG 配置页（8766），专供外部系统调用。

设计原则：
- 纯增量，不碰 web_ui.py 任何代码
- 直接调 engine 内部已有函数，不改造任何内部逻辑
- 所有端点返回 {"success": bool, ...}
"""
import json
import os
import sys
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

# 确保 engine 在 sys.path
ENGINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine")
if ENGINE_PATH not in sys.path:
    sys.path.insert(0, ENGINE_PATH)


class ExternalAPIHandler(BaseHTTPRequestHandler):
    """外部 API 请求处理器"""

    # Agent 实例由 start_external_api 注入
    agent = None

    def log_message(self, format, *args):
        logger.info(f"[ExternalAPI] {self.address_string()} - {format % args}")

    # ═══════════════════════════════════════════════════
    # 通用工具
    # ═══════════════════════════════════════════════════

    def _send_json(self, data: dict, code: int = 200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _ok(self, **kw):
        kw["success"] = True
        self._send_json(kw)

    def _err(self, msg: str, code: int = 400, **kw):
        kw["success"] = False
        kw["error"] = msg
        self._send_json(kw, code)

    # ═══════════════════════════════════════════════════
    # 路由
    # ═══════════════════════════════════════════════════

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        try:
            if path == "/api/health":
                self._ok(status="running", version=self._get_version())

            elif path == "/api/feature/status":
                self._handle_feature_status()

            elif path == "/api/kb/list":
                self._handle_kb_list()

            elif path == "/api/kb/sources":
                kb = qs.get("kb", [""])[0]
                self._handle_kb_sources(kb)

            elif path == "/api/kb/backups":
                kb = qs.get("kb", [""])[0]
                self._handle_kb_backups(kb)

            elif path == "/api/kb/signatures":
                self._handle_signature_list()

            elif path == "/api/kb/hnsw-config":
                kb = qs.get("kb_name", [""])[0]
                self._handle_hnsw_config(kb)

            elif path == "/api/prompt/template":
                self._handle_prompt_template_get()

            elif path == "/api/prompt/slots":
                self._handle_prompt_slots_get()

            elif path == "/api/prompt/presets":
                self._handle_prompt_presets_get()

            elif path == "/api/prompt/system-prefix":
                self._handle_prompt_prefix_get()

            elif path == "/api/input/strategies":
                self._handle_strategies_get()

            else:
                self._err(f"未知 GET 路径: {path}", 404)

        except Exception as e:
            logger.exception(f"GET {path} 异常")
            self._err(str(e), 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            body = self._read_body()

            if path == "/api/feature/toggle":
                self._handle_feature_toggle(body)

            elif path == "/api/model/embed":
                self._handle_model_embed(body)

            elif path == "/api/model/rerank":
                self._handle_model_rerank(body)

            elif path == "/api/model/nli":
                self._handle_model_nli(body)

            elif path == "/api/kb/create":
                self._handle_kb_create(body)

            elif path == "/api/kb/delete":
                self._handle_kb_delete(body)

            elif path == "/api/kb/move":
                self._handle_kb_move(body)

            elif path == "/api/kb/backup":
                self._handle_kb_backup(body)

            elif path == "/api/kb/restore":
                self._handle_kb_restore(body)

            elif path == "/api/kb/signature/build":
                self._handle_signature_build(body)

            elif path == "/api/kb/hnsw-config":
                self._handle_hnsw_update(body)

            elif path == "/api/kb/rebuild-hnsw":
                self._handle_hnsw_rebuild(body)

            elif path == "/api/kb/signature/rebuild-all":
                self._handle_signature_rebuild_all()

            elif path == "/api/prompt/template":
                self._handle_prompt_template_set(body)

            elif path == "/api/prompt/template/reset":
                self._handle_prompt_template_reset()

            elif path == "/api/prompt/slots":
                self._handle_prompt_slots_set(body)

            elif path == "/api/prompt/preset":
                self._handle_prompt_preset_save(body)

            elif path == "/api/prompt/preset/delete":
                self._handle_prompt_preset_delete(body)

            elif path == "/api/prompt/preset/apply":
                self._handle_prompt_preset_apply(body)

            elif path == "/api/prompt/system-prefix":
                self._handle_prompt_prefix_set(body)

            elif path == "/api/input/split":
                self._handle_input_split(body)

            elif path == "/api/input/query-slices":
                self._handle_query_slices(body)

            # ── KB 查询（结构化写手用） ──
            elif path == "/api/kb/query":
                self._handle_kb_query(body)

            else:
                self._err(f"未知 POST 路径: {path}", 404)

        except json.JSONDecodeError:
            self._err("请求体 JSON 解析失败", 400)
        except Exception as e:
            logger.exception(f"POST {path} 异常")
            self._err(str(e), 500)

    # ═══════════════════════════════════════════════════
    # 1. 功能开关
    # ═══════════════════════════════════════════════════

    def _get_version(self) -> str:
        try:
            from rag_assistant import __version__
            return __version__
        except Exception:
            return "unknown"

    def _handle_feature_status(self):
        from config import load_config
        cfg = load_config()
        self._ok(
            router=cfg.get("router", {}).get("enabled", True),
            reranker=cfg.get("reranker", {}).get("enabled", True),
            nli=cfg.get("nli", {}).get("enabled", False),
            web_search=cfg.get("web_search_enabled", False),
            auto_classify=cfg.get("kb", {}).get("auto_classify", False),
            geek_mode=cfg.get("geek_mode", {}).get("edit_enabled", False),
        )

    def _handle_feature_toggle(self, body: dict):
        """运行态切换功能开关，持久化到 config.json"""
        from config import load_config, save_config

        toggles = body.get("toggles", {})
        if not toggles:
            self._err("缺少 toggles 字段")
            return

        cfg = load_config()
        changed = []

        feature_map = {
            "router":       ("router", "enabled"),
            "reranker":     ("reranker", "enabled"),
            "nli":          ("nli", "enabled"),
            "web_search":   (None, "web_search_enabled"),      # 顶层键
            "auto_classify": ("kb", "auto_classify"),
            "geek_mode":    ("geek_mode", "edit_enabled"),
        }

        for feature, enabled in toggles.items():
            if feature not in feature_map:
                self._err(f"未知功能名: {feature}，可选: {list(feature_map.keys())}")
                return
            section, key = feature_map[feature]
            if section is None:
                cfg[key] = bool(enabled)
            else:
                if section not in cfg:
                    cfg[section] = {}
                cfg[section][key] = bool(enabled)
            changed.append(f"{feature}={'on' if enabled else 'off'}")

        save_config(cfg)
        self._ok(changed=changed)

    # ═══════════════════════════════════════════════════
    # 2. 模型直接调用
    # ═══════════════════════════════════════════════════

    def _handle_model_embed(self, body: dict):
        """直接调用嵌入模型，返回向量"""
        texts = body.get("texts") or [body.get("text", "")]
        if not texts or not texts[0]:
            self._err("缺少 texts 或 text 字段")
            return

        from rag_core import get_embeddings
        emb = get_embeddings()
        if emb is None:
            self._err("嵌入模型未加载")
            return

        vectors = []
        for t in texts:
            v = emb.embed_query(t)
            vectors.append(v)

        dim = len(vectors[0]) if vectors else 0
        self._ok(vectors=vectors, dimension=dim, count=len(vectors))

    def _handle_model_rerank(self, body: dict):
        """直接调用 Reranker 对文档列表精排"""
        query = body.get("query", "")
        docs = body.get("docs", [])
        top_k = body.get("top_k")

        if not query:
            self._err("缺少 query 字段")
            return
        if not docs:
            self._err("缺少 docs 字段")
            return

        from config import load_config
        from reranker import Reranker
        from utils import Document

        cfg = load_config()
        reranker = Reranker(cfg)

        # 接受字符串列表或 {content, metadata} 对象列表
        doc_objs = []
        for d in docs:
            if isinstance(d, str):
                doc_objs.append(Document(page_content=d))
            elif isinstance(d, dict):
                doc_objs.append(Document(page_content=d.get("content", ""),
                                         metadata=d.get("metadata", {})))
            else:
                doc_objs.append(d)

        reranked = reranker.rerank(query, doc_objs, top_k=top_k)
        result = []
        for doc, score in reranked:
            result.append({
                "content": doc.page_content[:500],
                "metadata": doc.metadata if hasattr(doc, "metadata") else {},
                "score": float(score) if score is not None else 0.0,
            })

        self._ok(reranked=result, count=len(result))

    def _handle_model_nli(self, body: dict):
        """直接调用 NLI 三向分类器"""
        query = body.get("query", "")
        docs = body.get("docs", [])
        top_k = body.get("top_k", 0)

        if not query:
            self._err("缺少 query 字段")
            return
        if not docs:
            self._err("缺少 docs 字段")
            return

        from nli_classifier import get_nli_classifier
        from utils import Document

        classifier = get_nli_classifier()
        if classifier is None:
            self._err("NLI 模型未加载")
            return

        doc_objs = []
        for d in docs:
            if isinstance(d, str):
                doc_objs.append(Document(page_content=d))
            elif isinstance(d, dict):
                doc_objs.append(Document(page_content=d.get("content", ""),
                                         metadata=d.get("metadata", {})))
            else:
                doc_objs.append(d)

        results = classifier.classify(query, doc_objs, top_k=top_k)
        output = []
        for r in results:
            output.append({
                "content": r.get("doc").page_content[:500] if hasattr(r.get("doc"), "page_content") else str(r.get("doc", ""))[:500],
                "label": r.get("label", ""),
                "scores": r.get("scores", {}),
            })

        self._ok(results=output, count=len(output))

    # ═══════════════════════════════════════════════════
    # 3. KB 管理
    # ═══════════════════════════════════════════════════

    def _handle_kb_list(self):
        from knowledge_base_manager import list_knowledge_bases, get_kb_stats
        kbs = list_knowledge_bases()
        stats = get_kb_stats()
        self._ok(kbs=kbs, stats=stats)

    def _handle_kb_create(self, body: dict):
        from knowledge_base_manager import create_knowledge_base
        name = body.get("name", "")
        description = body.get("description", "")
        model_id = body.get("model_id", "")
        if not name:
            self._err("缺少 name 字段")
            return
        ok, msg = create_knowledge_base(name, description, model_id)
        if ok:
            self._ok(message=msg, kb=name)
        else:
            self._err(msg)

    def _handle_kb_delete(self, body: dict):
        from knowledge_base_manager import delete_knowledge_base
        name = body.get("name", "")
        if not name:
            self._err("缺少 name 字段")
            return
        ok, msg = delete_knowledge_base(name)
        if ok:
            self._ok(message=msg)
        else:
            self._err(msg)

    def _handle_kb_sources(self, kb: str):
        from knowledge_base_manager import list_kb_sources
        if not kb:
            self._err("缺少 kb 参数")
            return
        sources = list_kb_sources(kb)
        self._ok(sources=sources, kb=kb)

    def _handle_kb_move(self, body: dict):
        from knowledge_base_manager import move_kb_documents
        src = body.get("src_kb", "")
        tgt = body.get("target_kb", "")
        sources = body.get("sources", [])
        if not src or not tgt:
            self._err("缺少 src_kb 或 target_kb 字段")
            return
        if not sources:
            self._err("缺少 sources 字段")
            return
        ok, msg = move_kb_documents(src, tgt, sources)
        if ok:
            self._ok(message=msg)
        else:
            self._err(msg)

    def _handle_kb_backup(self, body: dict):
        from knowledge_base_manager import manual_backup_kb
        kb = body.get("kb", "")
        if not kb:
            self._err("缺少 kb 字段")
            return
        ok, msg, path = manual_backup_kb(kb)
        if ok:
            self._ok(message=msg, backup_path=path)
        else:
            self._err(msg)

    def _handle_kb_backups(self, kb: str):
        from knowledge_base_manager import list_kb_backups
        if not kb:
            self._err("缺少 kb 参数")
            return
        backups = list_kb_backups(kb)
        self._ok(backups=backups, kb=kb)

    def _handle_kb_restore(self, body: dict):
        from knowledge_base_manager import restore_kb_backup
        kb = body.get("kb", "")
        backup_name = body.get("backup_name", "")
        if not kb or not backup_name:
            self._err("缺少 kb 或 backup_name 字段")
            return
        ok, msg = restore_kb_backup(kb, backup_name)
        if ok:
            self._ok(message=msg)
        else:
            self._err(msg)

    # ── HNSW 管理 ─────────────────────────────────

    def _handle_hnsw_config(self, kb: str):
        """GET: 查询 KB 的 HNSW 配置"""
        from knowledge_base_manager import get_kb_hnsw_config
        if not kb:
            self._err("缺少 kb 参数")
            return
        cfg = get_kb_hnsw_config(kb)
        self._ok(kb=kb, **cfg)

    def _handle_hnsw_update(self, body: dict):
        """POST: 更新 HNSW 配置（M/自动重建）"""
        from knowledge_base_manager import set_kb_hnsw_config
        kb = body.get("kb_name", "")
        if not kb:
            self._err("缺少 kb_name 字段")
            return
        hnsw_m = body.get("hnsw_m")
        auto_rebuild = body.get("auto_rebuild_hnsw")
        ok, msg, rebuilt = set_kb_hnsw_config(kb, hnsw_m=hnsw_m, auto_rebuild_hnsw=auto_rebuild)
        if ok:
            self._ok(message=msg, rebuilt=rebuilt, kb=kb)
        else:
            self._err(msg)

    def _handle_hnsw_rebuild(self, body: dict):
        """POST: 手动触发 HNSW 重建"""
        from knowledge_base_manager import rebuild_kb_hnsw
        kb = body.get("kb_name", "")
        if not kb:
            self._err("缺少 kb_name 字段")
            return
        ok, msg = rebuild_kb_hnsw(kb)
        if ok:
            self._ok(message=msg, kb=kb)
        else:
            self._err(msg)

    # ═══════════════════════════════════════════════════
    # 4. KB 签名管理
    # ═══════════════════════════════════════════════════

    def _handle_signature_list(self):
        from router import list_kb_signatures
        sigs = list_kb_signatures()
        self._ok(signatures=sigs)

    def _handle_signature_build(self, body: dict):
        from router import build_kb_signature
        kb = body.get("kb", "")
        if not kb:
            self._err("缺少 kb 字段")
            return
        sig = build_kb_signature(kb)
        self._ok(signature=sig, kb=kb)

    def _handle_signature_rebuild_all(self):
        from router import rebuild_all_signatures
        rebuild_all_signatures()
        self._ok(message="所有 KB 签名已重建")

    # ═══════════════════════════════════════════════════
    # 5. 提示词管理
    # ═══════════════════════════════════════════════════

    def _handle_prompt_template_get(self):
        from prompt_manager import load_template, get_template_path
        content = load_template()
        path = get_template_path()
        self._ok(template=content, template_path=path)

    def _handle_prompt_template_set(self, body: dict):
        from prompt_manager import save_template
        content = body.get("content", "")
        if not content:
            self._err("缺少 content 字段")
            return
        save_template(content)
        self._ok(message="模板已保存")

    def _handle_prompt_template_reset(self):
        from prompt_manager import reset_template
        reset_template()
        self._ok(message="模板已重置为默认")

    def _handle_prompt_slots_get(self):
        from prompt_manager import load_slots
        slots = load_slots()
        self._ok(slots=slots)

    def _handle_prompt_slots_set(self, body: dict):
        from prompt_manager import save_slots
        slots = body.get("slots", {})
        if not slots:
            self._err("缺少 slots 字段")
            return
        save_slots(slots)
        self._ok(message="插槽已保存")

    def _handle_prompt_presets_get(self):
        from prompt_manager import get_all_presets, get_selected_preset
        presets = get_all_presets()
        selected = get_selected_preset()
        self._ok(presets=presets, selected=selected)

    def _handle_prompt_preset_save(self, body: dict):
        from prompt_manager import save_custom_preset
        label = body.get("label", "")
        slots = body.get("slots", {})
        description = body.get("description", "")
        if not label:
            self._err("缺少 label 字段")
            return
        result = save_custom_preset(label, slots, description)
        self._ok(**result)

    def _handle_prompt_preset_delete(self, body: dict):
        from prompt_manager import delete_custom_preset
        key = body.get("key", "")
        if not key:
            self._err("缺少 key 字段")
            return
        result = delete_custom_preset(key)
        self._ok(**result)

    def _handle_prompt_preset_apply(self, body: dict):
        from prompt_manager import apply_preset
        key = body.get("key", "")
        if not key:
            self._err("缺少 key 字段")
            return
        ok = apply_preset(key)
        if ok:
            self._ok(message=f"预设 {key} 已应用")
        else:
            self._err(f"预设 {key} 不存在")

    def _handle_prompt_prefix_get(self):
        from prompt_manager import get_system_prefix
        prefix = get_system_prefix()
        self._ok(system_prefix=prefix)

    def _handle_prompt_prefix_set(self, body: dict):
        from prompt_manager import set_system_prefix
        prefix = body.get("prefix", "")
        set_system_prefix(prefix)
        self._ok(message="系统前缀已更新")

    # ── KB 查询（结构化写手外部调用） ──

    def _handle_kb_query(self, body: dict):
        """检索知识库返回上下文，不调 LLM 生成回答"""
        query = body.get("query", "")
        kb = body.get("kb", "")        # 空=自动路由
        top_k = body.get("top_k", 5)
        score_threshold = body.get("score_threshold")
        include_header = body.get("include_header", False)

        if not query:
            self._err("缺少 query 字段")
            return

        if self.agent is None or not hasattr(self.agent, 'rag'):
            self._err("RAG 模块未就绪", 500)
            return

        try:
            result = self.agent.rag.query(
                question=query,
                kb_name=kb or None,    # None=交给路由器
                k=top_k,
                score_threshold=score_threshold,
                include_header=include_header,
            )
            resp = {
                "context": result.get("context", ""),
                "sources": result.get("docs", []),
                "has_context": result.get("has_context", False),
                "kb": result.get("kb", kb),
            }
            if include_header and result.get("headers"):
                resp["headers"] = result["headers"]
            self._ok(**resp)
        except Exception as e:
            logger.exception(f"/api/kb/query 异常")
            self._err(str(e), 500)

    # ═══════════════════════════════════════════════════
    # 6. 输入管理（文本切分 + 问题切片）
    # ═══════════════════════════════════════════════════

    def _handle_strategies_get(self):
        from text_splitter import get_all_strategies_info, get_all_guards_info
        strategies = get_all_strategies_info()
        guards = get_all_guards_info()
        self._ok(strategies=strategies, guards=guards)

    def _handle_input_split(self, body: dict):
        """文本切分接口"""
        text = body.get("text", "")
        if not text:
            self._err("缺少 text 字段")
            return

        from config import load_config
        cfg = load_config()
        split_cfg = cfg.get("splitting", {})

        primary = body.get("strategy", split_cfg.get("strategy", "recursive"))
        secondary = body.get("secondary", split_cfg.get("secondary_strategy"))
        chunk_size = body.get("chunk_size", split_cfg.get("chunk_size", 500))
        chunk_overlap = body.get("chunk_overlap", split_cfg.get("chunk_overlap", 50))
        guards = body.get("guards", split_cfg.get("guards", []))
        separators = body.get("separators", split_cfg.get("separators"))

        from text_splitter import split_pipeline
        kwargs = {}
        if separators:
            kwargs["separators"] = separators

        chunks = split_pipeline(
            text,
            guards=guards,
            primary=primary,
            secondary=secondary,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            **kwargs,
        )

        # chunks 是 Document 列表
        result = []
        for c in chunks:
            if hasattr(c, "page_content"):
                result.append({
                    "content": c.page_content,
                    "metadata": c.metadata if hasattr(c, "metadata") else {},
                    "length": len(c.page_content),
                })
            else:
                result.append({"content": str(c), "metadata": {}, "length": len(str(c))})

        self._ok(chunks=result, count=len(result), strategy=primary,
                 chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def _handle_query_slices(self, body: dict):
        """问题组合切片展开（entities x attrs 穷举）"""
        entities = body.get("entities", "")
        attrs = body.get("attrs", "")
        rel = body.get("rel", "")

        if not entities and not attrs:
            self._err("缺少 entities 或 attrs 字段")
            return

        import re
        import itertools

        entity_list = [e.strip() for e in re.split(r'[,，]', entities) if e.strip()]
        attr_list = [a.strip() for a in re.split(r'[,，]', attrs) if a.strip()]

        # 过滤比较意图词和疑问词
        if rel:
            _compare_kw = {"异同", "区别", "差别", "对比", "共同点", "不同点", "异同点", "差异"}
            attr_list = [a for a in attr_list if a not in _compare_kw]
        _question_words = {"为什么", "怎么", "如何", "怎样", "怎么样", "是什么", "什么是"}
        attr_list = [a for a in attr_list if a not in _question_words]

        _slices = set()
        # 第一层：entity 单独
        for e in entity_list:
            _slices.add(e)
        # 第二层：entity x attr
        for e in entity_list:
            for a in attr_list:
                _slices.add(f"{e} {a}")
        # 第三层：rel 语义
        if rel:
            if len(entity_list) >= 2:
                for e1, e2 in itertools.combinations(entity_list, 2):
                    _slices.add(f"{e1} {e2} {rel}")
                    for a in attr_list:
                        _slices.add(f"{e1} {e2} {a} {rel}")
            else:
                e = entity_list[0] if entity_list else ""
                for a1, a2 in itertools.combinations(attr_list, 2):
                    _slices.add(f"{e} {a1} {a2} {rel}")

        slices = list(_slices)
        self._ok(slices=slices, count=len(slices),
                 entities=entity_list, attrs=attr_list, rel=rel)


def start_external_api(agent, port: int = 8767, host: str = "0.0.0.0"):
    """启动外部 API 服务"""
    ExternalAPIHandler.agent = agent

    # 确保 engine 模块可导入
    engine_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine")
    if engine_path not in sys.path:
        sys.path.insert(0, engine_path)

    server = HTTPServer((host, port), ExternalAPIHandler)
    logger.info(f"外部 API 服务启动: http://{host}:{port}")
    print(f"  外部 API (External API): http://{host}:{port}")
    print(f"  端点文档: EXTERNAL_API.md")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("外部 API 服务已停止")
        server.server_close()
