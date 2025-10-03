import asyncio
from typing import List, Dict, Optional
import time
from datetime import datetime

from quotexpy import Quotex
from quotexpy.utils import asset_parse
from quotexpy.utils.candles_period import CandlesPeriod
from quotexpy.utils.operation_type import OperationType


class QuotexClient:
    def __init__(self, email: str, password: str, demo: bool = True):
        self.email = email
        self.password = password
        self.demo = demo
        self.connected = False
        self.balance = 0.0
        
        self.client = Quotex(
            email=email,
            password=password,
            headless=True,
        )
        
    async def connect(self) -> bool:
        """Connect to Quotex"""
        try:
            check_connect = await self.client.connect()
            
            if check_connect:
                account_type = 'PRACTICE' if self.demo else 'REAL'
                self.client.change_account(account_type)
                
                self.balance = await self.client.get_balance()
                self.connected = True
                print(f"Connected to Quotex - Account: {account_type}, Balance: ${self.balance}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    async def get_balance(self) -> float:
        """Get account balance"""
        if not self.connected:
            return 0.0
        
        try:
            self.balance = await self.client.get_balance()
            return float(self.balance)
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0.0
    
    async def get_candles(self, asset: str, count: int = 100) -> List[Dict]:
        """Get historical candles for asset"""
        if not self.connected:
            return []
        
        try:
            asset_parsed = asset_parse(asset)
            asset_open = self.client.check_asset(asset_parsed)
            
            if not asset_open or not asset_open[2]:
                if not asset.endswith("_otc"):
                    asset = f"{asset}_otc"
                    asset_parsed = asset_parse(asset)
                    asset_open = self.client.check_asset(asset_parsed)
                
                if not asset_open or not asset_open[2]:
                    print(f"Asset {asset} is closed")
                    return []
            
            candles_data = await self.client.get_candle_v2(asset, CandlesPeriod.ONE_MINUTE)
            
            if not candles_data:
                return []
            
            candles = []
            for candle in candles_data[-count:]:
                candle_dict = {
                    'timestamp': int(candle['time']),
                    'open': float(candle['open']),
                    'high': float(candle['max']),
                    'low': float(candle['min']),
                    'close': float(candle['close']),
                    'volume': int(candle.get('volume', 0))
                }
                candles.append(candle_dict)
            
            return candles
            
        except Exception as e:
            print(f"Error getting candles: {e}")
            return []
    
    async def buy(self, asset: str, amount: float, direction: str, expiry: int) -> bool:
        """Execute a trade"""
        if not self.connected:
            return False
        
        try:
            asset_parsed = asset_parse(asset)
            asset_open = self.client.check_asset(asset_parsed)
            
            if not asset_open or not asset_open[2]:
                if not asset.endswith("_otc"):
                    asset = f"{asset}_otc"
                    asset_parsed = asset_parse(asset)
                    asset_open = self.client.check_asset(asset_parsed)
                
                if not asset_open or not asset_open[2]:
                    print(f"Asset {asset} is closed")
                    return False
            
            operation = OperationType.CALL if direction.lower() == "call" else OperationType.PUT
            
            status, trade_info = await self.client.trade(operation, amount, asset, expiry)
            
            if status:
                print(f"Trade executed: {asset} {direction} ${amount} for {expiry}s")
                return True
            else:
                print(f"Trade failed to execute")
                return False
            
        except Exception as e:
            print(f"Trade execution error: {e}")
            return False
    
    async def check_trade_result(self, trade_id: str) -> Optional[Dict]:
        """Check trade result"""
        try:
            if await self.client.check_win(trade_id):
                profit = self.client.get_profit()
                return {
                    'win': True,
                    'profit': profit
                }
            else:
                profit = self.client.get_profit()
                return {
                    'win': False,
                    'profit': profit
                }
        except Exception as e:
            print(f"Error checking trade result: {e}")
            return None
    
    async def get_assets_open(self) -> List[Dict]:
        """Get available assets"""
        if not self.connected:
            return []
        
        try:
            payment_data = self.client.get_payment()
            assets = []
            
            for asset_name, asset_data in payment_data.items():
                if asset_data['open'] and '_otc' in asset_name.lower():
                    assets.append({
                        'name': asset_name,
                        'open': asset_data['open'],
                        'payout': asset_data['payment']
                    })
            
            return assets
            
        except Exception as e:
            print(f"Error getting assets: {e}")
            return []
    
    async def disconnect(self):
        """Disconnect from Quotex"""
        self.connected = False
        try:
            self.client.close()
            print("Disconnected from Quotex")
        except Exception as e:
            print(f"Disconnect error: {e}")


async def test_client():
    """Test the Quotex client"""
    client = QuotexClient("test@example.com", "password", demo=True)
    
    if await client.connect():
        print("Connected successfully!")
        
        balance = await client.get_balance()
        print(f"Balance: ${balance}")
        
        candles = await client.get_candles("EURUSD_otc", 10)
        print(f"Got {len(candles)} candles")
        
        if candles:
            print(f"Last candle: {candles[-1]}")
        
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_client())
