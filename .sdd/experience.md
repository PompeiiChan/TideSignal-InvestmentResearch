# 项目经验

> 当前项目长期有效的经验。  
> Developer / Tester / Bugfix 在任务完成后维护本文件。

---

## Harness 系统经验摘要

新项目开始时，Developer / Tester / Bugfix 需要同时参考：

- 当前项目经验：`.sdd/experience.md`
- 系统级经验：`<Harness 根目录>/memory/harness-experience.md`

---

（项目经验将在开发过程中追加）

### T-001: 前端 Mock MVP 页面闭环
- **陷阱**：前端 Mock 页面容易直接复用内部展示实体，导致 `agent_label`、展示变体等契约外字段泄露到 endpoint DTO。
- **经验**：先按 `docs/api-contracts.md` 建立 Session、Message、Trace、数据源、配置状态类型，再由 Mock handler 显式构造每个 endpoint 的响应 DTO，可以同时满足页面交互和契约对齐。
- **避坑**：后续从 Mock 切真实 API 时，保留 `VITE_API_BASE_URL=/api` 和 `/api`、`/ws` 代理；客户端入口不要展示系统设置，管理端才展示系统设置入口。

### T-001: 前端 Mock MVP 页面闭环修复
- **陷阱**：Zustand selector 中使用 `?? []` / `?? {}` 这类字面量 fallback，会在空状态下每次返回新引用，真实浏览器可能触发 `getSnapshot should be cached` 和无限更新；type-check、lint、build 不会发现。
- **经验**：selector 只返回 store 中已有引用或 `undefined`，数组 / 对象 fallback 放到组件模块级稳定常量或组件外稳定引用中处理。
- **避坑**：[SYSTEM] 建议回传系统级经验：React + Zustand 前端规范应要求 selector fallback 引用稳定，Tester 对 Mock MVP 至少做一次真实浏览器首屏渲染检查。

### T-001: 会话历史删除菜单补充
- **陷阱**：历史行如果继续用一个整行 `button` 包住内容，就不能再嵌套三点菜单按钮，否则会产生无效交互结构。
- **经验**：把历史行拆成左侧选择按钮和右侧更多操作按钮，删除动作走 store，再由 Mock API 同步移除会话、消息和 Trace，能保持 UI 交互和后续真实 API 契约一致。
- **避坑**：新增前端 Mock 行为时，同步补 `docs/api-contracts.md` 和后续闭环任务的真实 API 验收点，避免 Mock 阶段做完但后端阶段漏实现。

### T-001: 会话历史点击热区修复
- **陷阱**：在历史行右侧加入三点菜单后，如果只让标题按钮处理选择，会留下 padding、gap、右侧空白等不响应区域，用户会感觉“点一次没反应”。
- **经验**：列表行应由外层容器兜底处理选择，行内菜单和删除按钮使用 `stopPropagation()` 隔离操作；标题按钮也要阻止冒泡，避免重复触发选择。
- **避坑**：给列表行增加二级操作时，必须用真实浏览器点行内空白、标题、时间和更多按钮四类热区，确认选择和菜单操作不会互相抢事件。

### T-002: 后端基础设施与本地联调代理
- **陷阱**：`pycore/` 与 `backend/` 并列时，后端运行和测试需要通过 `PYTHONPATH=..` 引入 `pycore`；不要对项目执行 editable install，因为根目录同时存在 `pycore`、`backend`、`frontend` 多个顶层包，`setuptools` package discovery 会失败。
- **经验**：质量门禁应收敛到 `backend/src backend/tests`，不要把 `pycore/` 纳入当前项目业务代码 lint/typecheck/test；依赖可安装到项目内 `.venv`，但不需要把整个仓库作为 Python 包安装。
- **避坑**：沙箱内短时端口绑定 smoke 可能被拦截，需要由 Orchestrator/Tester 授权或接手验证；Developer 收尾时应明确区分 ASGI 直连 smoke 通过和真实端口绑定 smoke 未授权。

### T-003: 会话历史与布局偏好真实 API 闭环
- **陷阱**：刷新后恢复布局宽度不能只靠 `PATCH /api/layout/preferences`；页面初始化必须有真实读取端点，否则只能依赖前端内存或 localStorage，无法证明真实 API 闭环。
- **经验**：新增 `GET /api/layout/preferences` 后，前端初始化先并行读取会话列表和布局偏好；会话与布局 Mock 改为 `VITE_USE_MOCK=true` 分支动态加载，`VITE_USE_MOCK=false` 时通过 `/api` 代理命中后端。
- **避坑**：浏览器自动化清空 `type=search` 输入时，空字符串 fill 可能不触发真实清空；验收清空搜索应使用键盘全选删除或真实浏览器控件，并确认输入值为空后列表恢复。SQLAlchemy async 运行依赖 `greenlet`，项目 `.venv` 缺失时真实端口服务会异常。

