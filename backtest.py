import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from strategy import TradingStrategy

class BacktestEngine:
    def __init__(self):
        self.results = []
        self.strategy = TradingStrategy()
        
    def run_backtest(self, candles: List[Dict], strategy: TradingStrategy, 
                    lookback_period: int = 100) -> Dict:
        """
        Run backtest on historical data to validate strategy performance
        
        Args:
            candles: List of historical candles
            strategy: Trading strategy instance
            lookback_period: Number of candles to look back for testing
            
        Returns:
            Dictionary with backtest results
        """
        if len(candles) < lookback_period:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_loss': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'details': []
            }
        
        # Use the most recent candles for backtest
        test_candles = candles[-lookback_period:]
        
        trades = []
        balance = 10000.0  # Starting balance for backtest
        initial_balance = balance
        peak_balance = balance
        max_drawdown = 0.0
        
        # Walk through candles looking for patterns
        for i in range(5, len(test_candles)):  # Start from index 5 to have 5 previous candles
            current_candles = test_candles[:i+1]
            
            # Check for pattern in the last 5 candles
            pattern_detected, pattern_type, confidence = strategy.detect_pattern(
                current_candles[-5:]
            )
            
            if pattern_detected and pattern_type and confidence >= 60.0:
                # Simulate trade execution
                trade_amount = 50.0  # Fixed amount for backtest
                if balance >= trade_amount:
                    
                    # Get expected direction
                    direction = strategy.get_trade_direction(pattern_type)
                    
                    # Look at the next candle to determine outcome
                    if i < len(test_candles) - 1:
                        next_candle = test_candles[i + 1]
                        current_candle = test_candles[i]
                        
                        # Determine if trade would be successful
                        if direction == "call":
                            # Expecting price to go up
                            win = next_candle['close'] > current_candle['close']
                        else:  # direction == "put"
                            # Expecting price to go down
                            win = next_candle['close'] < current_candle['close']
                        
                        # Calculate P&L (assume 80% payout for wins)
                        if win:
                            payout = trade_amount * 0.8
                            balance += payout
                            profit_loss = payout
                        else:
                            balance -= trade_amount
                            profit_loss = -trade_amount
                        
                        # Track peak and drawdown
                        if balance > peak_balance:
                            peak_balance = balance
                        
                        current_drawdown = (peak_balance - balance) / peak_balance
                        if current_drawdown > max_drawdown:
                            max_drawdown = current_drawdown
                        
                        # Record trade
                        trade_record = {
                            'timestamp': test_candles[i]['timestamp'],
                            'pattern': pattern_type,
                            'direction': direction,
                            'amount': trade_amount,
                            'confidence': confidence,
                            'win': win,
                            'profit_loss': profit_loss,
                            'balance': balance,
                            'entry_price': current_candle['close'],
                            'exit_price': next_candle['close']
                        }
                        
                        trades.append(trade_record)
        
        # Calculate statistics
        total_trades = len(trades)
        winning_trades = sum(1 for trade in trades if trade['win'])
        losing_trades = total_trades - winning_trades
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        total_profit_loss = balance - initial_balance
        
        # Calculate Sharpe ratio (simplified)
        if trades:
            returns = [trade['profit_loss'] / trade['amount'] for trade in trades]
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'profit_loss': round(total_profit_loss, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 3),
            'final_balance': round(balance, 2),
            'details': trades[-10:]  # Last 10 trades for reference
        }
    
    def analyze_pattern_performance(self, candles: List[Dict]) -> Dict:
        """
        Analyze performance of different patterns separately
        
        Args:
            candles: Historical candles
            
        Returns:
            Dictionary with pattern-specific performance
        """
        pattern_stats = {
            '5_green': {'total': 0, 'wins': 0, 'losses': 0},
            '5_red': {'total': 0, 'wins': 0, 'losses': 0}
        }
        
        # Run analysis similar to backtest but track by pattern type
        for i in range(5, len(candles) - 1):
            current_candles = candles[:i+1]
            
            pattern_detected, pattern_type, confidence = self.strategy.detect_pattern(
                current_candles[-5:]
            )
            
            if pattern_detected and pattern_type and confidence >= 60.0:
                next_candle = candles[i + 1]
                current_candle = candles[i]
                
                direction = self.strategy.get_trade_direction(pattern_type)
                
                if direction == "call":
                    win = next_candle['close'] > current_candle['close']
                else:
                    win = next_candle['close'] < current_candle['close']
                
                pattern_stats[pattern_type]['total'] += 1
                if win:
                    pattern_stats[pattern_type]['wins'] += 1
                else:
                    pattern_stats[pattern_type]['losses'] += 1
        
        # Calculate win rates
        for pattern in pattern_stats:
            total = pattern_stats[pattern]['total']
            wins = pattern_stats[pattern]['wins']
            win_rate_value = (wins / total * 100) if total > 0 else 0.0
            pattern_stats[pattern]['win_rate'] = float(round(win_rate_value, 2))
        
        return pattern_stats
    
    def optimize_parameters(self, candles: List[Dict]) -> Dict:
        """
        Test different parameters to find optimal settings
        
        Args:
            candles: Historical candles
            
        Returns:
            Dictionary with optimal parameters
        """
        best_performance = 0.0
        best_params = {}
        
        # Test different confidence thresholds
        confidence_thresholds = [50, 60, 70, 80]
        
        for confidence_threshold in confidence_thresholds:
            # Modify strategy temporarily
            original_threshold = 60.0  # Default
            
            # Run backtest with this threshold
            modified_results = self._backtest_with_confidence(candles, confidence_threshold)
            
            if modified_results['win_rate'] > best_performance:
                best_performance = modified_results['win_rate']
                best_params = {
                    'confidence_threshold': confidence_threshold,
                    'expected_win_rate': modified_results['win_rate'],
                    'total_trades': modified_results['total_trades']
                }
        
        return best_params
    
    def _backtest_with_confidence(self, candles: List[Dict], confidence_threshold: float) -> Dict:
        """
        Helper method to run backtest with specific confidence threshold
        """
        trades_count = 0
        wins = 0
        
        for i in range(5, len(candles) - 1):
            current_candles = candles[:i+1]
            
            pattern_detected, pattern_type, confidence = self.strategy.detect_pattern(
                current_candles[-5:]
            )
            
            if pattern_detected and pattern_type and confidence >= confidence_threshold:
                trades_count += 1
                
                next_candle = candles[i + 1]
                current_candle = candles[i]
                
                direction = self.strategy.get_trade_direction(pattern_type)
                
                if direction == "call":
                    win = next_candle['close'] > current_candle['close']
                else:
                    win = next_candle['close'] < current_candle['close']
                
                if win:
                    wins += 1
        
        win_rate = (wins / trades_count * 100) if trades_count > 0 else 0.0
        
        return {
            'total_trades': trades_count,
            'winning_trades': wins,
            'win_rate': float(round(win_rate, 2))
        }
    
    def generate_backtest_report(self, results: Dict) -> str:
        """
        Generate a formatted backtest report
        
        Args:
            results: Backtest results dictionary
            
        Returns:
            Formatted report string
        """
        report = f"""
    ═══════════════════════════════════════
         BACKTEST REPORT - 5 Velas Iguais
    ═══════════════════════════════════════
    
    📊 PERFORMANCE METRICS
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Total Trades: {results['total_trades']}
    Winning Trades: {results['winning_trades']}
    Losing Trades: {results['losing_trades']}
    Win Rate: {results['win_rate']}%
    
    💰 FINANCIAL RESULTS
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Profit/Loss: ${results['profit_loss']}
    Final Balance: ${results['final_balance']}
    Max Drawdown: {results['max_drawdown']}%
    Sharpe Ratio: {results['sharpe_ratio']}
    
    ✅ STRATEGY VALIDATION
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Strategy Approved: {'✅ YES' if results['win_rate'] >= 60 else '❌ NO'}
    Minimum Win Rate: 60%
    Current Win Rate: {results['win_rate']}%
    
    📈 RECOMMENDATION
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
        
        if results['win_rate'] >= 60:
            report += "Strategy shows positive results. Approved for live trading."
        else:
            report += "Strategy does not meet minimum requirements. Consider optimization."
        
        return report

# Example usage
if __name__ == "__main__":
    # Test backtest engine
    backtest = BacktestEngine()
    
    # Generate sample candles for testing
    sample_candles = []
    base_price = 1.2000
    
    for i in range(150):
        # Generate somewhat realistic price movement
        price_change = (np.random.random() - 0.5) * 0.002
        open_price = base_price + price_change
        close_price = open_price + (np.random.random() - 0.5) * 0.001
        high_price = max(open_price, close_price) + np.random.random() * 0.0005
        low_price = min(open_price, close_price) - np.random.random() * 0.0005
        
        candle = {
            'timestamp': 1000 + i * 60,
            'open': round(open_price, 5),
            'close': round(close_price, 5),
            'high': round(high_price, 5),
            'low': round(low_price, 5)
        }
        sample_candles.append(candle)
        base_price = close_price
    
    # Run backtest
    strategy = TradingStrategy()
    results = backtest.run_backtest(sample_candles, strategy)
    
    print("Backtest Results:")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']}%")
    print(f"Profit/Loss: ${results['profit_loss']}")
    
    # Generate report
    report = backtest.generate_backtest_report(results)
    print(report)
