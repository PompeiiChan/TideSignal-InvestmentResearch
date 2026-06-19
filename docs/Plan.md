# 开发计划

> 设计阶段与开发阶段的衔接文件。所有开发进度以本文件为准。

## 进度总览（2026-06-11 更新）

| 阶段 | 范围 | 任务 | 状态 |
|------|------|------|------|
| MVP | 前端页面 + 后端 API + fallback 演示链路 | T-001～T-008 | ✅ 已完成（8/8） |
| V1.1 | 硅基流动 LLM / Embedding / Rerank + 本地 Markdown 知识库 + LangGraph 真实编排 | T-009～T-013（待 Planner 写入 tasks.json） | ⏳ 前置就绪，待开发 |

**当前焦点**：V1.1 真实 AI / RAG / Agent 接入。

**V1.1 前置门禁**：

| 项 | 状态 |
|----|------|
| 硅基流动 Key（`backend/.env`） | ✅ 已配置 |
| 本地知识库 Markdown（`backend/data/knowledge-base/`） | ✅ 已就位（36 文件） |
| LangGraph 流转图（`docs/agent/langgraph-flow.md`） | ✅ 已提供 |

---

## 一、功能清单总览

### MVP 功能（已完成）

| 序号 | 功能名称 | 一句话描述 | 对应页面 | 优先级 | 状态 |
|------|----------|------------|----------|--------|------|
| F01 | 客户端对话页 | 面向散户 / 投顾的投研问答入口 | P01 | MVP | 已完成 |
| F02 | 管理端可观测页 | 同步会话并展示右侧 Trace 链路 | P02 | MVP | 已完成 |
| F03 | 会话历史视图 | 支持历史搜索、新建、切换、删除、拖拽调宽 | P03 | MVP | 已完成 |
| F04 | Trace 详情面板 | 摘要、内联展开、完整 JSON、拖拽调宽 | P04 | MVP | 已完成 |
| F05 | 本地知识库 / Mock 数据说明 | 展示本地模拟数据与 RAG 状态 | P05 | MVP | 已完成（fallback） |
| F06 | 系统设置页 | 管理端展示模型、Prompt、合规规则状态 | P06 | MVP | 已完成 |
| F07 | 富响应组件 | 表格、个股卡、热点摘要、引用、风险提示 | P01 / P02 | MVP | 已完成 |
| F08 | 交互式测算组件 | 输入参数后实时计算收益率和盈亏 | P01 / P02 | MVP | 已完成 |
| F09 | 后端基础设施 | FastAPI + PyCore 健康检查和统一响应 | 全局 | MVP | 已完成 |
| F10 | 会话与消息 API | 会话、消息、标题生成、历史搜索 | P01 / P02 / P03 | MVP | 已完成 |
| F11 | Trace API | Trace 列表、节点详情、完整 JSON | P02 / P04 | MVP | 已完成 |
| F12 | 配置与数据源 API | 数据源状态、模型配置、Prompt、合规规则 | P05 / P06 | MVP | 已完成 |

### V1.1 功能（下一阶段）

| 序号 | 功能名称 | 一句话描述 | 依赖 | 优先级 | 状态 |
|------|----------|------------|------|--------|------|
| F13 | 硅基流动 LLM 真实调用 | 意图识别、回答生成、质检走真实 DeepSeek | 用户已配 Key | V1.1 | 待开发 |
| F14 | Embedding 向量检索 | 对本地 Markdown 知识库做语义召回 | F13、知识库目录就绪 | V1.1 | 待开发 |
| F15 | Rerank 重排 | 对 RAG 召回结果重排 | F14 | V1.1 | 待开发 |
| F16 | 本地 Markdown 知识库真实检索 | 热点 / 财报 / 行业研报 / 公司研报 RAG | 知识库已就位 | V1.1 | 待开发 |
| F17 | LangGraph 真实编排 | 替换 fallback Trace，按流转图执行 Agent | 流转图 + F13～F16 | V1.1 | 待开发 |

### V1.2+  backlog（V1.1 之后，不阻塞当前迭代）

