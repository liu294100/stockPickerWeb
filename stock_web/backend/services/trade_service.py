from core.trade_engine import TradeEngine


class TradeService:
    def __init__(self):
        self.trade_engine = TradeEngine()

    def get_account_info(self):
        return self.trade_engine.get_account_info()

    def buy(self, code: str, quantity: int):
        return self.trade_engine.buy(code, quantity)

    def sell(self, code: str, quantity: int):
        return self.trade_engine.sell(code, quantity)
