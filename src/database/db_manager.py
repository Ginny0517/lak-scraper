import sqlite3
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple
import os

class ExchangeRateDB:
    def __init__(self):
        """初始化資料庫連接"""
        try:
            self.conn = sqlite3.connect('exchange_rates.db')
            self.cursor = self.conn.cursor()
            self._create_tables()
            logging.info("數據庫連接成功")
        except Exception as e:
            logging.error(f"數據庫連接失敗: {str(e)}")
            raise

    def _create_tables(self):
        """Create necessary tables"""
        try:
            # Create table if not exists
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    currency TEXT NOT NULL,
                    rate REAL NOT NULL,
                    rate_type TEXT NOT NULL,
                    date TEXT NOT NULL,
                    bank TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(currency, rate_type, date, bank)
                )
            ''')
            
            # Create indexes
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_currency ON exchange_rates(currency)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON exchange_rates(date)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_bank ON exchange_rates(bank)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_type ON exchange_rates(rate_type)')
            
            self.conn.commit()
            logging.info("Database tables created successfully")
        except Exception as e:
            logging.error(f"Failed to create tables: {str(e)}")
            raise

    def save_rate(self, currency: str, rate: float, rate_type: str, date: datetime, bank: str):
        """保存匯率數據"""
        try:
            date_str = date.strftime('%Y-%m-%d')
            self.cursor.execute('''
                INSERT OR REPLACE INTO exchange_rates 
                (currency, rate, rate_type, date, bank)
                VALUES (?, ?, ?, ?, ?)
            ''', (currency, rate, rate_type, date_str, bank))
            self.conn.commit()
            logging.info(f"成功保存 {bank} {currency} {rate_type} 匯率: {rate}")
        except Exception as e:
            logging.error(f"保存匯率數據失敗: {str(e)}")
            raise

    def get_rates_by_date(self, date: datetime) -> Dict[str, Dict[str, Dict[str, float]]]:
        """獲取指定日期的匯率"""
        try:
            date_str = date.strftime('%Y-%m-%d')
            self.cursor.execute('''
                SELECT currency, rate, rate_type, bank
                FROM exchange_rates
                WHERE date = ?
            ''', (date_str,))
            
            rates = {}
            for row in self.cursor.fetchall():
                currency, rate, rate_type, bank = row
                if bank not in rates:
                    rates[bank] = {}
                if currency not in rates[bank]:
                    rates[bank][currency] = {}
                rates[bank][currency][rate_type] = rate
                
            return rates
        except Exception as e:
            logging.error(f"獲取匯率數據失敗: {str(e)}")
            return {}

    def get_rate_comparison(self, date: datetime) -> Dict[str, Dict[str, Dict[str, float]]]:
        """獲取指定日期的匯率比較"""
        try:
            date_str = date.strftime('%Y-%m-%d')
            self.cursor.execute('''
                SELECT currency, rate, rate_type, bank
                FROM exchange_rates
                WHERE date = ?
                ORDER BY bank, currency, rate_type
            ''', (date_str,))
            
            comparison = {}
            for row in self.cursor.fetchall():
                currency, rate, rate_type, bank = row
                if currency not in comparison:
                    comparison[currency] = {}
                if rate_type not in comparison[currency]:
                    comparison[currency][rate_type] = {}
                comparison[currency][rate_type][bank] = rate
                
            return comparison
        except Exception as e:
            logging.error(f"獲取匯率比較失敗: {str(e)}")
            return {}

    def close(self):
        """關閉資料庫連接"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
                logging.info("數據庫連接已關閉")
        except Exception as e:
            logging.error(f"關閉數據庫連接失敗: {str(e)}")
            raise 