### T-004: Chat Query 与富响应 fallback 闭环
- **陷阱**：Chat Query 完成后如果前端立即调用 `GET /api/traces/{trace_id}`，会提前命中 T-005 的完整 Trace API，导致真实模式下出现 404 控制台错误。
- **经验**：T-004 只存储消息与会话摘要，前端应直接使用 `POST /api/chat/query` 返回的基础 Trace summary 更新管理端指标；完整 Trace steps 和 raw JSON 留给 T-005 接入。
- **避坑**：后端业务闭环必须用 `VITE_USE_MOCK=false` 启动前端做真实浏览器验证；终端 curl 要注意本机 `http_proxy`，本地联调用 `--noproxy '*'` 避免把 localhost 请求发到代理。

### T-005: Trace API 与管理端详情闭环
- **陷阱**：T-004 为了避免提前命中 Trace 详情 API，会把前端真实模式下的完整 Trace 拉取关掉；进入 T-005 后如果不撤掉这个保护，管理端会一直停留在基础 summary，看不到 steps 和 raw JSON。
- **经验**：Chat Query 可以继续返回轻量 summary，但后端必须同时持久化完整 Trace；前端在真实模式发送 Query 后立刻补拉 `/api/traces/{trace_id}`，历史切换时如果缓存里只有 summary，也要再次拉取 detail。
- **避坑**：Trace 属于会话关联数据，删除会话前要同步清理 `investment_traces`；测试既要直接打 8099，也要通过 5199 的 `/api` 代理 smoke，确认 `VITE_USE_MOCK=false` 没有回到 Mock Trace 分支。

### T-006: 数据源状态与系统设置真实 API 闭环
- **陷阱**：系统设置页很容易把“配置字段”误做成“配置值展示”，一旦后续 `.env` 存入真实 Key，就可能把密钥带到页面、报告或日志里。
- **经验**：配置状态 API 只返回字段名、状态和缺失字段；service 层用空值判断 `mocked`，不返回实际值。外部服务未配置时页面必须明确显示 `mocked`，不能用“已接入”这类暗示真实联调的表述。
- **避坑**：新增状态类页面时要同时验证三件事：真实模式是否经 `/api` 代理命中后端、客户端是否仍隐藏管理端入口、页面和报告中是否没有 `sk-` / `Bearer` / 长 token 样式内容。

### T-007: Agent/RAG/质检 fallback 链路闭环
- **陷阱**：如果只把 Chat Query 的基础 Trace 摘要做长一点，管理端看不到真正的 Agent 路由、工具调用、RAG 命中和质检拆解；用户会误以为“Trace 有了”但可解释链路仍不完整。
- **经验**：fallback 链路也要按真实链路形态拆节点：意图识别、路由决策、工具调用、RAG 命中、质检合规、回答组装分别落到 Trace step；节点 `raw_json` 保留 `routing_output`、`global_slots`、`rag_hits`、`quality_check`，前端只做通用渲染。
- **避坑**：外部服务缺失时，工程 Trace raw/config/status 与测试报告必须保留 fallback / blocked 边界说明，但客户端和管理端可见 UI 不展示“Agent fallback”“真实 LLM/LangGraph 未接入”等内部口径；不能把 fallback PASS 写成真实服务 PASS。

### T-007: Assistant 富响应气泡呈现修整
- **陷阱**：如果 `RichBlockRenderer` 自己在每个 block 后面渲染 `risk_notice`，风险提示会被拆到多个卡片外侧，看起来不像同一条模型 response，还会重复打断阅读。
- **经验**：assistant 消息应该由外层气泡统一包住正文、结构化卡片和最终风险提示；风险提示由 `ChatView` 收束到 response 结尾，有专门 `risk_notice` block 时用该 block，没有时用 block 上的 `risk_notice` 兜底。
- **避坑**：后续新增富响应 block 时不要在 block 组件内部额外输出整条回答级风险提示；只让 block 渲染自己的结构，回答级结尾提示留给消息容器统一处理。

