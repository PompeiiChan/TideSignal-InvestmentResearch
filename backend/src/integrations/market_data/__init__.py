"""Market data integrations (Eastmoney push2, adapted from third_party/a-stock-data)."""

from .cninfo_client import fetch_cninfo_announcements
from .eastmoney_client import (
    fetch_board_list,
    fetch_board_stock_ranking,
    find_board_by_keyword,
    industry_board_ranking,
)
from .news_client import fetch_global_news, filter_news_by_keyword
from .ths_client import fetch_ths_hot_stocks

__all__ = [
    "fetch_board_list",
    "fetch_board_stock_ranking",
    "fetch_cninfo_announcements",
    "fetch_global_news",
    "fetch_ths_hot_stocks",
    "filter_news_by_keyword",
    "find_board_by_keyword",
    "industry_board_ranking",
]
