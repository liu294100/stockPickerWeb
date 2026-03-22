import time
import requests
import random
import threading
import json
import logging
from collections import OrderedDict
from datetime import datetime, timedelta
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
    def get_realtime_quote(cls, code: str):
        now = time.time()
        cache_time = 5 if cls.is_trading_time()[0] else 30
        
        with cls._quote_cache_lock:
            if code in cls._quote_cache:
                ts, quote = cls._quote_cache[code]
                if now - ts < cache_time:
                    return quote.copy()
        
        quote = cls._fetch_from_sina(code)
        if not quote:
            quote = cls._fetch_from_tencent(code)
            
        if not quote and ConfigManager().get('settings.use_mock_on_fail', True):
            quote = cls._mock_quote(code)
        
        if quote:
            with cls._quote_cache_lock:
                cls._quote_cache[code] = (now, quote)
                if len(cls._quote_cache) > cls.MAX_CACHE_SIZE:
                    cls._quote_cache.popitem(last=False)
        return quote

    @classmethod
    def _fetch_from_sina(cls, code):
        try:
            prefix = 'sh' if code.startswith('6') else 'sz'
            url = f"http://hq.sinajs.cn/list={prefix}{code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=2)
            if resp.status_code != 200:
                return None
            content = resp.text
            if not content or '=' not in content:
                return None
            data_str = content.split('=')[1].strip().strip('";')
            data = data_str.split(',')
            if len(data) < 30:
                return None
            
            return {
                "code": code,
                "name": data[0],
                "price": float(data[3]),
                "change": float(data[3]) - float(data[2]),
                "change_pct": (float(data[3]) - float(data[2])) / float(data[2]) * 100 if float(data[2]) != 0 else 0,
                "volume": int(float(data[8])),
                "turnover": float(data[9]),
                "high": float(data[4]),
                "low": float(data[5]),
                "open": float(data[1]),
                "pre_close": float(data[2]),
                "source": "新浪"
            }
        except Exception as e:
            Logger().warning(f"Sina fetch failed for {code}: {e}")
            return None

    @classmethod
    def _fetch_from_tencent(cls, code):
        try:
            prefix = 'sh' if code.startswith('6') else 'sz'
            url = f"http://qt.gtimg.cn/q={prefix}{code}"
            resp = requests.get(url, timeout=2)
            if resp.status_code != 200:
                return None
            content = resp.text
            match = content.split('=')
            if len(match) < 2:
                return None
            data = match[1].strip('"').split('~')
            if len(data) < 30:
                return None
            
            return {
                "code": code,
                "name": data[1],
                "price": float(data[3]),
                "change": float(data[31]),
                "change_pct": float(data[32]),
                "volume": int(data[36]),
                "turnover": float(data[37]) * 10000,
                "high": float(data[33]),
                "low": float(data[34]),
                "open": float(data[5]),
                "pre_close": float(data[4]),
                "source": "腾讯"
            }
        except Exception as e:
            Logger().warning(f"Tencent fetch failed for {code}: {e}")
            return None

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
