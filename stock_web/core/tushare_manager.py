import threading
import logging
from .config_manager import ConfigManager
from .logger import Logger

try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False

class TushareManager:
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
        self.token = self.config.get('tushare_token')
        self.node_url = self.config.get('tushare_node')
        self.remaining = 0
        self.token_valid = False
        self.token_error_msg = ""
        self._lock = threading.RLock()
        self._pro = None
    
    def _get_pro(self):
        if self._pro is None and self.token and HAS_TUSHARE:
            try:
                pro = ts.pro_api(self.token)
                # Tushare pro API doesn't always support changing http_url directly like this in newer versions,
                # but we'll keep the logic from original code.
                if hasattr(pro, '_DataApi__http_url'):
                    pro._DataApi__http_url = self.node_url
                self._pro = pro
            except Exception as e:
                Logger().error(f"Tushare initialization error: {e}")
        return self._pro
    
    def set_token(self, new_token: str):
        with self._lock:
            self.token = new_token.strip()
            self.config.set('tushare_token', self.token)
            self.token_valid = False
            self._pro = None
    
    def get_capital_flow(self, code: str):
        with self._lock:
            pro = self._get_pro()
        if pro is None:
            return None, "Token invalid or Tushare not installed"
        try:
            if code.startswith('6'):
                ts_code = f"{code}.SH"
            else:
                ts_code = f"{code}.SZ"
            df = pro.moneyflow(ts_code=ts_code)
            if df is not None and not df.empty:
                return df.iloc[0].to_dict(), None
            return None, "No data"
        except Exception as e:
            Logger().error(f"Tushare error: {e}")
            return None, str(e)

    def get_financial_snapshot(self, code: str):
        with self._lock:
            pro = self._get_pro()
        if pro is None:
            return None, "Token invalid or Tushare not installed"
        try:
            ts_code = f"{code}.SH" if code.startswith("6") else f"{code}.SZ"
            basic_df = pro.daily_basic(ts_code=ts_code, fields="ts_code,trade_date,pe,pb,total_mv,circ_mv,turnover_rate")
            indicator_df = pro.fina_indicator(ts_code=ts_code, fields="ts_code,end_date,roe,roa,grossprofit_margin,netprofit_margin")
            result = {}
            if basic_df is not None and not basic_df.empty:
                result["daily_basic"] = basic_df.iloc[0].to_dict()
            if indicator_df is not None and not indicator_df.empty:
                result["fina_indicator"] = indicator_df.iloc[0].to_dict()
            if result:
                return result, None
            return None, "No data"
        except Exception as e:
            Logger().error(f"Tushare financial error: {e}")
            return None, str(e)
