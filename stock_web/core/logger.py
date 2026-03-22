import logging
import os
import threading
from datetime import datetime

class Logger:
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
        
        log_dir = os.path.join(os.getcwd(), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        self.logger = logging.getLogger("StockAssistant")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"stock_{datetime.now().strftime('%Y%m%d')}.log"),
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
    def info(self, msg):
        self.logger.info(msg)
        
    def error(self, msg):
        self.logger.error(msg)
        
    def warning(self, msg):
        self.logger.warning(msg)
