# 知识库扩容方法论（Raw → Markdown → 索引）

> **适用版本**：RAG 索引 `RAG_INDEX_VERSION = 7`（`backend/src/services/rag/chunker.py`）  
> **数据根目录**：`backend/data/knowledge-base/`（`LOCAL_KB_PATH=data/knowledge-base`）  
> **读者**：项目维护者、负责整理 raw 数据的 Agent、后续知识库扩容任务执行者

本文档是**知识库扩容的唯一操作手册**。当你拿到 PDF 解析文本、网页整理稿、CSV 清单等 raw 数据时，按本文档完成 Markdown 落盘、元数据标注、清单登记与索引验收，再交给系统自动切块与向量化。

目录索引与样本统计见 [`backend/data/knowledge-base/README.md`](../backend/data/knowledge-base/README.md)。

---

## 1. 总览：端到端流水线

```text
Raw 资料（PDF 解析 / 网页 / CSV / 人工整理）
    ↓ ① 判定资料类型 & 目标子目录
    ↓ ② 清洗 & 结构化写成 Markdown（含元数据表）
    ↓ ③ 按命名规范落盘到 knowledge-base/{subdir}/
    ↓ ④ 更新 structured-data/ 清单表（companies / industries / document_manifest）
    ↓ ⑤ 触发索引重建（改 RAG_INDEX_VERSION 或删 .index/）
    ↓ ⑥ 检索冒烟 + Trace 验收
系统自动：chunk_strategies → Embedding → BM25 混合 → 可选 Rerank
```

**核心原则**：

1. **机器可读优先**：元数据表、标题层级、章节边界决定切块质量；正文写法要配合现有 `chunk_strategies.py`，而不是指望检索层「猜」。
2. **元数据与正文分离**：迁移元数据、文件说明等**不得**与 `[page 1]` 财务正文混在同一块可检索正文里（V7 已跳过 `## 迁移元数据` 等 H2，但正文内重复元数据表仍会污染召回）。
3. **一份文档一个 doc_id**：合并文件（如年报+一季报）必须在文件头与各报告 `##` 分节各有一份元数据表，且 `doc_id` 全局唯一。
4. **先登记后索引**：`document_manifest.md` 是人工与系统的「总账」；新增文件必须补一行，否则 Demo 数据说明页与溯源会对不上。

---

## 2. 资料分类与落盘目录

| 子目录 | `source_type`（索引） | 典型 raw 来源 | 是否必须 company_id |
|--------|----------------------|---------------|---------------------|
| `hotspots/` | `market` | 月度市场复盘、政策事件整理 | 否 |
| `financials/` | `financial` | 年报、季报 PDF 解析文本 | 是 |
| `company-reports/` | `report` | 券商公司深度研报 PDF | 是 |
| `industry-reports/` | `report` | 行业策略/深度研报 PDF | 否（需 `industry_id`） |
| `structured-data/` | `knowledge` | 公司表、行业表、文档清单、问数模板 | 视表而定 |

**不要放入知识库**：

- 问数用的结构化 Mock 行情/估值 → `backend/data/mock/`（`MOCK_DATA_PATH`）
- 密钥、内部调试日志、未脱敏 API 响应

**热点文档边界**（`hotspots/`）：

- 只写市场热点、政策、板块、事件与公开报道归因；**不强制**映射五家样本公司。
- 文中个股仅为公开案例，不代表固定股票池。

---

## 3. 文件命名规范

| 子目录 | 模式 | 示例 |
|--------|------|------|
| `hotspots/` | `YYYY-MM-market-hotspots.md` | `2026-07-market-hotspots.md` |
| `financials/` | `{code}-{pinyin-slug}-financial-{periods}.md` | `300750-ningdeshidai-financial-2025A-2026Q1.md` |
| `company-reports/` | `{code}-{pinyin-slug}-company-report-{year}.md` | `300750-ningdeshidai-company-report-2026.md` |
| `industry-reports/` | `{industry-slug}-industry-report-{period}.md` | `baijiu-industry-report-2026.md` |

命名要求：

- 全小写、连字符分词；股票代码 6 位无前缀零丢失。
- 同一公司多年报可合并为一个 `financials` 文件，但须在文内用 `## 2025 年年度报告` / `## 2026 年第一季度报告` 分节（见 §6.2）。

