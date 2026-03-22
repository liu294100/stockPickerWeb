from core.data_fetcher import DataFetcher
from core.config_manager import ConfigManager
from core.tushare_manager import TushareManager
from core.tickflow_manager import TickFlowManager
from core.stock_store import StockStore
import re
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus


class MarketService:
    DEFAULT_STOCKS = [
        {"code": "000001", "name": "平安银行", "industry": "银行", "market": "A", "watchlist": 1},
        {"code": "000002", "name": "万科A", "industry": "房地产", "market": "A", "watchlist": 1},
        {"code": "600036", "name": "招商银行", "industry": "银行", "market": "A", "watchlist": 1},
        {"code": "000858", "name": "五粮液", "industry": "白酒", "market": "A", "watchlist": 1},
        {"code": "600519", "name": "贵州茅台", "industry": "白酒", "market": "A", "watchlist": 1},
        {"code": "300750", "name": "宁德时代", "industry": "新能源", "market": "A", "watchlist": 1},
        {"code": "601012", "name": "隆基绿能", "industry": "光伏", "market": "A", "watchlist": 1},
        {"code": "002460", "name": "赣锋锂业", "industry": "有色", "market": "A", "watchlist": 1},
        {"code": "600760", "name": "中航沈飞", "industry": "军工", "market": "A", "watchlist": 1},
        {"code": "600031", "name": "三一重工", "industry": "工程机械", "market": "A", "watchlist": 1},
        {"code": "688981", "name": "中芯国际", "industry": "芯片", "market": "A", "watchlist": 1},
        {"code": "601318", "name": "中国平安", "industry": "保险", "market": "A", "watchlist": 1},
        {"code": "000651", "name": "格力电器", "industry": "家电", "market": "A", "watchlist": 1},
        {"code": "002415", "name": "海康威视", "industry": "安防", "market": "A", "watchlist": 1},
        {"code": "300059", "name": "东方财富", "industry": "券商", "market": "A", "watchlist": 1},
        {"code": "00700.HK", "name": "腾讯控股", "industry": "互联网", "market": "HK", "watchlist": 1},
        {"code": "00941.HK", "name": "中国移动", "industry": "通信", "market": "HK", "watchlist": 1},
        {"code": "01810.HK", "name": "小米集团", "industry": "消费电子", "market": "HK", "watchlist": 1},
        {"code": "09988.HK", "name": "阿里巴巴", "industry": "互联网", "market": "HK", "watchlist": 1},
        {"code": "AAPL", "name": "Apple", "industry": "科技", "market": "US", "watchlist": 1},
        {"code": "MSFT", "name": "Microsoft", "industry": "科技", "market": "US", "watchlist": 1},
        {"code": "NVDA", "name": "NVIDIA", "industry": "半导体", "market": "US", "watchlist": 1},
        {"code": "TSLA", "name": "Tesla", "industry": "汽车", "market": "US", "watchlist": 1},
    ]
    NEWS_FEEDS = [
        {
            "url": "https://feeds.bloomberg.com/markets/news.rss",
            "source": "Bloomberg",
        },
        {
            "url": "https://news.google.com/rss/search?q=site:reuters.com+when:1d+stock+market&hl=en-US&gl=US&ceid=US:en",
            "source": "Reuters",
        },
        {
            "url": "https://news.google.com/rss/search?q=site:bloomberg.com+when:1d+stock+market&hl=en-US&gl=US&ceid=US:en",
            "source": "Bloomberg",
        },
        {
            "url": "https://news.google.com/rss/search?q=site:eastmoney.com+when:1d+股票&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            "source": "东方财富",
        },
        {
            "url": "https://news.google.com/rss/search?q=site:futunn.com+when:1d+美股+港股&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            "source": "富途牛牛",
        },
    ]

    def __init__(self):
        self.config = ConfigManager()
        self.tushare_manager = TushareManager()
        self.tickflow_manager = TickFlowManager()
        self.stock_store = StockStore()
        self._seed_default_stocks()

    def get_quote(self, code: str, source: str | None = None):
        source_order = [source] if source else self.config.get("settings.data_sources", ["tickflow", "eastmoney", "sina", "tencent"])
        for source_name in source_order:
            normalized_source = (source_name or "").strip().lower()
            if normalized_source == "tickflow":
                tickflow_quote = self.tickflow_manager.get_quote(code)
                normalized_quote = self._normalize_tickflow_quote(code, tickflow_quote)
                if normalized_quote:
                    return normalized_quote
            if normalized_source in {"eastmoney", "sina", "tencent"}:
                quote = DataFetcher.get_realtime_quote(code, preferred_source=normalized_source)
                if quote:
                    self._fill_quote_name(code, quote)
                    return quote
        quote = DataFetcher.get_realtime_quote(code, preferred_source="eastmoney")
        self._fill_quote_name(code, quote)
        return quote

    def get_daily_klines(self, code: str, source: str | None = None, limit: int = 60):
        source_order = [source] if source else self.config.get("settings.data_sources", ["tickflow", "eastmoney", "sina", "tencent"])
        eastmoney_tried = False
        for source_name in source_order:
            normalized_source = (source_name or "").strip().lower()
            if normalized_source == "tickflow":
                klines = self.tickflow_manager.get_daily_klines(code, limit=limit)
                if klines:
                    return klines
            if normalized_source in {"eastmoney", "sina", "tencent"}:
                if normalized_source == "eastmoney":
                    eastmoney_tried = True
                klines = DataFetcher.get_daily_klines(code, source=normalized_source, limit=limit)
                if klines:
                    return klines
        if not eastmoney_tried:
            return DataFetcher.get_daily_klines(code, source="eastmoney", limit=limit)
        return []

    def get_stock_pool(self, market: str | None = None, watchlist_only: bool = False):
        normalized_market = self._normalize_market(market)
        stocks = self.stock_store.list_stocks(market=normalized_market, watchlist_only=watchlist_only)
        return [
            {
                "code": item["code"],
                "name": item["name"],
                "industry": item["industry"],
                "market": item["market"],
                "watchlist": bool(item["watchlist"]),
            }
            for item in stocks
        ]

    def search_stocks(self, keyword: str, market: str | None = None, limit: int = 20):
        text = (keyword or "").strip()
        if not text:
            return []
        normalized_market = self._normalize_market(market)
        local_rows = self.get_stock_pool(market=normalized_market, watchlist_only=False)
        lowered = text.lower()
        local_matches = []
        for row in local_rows:
            code = str(row.get("code") or "")
            name = str(row.get("name") or "")
            if lowered in code.lower() or lowered in name.lower():
                local_matches.append(row)
        remote_matches = self._search_stocks_from_sina(text, market=normalized_market, limit=max(limit * 2, 30))
        merged = []
        seen = set()
        for row in local_matches + remote_matches:
            code = str(row.get("code") or "").upper()
            if not code or code in seen:
                continue
            seen.add(code)
            merged.append(row)
            if len(merged) >= max(5, min(limit, 100)):
                break
        return merged

    def upsert_stock(self, payload: dict):
        code = (payload.get("code") or "").strip().upper()
        if not code:
            return None, "缺少股票代码"
        name = (payload.get("name") or "").strip()
        if not name:
            return None, "缺少股票名称"
        industry = (payload.get("industry") or "其他").strip()
        market = self._normalize_market(payload.get("market"))
        watchlist = bool(payload.get("watchlist", True))
        self.stock_store.upsert_stock(code=code, name=name, industry=industry, market=market, watchlist=watchlist)
        return self.stock_store.get_stock(code), None

    def patch_stock(self, code: str, payload: dict):
        normalized_code = (code or "").strip().upper()
        if not normalized_code:
            return None, "缺少股票代码"
        if "market" in payload:
            payload["market"] = self._normalize_market(payload.get("market"))
        updated = self.stock_store.patch_stock(normalized_code, payload or {})
        if not updated:
            return None, "股票不存在"
        return updated, None

    def delete_stock(self, code: str):
        normalized_code = (code or "").strip().upper()
        if not normalized_code:
            return False
        return self.stock_store.delete_stock(normalized_code)

    def set_watchlist(self, code: str, watchlist: bool):
        normalized_code = (code or "").strip().upper()
        if not normalized_code:
            return False
        return self.stock_store.set_watchlist(normalized_code, watchlist)

    def get_overview(self, market: str | None = None, source: str | None = None, watchlist_only: bool = False):
        normalized_market = self._normalize_market(market)
        stocks = self.get_stock_pool(market=normalized_market, watchlist_only=watchlist_only)
        items = []
        sector_map = {}
        for stock in stocks:
            quote = self.get_quote(stock["code"], source=source)
            if not quote:
                continue
            self._fill_quote_name(stock["code"], quote)
            row = {
                "code": stock["code"],
                "name": stock["name"],
                "industry": stock["industry"],
                "market": stock["market"],
                "watchlist": stock["watchlist"],
                "price": self._to_float(quote.get("price"), 0),
                "change": self._to_float(quote.get("change"), 0),
                "change_pct": self._to_float(quote.get("change_pct"), 0),
                "volume": self._to_float(quote.get("volume"), 0),
                "source": quote.get("source", "未知"),
            }
            items.append(row)
            bucket = sector_map.setdefault(stock["industry"], [])
            bucket.append(row["change_pct"])
        items.sort(key=lambda x: x["change_pct"], reverse=True)
        market_order = ["A", "HK", "US"] if normalized_market == "ALL" else [normalized_market]
        gainers_by_market = {}
        losers_by_market = {}
        for market_key in market_order:
            scoped_items = [item for item in items if item.get("market") == market_key]
            if not scoped_items:
                continue
            sorted_desc = sorted(scoped_items, key=lambda x: x["change_pct"], reverse=True)
            sorted_asc = sorted(scoped_items, key=lambda x: x["change_pct"])
            gainers = [item for item in sorted_desc if item["change_pct"] >= 0][:10]
            if len(gainers) < min(10, len(sorted_desc)):
                picked_codes = {item["code"] for item in gainers}
                for item in sorted_desc:
                    if item["code"] in picked_codes:
                        continue
                    gainers.append(item)
                    if len(gainers) >= min(10, len(sorted_desc)):
                        break
            losers = [item for item in sorted_asc if item["change_pct"] < 0][:10]
            if len(losers) < min(10, len(sorted_asc)):
                picked_codes = {item["code"] for item in losers}
                for item in sorted_asc:
                    if item["code"] in picked_codes:
                        continue
                    losers.append(item)
                    if len(losers) >= min(10, len(sorted_asc)):
                        break
            gainers_by_market[market_key] = [{**item, "recommend_tag": "涨幅领先"} for item in gainers]
            losers_by_market[market_key] = [{**item, "recommend_tag": "跌幅关注"} for item in losers]
        recommendations = []
        for market_key in market_order:
            recommendations.extend((gainers_by_market.get(market_key) or [])[:4])
            recommendations.extend((losers_by_market.get(market_key) or [])[:4])
        flat_gainers = []
        flat_losers = []
        for market_key in market_order:
            flat_gainers.extend(gainers_by_market.get(market_key, []))
            flat_losers.extend(losers_by_market.get(market_key, []))
        heatmap = []
        for industry, values in sector_map.items():
            avg_change = sum(values) / len(values) if values else 0
            heatmap.append({"label": industry, "value": round(avg_change, 2), "count": len(values)})
        heatmap.sort(key=lambda x: abs(x["value"]), reverse=True)
        return {
            "market": normalized_market,
            "recommendations": recommendations[:8],
            "gainers": flat_gainers,
            "losers": flat_losers,
            "gainers_by_market": gainers_by_market,
            "losers_by_market": losers_by_market,
            "items": items[:40],
            "heatmap": heatmap[:25],
        }

    def get_news(self):
        return self.search_news()

    def get_news_sources(self):
        sources = []
        seen = set()
        for feed in self.NEWS_FEEDS:
            source = feed.get("source")
            if source and source not in seen:
                seen.add(source)
                sources.append(source)
        return sources

    def search_news(
        self,
        source: str | None = None,
        query: str | None = None,
        search_type: str | None = None,
        mode: str | None = None,
        limit: int = 30,
    ):
        source_filter = (source or "ALL").strip()
        keyword = (query or "").strip()
        normalized_search_type = (search_type or "keyword").strip().lower()
        normalized_mode = (mode or "all").strip().lower()
        result = []
        seen_titles = set()
        candidate_feeds = [feed for feed in self.NEWS_FEEDS if not source_filter or source_filter == "ALL" or feed["source"] == source_filter]
        feed_items = self._fetch_news_feed_items(candidate_feeds, limit=5, use_parallel=(source_filter == "ALL"))
        for _, _, items in feed_items:
            for item in items:
                title = item.get("title", "")
                if not title or title in seen_titles:
                    continue
                if not self._match_news_search(item, keyword, normalized_search_type):
                    continue
                seen_titles.add(title)
                result.append(item)
        if normalized_mode == "watchlist":
            watchlist_items = self._fetch_watchlist_news(source_filter, keyword, normalized_search_type, seen_titles)
            result.extend(watchlist_items)
        if keyword and len(result) < 8:
            extra_items = self._fetch_query_news(keyword, source_filter, seen_titles)
            result.extend(extra_items)
        if result:
            result.sort(key=lambda item: item.get("published_ts", 0), reverse=True)
            return result[:limit]
        return [
            {"title": "资讯源暂不可用", "summary": "请检查网络连接或稍后重试。", "source": "系统", "link": "", "published_at": "--", "published_ts": 0},
        ]

    def _fetch_news_feed_items(self, feeds: list[dict], limit: int = 5, use_parallel: bool = False):
        if not feeds:
            return []
        indexed_feeds = list(enumerate(feeds))
        if not use_parallel or len(indexed_feeds) == 1:
            return [(idx, feed.get("source", ""), self._fetch_rss_feed(feed.get("url", ""), feed.get("source", ""), limit=limit)) for idx, feed in indexed_feeds]
        workers = min(8, len(indexed_feeds))
        result = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(self._fetch_rss_feed, feed.get("url", ""), feed.get("source", ""), limit): (idx, feed.get("source", ""))
                for idx, feed in indexed_feeds
            }
            for future, (idx, source_name) in future_map.items():
                try:
                    items = future.result()
                except Exception:
                    items = []
                result.append((idx, source_name, items))
        result.sort(key=lambda item: item[0])
        return result

    def get_stock_details(self, code: str, source: str | None = None):
        quote = self.get_quote(code, source=source)
        self._fill_quote_name(code, quote)
        capital_flow, capital_flow_error = self.tushare_manager.get_capital_flow(code)
        financial_data, financial_data_error = self.tushare_manager.get_financial_snapshot(code)
        daily_klines = self.get_daily_klines(code, source=source, limit=60)
        source = quote.get("source", "未知") if quote else "未知"
        stock_meta = self.stock_store.get_stock(code.upper()) if code else None
        return {
            "code": code,
            "name": (stock_meta or {}).get("name", code),
            "market": (stock_meta or {}).get("market", self._normalize_market(None)),
            "industry": (stock_meta or {}).get("industry", "--"),
            "quote": quote,
            "capital_flow": capital_flow,
            "capital_flow_error": capital_flow_error,
            "financial_data": financial_data,
            "financial_data_error": financial_data_error,
            "daily_klines": daily_klines,
            "source": source,
        }

    def screen_stocks(self, filters: dict | None = None):
        payload = filters or {}
        source = payload.get("source")
        if source == "auto":
            source = None
        market = self._normalize_market(payload.get("market"))
        watchlist_only = bool(payload.get("watchlist_only", False))
        conditions = {
            "market_cap_min": self._to_float(payload.get("market_cap_min"), 0),
            "market_cap_max": self._to_float(payload.get("market_cap_max"), float("inf")),
            "price_min": self._to_float(payload.get("price_min"), 0),
            "price_max": self._to_float(payload.get("price_max"), float("inf")),
            "pe_max": self._to_float(payload.get("pe_max"), float("inf")),
            "pb_max": self._to_float(payload.get("pb_max"), float("inf")),
            "roe_min": self._to_float(payload.get("roe_min"), float("-inf")),
            "gross_margin_min": self._to_float(payload.get("gross_margin_min"), float("-inf")),
            "net_margin_min": self._to_float(payload.get("net_margin_min"), float("-inf")),
        }
        result = []
        for stock in self.get_stock_pool(market=market, watchlist_only=watchlist_only):
            code = stock["code"]
            quote = self.get_quote(code, source=source)
            if not quote:
                continue
            self._fill_quote_name(code, quote)
            financial_data, _ = self.tushare_manager.get_financial_snapshot(code)
            metrics = self._build_screener_metrics(code, quote, financial_data)
            if not self._match_screener_conditions(metrics, conditions):
                continue
            result.append(
                {
                    "code": code,
                    "name": stock["name"],
                    "industry": stock.get("industry", "--"),
                    "market": stock.get("market", "A"),
                    "watchlist": stock.get("watchlist", False),
                    "price": round(metrics["price"], 2),
                    "change_pct": round(metrics["change_pct"], 2),
                    "pe": round(metrics["pe"], 2) if metrics["pe"] is not None else None,
                    "pb": round(metrics["pb"], 2) if metrics["pb"] is not None else None,
                    "roe": round(metrics["roe"], 2) if metrics["roe"] is not None else None,
                    "gross_margin": round(metrics["gross_margin"], 2) if metrics["gross_margin"] is not None else None,
                    "net_margin": round(metrics["net_margin"], 2) if metrics["net_margin"] is not None else None,
                    "market_cap": round(metrics["market_cap"], 2) if metrics["market_cap"] is not None else None,
                    "source": quote.get("source", "未知"),
                    "data_quality": metrics.get("data_quality", "实时行情"),
                }
            )
        result.sort(key=lambda item: item["change_pct"], reverse=True)
        return result

    def _normalize_tickflow_quote(self, code: str, quote: dict | None):
        if not isinstance(quote, dict):
            return None
        symbol = quote.get("symbol", "")
        name = quote.get("name", code)
        price = quote.get("last", quote.get("price", quote.get("close")))
        pre_close = quote.get("pre_close", quote.get("prev_close", price))
        high = quote.get("high", price)
        low = quote.get("low", price)
        open_price = quote.get("open", price)
        volume = quote.get("volume", 0)
        turnover = quote.get("turnover", quote.get("amount", 0))
        if price is None:
            return None
        price = float(price)
        pre_close = float(pre_close) if pre_close is not None else price
        change = price - pre_close
        change_pct = (change / pre_close * 100) if pre_close else 0
        return {
            "code": symbol or code,
            "name": name,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(float(volume or 0)),
            "turnover": float(turnover or 0),
            "high": float(high or price),
            "low": float(low or price),
            "open": float(open_price or price),
            "pre_close": pre_close,
            "source": "TickFlow",
        }

    def _seed_default_stocks(self):
        if self.stock_store.count() > 0:
            return
        self.stock_store.bulk_seed(self.DEFAULT_STOCKS)

    def _normalize_market(self, market: str | None):
        token = (market or "ALL").strip().upper()
        if token in {"", "ALL"}:
            return "ALL"
        if token in {"A", "CN", "A股"}:
            return "A"
        if token in {"HK", "港股"}:
            return "HK"
        if token in {"US", "美股"}:
            return "US"
        return "ALL"

    def _fill_quote_name(self, code: str, quote: dict | None):
        if not isinstance(quote, dict):
            return
        stock = self.stock_store.get_stock((code or "").upper())
        if not stock:
            return
        current_name = quote.get("name")
        if not current_name or str(current_name).startswith("模拟"):
            quote["name"] = stock["name"]

    def _search_stocks_from_sina(self, keyword: str, market: str = "ALL", limit: int = 30):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            url = f"https://suggest3.sinajs.cn/suggest/type=&key={quote_plus(keyword)}"
            response = requests.get(url, timeout=4, headers=headers)
            if response.status_code != 200:
                return []
            response.encoding = response.apparent_encoding or "utf-8"
            content = response.text or ""
            matched = re.search(r'var\s+suggestvalue="(.*)"\s*;', content, flags=re.S)
            if not matched:
                return []
            body = (matched.group(1) or "").strip()
            if not body:
                return []
            result = []
            seen = set()
            for raw in body.split(";"):
                fields = [part.strip() for part in raw.split(",")]
                if len(fields) < 5:
                    continue
                stock = self._parse_sina_suggest_row(fields)
                if not stock:
                    continue
                if market != "ALL" and stock.get("market") != market:
                    continue
                code_key = str(stock.get("code") or "").upper()
                if not code_key or code_key in seen:
                    continue
                seen.add(code_key)
                result.append(stock)
                if len(result) >= max(5, min(limit, 100)):
                    break
            return result
        except Exception:
            return []

    def _parse_sina_suggest_row(self, fields: list[str]):
        category = fields[1]
        raw_code = fields[2]
        name = fields[4] or raw_code
        normalized_code = ""
        normalized_market = ""
        if category == "11":
            if re.fullmatch(r"\d{6}", raw_code):
                normalized_code = raw_code
                normalized_market = "A"
        elif category == "31":
            if re.fullmatch(r"\d{3,5}", raw_code):
                normalized_code = f"{raw_code.zfill(5)}.HK"
                normalized_market = "HK"
        elif category in {"41", "103"}:
            code = (raw_code or "").upper()
            if code:
                normalized_code = code
                normalized_market = "US"
        if not normalized_code or not normalized_market:
            return None
        local_stock = self.stock_store.get_stock(normalized_code)
        if local_stock:
            return {
                "code": local_stock["code"],
                "name": local_stock["name"],
                "industry": local_stock["industry"],
                "market": local_stock["market"],
                "watchlist": bool(local_stock["watchlist"]),
            }
        return {
            "code": normalized_code,
            "name": name,
            "industry": "--",
            "market": normalized_market,
            "watchlist": False,
        }

    def _build_screener_metrics(self, code: str, quote: dict, financial_data: dict | None):
        daily_basic = (financial_data or {}).get("daily_basic", {})
        indicator = (financial_data or {}).get("fina_indicator", {})
        market_cap = self._to_optional_float(daily_basic.get("total_mv"))
        pe = self._to_optional_float(daily_basic.get("pe"))
        pb = self._to_optional_float(daily_basic.get("pb"))
        roe = self._to_optional_float(indicator.get("roe"))
        gross_margin = self._to_optional_float(indicator.get("grossprofit_margin"))
        net_margin = self._to_optional_float(indicator.get("netprofit_margin"))
        finance_ready_count = len([x for x in [market_cap, pe, pb, roe, gross_margin, net_margin] if x is not None])
        if finance_ready_count >= 4:
            quality = "行情+财务真实"
        elif finance_ready_count > 0:
            quality = "行情真实/财务部分缺失"
        else:
            quality = "仅实时行情"
        return {
            "price": self._to_float(quote.get("price"), 0),
            "change_pct": self._to_float(quote.get("change_pct"), 0),
            "market_cap": market_cap,
            "pe": pe,
            "pb": pb,
            "roe": roe,
            "gross_margin": gross_margin,
            "net_margin": net_margin,
            "data_quality": quality,
        }

    def _match_screener_conditions(self, metrics: dict, conditions: dict):
        if not self._in_range(metrics["market_cap"], conditions["market_cap_min"], conditions["market_cap_max"], default_min=0):
            return False
        if not self._in_range(metrics["price"], conditions["price_min"], conditions["price_max"], default_min=0):
            return False
        if not self._max_rule(metrics["pe"], conditions["pe_max"]):
            return False
        if not self._max_rule(metrics["pb"], conditions["pb_max"]):
            return False
        if not self._min_rule(metrics["roe"], conditions["roe_min"]):
            return False
        if not self._min_rule(metrics["gross_margin"], conditions["gross_margin_min"]):
            return False
        if not self._min_rule(metrics["net_margin"], conditions["net_margin_min"]):
            return False
        return True

    def _to_optional_float(self, value):
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _in_range(self, value, min_value, max_value, default_min=0):
        if value is None:
            if min_value <= default_min and math.isinf(max_value):
                return True
            return False
        return min_value <= value <= max_value

    def _max_rule(self, value, threshold):
        if math.isinf(threshold):
            return True
        if value is None:
            return False
        return value <= threshold

    def _min_rule(self, value, threshold):
        if threshold == float("-inf"):
            return True
        if value is None:
            return False
        return value >= threshold

    def _to_float(self, value, default):
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _fetch_rss_feed(self, url: str, source: str, limit: int = 8):
        try:
            response = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                return []
            root = ET.fromstring(response.content)
            entries = root.findall(".//item")
            result = []
            for entry in entries:
                title = (entry.findtext("title") or "").strip()
                if not title:
                    continue
                summary = self._normalize_news_text(entry.findtext("description") or "")
                link = (entry.findtext("link") or "").strip()
                published_raw = (entry.findtext("pubDate") or entry.findtext("updated") or "").strip()
                published_at, published_ts = self._parse_news_datetime(published_raw)
                result.append(
                    {
                        "title": title,
                        "summary": summary or "查看原文获取更多信息。",
                        "source": source,
                        "link": link,
                        "published_at": published_at,
                        "published_ts": published_ts,
                    }
                )
                if len(result) >= limit:
                    break
            return result
        except Exception:
            return []

    def _parse_news_datetime(self, raw_value: str):
        if not raw_value:
            return "--", 0
        try:
            dt = parsedate_to_datetime(raw_value)
            if dt is None:
                return "--", 0
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone()
            return local_dt.strftime("%m-%d %H:%M"), int(local_dt.timestamp())
        except Exception:
            text = raw_value.strip()
            try:
                for pattern in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
                    dt = datetime.strptime(text, pattern)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    local_dt = dt.astimezone()
                    return local_dt.strftime("%m-%d %H:%M"), int(local_dt.timestamp())
            except Exception:
                return text[:16], 0
            return "--", 0

    def _match_news_search(self, item: dict, keyword: str, search_type: str):
        if not keyword:
            return True
        target = keyword.lower()
        title = str(item.get("title", "")).lower()
        summary = str(item.get("summary", "")).lower()
        source = str(item.get("source", "")).lower()
        if search_type == "title":
            return target in title
        if search_type == "code":
            return target in title or target in summary
        if search_type == "stock":
            return target in title or target in summary
        if search_type == "source":
            return target in source
        return target in title or target in summary or target in source

    def _fetch_query_news(self, keyword: str, source_filter: str, seen_titles: set[str]):
        if not keyword:
            return []
        extra = []
        query = quote_plus(f"{keyword} 股票 财经 when:2d")
        feeds = []
        if source_filter == "ALL":
            feeds = [
                {"source": "GoogleNews", "url": f"https://news.google.com/rss/search?q={query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"},
            ]
        else:
            domain_map = {
                "Bloomberg": "bloomberg.com",
                "Reuters": "reuters.com",
                "东方财富": "eastmoney.com",
                "富途牛牛": "futunn.com",
            }
            domain = domain_map.get(source_filter)
            if domain:
                scoped = quote_plus(f"site:{domain} {keyword} when:3d")
                feeds = [
                    {
                        "source": source_filter,
                        "url": f"https://news.google.com/rss/search?q={scoped}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
                    }
                ]
        for feed in feeds:
            items = self._fetch_rss_feed(feed["url"], feed["source"], limit=12)
            for item in items:
                title = item.get("title", "")
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                extra.append(item)
        return extra

    def _fetch_watchlist_news(self, source_filter: str, keyword: str, search_type: str, seen_titles: set[str]):
        watchlist = self.stock_store.list_stocks(market="ALL", watchlist_only=True)
        if not watchlist:
            return []
        picked = watchlist[:5]
        terms = [item["name"] for item in picked if item.get("name")]
        terms.extend(item["code"] for item in picked if item.get("code"))
        if keyword:
            terms.insert(0, keyword)
        if not terms:
            return []
        join_query = " OR ".join(terms[:6])
        query = quote_plus(f"{join_query} 股票 财经 when:2d")
        source_name = "自选资讯"
        if source_filter not in {"", "ALL"}:
            source_name = source_filter
        items = self._fetch_rss_feed(
            f"https://news.google.com/rss/search?q={query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            source_name,
            limit=20,
        )
        result = []
        watch_keys = [str(item["name"]).lower() for item in picked] + [str(item["code"]).lower() for item in picked]
        for item in items:
            title = (item.get("title") or "").strip()
            if not title or title in seen_titles:
                continue
            text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
            if not any(key and key in text for key in watch_keys):
                continue
            if not self._match_news_search(item, keyword, search_type):
                continue
            seen_titles.add(title)
            result.append(item)
        return result

    def _normalize_news_text(self, raw_text: str):
        plain = unescape(raw_text or "")
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        return plain[:220]