> **工具数据丰富度（当前迭代）**：见 [`docs/agent/tool-richness-roadmap.md`](agent/tool-richness-roadmap.md)。  
> **当前活动**：工具丰富度路线图 **T-020～T-024 已全部验收**（2026-06-19）。下一迭代见 [`tool-richness-roadmap.md`](agent/tool-richness-roadmap.md) §二 backlog 或 `docs/Plan.md` V1.2+。

| 序号 | 功能名称 | 一句话描述 | 依赖 | 优先级 | 状态 |
|------|----------|------------|------|--------|------|
| F18 | Query 改写（`query_rewrite`） | 将用户口语 / 多轮指代转为检索友好 `retrieval_query`，提升 RAG 召回 | F17、F19、F20 | V1.2+ | **延后**（T-014） |
| F19 | 槽位 schema 与多轮澄清闭环 | 按意图必填槽位表、会话级 `pending_slots` 继承、单槽位置信度阈值 | F17、F20 | V1.2+ | 规划中（T-016） |
| F20 | 短期对话记忆（5 轮 QA） | 同一会话保留最近 5 轮 QA 上下文，注入意图/槽位/回答组装；长期记忆仍 V2+ 延后 | F17 | V1.2+ | 规划中（T-015、T-017） |

---

## 二、数据契约摘要

完整数据契约见 `docs/PRD.md`「数据契约确认清单」章节。统一响应格式与接口契约见 `docs/api-contracts.md`，该文件是前后端接口对齐的唯一权威源。

## 二点五、外部服务与测试权限清单

> 开发硬门禁：真实 Key / Token / Secret 不写入本文档或任何 `docs/**`、`.sdd/**` 可读产物，只记录字段名、用途和配置状态；真实值只能进入 `.env` 等配置文件。

| 服务 | 用途 | 配置项字段 | V1.1 必需 | Tester 完整联调权限 | 缺失时策略 | 状态 |
|------|------|------------|-----------|--------------------|------------|------|
| 硅基流动 LLM / DeepSeek | 意图识别、回答生成、质检 | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | 是 | 测试 Key + 可调用额度 | MVP 已用 fallback；V1.1 必须真实调用 | **已配置**（`backend/.env`） |
| 硅基流动 Embedding / 千问 | 本地知识库向量化与语义检索 | `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` | 是 | 测试 Key + 可调用额度 | MVP 模拟 RAG 命中 | **已配置**（`backend/.env`） |
| 硅基流动 Rerank / 千问 | RAG 召回结果重排 | `RERANK_API_KEY`, `RERANK_BASE_URL`, `RERANK_MODEL` | 是 | 测试 Key + 可调用额度 | MVP 静态排序 | **已配置**（`backend/.env`） |
| 本地 Markdown 知识库 | 热点、财报、研报、清单与结构化 RAG | `LOCAL_KB_PATH` | 是 | 本地目录 + 可读 `.md` 文件 | MVP 用示例路径占位 | **已就位**（`backend/data/knowledge-base/`，36 文件） |
| 本地 Mock 行情 / 财务 / 公告 / 宏观数据 | 问数、问股、热点工具调用 | `MOCK_DATA_PATH` | MVP 是 | 本地文件路径 | 内置示例 Mock 数据 | 已确认 |
| LangGraph | 后端 Agent 编排 | `LANGGRAPH_ENV` 等 | 是 | 本地依赖 + **完整流转图** | MVP fallback Trace | **流转图已提供**（`docs/agent/langgraph-flow.md`） |
| 第三方真实金融数据 API | 真实行情、财务、公告、宏观数据 | 无 | 否 | 无 | MVP 不接入 | 已确认：不接入 |
| 支付 / 结算 | 无 | 无 | 否 | 无 | 不涉及 | 已确认：无 |
| 短信 / 邮件 / 推送 | 无 | 无 | 否 | 无 | 不涉及 | 已确认：无 |
| 对象存储 / 文件服务 | MVP 使用本地文件 | 无 | 否 | 无 | 不涉及 | 已确认：无 |
| 第三方登录 / SSO / OAuth | MVP 不做多账号登录 | 无 | 否 | 无 | 不涉及 | 已确认：无 |
| 地图 / 定位 / 实名 / 风控 | 无 | 无 | 否 | 无 | 不涉及 | 已确认：无 |

