import sqlite3
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple
import os

class ExchangeRateDB:
    def __init__(self, db_path: str = "exchange_rates.db"):
        """初始化資料庫連接"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.logger = logging.getLogger(__name__)
        
        # 檢查資料庫是否存在
        db_exists = os.path.exists(self.db_path)
        
        self._connect()
        
        # 只在資料庫不存在時初始化
        if not db_exists:
            self._init_db()

    def _connect(self):
        """建立資料庫連接"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.logger.info("數據庫連接成功")
        except Exception as e:
            self.logger.error(f"數據庫連接失敗: {str(e)}")
            raise

    def _init_db(self):
        """初始化資料庫表結構"""
        try:
            # 創建匯率表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    currency TEXT NOT NULL,
                    rate REAL NOT NULL,
                    bank TEXT NOT NULL,
                    date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(currency, bank, date)
                )
            ''')
            
            # 創建索引
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_currency_bank_date 
                ON exchange_rates(currency, bank, date)
            ''')
            
            self.conn.commit()
            self.logger.info("數據庫初始化成功")
        except Exception as e:
            self.logger.error(f"數據庫初始化失敗: {str(e)}")
            raise

    def save_rate(self, currency: str, rate: float, date: datetime, bank: str):
        """
        保存匯率數據
        
        Args:
            currency (str): 貨幣代碼
            rate (float): 匯率
            date (datetime): 日期
            bank (str): 銀行名稱 ('BOL' 或 'BCEL')
        """
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO exchange_rates (currency, rate, bank, date)
                VALUES (?, ?, ?, ?)
            ''', (currency, rate, bank, date.strftime('%Y-%m-%d')))
            self.conn.commit()
            self.logger.info(f"成功保存匯率數據: {currency} {rate} {date} {bank}")
        except Exception as e:
            self.logger.error(f"保存匯率數據失敗: {str(e)}")
            raise

    def get_rates_by_date(self, date: datetime) -> Dict[str, Dict[str, float]]:
        """
        獲取指定日期的所有匯率
        
        Args:
            date (datetime): 查詢日期
            
        Returns:
            Dict[str, Dict[str, float]]: 格式為 {currency: {bank: rate}}
        """
        try:
            self.cursor.execute('''
                SELECT currency, bank, rate
                FROM exchange_rates
                WHERE date = ?
            ''', (date.strftime('%Y-%m-%d'),))
            
            results = self.cursor.fetchall()
            rates = {}
            
            for currency, bank, rate in results:
                if currency not in rates:
                    rates[currency] = {}
                rates[currency][bank] = rate
                
            return rates
        except Exception as e:
            self.logger.error(f"獲取匯率數據失敗: {str(e)}")
            return {}

    def get_rate_comparison(self, date: datetime) -> List[Dict]:
        """
        獲取指定日期的匯率比較
        
        Args:
            date (datetime): 查詢日期
            
        Returns:
            List[Dict]: 包含匯率比較資訊的列表
        """
        rates = self.get_rates_by_date(date)
        comparison = []
        
        for currency, bank_rates in rates.items():
            if 'BOL' in bank_rates and 'BCEL' in bank_rates:
                bol_rate = bank_rates['BOL']
                bcel_rate = bank_rates['BCEL']
                diff = bcel_rate - bol_rate
                diff_percent = (diff / bol_rate) * 100 if bol_rate != 0 else 0
                
                comparison.append({
                    'currency': currency,
                    'bol_rate': bol_rate,
                    'bcel_rate': bcel_rate,
                    'difference': diff,
                    'difference_percent': diff_percent
                })
                
        return comparison

    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
            self.logger.info("數據庫連接已關閉") 