### T-007: 个股基本面富响应编排
- **陷阱**：只返回 `stock_card` 会让用户感觉模型“丢了一张卡”就结束，且把引用来源、风险提示单独做成卡片会割裂模型回答。
- **经验**：个股基本面回答应按 `stock_card -> text -> risk_notice -> citation_list` 组织；结构化卡片先承载核心指标，后续文本段落补 200–300 字基本面点评，风险提示和来源作为普通 Markdown 文字段落收尾。
- **避坑**：客户端不要展示“Agent fallback 回答摘要”这类内部口径；新增财务指标时同步 mock、真实 fallback、测试断言和默认历史样例，避免 mock/real 视觉不一致。

### T-007: 历史富响应内部文案清洗
- **陷阱**：只修新生成响应不够，旧 SQLite 会话里已经持久化的 `Agent fallback 回答摘要`、`当前回答由演示级 Agent fallback 链路生成` 和旧 `last_message_preview` 仍会通过历史详情接口回灌到客户端。
- **经验**：后端输出层需要统一 sanitize assistant message 和 session preview：过滤内部摘要 block、重排风险/来源、补齐个股点评和财务指标，并把 fallback/未联调状态留在工程 Trace 数据而不是用户回答里。
- **避坑**：真实浏览器验收如果向真实 SQLite 发送测试问题，收尾前必须删除本轮测试 message/trace 并恢复 session `updated_at`、`last_message_preview`、`last_trace_id`，避免污染演示历史。

### T-007: 前端富响应防御性清洗
- **陷阱**：只在后端清洗内部文案仍不够；用户可能连着旧后端、旧 dev server、旧 mock 或已缓存的历史响应，客户端如果信任 API 原样渲染，`Agent fallback 回答摘要` 仍会出现。
- **经验**：前端 store 和 ChatView 都要接入 sanitizer：session preview、session detail messages、chat query response、最终渲染消息、TracePanel 可见摘要全部过一遍内部词过滤。
- **避坑**：凡是包含 `Agent fallback`、`当前回答由`、`用于验证路由`、`fallback 规则`、`真实 LLM`、`LangGraph` 的内容，只能作为黑名单/测试 fixture 或 raw debug data 存在，不能进入可见 UI。

### T-008: 全链路 E2E 回归与启动说明
- **陷阱**：E2E 脚本若直接写死后端 URL 或把 `VITE_USE_MOCK=true` 当默认，会绕过 Vite `/api` 代理，无法证明 T-003～T-007 的真实 API fallback 闭环；`docs/startup.md` 也容易误把 fallback 写成“已接入”。
- **经验**：`docs/startup.md` 应分 Mock MVP 与 `VITE_USE_MOCK=false` 两节，并单列外部服务字段与「未完成真实联调清单」；浏览器回归用 `frontend/e2e/regression.mjs`（Playwright）覆盖 1440×900 / 390×844，API 层用 `backend/tests/test_api_regression.py` 在隔离库做全链路 smoke；E2E 结束按 marker 清理会话，避免污染演示 SQLite。
- **避坑**：布局 PATCH 验收须使用契约允许宽度（如 `sidebar_width` ≥ 约束下限）；会话列表响应字段为 `data.items` 而非 `data.sessions`；E2E 只作全系统回归，首次真实 API 联调证据仍引用 T-003～T-007 报告，不得在本任务补做后改口为真实服务 PASS。

### T-010: Embedding + 本地 Markdown 知识库检索
- **陷阱**：`rag/__init__.py` 若提前 export `RagService` 但 `service.py` 未落地，会在 import 阶段直接失败；Chat 单测只 mock LLM 时，T-007 仍断言 `rag_hits == []` 会与真实 RAG 链路冲突。
- **经验**：索引缓存放 `LOCAL_KB_PATH/.index/` 并用文件指纹增量重建；`hotspots→market`、`financials→financial`、`*-reports→report`、`structured-data→knowledge`；Chat 在 intent 后检索、流式 prompt 注入片段、`citation_list` 与 Trace `rag_retrieval` 统一来自 `RagHit`。
- **避坑**：pytest 需同时 mock `RagService` 或接受 Trace 有命中；真实 Embedding 用 `REAL_API_TEST=1` 单测，禁止永久 skip；`.index/` 必须 gitignore；config status 只返回字段名与 ready/mock 状态；`EMBEDDING_DIM` 必须与所选模型实际输出维度一致（如 `Qwen3-Embedding-8B` 为 4096）。