## 二点六、本地数据目录与 Agent 资料存放（V1.1 权威约定）

> 供用户侧其他 Agent 写入知识库文件，以及用户稍后粘贴 LangGraph 流转图。路径均相对于**项目根** `Projects_Repo/smart-investment-research/`。

### 1. 本地 Markdown 知识库（RAG）

**根目录（`LOCAL_KB_PATH` 应指向此处）**：

```text
backend/data/knowledge-base/
```

在 `backend/.env` 中配置（相对路径相对于 `backend/` 目录解析）：

```env
LOCAL_KB_PATH=data/knowledge-base
```

**完整目录树（当前已就位）**：

```text
backend/data/knowledge-base/
├── README.md
├── hotspots/                    # 市场热点（独立于样本公司池）
│   ├── 2026-04-market-hotspots.md
│   ├── 2026-05-market-hotspots.md
│   └── 2026-06-market-hotspots.md   # 截至 2026-06-11 的阶段性月报
├── financials/                  # 5 家样本公司财报（2025A + 2026Q1 合并）
├── company-reports/             # 5 份公司研报
├── industry-reports/            # 10 份行业研报
└── structured-data/             # document_manifest、companies、industries、问数 mock 表
```

**热点文档原则**：`hotspots/` 只描述 A 股市场热点（主题、政策、板块、事件），**不要求**与 `financials/` / `company-reports/` 中五家样本公司绑定。运行时由 Agent 组合多路 RAG，不在热点文档内预先硬映射股票池。

**命名规则摘要**：

| 子目录 | 内容 | 文件命名模式 | 当前数量 |
|--------|------|--------------|----------|
| `hotspots/` | 月度市场热点 | `YYYY-MM-market-hotspots.md` | 3 |
| `financials/` | 上市公司财报 | `{code}-{slug}-financial-2025A-2026Q1.md` | 5 |
| `industry-reports/` | 行业研究报告 | `{industry}-industry-report-{period}.md` | 10 |
| `company-reports/` | 公司研报 | `{code}-{slug}-company-report-2026.md` | 5 |
| `structured-data/` | 索引表与问数结构化数据 | 见 `document_manifest.md` | 13 |

**Markdown 文件建议元数据**（文件顶部 YAML front matter，便于 RAG 索引）：

```yaml
---
doc_type: hotspot | financial | industry_report | company_report
title: 文档标题
period: 2026-04          # 热点用 YYYY-MM；财报/研报用报告期（当前基准年：2026）
stock_code: 300750       # 公司相关文档必填
company_name: 宁德时代   # 公司相关文档必填
industry: 新能源电池     # 行业研报必填
source: 用户提供
updated_at: 2026-06-01
---
```

**与问股 / 热点 / RAG 的映射**（`api-contracts.md` 来源类型）：

| 子目录 | `source_type` 建议 |
|--------|-------------------|
| `hotspots/` | `market` |
| `financials/` | `financial` |
| `industry-reports/` | `report` |
| `company-reports/` | `report` |

**说明**：`backend/data/mock/` 继续用于行情 / 问数等**结构化 Mock 工具数据**（`MOCK_DATA_PATH`），与 RAG 知识库分离，不要混放。

### 2. LangGraph Agent 流转图

**主文件（已提供）**：

```text
docs/agent/langgraph-flow.md
```

**推荐目录结构**：

```text
docs/agent/
├── README.md                 # Agent 编排资料说明（节点清单、版本、变更记录）
├── langgraph-flow.md         # ★ 主流转图：Mermaid 或文字版节点/边/分支（用户粘贴处）
└── nodes/                    # 可选：各节点输入输出、Prompt 片段补充说明
    └── README.md
```

**`langgraph-flow.md` 最低内容要求**（进入 T-012 开发前必须齐全）：

