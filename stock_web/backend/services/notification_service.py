from core.notification import NotificationManager


class NotificationService:
    def __init__(self):
        self.notification_manager = NotificationManager()

    def send_test(self, message: str, channels: list[str]):
        results = {}
        if "wechat" in channels:
            results["wechat"] = self.notification_manager.send_wechat("Test", message)
        if "whatsapp" in channels:
            results["whatsapp"] = self.notification_manager.send_whatsapp(message)
        if "telegram" in channels:
            results["telegram"] = self.notification_manager.send_telegram(message)
        return results