---

## 4. 元数据（Metadata）

### 4.1 解析规则（代码契约）

索引器通过 `parse_metadata_table()` / `parse_all_metadata_tables()` 读取 Markdown **第一张**（或分节第一张）管道表：

- 表头行含 `字段` | `内容`（或英文键名见下表）
- 必须能解析出 `doc_id` 或 `company_id` 才视为有效元数据
- 支持的字段别名 → 内部字段：

| 表内字段名 | 内部字段 | 用途 |
|-----------|----------|------|
| `doc_id` | `doc_id` | 全局唯一文档 ID、chunk_id 前缀 |
| `资料类型` | `doc_type` | 检索过滤、上下文前缀 |
| `标题` | `title` | 引用展示、breadcrumb |
| `公司ID` / `公司id` | `company_id` | 公司过滤、embed 前缀补全 |
| `行业ID` / `行业id` | `industry_id` | 行业归类 |
| `时间口径` | `time_period` | 引用展示、期间加权 |
| `公司名称` | `company_name` | embed 上下文前缀 |
| `股票代码` | `ticker` | embed 上下文前缀 |

表外字段（写在表里即可，供人工溯源，**不参与** `parse_metadata_table`）：

`发布日期`、`来源`、`原始路径`、`is_mock`、`备注`、`迁移后目录`、`迁移文件` 等。

### 4.2 `doc_id` 命名约定

| 资料类型 | `doc_type` | `doc_id` 模式 | 示例 |
|----------|------------|---------------|------|
| 年报 | `annual_report` | `ann_{code}_{year}` | `ann_300750_2025` |
| 季报 | `quarterly_report` | `q1_{code}_{year}` | `q1_300750_2026` |
| 公司研报 | `company_research` | `research_{code}_{broker_slug}` | `research_300750_dwzq` |
| 行业研报 | `industry_research` | `industry_{industry}_{broker}_{period}` | `industry_baijiu_cms_2026` |
| 市场热点 | `market_event` | `event_ashare_{YYYYMM}` | `event_ashare_202607` |
| 结构化表 | `structured_csv` | 文件名 stem | `document_manifest` |

**禁止**：重复 `doc_id`、仅用随机 hash、与 `document_manifest` 不一致。

### 4.3 `company_id` / `industry_id`

- 公司：`company_{6位代码}`，如 `company_300750`
- 行业：`industry_{slug}`，如 `industry_baijiu`、`industry_new_energy_battery`
- 新公司：先写入 `structured-data/companies.md`，再写财报/研报
- 新行业：先写入 `structured-data/industries.md`

`companies.md` 同时驱动查询侧别名（`load_company_aliases`）：公司中文名、6 位代码会用于从用户问句推断 `company_id` 过滤。

### 4.4 `time_period` 口径

| 场景 | 推荐写法 |
|------|----------|
| 年报 | `2025A` |
| 一季报 | `2026Q1` |
| 月度热点 | `2026-07-01 至 2026-07-31` 或 `2026-07` |
| 行业研报无明确财季 | 可留空，用 `发布日期` 补充 |

### 4.5 `is_mock` 与数据标签

| 标签 | 含义 | 写法 |
|------|------|------|
| `is_mock: false` | 真实或忠实整理的公开资料，可进 RAG 主证据 | 元数据表 + `document_manifest` 列 |
| `is_mock: true` | 仅 Demo / 字段补齐，**不得**当事实陈述 | 文件名可含 `mock`；清单表统计须标明 |

`structured-data/` 下文件名含 `mock`、`template`、`demo` 的表默认视为问数 Demo，RAG 可索引但 Agent 应优先 `is_mock=false` 来源。

---

## 5. Markdown 文档骨架（按类型）

### 5.1 通用结构

```markdown
# {标题}

> 迁移说明：…用途…不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| doc_id | ... |
| 资料类型 | ... |
| ... | ... |

## 文件说明

（可选）合并了哪些 raw、时间范围、合规声明。

## {正文分节}

### 原始解析文本

（财报/研报 PDF 正文放这里）
```

