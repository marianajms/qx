import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Optional

class TradingStrategy:
    def __init__(self):
        self.pattern_history = []
        self.min_candles_required = 6  # Need at least 6 candles to detect 5 same + next
        
    def detect_pattern(self, candles: List[Dict]) -> Tuple[bool, Optional[str], float]:
        """
        Detect if last 5 candles are of same color (all green or all red)
        
        Args:
            candles: List of candle dictionaries with OHLC data
            
        Returns:
            Tuple of (pattern_detected, pattern_type, confidence)
        """
        if len(candles) < 5:
            return False, None, 0.0
        
        # Get last 5 candles
        last_5_candles = candles[-5:]
        
        # Determine candle colors (green if close > open, red if close < open)
        colors = []
        for candle in last_5_candles:
            if candle['close'] > candle['open']:
                colors.append('green')
            elif candle['close'] < candle['open']:
                colors.append('red')
            else:
                colors.append('neutral')  # Doji
        
        # Check if all 5 candles are the same color (excluding neutral)
        if len(set(colors)) == 1 and colors[0] != 'neutral':
            pattern_type = f"5_{colors[0]}"
            
            # Calculate confidence based on candle body sizes
            confidence = self._calculate_confidence(last_5_candles)
            
            return True, pattern_type, confidence
        
        return False, None, 0.0
    
    def _calculate_confidence(self, candles: List[Dict]) -> float:
        """
        Calculate confidence level based on candle characteristics
        
        Args:
            candles: List of candle dictionaries
            
        Returns:
            Confidence percentage (0-100)
        """
        if not candles:
            return 0.0
        
        total_confidence = 0.0
        
        for candle in candles:
            body_size = abs(candle['close'] - candle['open'])
            wick_size = candle['high'] - candle['low']
            
            # Higher body to wick ratio = higher confidence
            if wick_size > 0:
                body_ratio = body_size / wick_size
                candle_confidence = min(body_ratio * 100, 100)  # Cap at 100%
            else:
                candle_confidence = 50.0  # Default for edge case
            
            total_confidence += candle_confidence
        
        average_confidence = total_confidence / len(candles)
        
        # Boost confidence if all candles have good body sizes
        if average_confidence > 70:
            average_confidence = min(average_confidence * 1.1, 100)
        
        return round(average_confidence, 1)
    
    def get_trade_direction(self, pattern_type: str) -> str:
        """
        Get trade direction based on pattern
        
        Args:
            pattern_type: Pattern type ('5_green' or '5_red')
            
        Returns:
            Trade direction ('call' or 'put')
        """
        if pattern_type == "5_green":
            return "put"  # Expect reversal down
        elif pattern_type == "5_red":
            return "call"  # Expect reversal up
        else:
            return "call"  # Default
    
    def should_trade(self, candles: List[Dict], backtest_win_rate: float, 
                    min_win_rate: float = 60.0) -> bool:
        """
        Determine if we should execute a trade based on pattern and backtest results
        
        Args:
            candles: Historical candles
            backtest_win_rate: Win rate from backtest
            min_win_rate: Minimum required win rate
            
        Returns:
            Boolean indicating if we should trade
        """
        pattern_detected, pattern_type, confidence = self.detect_pattern(candles)
        
        if not pattern_detected:
            return False
        
        # Check if backtest meets minimum win rate
        if backtest_win_rate < min_win_rate:
            return False
        
        # Check confidence level
        if confidence < 60.0:  # Minimum confidence threshold
            return False
        
        return True
    
    def analyze_market_condition(self, candles: List[Dict]) -> Dict:
        """
        Analyze current market conditions
        
        Args:
            candles: Historical candles
            
        Returns:
            Dictionary with market analysis
        """
        if len(candles) < 20:
            return {"trend": "unknown", "volatility": "unknown", "strength": 0}
        
        df = pd.DataFrame(candles)
        
        # Calculate trend using simple moving averages
        df['sma_5'] = df['close'].rolling(5).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        
        # Determine trend
        last_sma_5 = df['sma_5'].iloc[-1]
        last_sma_20 = df['sma_20'].iloc[-1]
        
        if last_sma_5 > last_sma_20:
            trend = "bullish"
        elif last_sma_5 < last_sma_20:
            trend = "bearish"
        else:
            trend = "sideways"
        
        # Calculate volatility using ATR approximation
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = abs(df['high'] - df['close'].shift(1))
        df['low_close'] = abs(df['low'] - df['close'].shift(1))
        df['true_range'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        
        atr = df['true_range'].rolling(14).mean().iloc[-1]
        
        # Classify volatility
        if atr > df['close'].iloc[-1] * 0.002:  # > 0.2%
            volatility = "high"
        elif atr > df['close'].iloc[-1] * 0.001:  # > 0.1%
            volatility = "medium"
        else:
            volatility = "low"
        
        # Calculate trend strength
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20]
        strength = min(abs(price_change) * 100, 100)  # Convert to percentage, cap at 100
        
        return {
            "trend": trend,
            "volatility": volatility,
            "strength": round(strength, 1),
            "atr": round(atr, 6)
        }
    
    def get_optimal_trade_amount(self, balance: float, win_rate: float, 
                               risk_percentage: float = 2.0) -> float:
        """
        Calculate optimal trade amount using Kelly Criterion approximation
        
        Args:
            balance: Current account balance
            win_rate: Historical win rate (0-100)
            risk_percentage: Maximum risk per trade as percentage of balance
            
        Returns:
            Recommended trade amount
        """
        if balance <= 0 or win_rate <= 0:
            return 0.0
        
        # Convert win rate to decimal
        p = win_rate / 100.0
        
        # Assume binary options typical payout ratio (80%)
        b = 0.8
        
        # Kelly Criterion: f = (bp - q) / b
        # where f = fraction of capital to bet
        # p = probability of winning
        # q = probability of losing = 1 - p
        # b = payout ratio
        
        q = 1 - p
        kelly_fraction = (b * p - q) / b
        
        # Be conservative - use half Kelly
        conservative_fraction = kelly_fraction * 0.5
        
        # Apply maximum risk limit
        max_risk_amount = balance * (risk_percentage / 100.0)
        kelly_amount = balance * max(conservative_fraction, 0)
        
        # Use the smaller of the two amounts
        recommended_amount = min(kelly_amount, max_risk_amount)
        
        # Round to reasonable amount and ensure minimum
        recommended_amount = max(round(recommended_amount, 2), 1.0)
        
        return min(recommended_amount, balance)

