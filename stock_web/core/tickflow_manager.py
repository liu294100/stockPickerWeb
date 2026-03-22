import threading
from .config_manager import ConfigManager
from .logger import Logger

try:
    from tickflow import TickFlow

    HAS_TICKFLOW = True
except ImportError:
    HAS_TICKFLOW = False


class TickFlowManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.config = ConfigManager()
        self._client = None
        self._free_client = None

    def _normalize_symbol(self, code: str):
        if "." in code:
            return code.upper()
        if code.startswith("6"):
            return f"{code}.SH"
        return f"{code}.SZ"

    def _get_client(self):
        if not HAS_TICKFLOW:
            return None
        if self._client is not None:
            return self._client
        api_key = self.config.get("tickflow_api_key", "").strip()
        if not api_key:
            return None
        try:
            self._client = TickFlow(api_key=api_key)
            return self._client
        except Exception as e:
            Logger().warning(f"TickFlow client init failed: {e}")
            return None

    def _get_free_client(self):
        if not HAS_TICKFLOW:
            return None
        if self._free_client is not None:
            return self._free_client
        try:
            self._free_client = TickFlow.free()
            return self._free_client
        except Exception as e:
            Logger().warning(f"TickFlow free client init failed: {e}")
            return None

    def get_quote(self, code: str):
        client = self._get_client()
        if client is None:
            return None
        symbol = self._normalize_symbol(code)
        try:
            quotes = client.quotes.get(symbols=[symbol])
            if isinstance(quotes, list) and quotes:
                first = quotes[0]
            elif isinstance(quotes, dict):
                if symbol in quotes:
                    first = quotes[symbol]
                elif "data" in quotes and isinstance(quotes["data"], list) and quotes["data"]:
                    first = quotes["data"][0]
                else:
                    first = quotes
            else:
                return None
            return first
        except Exception as e:
            Logger().warning(f"TickFlow quote failed for {code}: {e}")
            return None

    def get_daily_klines(self, code: str, limit: int = 30):
        symbol = self._normalize_symbol(code)
        client = self._get_client() or self._get_free_client()
        if client is None:
            return []
        try:
            df = client.klines.get(symbol, period="1d", as_dataframe=True)
            if df is None or df.empty:
                return []
            rows = []
            for _, row in df.tail(limit).iterrows():
                row_data = row.to_dict()
                rows.append(
                    {
                        "date": str(row_data.get("date", row_data.get("time", ""))),
                        "open": float(row_data.get("open", 0) or 0),
                        "high": float(row_data.get("high", 0) or 0),
                        "low": float(row_data.get("low", 0) or 0),
                        "close": float(row_data.get("close", 0) or 0),
                        "volume": float(row_data.get("volume", 0) or 0),
                    }
                )
            return rows
        except Exception as e:
            Logger().warning(f"TickFlow kline failed for {code}: {e}")
            return []
