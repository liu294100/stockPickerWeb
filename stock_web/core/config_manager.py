import os
import json
import threading
import copy
from datetime import datetime

class ConfigManager:
    """管理所有配置参数和用户设置"""
    CONFIG_DIR = os.path.join(os.getcwd(), "data")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
    
    DEFAULTS = {
        "version": "1.0.0",
        "wechat_token": "",
        "whatsapp_token": "",
        "whatsapp_sid": "",
        "whatsapp_from": "",
        "whatsapp_to": "",
        "telegram_token": "",
        "telegram_chat_id": "",
        "tushare_token": "",
        "tickflow_api_key": "",
        "tushare_node": "http://118.178.243.149/dataapi",
        "price_alerts": [],
        "condition_alerts": [],
        "account": {
            "cash": 1000000,
            "positions": {}
        },
        "auto_account": {
            "cash": 1000000,
            "positions": {}
        },
        "trade_history": [],
        "settings": {
            "quote_cache_time": 5,
            "quote_cache_time_nontrade": 30,
            "capital_cache_time": 30,
            "minute_cache_time": 60,
            "commission_rate": 0.00025,
            "min_commission": 5.0,
            "stamp_tax_rate": 0.001,
            "transfer_fee_rate": 0.00001,
            "min_transfer_fee": 1.0,
            "data_sources": ["tickflow", "sina", "tencent"],
            "use_mock_on_fail": True,
            "auto_trade_quantity": 1,
            "stop_loss_rate": 0.05,
            "take_profit_rate": 0.10,
            "kline_period": "daily",
            "kline_display_days": 60,
            "realtime_chart_update_interval": 1,
            "minute_periods": ["1min", "5min", "15min", "30min", "60min"],
            "auto_trade_auto_start": False
        }
    }
    
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
        self.config = self.load()
        self._save_lock = threading.Lock()
    
    @classmethod
    def ensure_config_dir(cls):
        if not os.path.exists(cls.CONFIG_DIR):
            os.makedirs(cls.CONFIG_DIR)
    
    def load(self) -> dict:
        self.ensure_config_dir()
        if not os.path.exists(self.CONFIG_FILE):
            return copy.deepcopy(self.DEFAULTS)
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                merged = copy.deepcopy(self.DEFAULTS)
                self._deep_update(merged, data)
                return merged
        except Exception as e:
            backup_name = self.CONFIG_FILE + ".bak." + datetime.now().strftime("%Y%m%d%H%M%S")
            try:
                os.rename(self.CONFIG_FILE, backup_name)
            except:
                pass
            print(f"配置文件损坏，已备份为 {backup_name}，使用默认配置。错误: {e}")
            return copy.deepcopy(self.DEFAULTS)
    
    def _deep_update(self, target: dict, source: dict):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def save(self):
        with self._save_lock:
            self.ensure_config_dir()
            try:
                with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存配置失败: {e}")
    
    def get(self, key: str, default=None):
        keys = key.split('.')
        val = self.config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
                if val is None:
                    return default
            else:
                return default
        return val
    
    def set(self, key: str, value):
        keys = key.split('.')
        target = self.config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save()
