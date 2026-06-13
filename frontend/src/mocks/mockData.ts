import type {
  ConfigStatus,
  DataSourceStatus,
  Message,
  RichBlock,
  Session,
  SessionSource,
  Trace,
  TraceStep,
} from '../types/api'

export interface MockSessionEntity extends Session {
  agent_label: string
  default_trace_id: string
}

const now = '2026-06-08T14:05:00+08:00'

const rankingBlock: RichBlock = {
  id: 'block_001',
  type: 'ranking_table',
  title: '半导体板块涨幅排行',
  payload: {
    columns: ['排名', '股票名称', '涨跌幅', '收盘价'],
    rows: [
      { 排名: 1, 股票名称: '寒武纪', 涨跌幅: '+8.76%', 收盘价: '287.50' },
      { 排名: 2, 股票名称: '北方华创', 涨跌幅: '+6.23%', 收盘价: '385.20' },
      { 排名: 3, 股票名称: '中微公司', 涨跌幅: '+5.87%', 收盘价: '198.60' },
      { 排名: 4, 股票名称: '韦尔股份', 涨跌幅: '+4.52%', 收盘价: '112.80' },
      { 排名: 5, 股票名称: '兆易创新', 涨跌幅: '+4.11%', 收盘价: '145.30' },
    ],
  },
  sources: [{ type: 'market', label: '本地行情模拟数据', time: '2026-06-08 14:05' }],
  risk_notice: '以上内容仅为信息整理，不构成投资建议。',
}

const stockBlock: RichBlock = {
  id: 'block_002',
  type: 'stock_card',
  title: '个股基本面信息卡',
  payload: {
    name: '宁德时代',
    code: '300750',
    price: '185.42',
    change_pct: '+2.18%',
    tags: ['动力电池', '新能源车', '创业板'],
    metrics: {
      columns: ['指标', '当前值', '报告期', '解读'],
      rows: [
        { metric: '营业收入', value: '4009.2亿', period: '2025年报', note: '规模保持行业领先' },
        { metric: '归母净利润', value: '441.2亿', period: '2025年报', note: '盈利能力稳定' },
        { metric: 'ROE', value: '21.6%', period: '2025年报', note: '资本回报较强' },
        { metric: '毛利率', value: '22.9%', period: '2025年报', note: '制造端仍具规模优势' },
        { metric: '净利率', value: '11.0%', period: '2025年报', note: '费用与价格压力需要跟踪' },
        { metric: '经营性现金流量净额', value: '683.5亿', period: '2025年报', note: '现金创造能力较强' },
      ],
    },
  },
  sources: [
    { type: 'financial', label: '本地财务模拟数据', time: '2025年报' },
    { type: 'report', label: '本地研报摘要', time: '2026-06-06' },
  ],
  risk_notice: '以上为个股基本面信息整理，不构成投资建议。',
}

const stockAnalysisBlock: RichBlock = {
  id: 'block_002_analysis',
  type: 'text',
  title: '基本面点评',
  payload: {
    paragraphs: [
      '从模拟财务口径看，宁德时代仍然呈现典型龙头公司的基本面特征：收入规模和利润体量较大，ROE 维持在较高水平，说明资产周转和盈利能力仍有支撑。毛利率保持在两成以上，反映制造效率、客户结构和供应链议价仍有优势；净利率低于毛利率较多，也提示价格竞争、研发投入和费用端压力不能忽视。经营性现金流量净额为正且规模较高，说明利润质量相对扎实，不是单纯依赖账面利润。后续更值得跟踪的是动力电池价格周期、海外产能爬坡、储能业务占比变化，以及现金流能否持续覆盖资本开支。',
    ],
  },
  sources: [],
  risk_notice: stockBlock.risk_notice,
}

