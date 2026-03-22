import threading
import json
import os
import time
from datetime import datetime
from .config_manager import ConfigManager
from .data_fetcher import DataFetcher
from .logger import Logger

class TradeHistory:
    def __init__(self):
        self.config = ConfigManager()
        self.history = self.config.get('trade_history', [])
        self._lock = threading.Lock()
    
    def add_record(self, record: dict):
        with self._lock:
            record['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.history.insert(0, record)
            # Keep only last 1000 records
            if len(self.history) > 1000:
                self.history = self.history[:1000]
            self.config.set('trade_history', self.history)
            
    def get_all(self):
        return self.history

class TradeEngine:
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
        self.history = TradeHistory()
        self._lock = threading.RLock()
        self.account = self.config.get('account', {
            'cash': 1000000.0,
            'positions': {}
        })
        
    def _save_account(self):
        self.config.set('account', self.account)
        
    def get_account_info(self):
        with self._lock:
            # Update market value
            total_market_value = 0
            positions = self.account.get('positions', {})
            updated_positions = []
            
            for code, pos in positions.items():
                quote = DataFetcher.get_realtime_quote(code)
                current_price = quote['price'] if quote else pos.get('cost', 0)
                market_value = pos['shares'] * current_price
                profit = market_value - (pos['shares'] * pos['cost'])
                profit_pct = (profit / (pos['shares'] * pos['cost'])) * 100 if pos['cost'] > 0 else 0
                
                total_market_value += market_value
                
                updated_positions.append({
                    'code': code,
                    'name': pos['name'],
                    'shares': pos['shares'],
                    'cost': pos['cost'],
                    'current_price': current_price,
                    'market_value': round(market_value, 2),
                    'profit': round(profit, 2),
                    'profit_pct': round(profit_pct, 2)
                })
            
            cash = self.account.get('cash', 0)
            total_assets = cash + total_market_value
            
            return {
                'cash': round(cash, 2),
                'market_value': round(total_market_value, 2),
                'total_assets': round(total_assets, 2),
                'positions': updated_positions
            }

    def buy(self, code: str, quantity: int):
        # Quantity is in hands (1 hand = 100 shares)
        if quantity <= 0:
            return False, "Quantity must be positive"
            
        quote = DataFetcher.get_realtime_quote(code)
        if not quote:
            return False, "Cannot get stock quote"
            
        price = quote['price']
        if price <= 0:
            return False, "Invalid price"
            
        shares = quantity * 100
        amount = price * shares
        
        # Calculate fees
        commission_rate = self.config.get('settings.commission_rate', 0.00025)
        min_commission = self.config.get('settings.min_commission', 5.0)
        commission = max(amount * commission_rate, min_commission)
        
        transfer_fee = 0
        if code.startswith('6'): # Shanghai stock
            transfer_fee_rate = self.config.get('settings.transfer_fee_rate', 0.00001)
            min_transfer_fee = self.config.get('settings.min_transfer_fee', 1.0)
            transfer_fee = max(amount * transfer_fee_rate, min_transfer_fee)
            
        total_cost = amount + commission + transfer_fee
        
        with self._lock:
            cash = self.account.get('cash', 0)
            if cash < total_cost:
                return False, f"Insufficient funds. Need {total_cost:.2f}, have {cash:.2f}"
            
            self.account['cash'] = cash - total_cost
            positions = self.account.get('positions', {})
            
            if code in positions:
                old_pos = positions[code]
                total_shares = old_pos['shares'] + shares
                total_cost_all = (old_pos['shares'] * old_pos['cost']) + total_cost
                avg_cost = total_cost_all / total_shares
                positions[code]['shares'] = total_shares
                positions[code]['cost'] = avg_cost
            else:
                positions[code] = {
                    'name': quote['name'],
                    'shares': shares,
                    'cost': total_cost / shares
                }
            
            self.account['positions'] = positions
            self._save_account()
            
            self.history.add_record({
                'action': 'Buy',
                'code': code,
                'name': quote['name'],
                'price': price,
                'shares': shares,
                'amount': amount,
                'fee': commission + transfer_fee
            })
            
            return True, f"Bought {quantity} hands of {quote['name']} at {price}"

    def sell(self, code: str, quantity: int):
        if quantity <= 0:
            return False, "Quantity must be positive"
            
        with self._lock:
            positions = self.account.get('positions', {})
            if code not in positions:
                return False, "Not holding this stock"
                
            pos = positions[code]
            shares_available = pos['shares']
            shares_to_sell = quantity * 100
            
            if shares_to_sell > shares_available:
                return False, f"Not enough shares. Have {shares_available/100} hands"
                
            quote = DataFetcher.get_realtime_quote(code)
            if not quote:
                return False, "Cannot get stock quote"
                
            price = quote['price']
            amount = price * shares_to_sell
            
            # Calculate fees
            commission_rate = self.config.get('settings.commission_rate', 0.00025)
            min_commission = self.config.get('settings.min_commission', 5.0)
            commission = max(amount * commission_rate, min_commission)
            
            stamp_tax_rate = self.config.get('settings.stamp_tax_rate', 0.001)
            stamp_tax = amount * stamp_tax_rate
            
            transfer_fee = 0
            if code.startswith('6'):
                transfer_fee_rate = self.config.get('settings.transfer_fee_rate', 0.00001)
                min_transfer_fee = self.config.get('settings.min_transfer_fee', 1.0)
                transfer_fee = max(amount * transfer_fee_rate, min_transfer_fee)
                
            total_fee = commission + stamp_tax + transfer_fee
            net_income = amount - total_fee
            
            self.account['cash'] = self.account.get('cash', 0) + net_income
            
            if shares_to_sell == shares_available:
                del positions[code]
            else:
                positions[code]['shares'] -= shares_to_sell
                
            self.account['positions'] = positions
            self._save_account()
            
            self.history.add_record({
                'action': 'Sell',
                'code': code,
                'name': pos['name'],
                'price': price,
                'shares': shares_to_sell,
                'amount': amount,
                'fee': total_fee
            })
            
            return True, f"Sold {quantity} hands of {pos['name']} at {price}"
