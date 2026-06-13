# 接口契约

> 前端 Mock 和后端实现的唯一对齐依据。任何变更必须同步更新本文件。

## 通用约定

### 统一响应格式

成功：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

错误：

```json
{
  "code": 400,
  "message": "参数错误",
  "data": null
}
```

分页：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

### HTTP 状态码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 业务规则校验失败 |
| 500 | 服务器内部错误 |

### 枚举

```json
{
  "session_source": ["client", "admin"],
  "message_role": ["user", "assistant", "system"],
  "trace_status": ["pending", "running", "success", "failed"],
  "sub_agent": ["hotspot_agent", "data_agent", "stock_agent", "chit_chat", "clarification"],
  "risk_level": ["low", "medium", "high"],
  "quality_result": ["PASS", "FAIL"],
  "rich_block_type": ["text", "stock_card", "metric_table", "ranking_table", "citation_list", "risk_notice", "calculator", "trace_summary"],
  "source_type": ["announcement", "report", "financial", "market", "qa", "knowledge"]
}
```

---

## 数据模型

### Session

```json
{
  "id": "sess_20260608_001",
  "title": "今天涨幅靠前的半导体股票有哪些",
  "title_source": "first_query",
  "is_draft": false,
  "source": "client",
  "created_at": "2026-06-08T14:05:00+08:00",
  "updated_at": "2026-06-08T14:05:12+08:00",
  "last_message_preview": "今日半导体板块涨幅靠前的个股如下",
  "last_trace_id": "trace_20260608_001"
}
```

### Message

```json
{
  "id": "msg_001",
  "session_id": "sess_20260608_001",
  "role": "assistant",
  "content": "今日半导体板块涨幅靠前的个股如下。",
  "rich_blocks": [],
  "trace_id": "trace_20260608_001",
  "created_at": "2026-06-08T14:05:12+08:00"
}
```

### RichBlock

```json
{
  "id": "block_001",
  "type": "ranking_table",
  "title": "半导体板块涨幅排行",
  "payload": {},
  "sources": [],
  "risk_notice": "以上数据来自本地模拟数据，仅用于产品验证，不构成投资建议。"
}
```

### Trace

```json
{
  "id": "trace_20260608_001",
  "session_id": "sess_20260608_001",
  "message_id": "msg_002",
  "user_query": "今天涨幅靠前的半导体股票有哪些",
  "status": "success",
  "steps": [],
  "metadata": {
    "total_latency_ms": 2240,
    "tool_calls_count": 1,
    "quality_check_result": "PASS",
    "model_versions": {
      "master_bot": "mock-master",
      "data_agent": "mock-data-agent"
    }
  }
}
```

### TraceStep

```json
{
  "step_id": "step_002",
  "step_index": 2,
  "name": "意图与槽位",
  "node": "master_bot_intent_recognition",
  "status": "success",
  "latency_ms": 278,
  "summary": "意图：数据查询；主体：半导体；动作：排名。",
  "detail_sections": [
    {
      "title": "槽位",
      "items": [
        {"label": "subject", "value": "半导体"},
        {"label": "metric", "value": "涨跌幅"}
      ]
    }
  ],
  "input": {"query": "今天涨幅靠前的半导体股票有哪些"},
  "output": {"sub_agent": "data_agent"},
  "raw_json": {"node": "master_bot_intent_recognition"},
  "error": null
}
```

### TraceStep.raw_json（`rag_retrieval` 节点）

RAG 检索节点 `node=rag_retrieval` 的 `raw_json` 除 `rag_hits` 外，还应包含 Rerank 可观测字段：