- 节点列表：上下文预处理、意图识别、路由决策、工具调用、RAG 命中、质检合规、回答组装等
- 边与分支条件：各节点之间的流转条件
- 与 Trace `node` 字段的对应关系（便于管理端展示）
- 输出结构：`routing_output`、`global_slots`、`rag_hits`、`quality_check`、`final_response` 等

**门禁**：流转图未写入 `docs/agent/langgraph-flow.md` 前，不得启动 T-012 LangGraph 真实编排开发；T-009～T-011 可先行。

### 3. 业务数据库（SQLite，无需用户配置）

```text
backend/data/smart_investment.db    # 会话 / 消息 / Trace / 布局偏好，启动自动建表
```

---

## 三、前端开发清单

### 前端技术选型

| 层级 | 选择 | 说明 |
|------|------|------|
| 框架 | React | 业务型 Web App |
| 语言 | TypeScript | 所有组件、service、DTO 必须类型化 |
| 构建工具 | Vite | 本地开发、代理、构建统一使用 Vite |
| 路由 | react-router | 客户端、管理端、数据说明、系统设置 |
| 状态管理 | Zustand | 会话、视图模式、布局宽度、Trace 展开状态 |
| 请求库 | Axios | 统一 API 实例、错误处理 |
| 桌面 Web 组件基底 | Ant Design 风格基底 | 结合自定义对话与 Trace 组件 |
| 工程化 | ESLint + Prettier + type-check + build | 自动验收必须覆盖 |

### 前端页面任务

| 序号 | 页面名称 | 涉及功能 | 数据来源 | 状态 |
|------|----------|----------|----------|------|
| FE01 | 应用骨架 | 左侧历史、顶部导航、客户端/管理端模式 | 真实 API | 已完成 |
| FE02 | 客户端对话页 | 消息区、固定输入框、富响应、风险提示 | `POST /api/chat/query` | 已完成（V1.1 切换真实 LLM 输出） |
| FE03 | 管理端可观测页 | 双端同步、右侧 Trace 面板 | `GET /api/traces/{trace_id}` | 已完成（V1.1 切换真实 Trace） |
| FE04 | 会话历史视图 | 搜索、新建、切换、删除、标题省略、侧栏拖拽 | 会话 API | 已完成 |
| FE05 | Trace 详情面板 | 内联展开、完整 JSON 弹窗、Trace 面板拖拽 | Trace API | 已完成 |
| FE06 | 富响应组件 | 排行表、个股卡、热点摘要、引用、风险提示 | `rich_blocks` | 已完成 |
| FE07 | 交互式测算组件 | 买入价、情景价、持仓数量、费率、收益率 | 前端本地计算 | 已完成 |
| FE08 | 数据说明页 | 数据源状态、RAG 状态 | `GET /api/data-sources/status` | 已完成（V1.1 展示真实 KB 状态） |
| FE09 | 系统设置页 | 模型、Prompt、合规规则状态，仅管理端可见 | `GET /api/config/status` | 已完成（V1.1 展示真实服务 ready） |

### 前端自动验收标准（MVP 已达成）

- [x] 所有页面 UI 与 `docs/prototypes/index.html` 一致。
- [x] 客户端不展示系统设置入口，管理端展示系统设置入口。
- [x] 输入框固定在对话主区底部，不被消息区或历史列表顶走。
- [x] 历史会话搜索可输入并实时过滤；无结果有空状态。
- [x] 新建会话发送前显示“新对话”，发送首条 Query 后标题替换为 Query。
- [x] 历史列和 Trace 面板均可拖拽调宽，且不造成遮挡、跳动、溢出。
- [x] Trace 节点默认摘要展示，点击内联展开，完整 JSON 弹窗可打开。
- [x] 交互式测算组件可实时计算。
- [x] Mock 数据格式与 `docs/api-contracts.md` 完全一致。
- [x] 桌面 1440×900 与移动 390×844 均无明显布局溢出。

---

## 四、后端开发清单

### Python 环境

- **Python 指令**：`python3`
- **Python 版本**：`Python 3.13.5`
- **虚拟环境**：`.venv`
- [x] Agent 已确认 Python 指令（`python3 --version` 输出 3.11 或更高）

