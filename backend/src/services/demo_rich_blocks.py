"""Demo rich_blocks payloads for seeded history showcase sessions."""

from __future__ import annotations

from typing import Any

from ..integrations.llm.rich_block_builders import (
    build_calculator_rich_payload,
    build_sector_heatmap_payload,
)

RANKING_TABLE_DEMO: dict[str, Any] = {
    "id": "block_demo_ranking",
    "type": "ranking_table",
    "title": "半导体板块涨幅排行",
    "payload": {
        "columns": ["排名", "股票名称", "涨跌幅", "收盘价"],
        "rows": [
            {"排名": 1, "股票名称": "寒武纪", "涨跌幅": "+8.76%", "收盘价": "287.50"},
            {"排名": 2, "股票名称": "北方华创", "涨跌幅": "+6.23%", "收盘价": "385.20"},
            {"排名": 3, "股票名称": "中微公司", "涨跌幅": "+5.87%", "收盘价": "198.60"},
            {"排名": 4, "股票名称": "韦尔股份", "涨跌幅": "+4.52%", "收盘价": "112.80"},
            {"排名": 5, "股票名称": "兆易创新", "涨跌幅": "+4.11%", "收盘价": "145.30"},
        ],
    },
    "sources": [{"type": "market", "label": "本地 demo 行情截面", "time": "2026-06-08 14:05"}],
    "risk_notice": "以上内容仅为信息整理，不构成投资建议。",
}

_CALCULATOR_TOOL_RESULT = {
    "buy_price": 15.0,
    "sell_price": 20.0,
    "share_count": 1000,
    "fee_rate": 0.03,
    "net_profit": 4991.5,
    "return_pct": 33.27,
    "formula": "net_profit = (sell_price - buy_price) * share_count - (buy_price + sell_price) * share_count * fee_rate",
}

CALCULATOR_DEMO: dict[str, Any] = {
    "id": "block_demo_calculator",
    "type": "calculator",
    "title": "收益率测算",
    "payload": build_calculator_rich_payload(_CALCULATOR_TOOL_RESULT),
    "sources": [{"type": "knowledge", "label": "本地公式计算"}],
    "risk_notice": "测算结果仅供参考，不构成投资建议。",
}

RANKING_DEMO_CONTENT = """近一交易日半导体板块涨幅靠前，领涨股集中在 AI 算力链与设备环节。

### 排行解读

- **龙头集中**：寒武纪、北方华创领涨，板块内涨幅分化明显。
- **量能观察**：成交额靠前的个股与涨幅前列部分重叠，资金集中度较高。
- **数据口径**：下表为本地 demo 行情截面，非实时交易所行情。

### 参考来源

- 本地 demo 行情截面（2026-06-08 14:05）

以上内容仅为信息整理，不构成投资建议。"""

CALCULATOR_DEMO_CONTENT = """已根据你给出的买入价与情景价生成可交互测算组件，可在下方调整参数查看收益率变化。

### 测算说明

- **参数口径**：默认买入价 15 元、情景价 20 元、1000 股、费率 0.03%。
- **交互方式**：修改输入后，收益率与盈亏由前端按同一公式实时重算。
- **边界**：仅做参数测算，不提供目标价或买卖建议。

### 参考来源

- 用户输入参数 + 本地公式计算

测算结果仅供参考，不构成投资建议。"""

HEATMAP_DEMO_TITLE = "帮我看一下今天A股行业板块热力图"

_HEATMAP_TOOL_DEMO: dict[str, Any] = {
    "board_kind": "industry",
    "trade_date": "2026-06-08",
    "tiles": [
        {"board_name": "半导体", "board_code": "BK1036", "pct_change": 3.42, "turnover_amount": 84200000000, "leader": "寒武纪", "leader_change": 8.76},
        {"board_name": "白酒", "board_code": "BK0477", "pct_change": -0.85, "turnover_amount": 62100000000, "leader": "贵州茅台", "leader_change": -0.42},
        {"board_name": "电池", "board_code": "BK1033", "pct_change": 1.28, "turnover_amount": 59800000000, "leader": "宁德时代", "leader_change": 2.18},
        {"board_name": "光学光电子", "board_code": "BK1038", "pct_change": 2.91, "turnover_amount": 45600000000, "leader": "京东方A", "leader_change": 3.55},
        {"board_name": "证券", "board_code": "BK0473", "pct_change": 0.64, "turnover_amount": 43200000000, "leader": "中信证券", "leader_change": 0.88},
        {"board_name": "医疗器械", "board_code": "BK1041", "pct_change": -1.12, "turnover_amount": 38900000000, "leader": "迈瑞医疗", "leader_change": -0.95},
        {"board_name": "汽车零部件", "board_code": "BK0481", "pct_change": 1.76, "turnover_amount": 36500000000, "leader": "比亚迪", "leader_change": 1.44},
        {"board_name": "通信设备", "board_code": "BK0448", "pct_change": 2.35, "turnover_amount": 34100000000, "leader": "中兴通讯", "leader_change": 2.02},
        {"board_name": "电力", "board_code": "BK0428", "pct_change": 0.22, "turnover_amount": 31800000000, "leader": "长江电力", "leader_change": 0.15},
        {"board_name": "银行", "board_code": "BK0475", "pct_change": -0.31, "turnover_amount": 30500000000, "leader": "招商银行", "leader_change": -0.28},
        {"board_name": "软件开发", "board_code": "BK0737", "pct_change": 1.95, "turnover_amount": 28800000000, "leader": "金山办公", "leader_change": 2.31},
        {"board_name": "光伏设备", "board_code": "BK1031", "pct_change": -0.68, "turnover_amount": 26500000000, "leader": "隆基绿能", "leader_change": -1.02},
    ],
}