```json
{
  "node": "rag_retrieval",
  "rag_hits": [
    {
      "chunk_id": "chunk_300750_q1_001",
      "doc_id": "q1_300750_2026",
      "title": "宁德时代 2026 年第一季度报告",
      "source_type": "financial",
      "path": "financials/300750-ningdeshidai-financial-2025A-2026Q1.md",
      "score": 0.8152,
      "snippet": "一、主要财务数据…",
      "relevance_reason": "rerank 命中 0.82，章节「2026 年第一季度报告」",
      "retrieval_mode": "rerank"
    }
  ],
  "embedding_connected": true,
  "rerank_connected": true,
  "rerank_before": [
    {
      "chunk_id": "chunk_hotspot_001",
      "title": "2026 年 6 月市场热点",
      "score": 0.9012
    },
    {
      "chunk_id": "chunk_300750_q1_001",
      "title": "宁德时代 2026 年第一季度报告",
      "score": 0.8744
    }
  ],
  "rerank_after": [
    {
      "chunk_id": "chunk_300750_q1_001",
      "title": "宁德时代 2026 年第一季度报告",
      "score": 0.9521
    },
    {
      "chunk_id": "chunk_hotspot_001",
      "title": "2026 年 6 月市场热点",
      "score": 0.7103
    }
  ],
  "mode": "hybrid",
  "index_chunk_count": 2510,
  "latency_ms": 186,
  "model": "Qwen/Qwen3-Embedding-8B"
}
```

`rerank_before[].score` 为 hybrid 候选分；`rerank_after[].score` 为 Rerank 模型分。Rerank 失败降级时 `rerank_connected=false`，`rerank_before` 仍保留候选，`rerank_after` 为空。

---

## 接口清单

### GET /api/health

**用途：** 后端健康检查。

**请求参数：** 无。

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "ok",
    "service": "smart-investment-research-api",
    "timestamp": "2026-06-08T14:05:00+08:00"
  }
}
```

**响应（失败 500）：**

```json
{
  "code": 500,
  "message": "服务不可用",
  "data": null
}
```

---

### GET /api/sessions

**用途：** 获取会话历史列表，支持关键词过滤。

**Query 参数：**

```json
{
  "keyword": "半导体",
  "page": 1,
  "page_size": 20
}
```

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "sess_20260608_001",
        "title": "今天涨幅靠前的半导体股票有哪些",
        "title_source": "first_query",
        "is_draft": false,
        "source": "client",
        "created_at": "2026-06-08T14:05:00+08:00",
        "updated_at": "2026-06-08T14:05:12+08:00",
        "last_message_preview": "今日半导体板块涨幅靠前的个股如下",
        "last_trace_id": "trace_20260608_001"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

**响应（失败 400）：**

```json
{
  "code": 400,
  "message": "page_size 必须在 1 到 100 之间",
  "data": null
}
```

---

### POST /api/sessions

**用途：** 新建草稿会话。发送首条 Query 前标题显示为“新对话”。

**请求体：**

```json
{
  "source": "client"
}
```

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "sess_20260608_002",
    "title": "新对话",
    "title_source": "system",
    "is_draft": true,
    "source": "client",
    "created_at": "2026-06-08T14:10:00+08:00",
    "updated_at": "2026-06-08T14:10:00+08:00",
    "last_message_preview": "",
    "last_trace_id": null
  }
}
```

**响应（失败 400）：**

```json
{
  "code": 400,
  "message": "source 必须为 client 或 admin",
  "data": null
}
```

---

### GET /api/sessions/{session_id}

**用途：** 获取会话详情与消息列表。

**路径参数：**