### T-010: 财报类 RAG 命中偏差与片段过短
- **陷阱**：合并年报+季报的大文件把元数据表与 `[page 1]` 主要财务数据塞进同一 chunk；检索 snippet 仅 240 字且从表头截取，模型只看到所有者权益而看不到营收/净利润；语义 top1 常落到年报元数据表。
- **经验**：财报/研报 PDF 文本按 `[page N]` 先切页再分块；`build_excerpt` 从「主要财务数据/营业收入」起截取至 1200 字；财报问句对含指标正文加权、对纯元数据表降权；索引 `RAG_INDEX_VERSION` 变更触发重建。
- **避坑**：验收财报 RAG 时 Trace 里除 doc_id 外应能看到 `营业收入` 数值片段；一季报问句应命中 `q1_603288_2026` 而非 `ann_603288_2025` 元数据块。

### T-010: Chat 发送后消息消失与无进度反馈
- **陷阱**：`sendQuery` 在 fetch/SSE 失败时 `catch` 会移除乐观 user/assistant 两条消息，用户看到空白对话；SSE `error` 事件未处理时 `isQueryPending` 可能卡住；无 `activeSessionId` 时静默 return 但输入框已清空。
- **经验**：乐观 UI 必须先于网络请求 `set`；失败时保留 user 气泡、assistant 展示错误文案；处理 `error`/`done`/流结束三种收尾；`queryStatusLabel` + 助手 `status_label` 同步展示「识别意图 / 构建索引 / 检索 / 生成」；Vite `/api` 代理对 `/stream` 删除 `content-length` 减少缓冲。
- **避坑**：长耗时 RAG 首次建索引前，后端应 yield `正在构建知识库索引…` 状态；用户门禁验收时若改 vite 配置需重启 dev server。

### T-010: 索引构建超时与 Chat 500 返工
- **陷阱**：大 Embedding 模型全量 2000+ chunks 用 60s 固定超时、无重试、原子写入，某批超时后 8 分钟白跑且 `EmbeddingClientError` 穿透 Chat 变 500。
- **经验**：`EMBEDDING_TIMEOUT`（默认 180）+ 3 次指数退避重试；batch=4；`chunks.jsonl`/`vectors.jsonl` 每批 append 支持断点续建；增大 chunk（1036 块）减少调用；`retrieve` 对索引/查询 embed 失败统一降级 `mode=mock`。
- **避坑**：[SYSTEM] 建议回传系统级经验：外部 Embedding 批量索引必须可配置超时、重试、分批落盘；RAG 失败禁止未捕获异常直达 Chat 500；`REAL_API_TEST` 集成测应复用已建 `.index/` 避免每次 CI 跑 10 分钟。

### T-009: 硅基流动 LLM 真实接入
- **陷阱**：`ConfigManager` 只读 `app.toml` 时，写在 `backend/.env` 的 `LLM_*` 不会自动生效，`GET /api/config/status` 与真实调用都会误判为未配置。
- **经验**：在 `get_settings()` 中用 `dotenv_values` 叠加 `backend/.env` 到 `AppSettings` 字段；外部 HTTP 统一走 `httpx.AsyncClient(trust_env=False)`，解析 OpenAI 兼容 `choices[0].message.content` JSON。
- **避坑**：切换 Chat 到真实 LLM 后，所有依赖 `POST /api/chat/query` 的 pytest 需 autouse mock，否则 CI 无 Key 会 503；真实上游验收用 `REAL_API_TEST=1` 单测，禁止永久 skip。

### T-008: E2E Trace 选择器 strict mode（第 1 次返工）
- **陷阱**：管理端 Topbar 描述段落含「Trace 链路」子串（`同一会话基础上展示右侧 Trace 链路。`），与 TracePanel `<h2>Trace 链路</h2>` 同时存在；裸 `getByText('Trace 链路')` 在 Playwright strict mode 下双匹配直接失败，后续测算组件与 mobile 视口步骤均未执行。
- **经验**：等待 Trace 面板就绪应使用 `getByRole('heading', { name: 'Trace 链路' })` 或 `.trace-panel` 作用域内的 heading locator，避免与页面描述文案冲突。
- **避坑**：E2E 选择器优先 `getByRole('heading'|'button', ...)`、`data-testid` 或组件作用域 locator；对可能出现在副标题/描述与标题中的同一子串，禁止裸 `getByText`；Trace 多 step 展开后「查看完整 JSON」按钮会重复，须用 `.trace-step` 作用域限定。窄视口（≤1080px）侧栏 `display:none`，E2E 应跳过「新建会话/历史搜索/侧栏模式切换」，改用 `/admin`、`/client` 直链与 Topbar 导航。[SYSTEM] 建议回传系统级经验：Playwright strict mode 下宽泛文本选择器是跨项目通用踩坑点。