const hotspotBlock: RichBlock = {
  id: 'block_003',
  type: 'text',
  title: '热点归因摘要',
  payload: {
    paragraphs: [
      '市场表现：机器人板块今日模拟涨幅 +3.47%，成交额 187.3 亿。',
      '当日驱动：产业政策发布与人形机器人量产进展形成短期催化。',
      '近期背景：相关 ETF 资金流入和机构研报关注度上升。',
    ],
  },
  sources: [
    { type: 'market', label: '本地行情模拟数据', time: '2026-06-08 10:32' },
    { type: 'report', label: '本地研报摘要', time: '2026-06-07' },
  ],
  risk_notice: '热点归因只做信息整理，相关标的为客观列示，不构成投资建议。',
}

export const calculatorBlock: RichBlock = {
  id: 'block_004',
  type: 'calculator',
  title: '收益率测算组件',
  payload: {
    fields: [
      { key: 'buy_price', label: '买入价', value: 15, unit: '元' },
      { key: 'target_price', label: '情景价', value: 20, unit: '元' },
      { key: 'share_count', label: '持仓数量', value: 1000, unit: '股' },
      { key: 'fee_rate', label: '估算费率', value: 0.03, unit: '%' },
    ],
    results: [
      { key: 'return_rate', label: '收益率', value: '33.27%' },
      { key: 'profit_amount', label: '预估盈亏', value: '4991.50 元' },
      { key: 'cost_amount', label: '测算成本', value: '15000.00 元' },
    ],
  },
  sources: [],
  risk_notice: '测算结果仅基于用户输入参数，不构成投资建议。',
}

const heatmapBlock: RichBlock = {
  id: 'block_demo_heatmap',
  type: 'sector_heatmap',
  title: '行业板块热力图',
  payload: {
    board_kind: 'industry',
    trade_date: '2026-06-08',
    size_by: 'turnover_amount',
    tiles: [
      { board_name: '半导体', board_code: 'BK1036', pct_change: 3.42, turnover_amount: 84200000000, leader: '寒武纪', leader_change: 8.76, up_count: 0, down_count: 0 },
      { board_name: '白酒', board_code: 'BK0477', pct_change: -0.85, turnover_amount: 62100000000, leader: '贵州茅台', leader_change: -0.42, up_count: 0, down_count: 0 },
      { board_name: '电池', board_code: 'BK1033', pct_change: 1.28, turnover_amount: 59800000000, leader: '宁德时代', leader_change: 2.18, up_count: 0, down_count: 0 },
      { board_name: '光学光电子', board_code: 'BK1038', pct_change: 2.91, turnover_amount: 45600000000, leader: '京东方A', leader_change: 3.55, up_count: 0, down_count: 0 },
      { board_name: '证券', board_code: 'BK0473', pct_change: 0.64, turnover_amount: 43200000000, leader: '中信证券', leader_change: 0.88, up_count: 0, down_count: 0 },
      { board_name: '医疗器械', board_code: 'BK1041', pct_change: -1.12, turnover_amount: 38900000000, leader: '迈瑞医疗', leader_change: -0.95, up_count: 0, down_count: 0 },
      { board_name: '汽车零部件', board_code: 'BK0481', pct_change: 1.76, turnover_amount: 36500000000, leader: '比亚迪', leader_change: 1.44, up_count: 0, down_count: 0 },
      { board_name: '通信设备', board_code: 'BK0448', pct_change: 2.35, turnover_amount: 34100000000, leader: '中兴通讯', leader_change: 2.02, up_count: 0, down_count: 0 },
      { board_name: '电力', board_code: 'BK0428', pct_change: 0.22, turnover_amount: 31800000000, leader: '长江电力', leader_change: 0.15, up_count: 0, down_count: 0 },
      { board_name: '银行', board_code: 'BK0475', pct_change: -0.31, turnover_amount: 30500000000, leader: '招商银行', leader_change: -0.28, up_count: 0, down_count: 0 },
      { board_name: '软件开发', board_code: 'BK0737', pct_change: 1.95, turnover_amount: 28800000000, leader: '金山办公', leader_change: 2.31, up_count: 0, down_count: 0 },
      { board_name: '光伏设备', board_code: 'BK1031', pct_change: -0.68, turnover_amount: 26500000000, leader: '隆基绿能', leader_change: -1.02, up_count: 0, down_count: 0 },
    ],
  },
  sources: [{ type: 'market', label: '本地 demo 行业板块截面', time: '2026-06-08 11:20' }],
  risk_notice: '以上内容仅为信息整理，不构成投资建议。',
}