```json
{
  "session_id": "sess_20260608_001"
}
```

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "session": {
      "id": "sess_20260608_001",
      "title": "今天涨幅靠前的半导体股票有哪些",
      "title_source": "first_query",
      "is_draft": false,
      "source": "client",
      "created_at": "2026-06-08T14:05:00+08:00",
      "updated_at": "2026-06-08T14:05:12+08:00",
      "last_message_preview": "今日半导体板块涨幅靠前的个股如下",
      "last_trace_id": "trace_20260608_001"
    },
    "messages": [
      {
        "id": "msg_001",
        "session_id": "sess_20260608_001",
        "role": "user",
        "content": "今天涨幅靠前的半导体股票有哪些？",
        "rich_blocks": [],
        "trace_id": null,
        "created_at": "2026-06-08T14:05:00+08:00"
      },
      {
        "id": "msg_002",
        "session_id": "sess_20260608_001",
        "role": "assistant",
        "content": "今日半导体板块涨幅靠前的个股如下。",
        "rich_blocks": [
          {
            "id": "block_001",
            "type": "ranking_table",
            "title": "半导体板块涨幅排行",
            "payload": {
              "columns": ["排名", "股票名称", "代码", "涨跌幅", "现价", "成交额"],
              "rows": [
                {"rank": 1, "name": "寒武纪", "code": "688256", "change_pct": "+8.76%", "price": "287.50", "turnover": "42.1亿"}
              ]
            },
            "sources": [
              {"type": "market", "label": "本地行情模拟数据", "time": "2026-06-08 14:05"}
            ],
            "risk_notice": "以上数据来自本地模拟数据，仅用于产品验证，不构成投资建议。"
          }
        ],
        "trace_id": "trace_20260608_001",
        "created_at": "2026-06-08T14:05:12+08:00"
      }
    ]
  }
}
```

**响应（失败 404）：**

```json
{
  "code": 404,
  "message": "会话不存在",
  "data": null
}
```

---

### DELETE /api/sessions/{session_id}

**用途：** 删除指定会话及其消息、Trace 关联记录。用于会话历史行右侧“更多操作 -> 删除”。

**路径参数：**

```json
{
  "session_id": "sess_20260608_001"
}
```

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "sess_20260608_001",
    "deleted": true
  }
}
```

**响应（失败 404）：**

```json
{
  "code": 404,
  "message": "会话不存在",
  "data": null
}
```

---

### POST /api/chat/query

**用途：** 发送用户 Query，返回助手消息、富响应和 Trace。若目标会话为草稿会话，后端必须将标题替换为首条 Query。

**请求体：**

