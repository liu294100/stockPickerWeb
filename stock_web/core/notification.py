import requests
import threading
from .config_manager import ConfigManager
from .logger import Logger

class NotificationManager:
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
        
    def send_wechat(self, title: str, content: str, template: str = "txt"):
        token = self.config.get('wechat_token')
        if not token:
            return False, "WeChat Token not configured"
            
        url = "http://www.pushplus.plus/send"
        params = {
            "token": token,
            "title": title,
            "content": content,
            "template": template
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            if data.get("code") == 200:
                return True, "WeChat sent successfully"
            else:
                return False, f"WeChat failed: {data.get('msg')}"
        except Exception as e:
            Logger().error(f"WeChat send error: {e}")
            return False, f"WeChat exception: {e}"

    def send_whatsapp(self, message: str):
        # Using Twilio
        account_sid = self.config.get('whatsapp_sid')
        auth_token = self.config.get('whatsapp_token')
        from_whatsapp_number = self.config.get('whatsapp_from')
        to_whatsapp_number = self.config.get('whatsapp_to')
        
        if not all([account_sid, auth_token, from_whatsapp_number, to_whatsapp_number]):
            return False, "WhatsApp configuration missing"
            
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=message,
                from_=from_whatsapp_number,
                to=to_whatsapp_number
            )
            return True, f"WhatsApp sent: {message.sid}"
        except Exception as e:
            Logger().error(f"WhatsApp send error: {e}")
            return False, f"WhatsApp exception: {e}"

    def send_telegram(self, message: str):
        bot_token = self.config.get('telegram_token')
        chat_id = self.config.get('telegram_chat_id')
        
        if not bot_token or not chat_id:
            return False, "Telegram configuration missing"
            
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        try:
            resp = requests.post(url, json=payload, timeout=5)
            data = resp.json()
            if data.get("ok"):
                return True, "Telegram sent successfully"
            else:
                return False, f"Telegram failed: {data.get('description')}"
        except Exception as e:
            Logger().error(f"Telegram send error: {e}")
            return False, f"Telegram exception: {e}"

    def send_all(self, title: str, content: str):
        results = []
        results.append(self.send_wechat(title, content))
        results.append(self.send_whatsapp(f"{title}\n{content}"))
        results.append(self.send_telegram(f"{title}\n{content}"))
        return results