# Example usage and testing
if __name__ == "__main__":
    strategy = TradingStrategy()
    
    # Test with sample candles
    sample_candles = [
        {'open': 1.2000, 'close': 1.2010, 'high': 1.2015, 'low': 1.1995, 'timestamp': 1000},
        {'open': 1.2010, 'close': 1.2020, 'high': 1.2025, 'low': 1.2005, 'timestamp': 1060},
        {'open': 1.2020, 'close': 1.2030, 'high': 1.2035, 'low': 1.2015, 'timestamp': 1120},
        {'open': 1.2030, 'close': 1.2040, 'high': 1.2045, 'low': 1.2025, 'timestamp': 1180},
        {'open': 1.2040, 'close': 1.2050, 'high': 1.2055, 'low': 1.2035, 'timestamp': 1240},
    ]
    
    detected, pattern_type, confidence = strategy.detect_pattern(sample_candles)
    print(f"Pattern detected: {detected}")
    print(f"Pattern type: {pattern_type}")
    print(f"Confidence: {confidence}%")
    
    if detected:
        direction = strategy.get_trade_direction(pattern_type)
        print(f"Trade direction: {direction}")
    
    # Test market analysis
    market_analysis = strategy.analyze_market_condition(sample_candles)
    print(f"Market analysis: {market_analysis}")
    
    # Test optimal trade amount
    optimal_amount = strategy.get_optimal_trade_amount(1000, 65, 2.0)
    print(f"Optimal trade amount: ${optimal_amount}")