const knowledgeBlock: RichBlock = {
  id: 'block_005',
  type: 'text',
  title: '知识库解释',
  payload: {
    paragraphs: ['同比用于比较同一周期的年度变化，环比用于比较相邻周期的变化。系统会根据用户问题选择更合适的展示方式。'],
  },
  sources: [{ type: 'knowledge', label: '本地投研知识库', time: '2026-06-08' }],
  risk_notice: '以上解释来自本地投研知识库，不构成投资建议。',
}

function createCitationBlock(block: RichBlock): RichBlock {
  const sources = block.sources.length > 0 ? block.sources : [{ type: 'qa' as const, label: '用户输入参数', time: '本轮会话' }]
  return {
    id: `${block.id}_citation`,
    type: 'citation_list',
    title: '引用来源',
    payload: { items: sources },
    sources,
    risk_notice: block.risk_notice,
  }
}

function createRiskBlock(block: RichBlock): RichBlock {
  return {
    id: `${block.id}_risk`,
    type: 'risk_notice',
    title: '风险提示',
    payload: {
      level: 'medium',
      text: block.risk_notice,
      items: ['不提供买入、卖出或目标价建议'],
    },
    sources: [],
    risk_notice: block.risk_notice,
  }
}

export const mockSessions: MockSessionEntity[] = [
  {
    id: 'sess_20260608_006',
    title: '帮我看一下今天A股行业板块热力图',
    title_source: 'first_query',
    is_draft: false,
    source: 'client',
    created_at: '2026-06-08T11:20:00+08:00',
    updated_at: '2026-06-08T11:20:18+08:00',
    last_message_preview: '近一交易日 A 股行业板块呈现「科技偏强、消费分化、金融平稳」的结构',
    last_trace_id: 'trace_20260608_006',
    agent_label: '问数助手',
    default_trace_id: 'trace_20260608_006',
  },
  {
    id: 'sess_20260608_001',
    title: '今天涨幅靠前的半导体股票有哪些',
    title_source: 'first_query',
    is_draft: false,
    source: 'client',
    created_at: now,
    updated_at: '2026-06-08T14:05:12+08:00',
    last_message_preview: '今日半导体板块涨幅靠前的个股如下',
    last_trace_id: 'trace_20260608_001',
    agent_label: '问数助手',
    default_trace_id: 'trace_20260608_001',
  },
  {
    id: 'sess_20260608_002',
    title: '宁德时代基本面怎么样',
    title_source: 'first_query',
    is_draft: false,
    source: 'client',
    created_at: '2026-06-08T13:42:00+08:00',
    updated_at: '2026-06-08T13:42:21+08:00',
    last_message_preview: '我会从公司业务、财务指标、研报观点和风险提示四个维度整理',
    last_trace_id: 'trace_20260608_002',
    agent_label: '问股助手',
    default_trace_id: 'trace_20260608_002',
  },
  {
    id: 'sess_20260608_003',
    title: '机器人板块今天为什么涨',
    title_source: 'first_query',
    is_draft: false,
    source: 'client',
    created_at: '2026-06-08T10:32:00+08:00',
    updated_at: '2026-06-08T10:32:34+08:00',
    last_message_preview: '我会区分当日驱动和近期背景',
    last_trace_id: 'trace_20260608_003',
    agent_label: '热点助手',
    default_trace_id: 'trace_20260608_003',
  },
  {
    id: 'sess_20260608_004',
    title: '15元买入未来预期回报率怎么算',
    title_source: 'first_query',
    is_draft: false,
    source: 'client',
    created_at: '2026-06-08T09:58:00+08:00',
    updated_at: '2026-06-08T09:58:19+08:00',
    last_message_preview: '已生成可交互测算组件',
    last_trace_id: 'trace_20260608_004',
    agent_label: '测算组件',
    default_trace_id: 'trace_20260608_004',
  },
  {
    id: 'sess_20260607_001',
    title: '财报同比和环比有什么差异',
    title_source: 'first_query',
    is_draft: false,
    source: 'client',
    created_at: '2026-06-07T18:20:00+08:00',
    updated_at: '2026-06-07T18:20:12+08:00',
    last_message_preview: '已生成知识库解释',
    last_trace_id: 'trace_20260608_005',
    agent_label: '投研知识库',
    default_trace_id: 'trace_20260608_005',
  },
]