SECTOR_HEATMAP_DEMO: dict[str, Any] = {
    "id": "block_demo_heatmap",
    "type": "sector_heatmap",
    "title": "行业板块热力图",
    "payload": build_sector_heatmap_payload(_HEATMAP_TOOL_DEMO),
    "sources": [{"type": "market", "label": "本地 demo 行业板块截面", "time": "2026-06-08 11:20"}],
    "risk_notice": "以上内容仅为信息整理，不构成投资建议。",
}

HEATMAP_DEMO_CONTENT = """近一交易日 A 股行业板块呈现「科技偏强、消费分化、金融平稳」的结构。

### 结构解读

- **成交集中**：半导体、白酒、电池成交额居前，热力图方块面积已按成交额缩放。
- **涨跌分化**：算力链相关板块涨幅更高，部分消费与光伏板块承压。
- **数据口径**：下图为本地 demo 行业板块截面（演示 12 个板块），非实时交易所行情。

### 参考来源

- 本地 demo 行业板块截面（2026-06-08 11:20）

以上内容仅为信息整理，不构成投资建议。"""

SHOWCASE_ASSISTANT_MESSAGES: dict[str, dict[str, Any]] = {
    "msg_20260608_001_assistant": {
        "content": RANKING_DEMO_CONTENT,
        "rich_blocks": [RANKING_TABLE_DEMO],
    },
    "msg_20260608_002_assistant": {
        "content": CALCULATOR_DEMO_CONTENT,
        "rich_blocks": [CALCULATOR_DEMO],
    },
    "msg_20260608_004_assistant": {
        "content": HEATMAP_DEMO_CONTENT,
        "rich_blocks": [SECTOR_HEATMAP_DEMO],
    },
}

RANKING_DEMO_SESSION_ID = "sess_20260608_001"
RANKING_DEMO_USER_MESSAGE_ID = "msg_20260608_001_user"
RANKING_DEMO_ASSISTANT_MESSAGE_ID = "msg_20260608_001_assistant"
RANKING_DEMO_TITLE = "今天涨幅靠前的半导体股票有哪些"

CALCULATOR_DEMO_SESSION_ID = "sess_20260608_002"
CALCULATOR_DEMO_USER_MESSAGE_ID = "msg_20260608_002_user"
CALCULATOR_DEMO_ASSISTANT_MESSAGE_ID = "msg_20260608_002_assistant"
CALCULATOR_DEMO_TITLE = "15元买入未来预期回报率怎么算"

HEATMAP_DEMO_SESSION_ID = "sess_20260608_004"
HEATMAP_DEMO_USER_MESSAGE_ID = "msg_20260608_004_user"
HEATMAP_DEMO_ASSISTANT_MESSAGE_ID = "msg_20260608_004_assistant"

CLIENT_SHOWCASE_SESSIONS: list[dict[str, Any]] = [
    {
        "session_id": RANKING_DEMO_SESSION_ID,
        "user_message_id": RANKING_DEMO_USER_MESSAGE_ID,
        "assistant_message_id": RANKING_DEMO_ASSISTANT_MESSAGE_ID,
        "title": RANKING_DEMO_TITLE,
        "assistant_content": RANKING_DEMO_CONTENT,
        "rich_blocks": [RANKING_TABLE_DEMO],
        "created_at": "2026-06-08T14:05:00+08:00",
    },
    {
        "session_id": CALCULATOR_DEMO_SESSION_ID,
        "user_message_id": CALCULATOR_DEMO_USER_MESSAGE_ID,
        "assistant_message_id": CALCULATOR_DEMO_ASSISTANT_MESSAGE_ID,
        "title": CALCULATOR_DEMO_TITLE,
        "assistant_content": CALCULATOR_DEMO_CONTENT,
        "rich_blocks": [CALCULATOR_DEMO],
        "created_at": "2026-06-08T13:42:00+08:00",
    },
    {
        "session_id": HEATMAP_DEMO_SESSION_ID,
        "user_message_id": HEATMAP_DEMO_USER_MESSAGE_ID,
        "assistant_message_id": HEATMAP_DEMO_ASSISTANT_MESSAGE_ID,
        "title": HEATMAP_DEMO_TITLE,
        "assistant_content": HEATMAP_DEMO_CONTENT,
        "rich_blocks": [SECTOR_HEATMAP_DEMO],
        "created_at": "2026-06-08T11:20:00+08:00",
    },
]