### MVP 后端（已完成）

| 序号 | 功能名称 | 依赖 | 对应接口 | 状态 |
|------|----------|------|----------|------|
| BE00 | 基础设施 | 无 | `GET /api/health` | 已完成 |
| BE01 | 会话服务 | BE00 | 会话 CRUD + 搜索 | 已完成 |
| BE02 | Chat Query 服务 | BE01 | `POST /api/chat/query` | 已完成（fallback） |
| BE03 | Trace 服务 | BE02 | Trace 详情 + raw JSON | 已完成（fallback） |
| BE04 | 布局偏好服务 | BE00 | 布局读写 | 已完成 |
| BE05 | 数据源状态服务 | BE00 | `GET /api/data-sources/status` | 已完成 |
| BE06 | 配置状态服务 | BE00 | `GET /api/config/status` | 已完成 |

### V1.1 后端（待开发）

| 序号 | 功能名称 | 依赖 | 对应任务 | 状态 |
|------|----------|------|----------|------|
| BE10 | 硅基流动 LLM 集成 | BE02、Key 已配 | T-009 | 待开发 |
| BE11 | Embedding + 知识库索引与检索 | BE10、`LOCAL_KB_PATH` | T-010 | 待开发 |
| BE12 | Rerank 重排 | BE11 | T-011 | 待开发 |
| BE13 | LangGraph 真实编排 | `docs/agent/langgraph-flow.md`、BE10～BE12 | T-012 | 待开发（等流转图） |
| BE09 | 质检合规模块（真实 LLM） | BE10 | 并入 T-009 / T-012 | 待开发 |

### 后端任务验收规则

- 基础设施任务基于 `pycore` 框架，禁止重写已有 `config.py`、`server.py`、`logger.py`。
- 配置管理使用 `pycore.core.ConfigManager`，服务器使用 `pycore.api.APIServer`。
- V1.1 外部服务调用必须使用 `httpx` 且 `trust_env=False`；禁止硬编码 Key。
- `VITE_USE_MOCK=false` 时，前端必须调用真实后端 API；V1.1 不得回退到 fallback 作为默认验收路径。
- 涉及外部服务时，Tester 报告必须区分「真实联调通过」与「fallback」；Key 已配则必须做真实调用验收。

---

## 五、功能详情（开发时逐个展开）

> MVP 阶段详情（T-001～T-007）保留于 `.sdd/test-reports/` 与各任务 `notes`；下文仅补充 V1.1 实现要点。

### F13 / BE10 硅基流动 LLM 真实接入（T-009）

- **分层**：`backend/src/integrations/llm/` 封装硅基流动 OpenAI 兼容 HTTP 调用；`chat_service` / 意图 / 质检改为真实 LLM，保留可观测错误与超时。
- **配置**：只读 `backend/.env` 中 `LLM_*` 字段；`GET /api/config/status` 在 Key 有效时标记 `ready`。
- **验收**：真实浏览器提问后，回答由模型生成；Trace 记录真实调用元数据（不含 Key）；不得再声明 fallback PASS。

### F14 / F16 / BE11 本地 Markdown 知识库 + Embedding（T-010）

- **数据路径**：`backend/data/knowledge-base/`（见「二点六」）；扫描 `hotspots/`、`financials/`、`industry-reports/`、`company-reports/`、`structured-data/`（清单表可选索引）。
- **索引**：对 `.md` 分块向量化（硅基流动 Embedding）；向量缓存策略在实现时写入 `backend/data/knowledge-base/.index/`（可 gitignore）。
- **检索（当前已实现）**：用户 `normalized_query` → **BM25 + 向量混合召回**（加权融合，可选 Rerank）→ Top-K → 注入上下文；Embedding 不可用时 **BM25-only 降级**。`GET /api/data-sources/status` 反映真实文件数与 `ready` 状态。
- **检索（规划，延后）**：独立 `query_rewrite` 节点产出 `retrieval_query`（见 F18 / `docs/agent/langgraph-flow.md` §7.1），不阻塞 V1.1。
- **验收**：热点 / 财报 / 行业 / 公司四类文档各至少命中 1 条可验证用例。