**必须跳过的 H2**（不会进入可检索 chunk，`chunk_strategies._SKIP_H2`）：

`迁移元数据`、`文件说明`、`数据表说明`、`字段`、`数据`

> 注意：`structured-data` 清单表里 `## 数据` 整节会被跳过——清单表靠 BM25/结构化查询，不靠语义正文。

### 5.2 热点 `hotspots/`

推荐层级：

```text
# 月报标题
## 迁移元数据
## 本月市场总览
## 核心结论
## 热点主线一：{主题}
### 现象
### 公开报道中的关键事实
### 多因素驱动
### 解释边界
```

- 用 `##` 表主线、`###` 表子话题；chunker 对 `###` 做 child 块，对上级 `##` 保留 `parent_text`。
- 关键事实尽量写清「来源 + 日期 + URL」，便于 hotspot_agent 归因。
- 阶段性月报（月末未结束）在元数据 `备注` 标明截止日期。

### 5.3 财报 `financials/`

**合并年报 + 一季报**（推荐，与现网一致）：

```markdown
## 迁移元数据
（两张表：ann_xxx / q1_xxx）

## 2025 年年度报告

| 字段 | 内容 |
| doc_id | ann_300750_2025 |
| 资料类型 | annual_report |
| ... |

### 原始解析文本

[page 1]
...

## 2026 年第一季度报告

| 字段 | 内容 |
| doc_id | q1_300750_2026 |
| 资料类型 | quarterly_report |
| ... |

### 原始解析文本

[page 1]
...
```

要点：

- `## 2025 年年度报告` / `## 2026 年第一季度报告` 是**分报告边界**（`_FIN_REPORT_SPLIT_RE`），不是普通 H2。
- 每个分节内元数据表须含正确 `doc_type` 与 `time_period`。
- 正文保留 `[page N]` 分页标记无妨，`clean_financial_text` 会清理；但**不要**在元数据表段落里夹带长正文。

### 5.4 研报 `company-reports/` / `industry-reports/`

```markdown
## 迁移元数据
（单表）

## 原始解析文本

[page 1]
证券研究报告...
1. 投资要点
1.1. 子标题
```

要点：

- 正文必须从 `## 原始解析文本` 或 `### 原始解析文本` 之后开始（`_RAW_TEXT_MARKERS`）。
- 章节用 `1.`、`1.1.` 编号标题；chunker 按 `_REPORT_SECTION_RE` 切分。
- `[Table_EPS]` 盈利预测表会被单独提成一块 `profit_forecast` chunk，高价值，勿删。
- PDF 页眉页脚、免责声明行会被 `clean_report_text` 剥离，无需手工删净。

### 5.5 结构化清单 `structured-data/`

| 文件 | 何时更新 |
|------|----------|
| `document_manifest.md` | **每新增/变更**一篇可检索文档 |
| `companies.md` | 新增样本公司 |
| `industries.md` | 新增行业维度 |
| `*_template.md` / `*_mock.md` | 仅 Demo，按需 |

`document_manifest.md` 列：`doc_id`, `doc_type`, `title`, `company_id`, `industry_id`, `period`, `publish_date`, `source`, `file_path`, `is_mock`, `notes`

---

## 6. 切块（Chunking）如何被系统执行

你**不需要手写 chunk**，但必须按下列规则写 Markdown，使自动切块可检索。

### 6.1 关键参数（V7）

| 参数 | 值 | 含义 |
|------|-----|------|
| `_CHILD_MAX_CHARS` | 900 | 单 embed 子块上限 |
| `_PARENT_MAX_CHARS` | 4500 | parent 上下文截断 |
| `_PROSE_OVERLAP_CHARS` | 120 | 硬切重叠 |
| `_MIN_CHUNK_CHARS` | 80 | 低于此长度丢弃（summary 块 40） |

### 6.2 分类型策略摘要

| 类型 | 策略 | 特殊产物 |
|------|------|----------|
| `hotspots` | `##` → `###` → 段落切分；parent-child | `breadcrumb` + `parent_text` |
| `financials` | 分报告 → `第X节` → MDA 中文序号子节；财报表整表合并后按行拆 embed | `业绩摘要` summary 块（`chunk_role=summary`） |
| `reports` | 盈利预测表独立块 + 编号章节 prose 切分 | `*_profit_forecast_*` |
| `structured-data` | `##` 节下 prose 切分 | 清单 `## 数据` 不索引 |