export const mockMessagesBySession: Record<string, Message[]> = {
  sess_20260608_006: [
    {
      id: 'msg_heatmap_user',
      session_id: 'sess_20260608_006',
      role: 'user',
      content: '帮我看一下今天A股行业板块热力图',
      rich_blocks: [],
      trace_id: null,
      created_at: '2026-06-08T11:20:00+08:00',
    },
    {
      id: 'msg_heatmap_assistant',
      session_id: 'sess_20260608_006',
      role: 'assistant',
      content:
        '近一交易日 A 股行业板块呈现「科技偏强、消费分化、金融平稳」的结构。下方热力图按成交额缩放方块面积，红涨绿跌。',
      rich_blocks: [heatmapBlock],
      trace_id: 'trace_20260608_006',
      created_at: '2026-06-08T11:20:18+08:00',
    },
  ],
  sess_20260608_001: [
    {
      id: 'msg_001',
      session_id: 'sess_20260608_001',
      role: 'user',
      content: '今天涨幅靠前的半导体股票有哪些？',
      rich_blocks: [],
      trace_id: null,
      created_at: now,
    },
    {
      id: 'msg_002',
      session_id: 'sess_20260608_001',
      role: 'assistant',
      content: '今日半导体板块涨幅靠前的个股如下。',
      rich_blocks: [rankingBlock],
      trace_id: 'trace_20260608_001',
      created_at: '2026-06-08T14:05:12+08:00',
    },
  ],
  sess_20260608_002: [
    {
      id: 'msg_003',
      session_id: 'sess_20260608_002',
      role: 'user',
      content: '宁德时代基本面怎么样？',
      rich_blocks: [],
      trace_id: null,
      created_at: '2026-06-08T13:42:00+08:00',
    },
    {
      id: 'msg_004',
      session_id: 'sess_20260608_002',
      role: 'assistant',
      content: '以下是宁德时代的基本面信息整理（演示会话：正文为 Markdown，富组件见「排行表」「测算器」示例会话）。',
      rich_blocks: [],
      trace_id: 'trace_20260608_002',
      created_at: '2026-06-08T13:42:21+08:00',
    },
  ],
  sess_20260608_003: [
    {
      id: 'msg_005',
      session_id: 'sess_20260608_003',
      role: 'user',
      content: '机器人板块今天为什么涨？',
      rich_blocks: [],
      trace_id: null,
      created_at: '2026-06-08T10:32:00+08:00',
    },
    {
      id: 'msg_006',
      session_id: 'sess_20260608_003',
      role: 'assistant',
      content: '我会区分当日驱动和近期背景，避免把旧新闻误归因为当天因素（演示会话：热点解读为 Markdown 正文）。',
      rich_blocks: [],
      trace_id: 'trace_20260608_003',
      created_at: '2026-06-08T10:32:34+08:00',
    },
  ],
  sess_20260608_004: [
    {
      id: 'msg_007',
      session_id: 'sess_20260608_004',
      role: 'user',
      content: '如果我 15 元买入，未来到 20 元，预期回报率是多少？',
      rich_blocks: [],
      trace_id: null,
      created_at: '2026-06-08T09:58:00+08:00',
    },
    {
      id: 'msg_008',
      session_id: 'sess_20260608_004',
      role: 'assistant',
      content: '已生成可交互测算组件，你可以调整买入价、情景价和持仓数量。',
      rich_blocks: [calculatorBlock],
      trace_id: 'trace_20260608_004',
      created_at: '2026-06-08T09:58:19+08:00',
    },
  ],
  sess_20260607_001: [
    {
      id: 'msg_009',
      session_id: 'sess_20260607_001',
      role: 'user',
      content: '财报同比和环比有什么差异？',
      rich_blocks: [],
      trace_id: null,
      created_at: '2026-06-07T18:20:00+08:00',
    },
    {
      id: 'msg_010',
      session_id: 'sess_20260607_001',
      role: 'assistant',
      content: '下面是相关知识解释（演示会话：纯 Markdown 正文）。',
      rich_blocks: [],
      trace_id: 'trace_20260608_005',
      created_at: '2026-06-07T18:20:12+08:00',
    },
  ],
}