### Bugfix: 聊天气泡 Markdown 表格裸文本
- **陷阱**：后端 `split_body_paragraphs` 在无 `\n\n` 时按行拆段，前端 `text` rich_block 逐段 `<p>` 渲染，GFM 表格行被拆碎后 `react-markdown` 也无法识别。
- **经验**：前端用 `react-markdown` + `remark-gfm` 统一渲染 assistant 正文；`paragraphsToMarkdown()` 将表格行用 `\n`、普通段用 `\n\n` 合并；后端表格行分组为单 paragraph 兜底；流式中保持纯文本+光标，结束后走 Markdown。

### T-011: Rerank 重排 Trace 可观测性
- **陷阱**：`search_chunks` 里 `except Exception: pass` 会吞掉 Rerank 失败；Trace 只有 `rerank_connected` 布尔值，管理端无法核对重排依据。
- **经验**：Rerank 前捕获 top-N `RerankCandidateSnapshot`（chunk_id、title、hybrid_score），成功后写 `rerank_after`（rerank_score）；失败时 `logger.warning` + 保留 `rerank_before`、清空 `rerank_after`、降级 hybrid；`trace_service._rag_step` 的 `detail_sections` 增加「重排前候选」「重排后结果」。
- **避坑**：pycore `get_logger()` 输出不走 pytest `caplog`，验证 warning 需 `patch(logger.warning)`；`IndexSnapshot.version` 为 `int` 非字符串。

### T-011a: 系统权威时间注入
- **陷阱**：质检模型用训练截止附近的日历常识否定知识库中的 2025A/2026Q1 文档，误判「报告尚未发布」导致 FAIL。
- **经验**：`resolve_system_time()` 注入 `REFERENCE_DATE` 或 Asia/Shanghai 服务器日期；意图/回答/质检 System Prompt 前置权威时间块；`quality_check` payload 带 `system_context` + `rag_citations.time_period`；引用 `time` 展示 `2025A，本地知识库`。
- **避坑**：T-012 `context_preprocess` 应复用同一 `SystemTimeContext`，避免各节点各猜日期。

### T-012 P1: LangGraph 基础设施骨架
- **陷阱**：`prompts.py` 与 `prompts/` 包不能并存；须将原模块迁入 `prompts/__init__.py` + `prompts/_shared.py`，LangGraph 专用 intent 放 `prompts/intent.py`，LLMService 继续用 legacy intent 导出。
- **经验**：Phase 1 图用 stub 节点 + `routing.py` 条件边骨架即可 compile；`TraceRecorder.record()` 与 `create_langgraph_trace()` 先打通单步落库，Phase 2 起各节点末尾写 step。
- **避坑**：`is_langgraph_enabled()` 仅 `langgraph_env.strip()=="local"`；config/status `orchestration` 同时检查 LLM 配置；Phase 4 前勿改 `chat_service` 线性链路。

### T-012 P3: LangGraph 执行链路
- **陷阱**：并行 `rag_retrieval`/`tool_call` 若写 `current_node` 会触发 `InvalidUpdateError`；`response_assembly` 若让 LLM 填 calculator/stock_card 数字会与「数字来自 tool_result」冲突。
- **经验**：用 `build_parallel_trace_update` 只 append `trace_steps`；`rag_retrieval` Trace 复用 `RerankCandidateSnapshot` 写 `detail_sections`；`response_assembly` 从 `evidence_pack.tool_result` 构造 `ranking_table`/`stock_card`/`calculator` 再 `enrich_rich_blocks`；`quality_check` 在组装前对 draft answer 调 `LLMService.quality_check` 并映射 pass/revise/reject。
- **避坑**：`prediction_request` 走 `fallback_response` 模板禁 LLM 测算数字；Runner `ainvoke` 末尾 append `END` step；集成测 mock `_intent_client` + `_output_client` + `RagService.retrieve`。

### T-012 P4: Chat 接入 LangGraph
- **陷阱**：`get_settings()` 通过 `dotenv_values` 读 `backend/.env`，`monkeypatch.setenv("LANGGRAPH_ENV")` 对 pytest 无效；conftest 应 patch `is_langgraph_enabled` 或 mock `dotenv_values`。
- **经验**：`LangGraphRunner.run_stream` 用 `astream(stream_mode="values")` + `stream_callback` 队列推 SSE；结束后 `create_langgraph_trace` + `END` step；`chat_service` 删除线性 `create_llm_trace` 路径。
- **避坑**：conftest 勿 patch `runner.LLMService` 为 lambda，会破坏 `LLMService.default_blocks` 类方法调用；用 `llm_service_module.LLMService.default_blocks`；每轮图执行前重置 `_intent_call_count`；data_query 测算 mock 槽位须含 `metric` 避免澄清分支。