```json
{
  "session_id": "sess_20260608_002",
  "source": "client",
  "query": "15元买入未来预期回报率怎么算"
}
```

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "session": {
      "id": "sess_20260608_002",
      "title": "15元买入未来预期回报率怎么算",
      "title_source": "first_query",
      "is_draft": false,
      "source": "client",
      "created_at": "2026-06-08T14:10:00+08:00",
      "updated_at": "2026-06-08T14:10:18+08:00",
      "last_message_preview": "已生成可交互测算组件",
      "last_trace_id": "trace_20260608_002"
    },
    "user_message": {
      "id": "msg_003",
      "session_id": "sess_20260608_002",
      "role": "user",
      "content": "15元买入未来预期回报率怎么算",
      "rich_blocks": [],
      "trace_id": null,
      "created_at": "2026-06-08T14:10:18+08:00"
    },
    "assistant_message": {
      "id": "msg_004",
      "session_id": "sess_20260608_002",
      "role": "assistant",
      "content": "已生成可交互测算组件，你可以调整买入价、情景价和持仓数量。",
      "rich_blocks": [
        {
          "id": "block_002",
          "type": "calculator",
          "title": "收益率测算组件",
          "payload": {
            "fields": [
              {"key": "buy_price", "label": "买入价", "value": 15, "unit": "元"},
              {"key": "target_price", "label": "情景价", "value": 20, "unit": "元"},
              {"key": "share_count", "label": "持仓数量", "value": 1000, "unit": "股"},
              {"key": "fee_rate", "label": "估算费率", "value": 0.03, "unit": "%"}
            ],
            "results": [
              {"key": "return_rate", "label": "收益率", "value": "33.27%"},
              {"key": "profit_amount", "label": "预估盈亏", "value": "4991.50 元"},
              {"key": "cost_amount", "label": "测算成本", "value": "15000.00 元"}
            ]
          },
          "sources": [],
          "risk_notice": "测算结果仅基于用户输入参数，不构成投资建议。"
        }
      ],
      "trace_id": "trace_20260608_002",
      "created_at": "2026-06-08T14:10:19+08:00"
    },
    "trace": {
      "id": "trace_20260608_002",
      "status": "success",
      "metadata": {
        "total_latency_ms": 420,
        "tool_calls_count": 0,
        "quality_check_result": "PASS"
      }
    }
  }
}
```

**响应（失败 422）：**

```json
{
  "code": 422,
  "message": "query 不能为空",
  "data": null
}
```

---

### POST /api/chat/regenerate/stream

**用途：** 对已有助手回答重新生成。复用原用户问题，不新增 user 消息；删除旧 assistant 消息后以 SSE 流式返回新回答。

**请求体：**

```json
{
  "session_id": "sess_20260608_002",
  "assistant_message_id": "msg_004",
  "source": "client"
}
```

**SSE 事件序列（成功）：**

| event | data 说明 |
| --- | --- |
| `user_message` | 原 user 消息（`MessageRead`） |
| `session` | 更新后的会话（`SessionRead`） |
| `message_removed` | `{ "assistant_message_id": "msg_004" }` |
| `status` | `{ "phase": "...", "label": "..." }` |
| `content_delta` | `{ "delta": "..." }` |
| `content_done` | `{ "content": "..." }` |
| `rich_blocks` | `{ "rich_blocks": [...] }` |
| `done` | 与 `POST /api/chat/query` 成功响应 `data` 结构一致 |

**SSE 事件（失败）：**

| event | data 说明 |
| --- | --- |
| `error` | `{ "message": "...", "code": 404 \| 422 \| 502 \| 503 }` |

**错误码：**

- `404`：会话或消息不存在
- `422`：目标消息不是 assistant，或找不到配对 user 消息

---

### GET /api/traces/{trace_id}

**用途：** 获取完整 Trace。管理端右侧面板使用。

**路径参数：**

```json
{
  "trace_id": "trace_20260608_001"
}
```

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "trace_20260608_001",
    "session_id": "sess_20260608_001",
    "message_id": "msg_002",
    "user_query": "今天涨幅靠前的半导体股票有哪些",
    "status": "success",
    "steps": [
      {
        "step_id": "step_001",
        "step_index": 1,
        "name": "上下文预处理",
        "node": "master_bot_preprocessing",
        "status": "success",
        "latency_ms": 38,
        "summary": "加载会话摘要，本轮 Query 主体明确，无需指代消解。",
        "detail_sections": [
          {
            "title": "预处理结果",
            "items": [
              {"label": "输入", "value": "用户 Query 与最近 1 轮会话摘要"},
              {"label": "输出", "value": "无指代消解需求"},
              {"label": "状态", "value": "success，进入意图识别"}
            ]
          }
        ],
        "input": {"query": "今天涨幅靠前的半导体股票有哪些"},
        "output": {"pronoun_resolution": false},
        "raw_json": {
          "node": "master_bot_preprocessing",
          "latency_ms": 38,
          "pronoun_resolution": false
        },
        "error": null
      }
    ],
    "metadata": {
      "total_latency_ms": 2240,
      "tool_calls_count": 1,
      "quality_check_result": "PASS",
      "model_versions": {
        "master_bot": "mock-master",
        "data_agent": "mock-data-agent"
      }
    }
  }
}
```

**响应（失败 404）：**

```json
{
  "code": 404,
  "message": "Trace 不存在",
  "data": null
}
```

---

### GET /api/traces/{trace_id}/steps/{step_id}/raw

**用途：** 获取某个 Trace 节点完整 JSON。完整 JSON 弹窗使用。

**路径参数：**

```json
{
  "trace_id": "trace_20260608_001",
  "step_id": "step_002"
}
```

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "trace_id": "trace_20260608_001",
    "step_id": "step_002",
    "raw_json": {
      "node": "master_bot_intent_recognition",
      "latency_ms": 278,
      "routing_output": {
        "sub_agent": "data_agent",
        "intent_level_1": "行情查询",
        "intent_level_2": "板块行情查询"
      },
      "global_slots": {
        "subject_name": "半导体",
        "time_range": "今天",
        "action_type": "排名",
        "missing_slots": []
      }
    }
  }
}
```

**响应（失败 404）：**

```json
{
  "code": 404,
  "message": "Trace 节点不存在",
  "data": null
}
```

---

### GET /api/layout/preferences

**用途：** 读取会话历史列宽、Trace 面板宽度等布局偏好，用于刷新页面后恢复上次设置。

**请求参数：** 无。

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "sidebar_width": 288,
    "sidebar_width_range": {"min": 240, "max": 420},
    "trace_panel_width": 488,
    "trace_panel_width_range": {"min": 380, "max": 640},
    "updated_at": "2026-06-08T14:12:00+08:00"
  }
}
```