function makeStep(
  step_index: number,
  name: string,
  node: string,
  latency_ms: number,
  summary: string,
  items: Array<{ label: string; value: string }>,
  raw_json: Record<string, unknown>,
): TraceStep {
  return {
    step_id: `step_${String(step_index).padStart(3, '0')}`,
    step_index,
    name,
    node,
    status: 'success',
    latency_ms,
    summary,
    detail_sections: [{ title: name, items }],
    input: { query: raw_json.query ?? 'mock query' },
    output: { status: 'success' },
    raw_json,
    error: null,
  }
}

export const mockTraces: Record<string, Trace> = {
  trace_20260608_001: {
    id: 'trace_20260608_001',
    session_id: 'sess_20260608_001',
    message_id: 'msg_002',
    user_query: '今天涨幅靠前的半导体股票有哪些',
    status: 'success',
    steps: [
      makeStep(1, '上下文预处理', 'master_bot_preprocessing', 38, '加载会话摘要，本轮 Query 主体明确，无需指代消解。', [
        { label: '输入', value: '用户 Query 与最近 1 轮会话摘要' },
        { label: '输出', value: '无指代消解需求' },
      ], { node: 'master_bot_preprocessing', latency_ms: 38, pronoun_resolution: false }),
      makeStep(2, '意图与槽位', 'master_bot_intent_recognition', 278, '意图：数据查询；主体：半导体；动作：排名。', [
        { label: '意图', value: '行情查询 / 板块行情查询' },
        { label: '槽位', value: 'subject=半导体，metric=涨跌幅，top_n=10' },
      ], { node: 'master_bot_intent_recognition', sub_agent: 'data_agent', global_slots: { subject_name: '半导体', action_type: '排名', missing_slots: [] } }),
      makeStep(3, '路由决策', 'master_bot_router', 6, '路由到问数助手，执行客观数据查询。', [
        { label: '路由', value: 'route_to_data_agent' },
        { label: '理由', value: '用户请求板块内涨幅排名，不需要热点归因' },
      ], { node: 'master_bot_router', decision: 'route_to_data_agent', reason: '数据查询' }),
      makeStep(4, '槽位转换', 'slot_converter', 4, '转换为问数助手任务槽位。', [
        { label: '指标', value: '涨跌幅' },
        { label: '排序', value: '降序' },
      ], { node: 'slot_converter', task_slots: { metric: '涨跌幅', ranking_order: 'desc', top_n: 10 } }),
      makeStep(5, '工具调用', 'market_data_tool', 198, 'market_data_tool 返回半导体板块涨幅 Top10。', [
        { label: '工具', value: 'market_data_tool' },
        { label: '请求', value: 'sector=半导体，metric=涨跌幅' },
        { label: '响应', value: '返回 Top10，摘要展示前 5 条' },
      ], { tool_name: 'market_data_tool', request: { sector: '半导体', metric: '涨跌幅', order: 'desc' }, response: { status: 'success', count: 10 } }),
      makeStep(6, '质检合规', 'quality_check', 52, '风险提示存在，citation 完整，结果 PASS。', [
        { label: '合规', value: '未命中黑名单表达' },
        { label: '引用', value: '行情数据来源与截止时间完整' },
        { label: '结论', value: 'PASS' },
      ], { node: 'quality_check', compliance_scan: { passed: true }, citation_check: { passed: true }, overall_result: 'PASS' }),
      makeStep(7, '最终输出', 'final_assembly', 8, '生成排行表、来源标签和风险提示。', [
        { label: '组件', value: 'ranking_table + citation_list + risk_notice' },
        { label: '输出', value: '已渲染到客户端和管理端' },
      ], { node: 'final_assembly', rich_blocks: ['ranking_table', 'citation_list', 'risk_notice'] }),
    ],
    metadata: {
      total_latency_ms: 2240,
      tool_calls_count: 1,
      quality_check_result: 'PASS',
      model_versions: { master_bot: 'mock-master', data_agent: 'mock-data-agent' },
    },
  },
  trace_20260608_002: {
    id: 'trace_20260608_002',
    session_id: 'sess_20260608_002',
    message_id: 'msg_004',
    user_query: '宁德时代基本面怎么样',
    status: 'success',
    steps: [
      makeStep(1, '上下文预处理', 'master_bot_preprocessing', 41, '识别用户关注新能源和基本面维度。', [{ label: '用户偏好', value: '新能源、基本面、机构评级' }], { node: 'preprocess', insights: ['新能源', '基本面'] }),
      makeStep(2, '意图与槽位', 'master_bot_intent_recognition', 295, '意图：个股基本面分析；主体：宁德时代。', [{ label: '主体', value: '宁德时代 / 300750' }, { label: '风险等级', value: '中' }], { sub_agent: 'stock_agent', subject_name: '宁德时代' }),
      makeStep(3, '工具调用', 'stock_agent_tools', 846, '查询公司信息、财务指标、研报观点。', [{ label: '工具', value: 'company_profile_tool、financial_data_tool、research_report_tool' }], { tools: ['company_profile_tool', 'financial_data_tool', 'research_report_tool'] }),
      makeStep(4, '质检合规', 'quality_check', 74, '机构观点不包装成系统建议，风险提示完整。', [{ label: '合规', value: 'PASS' }], { overall_result: 'PASS' }),
    ],
    metadata: {
      total_latency_ms: 3180,
      tool_calls_count: 3,
      quality_check_result: 'PASS',
      model_versions: { master_bot: 'mock-master', stock_agent: 'mock-stock-agent' },
    },
  },
  trace_20260608_003: {
    id: 'trace_20260608_003',
    session_id: 'sess_20260608_003',
    message_id: 'msg_006',
    user_query: '机器人板块今天为什么涨',
    status: 'success',
    steps: [
      makeStep(1, '上下文预处理', 'master_bot_preprocessing', 45, '识别用户偏好产业链逻辑。', [{ label: '偏好', value: '政策驱动、产业链逻辑' }], { node: 'preprocess' }),
      makeStep(2, '意图与槽位', 'master_bot_intent_recognition', 312, '意图：热点归因；主体：机器人板块；时间：今天。', [{ label: '主体', value: '机器人板块' }], { sub_agent: 'hotspot_agent' }),
      makeStep(3, '工具调用', 'hotspot_agent_tools', 1077, '并行查询行情、新闻、研报。', [{ label: '工具', value: 'market_data_tool、news_retrieval_tool、research_report_tool' }], { tools_parallel: true, count: 3 }),
      makeStep(4, '质检合规', 'quality_check', 89, '检查黑名单表达、时间口径和引用完整性。', [{ label: '合规', value: 'PASS' }, { label: '时间', value: '当日驱动与近期背景已区分' }], { overall_result: 'PASS' }),
    ],
    metadata: {
      total_latency_ms: 4760,
      tool_calls_count: 3,
      quality_check_result: 'PASS',
      model_versions: { master_bot: 'mock-master', hotspot_agent: 'mock-hotspot-agent' },
    },
  },
  trace_20260608_004: {
    id: 'trace_20260608_004',
    session_id: 'sess_20260608_004',
    message_id: 'msg_008',
    user_query: '15元买入未来预期回报率怎么算',
    status: 'success',
    steps: [
      makeStep(1, '参数识别', 'calculator_param_parser', 28, '识别买入价 15 元、情景价 20 元。', [{ label: '买入价', value: '15' }, { label: '情景价', value: '20' }, { label: '数量', value: '默认 1000 股，可调整' }], { buy_price: 15, target_price: 20, shares: 1000 }),
      makeStep(2, '富响应选择', 'rich_block_selector', 12, '选择 calculator 组件。', [{ label: '组件', value: 'calculator' }, { label: '边界', value: '只做测算，不给建议价' }], { rich_block: 'calculator' }),
      makeStep(3, '合规提示', 'quality_check', 9, '追加测算结果不构成投资建议。', [{ label: '风险提示', value: '已添加' }, { label: '质检', value: 'PASS' }], { risk_tip_present: true }),
    ],
    metadata: {
      total_latency_ms: 420,
      tool_calls_count: 0,
      quality_check_result: 'PASS',
      model_versions: { master_bot: 'mock-master' },
    },
  },
  trace_20260608_005: {
    id: 'trace_20260608_005',
    session_id: 'sess_20260607_001',
    message_id: 'msg_010',
    user_query: '财报同比和环比有什么差异',
    status: 'success',
    steps: [
      makeStep(1, '知识库检索', 'mock_rag_retrieval', 126, '命中财务指标解释知识库。', [{ label: '命中', value: '同比 / 环比解释' }, { label: '来源', value: '本地投研知识库' }], { rag_hit: '同比环比解释.md' }),
      makeStep(2, '最终输出', 'final_assembly', 16, '生成知识库解释和风险提示。', [{ label: '组件', value: 'text + citation_list + risk_notice' }], { rich_blocks: ['text', 'citation_list', 'risk_notice'] }),
    ],
    metadata: {
      total_latency_ms: 1060,
      tool_calls_count: 1,
      quality_check_result: 'PASS',
      model_versions: { master_bot: 'mock-master' },
    },
  },
}