### T-012 P2: LangGraph 前置链路
- **陷阱**：节点直接 `from ...integrations.langgraph.state` 会触发 `langgraph/__init__.py`  eager import `runner` → `graph` → `ALL_NODES`，与 `agents.nodes` 形成循环依赖；`Send` 并行分支若同时写 `current_node` 会触发 `InvalidUpdateError`。
- **经验**：`langgraph/__init__.py` 用 `__getattr__` 懒加载 `LangGraphRunner`；前置节点用 `_helpers.run_node_with_trace` 统一写 step；`rag_retrieval`/`tool_call` Phase 2 stub 不写 `current_node`。
- **避坑**：`clarification_check` 对 `time_range` 单独处理默认可路由；测试导入节点模块时注意包初始化顺序；集成测 mock `_intent_client` 即可覆盖意图/槽位/澄清三段 LLM。

### Query 改写（T-014 backlog，延后）
- **决策**：V1.1 阶段不实现独立 `query_rewrite` 节点；当前 RAG 主路径为 BM25 + 向量混合 + 可选 Rerank，检索 Query 使用 `normalized_query`。
- **经验**：多轮指代与口语化召回问题，在槽位 `pending_slots` 未闭环前，LLM 改写收益有限且易幻觉；优先 F19 再 F18。
- **避坑**：文档已写入 `docs/agent/langgraph-flow.md` §7、`docs/Plan.md` F18、`tasks.json` T-014（status=backlog）；勿在 T-012～T-013 验收中要求 retrieval_query 字段。

### 短期对话记忆（T-015～T-017 backlog，2026-06-12 补入）
- **决策**：PRD 短期记忆为同会话最近 5 轮 QA；长期记忆 V2+ 延后。实施顺序 T-015（窗口）→ T-016（pending_slots）→ T-017（下游注入）→ T-014（Query 改写）。
- **现状**：`runner` 已读 10 条消息、`history_summary`  mainly 供意图识别；槽位不跨轮、`response_assembly` 不看历史。
- **避坑**：勿把 UI 会话列表当成 Agent 多轮智能；验收须用指代续问用例（如宁德时代 → 它一季报）。

### 知识库扩容方法论（2026-06-12）
- **决策**：raw 数据（PDF 解析、网页整理、CSV）入库的统一手册沉淀在 `docs/knowledge-base-ingestion.md`；目录索引仍用 `backend/data/knowledge-base/README.md`。
- **经验**：扩容按「分类落盘 → 元数据表 → document_manifest 登记 → 升 RAG_INDEX_VERSION → 检索冒烟」执行；财报合并文件须在 `## 2025 年年度报告` / `## 2026 年第一季度报告` 分节各配 `doc_id`；正文放在 `## 原始解析文本` 之后，元数据勿与财务正文混段。
- **避坑**：给 Agent 贴 raw 时附带 `docs/knowledge-base-ingestion.md` §12 指令模板；勿只加 .md 不更新 manifest；Mock 行情放 `backend/data/mock/` 而非本目录。

### 助手气泡操作按钮（复制 / 重新生成 / 反馈）
- **陷阱**：重新生成若走 `query_stream` 会重复插入 user 消息；前端若不复用 SSE 事件处理，`sendQuery` 与 `regenerateMessage` 容易分叉。
- **经验**：后端抽取 `_stream_assistant_reply`，`regenerate_stream` 删除旧 assistant 后 yield `message_removed` 再流式生成；前端 `handleChatStreamEvent` + `runChatStream` 共用，`regenerateMessage` 仅替换 assistant 占位、不设 `pendingUserId`。
- **避坑**：操作栏仅在 `!streaming && hasAnswerBody && !pending_` 时显示；反馈只做 Demo UI，勿误接 API。

