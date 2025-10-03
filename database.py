import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Optional
import os


class TradesDatabase:
    def __init__(self):
        self.conn = None
        self.database_url = os.getenv("DATABASE_URL")
        
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self._create_tables()
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def _create_tables(self):
        """Create trades table if it doesn't exist"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        asset VARCHAR(50) NOT NULL,
                        direction VARCHAR(10) NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL,
                        expiry_time INTEGER NOT NULL,
                        pattern VARCHAR(50),
                        backtest_rate DECIMAL(5, 2),
                        status VARCHAR(20) NOT NULL,
                        result VARCHAR(20),
                        profit DECIMAL(10, 2),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_timestamp 
                    ON trades(timestamp DESC)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_asset 
                    ON trades(asset)
                """)
                
                self.conn.commit()
                print("Trades table created successfully")
        except Exception as e:
            print(f"Error creating tables: {e}")
            self.conn.rollback()
    
    def insert_trade(self, trade_data: Dict) -> Optional[int]:
        """Insert a new trade record"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trades 
                    (timestamp, asset, direction, amount, expiry_time, pattern, backtest_rate, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    trade_data.get('timestamp', datetime.now()),
                    trade_data.get('asset'),
                    trade_data.get('direction'),
                    trade_data.get('amount'),
                    trade_data.get('expiry_time', 60),
                    trade_data.get('pattern'),
                    trade_data.get('backtest_rate'),
                    trade_data.get('status', 'executed')
                ))
                
                trade_id = cur.fetchone()[0]
                self.conn.commit()
                return trade_id
        except Exception as e:
            print(f"Error inserting trade: {e}")
            self.conn.rollback()
            return None
    
    def update_trade_result(self, trade_id: int, result: str, profit: float):
        """Update trade result"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE trades 
                    SET result = %s, profit = %s
                    WHERE id = %s
                """, (result, profit, trade_id))
                
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Error updating trade result: {e}")
            self.conn.rollback()
            return False
    
    def get_all_trades(self, limit: int = 100) -> List[Dict]:
        """Get all trades ordered by timestamp"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM trades 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (limit,))
                
                trades = cur.fetchall()
                return [dict(trade) for trade in trades]
        except Exception as e:
            print(f"Error getting trades: {e}")
            return []
    
    def get_trades_by_asset(self, asset: str, limit: int = 50) -> List[Dict]:
        """Get trades for a specific asset"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM trades 
                    WHERE asset = %s
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (asset, limit))
                
                trades = cur.fetchall()
                return [dict(trade) for trade in trades]
        except Exception as e:
            print(f"Error getting trades by asset: {e}")
            return []
    
    def get_trades_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get trades within a date range"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM trades 
                    WHERE timestamp BETWEEN %s AND %s
                    ORDER BY timestamp DESC
                """, (start_date, end_date))
                
                trades = cur.fetchall()
                return [dict(trade) for trade in trades]
        except Exception as e:
            print(f"Error getting trades by date range: {e}")
            return []
    
    def get_trade_statistics(self) -> Dict:
        """Get overall trading statistics"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN result = 'win' THEN 1 END) as wins,
                        COUNT(CASE WHEN result = 'loss' THEN 1 END) as losses,
                        SUM(profit) as total_profit,
                        AVG(profit) as avg_profit,
                        SUM(amount) as total_volume
                    FROM trades
                    WHERE result IS NOT NULL
                """)
                
                stats = cur.fetchone()
                if stats:
                    stats_dict = dict(stats)
                    total = stats_dict['total_trades'] or 0
                    wins = stats_dict['wins'] or 0
                    stats_dict['win_rate'] = (wins / total * 100) if total > 0 else 0.0
                    return stats_dict
                return {}
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    
    def get_statistics_by_asset(self, asset: str) -> Dict:
        """Get statistics for a specific asset"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN result = 'win' THEN 1 END) as wins,
                        COUNT(CASE WHEN result = 'loss' THEN 1 END) as losses,
                        SUM(profit) as total_profit,
                        AVG(profit) as avg_profit
                    FROM trades
                    WHERE asset = %s AND result IS NOT NULL
                """, (asset,))
                
                stats = cur.fetchone()
                if stats:
                    stats_dict = dict(stats)
                    total = stats_dict['total_trades'] or 0
                    wins = stats_dict['wins'] or 0
                    stats_dict['win_rate'] = (wins / total * 100) if total > 0 else 0.0
                    return stats_dict
                return {}
        except Exception as e:
            print(f"Error getting asset statistics: {e}")
            return {}
    
    def get_statistics_by_pattern(self) -> List[Dict]:
        """Get statistics grouped by pattern"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        pattern,
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN result = 'win' THEN 1 END) as wins,
                        COUNT(CASE WHEN result = 'loss' THEN 1 END) as losses,
                        SUM(profit) as total_profit,
                        AVG(backtest_rate) as avg_backtest_rate
                    FROM trades
                    WHERE result IS NOT NULL AND pattern IS NOT NULL
                    GROUP BY pattern
                """)
                
                patterns = cur.fetchall()
                result = []
                for pattern in patterns:
                    pattern_dict = dict(pattern)
                    total = pattern_dict['total_trades'] or 0
                    wins = pattern_dict['wins'] or 0
                    pattern_dict['win_rate'] = (wins / total * 100) if total > 0 else 0.0
                    result.append(pattern_dict)
                
                return result
        except Exception as e:
            print(f"Error getting pattern statistics: {e}")
            return []
    
    def delete_old_trades(self, days: int = 30):
        """Delete trades older than specified days"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM trades 
                    WHERE timestamp < NOW() - INTERVAL '%s days'
                """, (days,))
                
                deleted_count = cur.rowcount
                self.conn.commit()
                print(f"Deleted {deleted_count} old trades")
                return deleted_count
        except Exception as e:
            print(f"Error deleting old trades: {e}")
            self.conn.rollback()
            return 0
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("Database connection closed")


# Test the database connection
if __name__ == "__main__":
    db = TradesDatabase()
    if db.connect():
        print("Database connected successfully!")
        
        # Test insert
        test_trade = {
            'timestamp': datetime.now(),
            'asset': 'EURUSD_otc',
            'direction': 'CALL',
            'amount': 10.0,
            'expiry_time': 60,
            'pattern': '5_red',
            'backtest_rate': 65.5,
            'status': 'executed'
        }
        
        trade_id = db.insert_trade(test_trade)
        print(f"Inserted trade with ID: {trade_id}")
        
        # Get stats
        stats = db.get_trade_statistics()
        print(f"Statistics: {stats}")
        
        db.close()