export const mockDataSourceStatus: DataSourceStatus = {
  mock_data: [
    { type: 'market', name: '行情数据', path: 'data/mock/market', status: 'ready', sample_count: 20 },
    { type: 'financial', name: '财务数据', path: 'data/mock/financial', status: 'ready', sample_count: 12 },
    { type: 'report', name: '研报数据', path: 'data/mock/reports', status: 'ready', sample_count: 8 },
    { type: 'announcement', name: '公告数据', path: 'data/mock/announcements', status: 'ready', sample_count: 10 },
    { type: 'knowledge', name: '投研知识库', path: 'data/knowledge-base', status: 'ready', sample_count: 30 },
  ],
  rag: {
    mode: 'mock',
    embedding_provider: 'siliconflow-qwen',
    rerank_provider: 'siliconflow-qwen',
    status: 'mocked',
  },
}

export const mockConfigStatus: ConfigStatus = {
  models: [
    {
      name: '硅基流动 LLM / 意图识别',
      fields: ['LLM_INTENT_API_KEY', 'LLM_INTENT_BASE_URL', 'LLM_INTENT_MODEL'],
      status: 'mocked',
      missing_fields: ['LLM_INTENT_API_KEY', 'LLM_INTENT_BASE_URL', 'LLM_INTENT_MODEL'],
    },
    {
      name: '硅基流动 LLM / 主输出',
      fields: ['LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL'],
      status: 'mocked',
      missing_fields: ['LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL'],
    },
    {
      name: '硅基流动 Embedding / 千问',
      fields: ['EMBEDDING_API_KEY', 'EMBEDDING_BASE_URL', 'EMBEDDING_MODEL', 'EMBEDDING_DIM'],
      status: 'mocked',
      missing_fields: ['EMBEDDING_API_KEY', 'EMBEDDING_BASE_URL', 'EMBEDDING_MODEL', 'EMBEDDING_DIM'],
    },
    {
      name: '硅基流动 Rerank / 千问',
      fields: ['RERANK_API_KEY', 'RERANK_BASE_URL', 'RERANK_MODEL'],
      status: 'mocked',
      missing_fields: ['RERANK_API_KEY', 'RERANK_BASE_URL', 'RERANK_MODEL'],
    },
  ],
  prompts: [
    { agent: 'master_agent', name: '总控 Agent', status: 'default' },
    { agent: 'hotspot_agent', name: '热点助手', status: 'default' },
    { agent: 'data_agent', name: '问数助手', status: 'default' },
    { agent: 'stock_agent', name: '问股助手', status: 'default' },
    { agent: 'quality_check', name: '质检模块', status: 'default' },
  ],
  compliance_rules: {
    blacklist_expressions: ['建议买入', '推荐', '值得关注', '重点关注', '逢低关注'],
    risk_tip_required: true,
    citation_required: true,
  },
}