### 6.3 Embed 文本如何生成

每个 chunk 的 `embed_text` 大致为：

```text
{公司名称}({代码}) {time_period} {文档类型标签} | {breadcrumb}：
{正文}
```

由 `build_context_prefix()` + 正文拼接；财报金额会在切块时**元 → 亿元**（`convert_financial_yuan_to_yi`）。

公司名前缀：若正文前 120 字不含公司名，会从 `companies.md` 自动补 `宁德时代(300750)` 类前缀。

### 6.4 检索加权（与写作相关）

| 机制 | 条件 | 影响 |
|------|------|------|
| `retrieval_weight` | 会计政策正文 | 0.35（降权） |
| `chunk_role=summary` | 业绩摘要 NL 块 | 优先命中财务问句 |
| `is_metadata_only_chunk` | 只有「字段\|内容」表、无营收/净利润等 | 检索分 **-0.18** |
| 财务问句期间加权 | 问「一季报」 | 含 `2026Q1` / `业绩摘要` 加分 |

**写作建议**：

1. 让「主要财务数据」「营业收入」「归属于上市公司股东的净利润」出现在**独立 chunk** 中，不要和迁移元数据表相邻在同一段落。
2. 合并报表（资产负债表等）可很长：系统会按表头+数据行拆多块，共享 `parent_text` 整表——**保持表头行**（含 `项目`、`单位：元`）便于拆块重复表头。
3. 热点文过长段落会被 900 字硬切；用 `###` 小标题控制语义边界优于巨型段落。

---

## 7. Raw 数据整理清单（执行者逐步勾选）

### Step A：接收与登记

- [ ] 确认 raw 类型：PDF 解析 / 网页 / 表格 / 人工稿
- [ ] 确认目标目录（§2）与是否新公司/新行业
- [ ] 分配 `doc_id`（§4.2），查重 `document_manifest.md`

### Step B：清洗

**PDF 解析文本**：

- [ ] 保留 `[page N]` 即可，不必手工去页码
- [ ] 删除或接受自动清理：免责声明、重复页眉、`图N：…资料来源` 行
- [ ] 研报：确认 `## 原始解析文本` 之后才是正文
- [ ] 财报：确认 `第X节` 标题行完整（「第一节 释义」类）

**网页/人工稿（热点）**：

- [ ] 统一为 Markdown 标题层级
- [ ] 每条关键事实带来源与时间
- [ ] 不写买卖建议、目标价、确定性涨跌预测

### Step C：写元数据表

- [ ] 文件头 `## 迁移元数据` 至少一张完整表
- [ ] 合并财报：文件头两张表 + 每个分节内各一张表
- [ ] `company_id` / `industry_id` / `time_period` / `doc_type` 正确
- [ ] `is_mock` 显式填写
- [ ] `原始路径` 指向 raw 存档位置（便于溯源）

### Step D：落盘

- [ ] 文件名符合 §3
- [ ] UTF-8 编码，Unix 换行
- [ ] 不提交 `.index/`（gitignore）

### Step E：更新清单

- [ ] `structured-data/document_manifest.md` 追加一行
- [ ] 新公司 → `companies.md`；新行业 → `industries.md`
- [ ] 更新 `backend/data/knowledge-base/README.md` 文件数（可选但建议）

### Step F：索引与验收

- [ ] 修改 `RAG_INDEX_VERSION`（`chunker.py`）或删除 `backend/data/knowledge-base/.index/` 触发全量重建
- [ ] 启动后端，观察首次检索是否完成索引（Chat 会提示「正在构建知识库索引…」）
- [ ] 运行 `pytest backend/tests/test_rag_service.py -q`
- [ ] 有 Key 时：`REAL_API_TEST=1` 做三条冒烟（热点 / 财报 / 研报）

**验收标准（最低）**：

| 问句类型 | 期望 |
|----------|------|
| 「宁德时代 2026 一季报营收」 | top hit `doc_type=quarterly_report`，snippet 含「营业收入」数值，而非纯元数据表 |
| 「2026年5月 A股热点」 | top hit `source_type=market`，`doc_id=event_ashare_202605` 或对应月份 |
| 「白酒行业 2026 策略」 | top hit `source_type=report`，行业研报标题 |

