from .market_service import MarketService
from .notification_service import NotificationService
from .settings_service import SettingsService
from .trade_service import TradeService


class ServiceContainer:
    def __init__(self):
        self.market_service = MarketService()
        self.trade_service = TradeService()
        self.notification_service = NotificationService()
        self.settings_service = SettingsService()