### [T-019]: 知识库扩容——创业板 50 家财报（新浪 API）
- **陷阱**：新浪 `report_list` 按报告期键倒序时，文件名 period 标签会变成 `2026Q1-2025A`；manifest 若先写入错误路径，幂等重跑不会自动修正。
- **经验**：用 `requests.Session(trust_env=False)` + ≥1s 节流拉三表；`_sorted_period_keys` 固定「年报 12-31 → 一季报 03-31」顺序；`### 主要财务数据` 表格正文可独立切块且含「营业收入」；无 pypinyin 时用 `chinext-{code}` slug 后备。
- **避坑**：structured-data 行数统计勿用 `| company_` 子串（会误计表头）；入库后升 `RAG_INDEX_VERSION` 并更新 `test_count_markdown_files_matches_repository`；全量 embedding 需重启后端触发。

### [T-020]: 工具数据丰富度路线图与问数动态编排
- **决策**：后续工具增强顺序与验收标准统一维护在 `docs/agent/tool-richness-roadmap.md`；`.sdd/status.json` 的 `current_task` / `notes` 指向当前 Phase。用户说「问数验收过了」或「继续工具路线图」时，Agent 应读 roadmap 执行 **T-021 估值**。
- **经验**：问数对齐问股方案 C：`data_query_tool_plan.py` 白名单 + `agent_tool_names`；`local_return_calculator` 槽位齐全时独占；热力图与排行可同时 `tool_names` 双工具。路由层勿再用 `wants_sector_heatmap` 硬切单工具。
- **避坑**：`time_range` 跨日历史仍属 T-020-P2/P3，P1 勿在正文假装已查区间；验收清单见 roadmap §2.4。

### [T-020]: 回答生成过程状态时间线（展开/折叠）
- **陷阱**：`tool_call` 若在解析 `tool_names` 之前发 progress 事件，资料子项会漏掉动态标的；`ProgressTimelineTracker` 与 `stream_callback` 存在循环引用，须先声明 tracker 再赋值。
- **经验**：后端用 `step_start` / `step_complete` / `response_stream_start` 三事件驱动；`tool_call` 在 `_resolve_tool_names` 后调用 `emit_tool_progress_start/end`；首包 `content_delta` 或兜底 `content_done` 前触发折叠；前端 timeline 存 `message.progress_timeline`（客户端字段），Mock `simulateQueryStream` 须模拟完整 6 步。
- **避坑**：澄清/兜底分支在 `routing_decision` 完成时勿误发 `match_expert`；并行 tool/rag 用 `_needs_tool/_needs_rag` 协调 `fetch_materials` 完成时机；历史消息无 timeline 时不渲染过程区。

- **决策**：问股链路在首轮 `tool_call + rag_retrieval → evidence_merge` 后增加 `evidence_gap_check → gap_planner → 定向补数 → evidence_merge(第2轮) → quality_check`；非问股路由直接跳过。
- **经验**：缺口由 `services/evidence_gaps.py` 规则检测（无公司 RAG、单期财报、亏损、风险信号未解释、缺估值工具）；`gap_planner` 生成 `rag_queries` + 可选 `valuation_profile_lookup` / **`stock_evidence_api_lookup`（巨潮公告+东财快讯）**；`company_rag_missing` 等缺口时补数并行 `rag_retrieval` + API `tool_call`；`RagService.retrieve_targeted` 对无 KB 文档标的须 `entity_name` 过滤，避免家电/调味品误召回；`evidence_merge` 用 `accumulated_*` 累加证据；Trace 可见 `evidence_gap_check` / `gap_planner`；前端 status 为 `Enriching`。
- **避坑**：仅允许一轮补数（`evidence_supplement_done`）；补数不能替代 T-022 财报字段扩展；`response_assembly` 仍用 state 中合并后的 `rag_hits`；API 快讯不得替代结构化财报数字。

### T-012: response_assembly 超时与风险提示
- **陷阱**：热点链路 evidence_pack 原文塞进 output prompt 易触发 LLM 超时，Trace 各节点 success 但 `assistant_message.content` 为空；问股长文经 citation retry 缓冲输出时，若在 `_emit_buffered_content` 之后才 `ensure_public_risk_notice`，流式 delta 与 `final_response` 不一致。
- **经验**：组装前用 `_compact_evidence_for_prompt()` 截断/摘要 evidence；`LLMClientError` 必须走 `_fallback_assembly_content()` 且 `runner` 对空 `final_response` 兜底；`ensure_public_risk_notice()` 应在任何 `content_delta` / `content_done` 发出之前执行，非 citation 校验路径对新增后缀单独 `_emit_delta`。
- **避坑**：Tester 除看 `final_response` 外，流式场景应断言 delta 拼接结果含标准免责声明；质量门禁 KB 文件计数测试应绑定 `list_markdown_files()` 而非硬编码常量。