---

### PATCH /api/layout/preferences

**用途：** 保存会话历史列宽、Trace 面板宽度等布局偏好。

**请求体：**

```json
{
  "sidebar_width": 288,
  "trace_panel_width": 488
}
```

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "sidebar_width": 288,
    "sidebar_width_range": {"min": 240, "max": 420},
    "trace_panel_width": 488,
    "trace_panel_width_range": {"min": 380, "max": 640},
    "updated_at": "2026-06-08T14:12:00+08:00"
  }
}
```

**响应（失败 422）：**

```json
{
  "code": 422,
  "message": "sidebar_width 必须在 240 到 420 之间，trace_panel_width 必须在 380 到 640 之间",
  "data": null
}
```

---

### GET /api/data-sources/status

**用途：** 获取本地知识库 / Mock 数据说明页的数据状态。

**请求参数：** 无。

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "mock_data": [
      {"type": "market", "name": "行情数据", "path": "data/mock/market", "status": "ready", "sample_count": 20},
      {"type": "financial", "name": "财务数据", "path": "data/mock/financial", "status": "ready", "sample_count": 12},
      {"type": "report", "name": "研报数据", "path": "data/mock/reports", "status": "ready", "sample_count": 8},
      {"type": "announcement", "name": "公告数据", "path": "data/mock/announcements", "status": "ready", "sample_count": 10},
      {"type": "knowledge", "name": "投研知识库", "path": "data/knowledge-base", "status": "ready", "sample_count": 30}
    ],
    "rag": {
      "mode": "mock",
      "embedding_provider": "siliconflow-qwen",
      "rerank_provider": "siliconflow-qwen",
      "status": "mocked"
    }
  }
}
```

**响应（失败 500）：**

```json
{
  "code": 500,
  "message": "数据源状态读取失败",
  "data": null
}
```

---

### GET /api/config/status

**用途：** 获取模型、Prompt、合规规则配置状态。系统设置页使用，仅管理端展示。

**请求参数：** 无。

**响应（成功 200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "models": [
      {
        "name": "硅基流动 LLM / DeepSeek",
        "fields": ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"],
        "status": "mocked",
        "missing_fields": ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]
      },
      {
        "name": "硅基流动 Embedding / 千问",
        "fields": ["EMBEDDING_API_KEY", "EMBEDDING_BASE_URL", "EMBEDDING_MODEL", "EMBEDDING_DIM"],
        "status": "mocked",
        "missing_fields": ["EMBEDDING_API_KEY", "EMBEDDING_BASE_URL", "EMBEDDING_MODEL", "EMBEDDING_DIM"]
      },
      {
        "name": "硅基流动 Rerank / 千问",
        "fields": ["RERANK_API_KEY", "RERANK_BASE_URL", "RERANK_MODEL"],
        "status": "mocked",
        "missing_fields": ["RERANK_API_KEY", "RERANK_BASE_URL", "RERANK_MODEL"]
      }
    ],
    "prompts": [
      {"agent": "master_agent", "name": "总控 Agent", "status": "default"},
      {"agent": "hotspot_agent", "name": "热点助手", "status": "default"},
      {"agent": "data_agent", "name": "问数助手", "status": "default"},
      {"agent": "stock_agent", "name": "问股助手", "status": "default"},
      {"agent": "quality_check", "name": "质检模块", "status": "default"}
    ],
    "compliance_rules": {
      "blacklist_expressions": ["建议买入", "推荐", "值得关注", "重点关注", "逢低关注"],
      "risk_tip_required": true,
      "citation_required": true
    }
  }
}
```

**响应（失败 500）：**

```json
{
  "code": 500,
  "message": "配置状态读取失败",
  "data": null
}
```