export function createTraceForQuery(sessionId: string, messageId: string, query: string, isCalculator: boolean): Trace {
  const baseTrace = isCalculator ? mockTraces.trace_20260608_004 : mockTraces.trace_20260608_001
  const id = `trace_${Date.now()}`
  return {
    ...baseTrace,
    id,
    session_id: sessionId,
    message_id: messageId,
    user_query: query,
    steps: baseTrace.steps.map((step) => ({
      ...step,
      input: { query },
      raw_json: { ...step.raw_json, query },
    })),
  }
}

export function createAssistantBlock(query: string): RichBlock {
  const normalized = query.toLowerCase()
  if (normalized.includes('回报') || normalized.includes('收益') || normalized.includes('测算')) return calculatorBlock
  if (query.includes('宁德') || query.includes('基本面')) return stockBlock
  if (query.includes('机器人') || query.includes('为什么涨')) return hotspotBlock
  if (query.includes('同比') || query.includes('环比')) return knowledgeBlock
  return rankingBlock
}

export function createAssistantBlocks(query: string): RichBlock[] {
  const block = createAssistantBlock(query)
  const analysisBlocks = block.type === 'stock_card' ? [stockAnalysisBlock] : []
  return [block, ...analysisBlocks, createRiskBlock(block), createCitationBlock(block)]
}