Trace 中应能看到：`chunk_id`、`time_period`、`breadcrumb`；财报类 snippet 优先从「业绩摘要/主要财务数据」起（`build_excerpt`）。

---

## 8. 反模式（务必避免）

| 反模式 | 后果 | 正确做法 |
|--------|------|----------|
| 元数据表与 `[page 1]` 正文在同一无标题段落 | top1 命中元数据表，看不到营收 | 元数据只在 `## 迁移元数据` 或分节表；正文在 `### 原始解析文本` 后 |
| 一季报问句但只有年报 `doc_id` 块含「营业收入」 | 期间错配 | 分节 `q1_` 元数据 + `2026Q1` time_period |
| 整篇热点一个巨型段落 | 语义切块断裂、上下文噪声 | 用 `##` / `###` 分层 |
| 新文档未进 `document_manifest` | 数据说明页、溯源不一致 | 先登记再索引 |
| 把 Mock 行情写进 `knowledge-base` | 用户混淆真实与 Demo | Mock → `backend/data/mock/` |
| 漏更新 `companies.md` | 问句无法解析公司过滤 | 先维护公司表 |
| 未升 `RAG_INDEX_VERSION` 就期望新切块生效 | 沿用旧 chunks | 升版本或删 `.index/` |

---

## 9. 索引版本与增量

- 当前版本号：`backend/src/services/rag/chunker.py` → `RAG_INDEX_VERSION = 7`
- 缓存目录：`backend/data/knowledge-base/.index/`（`chunks.jsonl`、`vectors.jsonl`、`index_meta.json`）
- 文件指纹变更会触发单文件重切；**切块策略变更**必须升 `RAG_INDEX_VERSION` 全量重建
- Embedding 模型或 `EMBEDDING_DIM` 变更也需重建

---

## 10. 扩容批次建议（Demo 阶段）

当 raw 数据量增大时，建议按批交付，每批 5～15 个文件：

1. **批 1**：补齐热点月份（`hotspots/`）— 对 hotspot_agent 见效最快  
2. **批 2**：扩展样本公司财报+研报（成对交付 `financials` + `company-reports`）  
3. **批 3**：扩展行业研报（与已有 `industries.md` 对齐）  
4. **批 4**：可选非 RAG 结构化 Demo（`structured-data` mock 表）

每批完成后执行 §7 Step F，并把结果记录到 `.sdd/test-reports/`（可复用 `rag-chunking-v*-report.md` 命名）。

---

## 11. 相关代码与文档

| 资源 | 路径 |
|------|------|
| 切块入口 | `backend/src/services/rag/chunker.py` |
| 分类型策略 | `backend/src/services/rag/chunk_strategies.py` |
| 元数据解析 | `backend/src/services/rag/metadata.py` |
| PDF 清洗 | `backend/src/services/rag/preprocess.py` |
| 检索加权 | `backend/src/services/rag/retriever.py` |
| 业绩 NL 摘要 | `backend/src/services/rag/financial_summary.py` |
| 目录 README | `backend/data/knowledge-base/README.md` |
| 项目经验 | `.sdd/experience.md`（T-010 财报 RAG 陷阱） |
| RAG 切块测试报告 | `.sdd/test-reports/rag-chunking-v5-retest-report.md` |

---

## 12. 给 Agent 的简短指令模板

下次扩容时，可将以下模板贴给执行 Agent：

```text
请按 docs/knowledge-base-ingestion.md 将附件 raw 数据写入 backend/data/knowledge-base/：
1. 判定目录与 doc_id
2. 写 Markdown（含迁移元数据表 + 原始解析文本）
3. 更新 structured-data/document_manifest.md（及 companies/industries 如需要）
4. 递增 RAG_INDEX_VERSION 并验收 test_rag_service.py + 三条检索冒烟
交付：变更文件列表、新增 doc_id 表、验收结果摘要。
```

---

*文档版本：2026-06-12，对齐 RAG_INDEX_VERSION=7、知识库 36 文件 / 2510 chunks。*
