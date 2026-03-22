import time
import requests
import random
import threading
import re
from collections import OrderedDict
from datetime import datetime
from .config_manager import ConfigManager
from .logger import Logger

class DataFetcher:
    STOCK_POOL = [
        {'code': '000001', 'name': '平安银行', 'industry': '银行'},
        {'code': '000002', 'name': '万科A', 'industry': '房地产'},
        {'code': '600036', 'name': '招商银行', 'industry': '银行'},
        {'code': '000858', 'name': '五粮液', 'industry': '白酒'},
        {'code': '600519', 'name': '贵州茅台', 'industry': '白酒'},
        {'code': '300750', 'name': '宁德时代', 'industry': '新能源'},
        {'code': '601012', 'name': '隆基绿能', 'industry': '光伏'},
        {'code': '002460', 'name': '赣锋锂业', 'industry': '有色'},
        {'code': '600760', 'name': '中航沈飞', 'industry': '军工'},
        {'code': '600031', 'name': '三一重工', 'industry': '工程机械'},
        {'code': '688981', 'name': '中芯国际', 'industry': '芯片'},
        {'code': '601318', 'name': '中国平安', 'industry': '保险'},
        {'code': '000651', 'name': '格力电器', 'industry': '家电'},
        {'code': '002415', 'name': '海康威视', 'industry': '安防'},
        {'code': '300059', 'name': '东方财富', 'industry': '券商'},
    ]
    
    _quote_cache = OrderedDict()
    _quote_cache_lock = threading.RLock()
    MAX_CACHE_SIZE = 500
    
    HOLIDAYS = [
        "2026-01-01", "2026-02-12", # Example holidays
    ]
    
    @classmethod
    def is_holiday(cls, date: datetime = None) -> bool:
        if date is None:
            date = datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        return date_str in cls.HOLIDAYS
    
    @classmethod
    def is_trading_time(cls):
        now = datetime.now()
        weekday = now.weekday()
        if weekday >= 5:
            return False, 0
        if cls.is_holiday(now):
            return False, 0
        
        # Simple trading time check: 9:30-11:30, 13:00-15:00
        current_time = now.time()
        start_am = datetime.strptime("09:30:00", "%H:%M:%S").time()
        end_am = datetime.strptime("11:30:00", "%H:%M:%S").time()
        start_pm = datetime.strptime("13:00:00", "%H:%M:%S").time()
        end_pm = datetime.strptime("15:00:00", "%H:%M:%S").time()
        
        if (start_am <= current_time <= end_am) or (start_pm <= current_time <= end_pm):
            return True, 0
        return False, 0

    @classmethod
    def get_realtime_quote(cls, code: str, preferred_source: str | None = None):
        normalized_code = (code or "").strip().upper()
        normalized_source = (preferred_source or "").strip().lower()
        now = time.time()
        cache_time = 5 if cls.is_trading_time()[0] else 30
        cache_key = f"{normalized_code}|{normalized_source or 'auto'}"
        with cls._quote_cache_lock:
            if cache_key in cls._quote_cache:
                ts, quote = cls._quote_cache[cache_key]
                if now - ts < cache_time:
                    return quote.copy()
        if normalized_source in {"sina", "tencent", "eastmoney"}:
            source_order = [normalized_source]
        else:
            source_order = ["eastmoney", "sina", "tencent"]
        quote = None
        for source_name in source_order:
            if source_name == "eastmoney":
                quote = cls._fetch_from_eastmoney(normalized_code)
            elif source_name == "sina":
                quote = cls._fetch_from_sina(normalized_code)
            elif source_name == "tencent":
                quote = cls._fetch_from_tencent(normalized_code)
            if quote:
                break
        if not quote and ConfigManager().get('settings.use_mock_on_fail', True):
            quote = cls._mock_quote(normalized_code)
        if quote:
            with cls._quote_cache_lock:
                cls._quote_cache[cache_key] = (now, quote)
                if len(cls._quote_cache) > cls.MAX_CACHE_SIZE:
                    cls._quote_cache.popitem(last=False)
        return quote

    @classmethod
    def get_daily_klines(cls, code: str, source: str | None = None, limit: int = 60):
        normalized_code = (code or "").strip().upper()
        normalized_source = (source or "").strip().lower()
        market = cls._detect_market(normalized_code)
        if normalized_source in {"", "auto", "eastmoney"}:
            eastmoney_klines = cls._fetch_kline_from_eastmoney(normalized_code, limit=limit)
            if eastmoney_klines:
                return eastmoney_klines
            if market == "US":
                return cls._fetch_kline_from_yahoo(normalized_code, limit=limit)
            return []
        if normalized_source in {"sina", "tencent"}:
            tencent_klines = cls._fetch_kline_from_tencent(normalized_code, limit=limit)
            if market == "US" and len(tencent_klines) < 10:
                return cls._fetch_kline_from_yahoo(normalized_code, limit=limit)
            return tencent_klines
        if normalized_source == "tickflow":
            return []
        return []

    @classmethod
    def _fetch_from_sina(cls, code):
        try:
            symbol = cls._build_sina_symbol(code)
            if not symbol:
                return None
            url = f"http://hq.sinajs.cn/list={symbol}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=2)
            if resp.status_code != 200:
                return None
            content = resp.text
            if not content or '=' not in content:
                return None
            data_str = content.split('=', 1)[1].strip().strip('";')
            data = data_str.split(',')
            if len(data) < 30:
                return None
            pre_close = cls._safe_float(data[2], 0)
            price = cls._safe_float(data[3], 0)
            open_price = cls._safe_float(data[1], price)
            high = cls._safe_float(data[4], price)
            low = cls._safe_float(data[5], price)
            volume = cls._safe_int(data[8], 0)
            turnover = cls._safe_float(data[9], 0)
            if pre_close == 0:
                change_pct = 0
            else:
                change_pct = (price - pre_close) / pre_close * 100
            return {
                "code": code,
                "name": data[0],
                "price": price,
                "change": price - pre_close,
                "change_pct": change_pct,
                "volume": volume,
                "turnover": turnover,
                "high": high,
                "low": low,
                "open": open_price,
                "pre_close": pre_close,
                "source": "新浪"
            }
        except Exception as e:
            Logger().warning(f"Sina fetch failed for {code}: {e}")
            return None

    @classmethod
    def _fetch_from_tencent(cls, code):
        try:
            symbol = cls._build_tencent_symbol(code)
            if not symbol:
                return None
            url = f"http://qt.gtimg.cn/q={symbol}"
            resp = requests.get(url, timeout=2)
            if resp.status_code != 200:
                return None
            content = resp.text
            match = content.split('=')
            if len(match) < 2:
                return None
            data = match[1].strip('";').split('~')
            if len(data) < 30:
                return None
            price = cls._safe_float(data[3], 0)
            change = cls._safe_float(data[31], 0)
            change_pct = cls._safe_float(data[32], 0)
            volume = cls._safe_int(data[36], 0)
            turnover = cls._safe_float(data[37], 0) * 10000
            high = cls._safe_float(data[33], price)
            low = cls._safe_float(data[34], price)
            open_price = cls._safe_float(data[5], price)
            pre_close = cls._safe_float(data[4], price)
            return {
                "code": code,
                "name": data[1],
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
                "turnover": turnover,
                "high": high,
                "low": low,
                "open": open_price,
                "pre_close": pre_close,
                "source": "腾讯"
            }
        except Exception as e:
            Logger().warning(f"Tencent fetch failed for {code}: {e}")
            return None

    @classmethod
    def _fetch_from_eastmoney(cls, code):
        try:
            secid = cls._build_eastmoney_secid(code)
            if not secid:
                return None
            url = (
                "https://push2.eastmoney.com/api/qt/stock/get"
                f"?secid={secid}&fields=f57,f58,f43,f169,f170,f47,f48,f44,f45,f46,f60"
            )
            resp = requests.get(url, timeout=2)
            if resp.status_code != 200:
                return None
            payload = resp.json()
            data = (payload or {}).get("data") or {}
            if not data:
                return None
            price = cls._safe_float(data.get("f43"), 0) / 100
            pre_close = cls._safe_float(data.get("f60"), 0) / 100
            change = cls._safe_float(data.get("f169"), 0) / 100
            change_pct = cls._safe_float(data.get("f170"), 0) / 100
            high = cls._safe_float(data.get("f44"), price * 100) / 100
            low = cls._safe_float(data.get("f45"), price * 100) / 100
            open_price = cls._safe_float(data.get("f46"), price * 100) / 100
            volume = cls._safe_int(data.get("f47"), 0)
            turnover = cls._safe_float(data.get("f48"), 0)
            return {
                "code": str(data.get("f57") or code).upper(),
                "name": data.get("f58") or code,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
                "turnover": turnover,
                "high": high,
                "low": low,
                "open": open_price,
                "pre_close": pre_close if pre_close else (price - change),
                "source": "东方财富",
            }
        except Exception as e:
            Logger().warning(f"EastMoney fetch failed for {code}: {e}")
            return None

    @classmethod
    def _fetch_kline_from_eastmoney(cls, code: str, limit: int = 60):
        try:
            secid = cls._build_eastmoney_secid(code)
            if not secid:
                return []
            bars = max(10, min(int(limit or 60), 240))
            url = (
                "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                f"?secid={secid}&klt=101&fqt=1&lmt={bars}&end=20500101"
                "&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
            )
            resp = requests.get(url, timeout=3)
            if resp.status_code != 200:
                return []
            payload = resp.json()
            data = (payload or {}).get("data") or {}
            raw_klines = data.get("klines") or []
            result = []
            for line in raw_klines:
                parts = str(line).split(",")
                if len(parts) < 6:
                    continue
                result.append(
                    {
                        "date": parts[0],
                        "open": cls._safe_float(parts[1], 0),
                        "close": cls._safe_float(parts[2], 0),
                        "high": cls._safe_float(parts[3], 0),
                        "low": cls._safe_float(parts[4], 0),
                        "volume": cls._safe_float(parts[5], 0),
                    }
                )
            return result
        except Exception as e:
            Logger().warning(f"EastMoney kline failed for {code}: {e}")
            return []

    @classmethod
    def _fetch_kline_from_tencent(cls, code: str, limit: int = 60):
        try:
            symbol = cls._build_tencent_symbol(code)
            if not symbol:
                return []
            bars = max(10, min(int(limit or 60), 320))
            url = (
                "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
                f"?param={symbol},day,,,{bars},qfq"
            )
            resp = requests.get(url, timeout=3)
            if resp.status_code != 200:
                return []
            payload = resp.json()
            data = (payload or {}).get("data") or {}
            item = data.get(symbol) or {}
            raw_klines = item.get("qfqday") or item.get("day") or []
            result = []
            for line in raw_klines[-bars:]:
                if not isinstance(line, (list, tuple)) or len(line) < 6:
                    continue
                result.append(
                    {
                        "date": str(line[0]),
                        "open": cls._safe_float(line[1], 0),
                        "close": cls._safe_float(line[2], 0),
                        "high": cls._safe_float(line[3], 0),
                        "low": cls._safe_float(line[4], 0),
                        "volume": cls._safe_float(line[5], 0),
                    }
                )
            return result
        except Exception as e:
            Logger().warning(f"Tencent kline failed for {code}: {e}")
            return []

    @classmethod
    def _fetch_kline_from_yahoo(cls, code: str, limit: int = 60):
        try:
            symbol = (code or "").strip().upper()
            if not symbol:
                return []
            bars = max(20, min(int(limit or 60), 320))
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            }
            params = {
                "interval": "1d",
                "range": "2y",
            }
            resp = requests.get(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
                headers=headers,
                params=params,
                timeout=4,
            )
            if resp.status_code != 200:
                return []
            payload = resp.json()
            chart = (payload or {}).get("chart") or {}
            result_list = chart.get("result") or []
            if not result_list:
                return []
            first = result_list[0] or {}
            timestamps = first.get("timestamp") or []
            quote = (((first.get("indicators") or {}).get("quote") or [{}])[0]) or {}
            opens = quote.get("open") or []
            highs = quote.get("high") or []
            lows = quote.get("low") or []
            closes = quote.get("close") or []
            volumes = quote.get("volume") or []
            rows = []
            size = min(len(timestamps), len(opens), len(highs), len(lows), len(closes), len(volumes))
            for idx in range(size):
                open_price = cls._safe_float(opens[idx], 0)
                high_price = cls._safe_float(highs[idx], 0)
                low_price = cls._safe_float(lows[idx], 0)
                close_price = cls._safe_float(closes[idx], 0)
                if not (open_price and high_price and low_price and close_price):
                    continue
                rows.append(
                    {
                        "date": datetime.utcfromtimestamp(int(timestamps[idx])).strftime("%Y-%m-%d"),
                        "open": open_price,
                        "close": close_price,
                        "high": high_price,
                        "low": low_price,
                        "volume": cls._safe_float(volumes[idx], 0),
                    }
                )
            return rows[-bars:]
        except Exception as e:
            Logger().warning(f"Yahoo kline failed for {code}: {e}")
            return []

    @classmethod
    def _detect_market(cls, code: str):
        if not code:
            return ""
        upper_code = code.upper()
        if upper_code.endswith(".HK"):
            return "HK"
        if re.fullmatch(r"\d{6}", upper_code):
            return "A"
        return "US"

    @classmethod
    def _build_sina_symbol(cls, code: str):
        upper_code = (code or "").strip().upper()
        market = cls._detect_market(upper_code)
        if market == "A":
            return ("sh" if upper_code.startswith(("5", "6", "9")) else "sz") + upper_code
        if market == "HK":
            digits = upper_code.replace(".HK", "").zfill(5)
            return f"rt_hk{digits}"
        if market == "US":
            return f"gb_{upper_code.lower()}"
        return None

    @classmethod
    def _build_tencent_symbol(cls, code: str):
        upper_code = (code or "").strip().upper()
        market = cls._detect_market(upper_code)
        if market == "A":
            return ("sh" if upper_code.startswith(("5", "6", "9")) else "sz") + upper_code
        if market == "HK":
            digits = upper_code.replace(".HK", "").zfill(5)
            return f"hk{digits}"
        if market == "US":
            return f"us{upper_code}"
        return None

    @classmethod
    def _build_eastmoney_secid(cls, code: str):
        upper_code = (code or "").strip().upper()
        market = cls._detect_market(upper_code)
        if market == "A":
            if upper_code.startswith(("5", "6", "9")):
                return f"1.{upper_code}"
            return f"0.{upper_code}"
        if market == "HK":
            digits = upper_code.replace(".HK", "").zfill(5)
            return f"116.{digits}"
        if market == "US":
            return f"105.{upper_code}"
        return None

    @classmethod
    def _safe_float(cls, value, default=0):
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _safe_int(cls, value, default=0):
        try:
            if value is None or value == "":
                return default
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @classmethod
    def _mock_quote(cls, code):
        base_price = 10.0 # Default base price
        # Try to find base price from a static map if possible or just random
        change_pct = random.uniform(-2, 2)
        price = base_price * (1 + change_pct / 100)
        return {
            "code": code,
            "name": f"模拟{code}",
            "price": round(price, 2),
            "change": round(price - base_price, 2),
            "change_pct": round(change_pct, 2),
            "volume": random.randint(10000, 1000000),
            "turnover": random.randint(100000, 10000000),
            "high": round(price * 1.01, 2),
            "low": round(price * 0.99, 2),
            "open": base_price,
            "pre_close": base_price,
            "source": "模拟"
        }