### F15 / BE12 Rerank 重排（T-011）

- **接入**：对 BE11 召回结果调用硅基流动 Rerank；失败时记录日志，不得静默吞错。
- **验收**：管理端 Trace RAG 节点可见重排前后顺序变化或重排分数。

### F17 / BE13 LangGraph 真实编排（T-012）

- **输入**：`docs/agent/langgraph-flow.md`（用户提供的完整流转图）。
- **实现**：按流转图定义 StateGraph；Trace `steps` 与图节点一一对应；替换 T-007 fallback 链路。
- **门禁**：流转图未就绪则任务 blocked，不猜测节点结构。

### V1.1 收尾回归（T-013）

- 全链路真实 AI 回归：LLM + RAG + Rerank + LangGraph；更新 `docs/startup.md` 中「未完成真实联调清单」。
- 双视口 E2E 扩展：覆盖真实 RAG 命中与 Trace 节点。

---

## 六、开发顺序建议

### 阶段 1～4：MVP（已完成）

1. 前端 Mock MVP → 用户门禁 ✅  
2. 后端基础设施 ✅  
3. 逐功能真实 API 闭环（T-003～T-007，fallback） ✅  
4. E2E 回归 + `docs/startup.md`（T-008） ✅  

### 阶段 5：V1.1 真实 AI / RAG / Agent（当前阶段）

**推荐优先级**（用户已确认）：

| 顺序 | 任务 ID | 标题 | 前置条件 |
|------|---------|------|----------|
| 1 | T-009 | 硅基流动 LLM 真实接入 | Key 已配 ✅ |
| 2 | T-010 | Embedding + 本地 Markdown 知识库检索 | T-009、知识库已就位 ✅ |
| 3 | T-011 | Rerank 重排 | T-010 |
| 4 | T-012 | LangGraph 真实编排 | T-009～T-011、`docs/agent/langgraph-flow.md` |
| 5 | T-013 | V1.1 全链路真实 AI 回归 | T-009～T-012 |

**V1.1 前置准备（已完成）**：

- 本地知识库已就位：`backend/data/knowledge-base/`（36 个 Markdown；热点 3 + 财报 5 + 公司研报 5 + 行业研报 10 + structured-data 13）。
- 文档清单已更新：`structured-data/document_manifest.md`（28 条文档登记，含 4/5/6 月热点）。
- LangGraph 流转图已就位：`docs/agent/langgraph-flow.md`（去除测算版，T-012 可启动）。

**V1.2+ backlog**（V1.1 验收后再排期，见 `.sdd/tasks.json` T-014～T-017）：

| 顺序 | 任务 ID | 标题 | 说明 |
|------|---------|------|------|
| 1 | T-015 | 五轮短期记忆窗口（F20） | 统一 5 轮 QA / 10 条消息窗口与 `history_summary`；意图层消费续问 |
| 2 | T-016 | 会话 `pending_slots` 多轮闭环（F19） | 槽位跨轮继承与覆盖；澄清机制产品化 |
| 3 | T-017 | 多轮上下文注入下游（F20） | `slot_extraction`、子 Agent、`response_assembly` 使用短期记忆 |
| 4 | T-014 | Query 改写节点（F18） | 依赖 T-016/T-017；`rag_retrieval` 使用 `retrieval_query` |

**其他可增量补充**（不阻塞 V1.1）：

- `2026-06-market-hotspots.md` 在 6 月结束后可更新为完整自然月复盘。

---

## 七、Plan 维护规则

1. 禁止跳过 `docs/Plan.md` 直接开发。
2. 禁止在 `docs/Plan.md` 之外另建进度文件。
3. 开发阶段由 Planner 根据本文件拆分 `.sdd/tasks.json`。
4. 每个任务完成后必须更新任务状态和验收记录。
5. V1.1 任务（T-009～T-013）须在用户确认本 Plan 更新后，由 Planner 写入 `tasks.json` 再进入开发循环。