export function createAssistantContent(query: string): string {
  const normalized = query.toLowerCase()
  if (normalized.includes('回报') || normalized.includes('收益') || normalized.includes('测算')) {
    return '已生成可交互测算组件，你可以调整买入价、情景价和持仓数量。'
  }
  if (query.includes('宁德') || query.includes('基本面')) {
    return '以下是宁德时代的基本面信息整理。'
  }
  return '下面是相关信息整理。'
}

export function inferAgentLabel(query: string): string {
  if (query.includes('回报') || query.includes('收益') || query.includes('测算')) return '测算组件'
  if (query.includes('宁德') || query.includes('基本面')) return '问股助手'
  if (query.includes('为什么涨') || query.includes('政策')) return '热点助手'
  if (query.includes('同比') || query.includes('环比')) return '投研知识库'
  return '总控 Agent'
}

export function createDraftSession(source: SessionSource): MockSessionEntity {
  const id = `sess_${Date.now()}`
  return {
    id,
    title: '新对话',
    title_source: 'system',
    is_draft: true,
    source,
    created_at: '2026-06-08T14:10:00+08:00',
    updated_at: '2026-06-08T14:10:00+08:00',
    last_message_preview: '',
    last_trace_id: null,
    agent_label: '总控 Agent',
    default_trace_id: 'trace_20260608_005',
  }
}