### T-020: 澄清/兜底非流式路径折叠事件修复（第 2 轮）
- **陷阱**：`run_stream` 在图结束后调用 `progress_tracker.on_response_stream_start()` 时，`_yield_events_during_task` 循环已退出，事件只入队未冲刷，客户端收不到 `response_stream_start`。
- **经验**：非流式 `content_done` 分支须在 `on_response_stream_start()` 后 `_drain_stream_queue` 并 `yield` 队列事件；前端 `content_done` 可对未折叠 timeline 做兜底调用 `applyResponseStreamStart`；集成测试须覆盖澄清/兜底 HTTP stream 且断言 `response_stream_start` 在 `content_done` 之前。
- **避坑**：[SYSTEM] 建议回传系统级经验：Runner 图结束后若经 callback 入队 SSE 事件，必须显式 drain 并 yield，不能假设 pump 循环仍在运行；chat 集成测试应 patch `mock_llm_service._intent_client` 而非类级 `LLMService._intent_client`（autouse fixture 已替换实例）。

### T-013 / T-020: 用户门禁收口（2026-06-18）
- **经验**：T-013（V1.1 全链路）与 tasks.json T-020（过程时间线）用户门禁均已确认；`status.json` 下一焦点切到 `roadmap-T-020`（问数工具丰富度 P1，见 `docs/agent/tool-richness-roadmap.md` §2.4），勿与 tasks T-020 任务 ID 混淆。
- **避坑**：本地仍有未提交改动（问数去 Mock、时间线 UI 等），打新检查点前须 commit；roadmap §2.4 第 5 条「demo 降级」已因问数 Mock 删除而过时，验收改为 API 失败空结果 + 正文说明。

### 路线图 T-020-P1：问数工具丰富度用户验收（2026-06-18）
- **经验**：P1 通过后 `status.json` → `roadmap-T-021`；T-020 在路线图 §一 标为「P1 已验收、P2/P3 待办」，勿与 tasks.json 的 T-020（过程时间线）混淆。
- **经验**：排行表 `ranking_table` 富组件须用中文表头（`排名/股票/板块/涨跌幅/收盘价`），字段 key 仅作行数据键，不可直接渲染为表头。

### 路线图 T-021-P1：估值历史分位（2026-06-15）
- **经验**：`valuation_profile_lookup` 实时估值仍走腾讯 `qt.gtimg.cn`；近 3 年 PE/PB 分位走东财 `datacenter-web` `RPT_VALUEANALYSIS_DET`，输出 `valuation_history`（`pe_ttm`/`pb` 分位 + `quarterly_series`）。PE 分位仅统计 PE>0 盈利期样本；亏损期当前 PE 可能为负，须在 `notes` 与正文说明。
- **避坑**：历史接口失败时须降级为仅实时估值，不得编造分位；`citation_catalog` 组装上下文须附带 `valuation_history` JSON，否则 assembly 易退回单点 PE 解读。

### 路线图 T-021-P1：估值工具丰富度用户验收（2026-06-19）
- **经验**：P1 通过后 `status.json` → `roadmap-T-022`；T-021 在路线图 §一 标为「P1 已验收、P2/P3 待办」，勿与 tasks.json 任务 ID 混淆。
- **经验**：用户说「估值 P1 验收通过」或「继续工具路线图」时，下一项为 **T-022 问股财报深化**（现金流/负债、RAG 多期、KB 扩容）。

### 路线图 T-022：问股财报深化（2026-06-19）
- **经验**：`periods[]` 扩展 `operating_cash_flow` / `debt_ratio`；Sina 拉三表（lrb/fzb/llb），KB loader 解析现金流量表与资产总计行。
- **经验**：`diversify_hits_by_time_period` 在 `retrieve_targeted` 与问股 `rag_retrieval` 应用，避免 RAG 命中全为同一 `time_period`。
- **避坑**：入库脚本 `_pick_periods` 扩展为「最新季报 + 至多 3 年报」后，须 `--dry-run` 验证再批量写入；已有 KB 文件不会自动更新，需重跑 ingest。

### 路线图 T-022-P1/P2：问股财报深化用户验收（2026-06-19）
- **经验**：P1/P2 通过后 `status.json` → `roadmap-T-023`；T-022 在路线图 §一 标为「P1/P2 已验收、P3 KB 重跑待办」。
- **经验**：用户说「财报 P1 验收通过」时，下一项为 **T-023 热点工具丰富度**（公告自动拉取、动态 tool_names、热点 RAG 多月份）。
