from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from bs4 import BeautifulSoup
import re
from ..core.base_scraper import BaseScraper
from ..core.config import HOLIDAYS, BANK_CONFIGS
import logging

class LDBScraper(BaseScraper):
    """LDB 匯率爬蟲"""
    
    def __init__(self):
        """初始化爬蟲"""
        config = BANK_CONFIGS['LDB']
        super().__init__(config['base_url'])
        self.headers = config['headers']
        self.auth = config.get('auth')
        # 設置 logger 級別為 DEBUG
        self.logger.setLevel(logging.DEBUG)
        # 確保 handler 也設置為 DEBUG
        for handler in self.logger.handlers:
            handler.setLevel(logging.DEBUG)
        
    @property
    def holidays(self) -> List[str]:
        """獲取假日列表"""
        return HOLIDAYS
        
    def parse(self, raw_data: Dict) -> List[Dict]:
        """
        解析原始數據
        
        Args:
            raw_data: 原始數據 (dict, 需含 'dataResponse' 欄)
            
        Returns:
            List[Dict]: 解析後的匯率數據列表
        """
        rates = []
        try:
            self.logger.info("開始解析 JSON 響應")
            self.logger.debug(f"JSON 響應內容: {raw_data}")
            
            # 確保 raw_data 是字典類型
            if isinstance(raw_data, str):
                import json
                raw_data = json.loads(raw_data)
            
            if not raw_data.get('status'):
                self.logger.error(f"API 返回錯誤: {raw_data.get('message')}")
                return rates
                
            data_response = raw_data.get('dataResponse')
            if not data_response:
                self.logger.error("API 返回的 dataResponse 為空")
                return rates
                
            for item in data_response:
                currency = item.get('fx_detail', {}).get('fxd_type_name_eng', '')
                buy_rate = item.get('fx_buy')
                sell_rate = item.get('fx_sell')
                
                if not currency or buy_rate is None or sell_rate is None:
                    continue
                    
                try:
                    buy = float(buy_rate)
                    sell = float(sell_rate)
                    rates.append({
                        'currency': currency,
                        'buy': buy,
                        'sell': sell
                    })
                    self.logger.info(f"成功解析 {currency} 匯率: 買入 {buy}, 賣出 {sell}")
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"解析匯率失敗: {currency}, 買入: {buy_rate}, 賣出: {sell_rate}, 錯誤: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析數據時發生錯誤: {str(e)}")
        return rates
        
    def fetch_rate(self, date: Optional[datetime] = None) -> Tuple[Optional[Dict], Optional[datetime]]:
        """
        獲取匯率數據
        
        Args:
            date: 查詢日期
            
        Returns:
            Tuple[Optional[Dict], Optional[datetime]]: (匯率數據, 日期)
        """
        try:
            # 檢查是否為假日
            if date and self._is_holiday(date):
                self.logger.info(f"{date.strftime('%Y-%m-%d')} 是假日，嘗試獲取上一個營業日的匯率")
                date = self._get_previous_business_day(date)
                
            # 格式化日期
            formatted_date = date.strftime('%d-%m-%Y') if date else datetime.now().strftime('%d-%m-%Y')
            
            # 構建請求 URL
            endpoint = f"/bydate/{formatted_date}"
            self.logger.info(f"請求 URL: {self.base_url}{endpoint}")
            
            # 發送請求
            response = self.http_client.fetch(
                endpoint=endpoint,
                method='GET',
                headers={
                    **self.headers,
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Cache-Control': 'no-cache',
                    'Origin': 'https://www.ldblao.la',
                    'Pragma': 'no-cache',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site'
                },
                auth=self.auth
            )
            
            if not response:
                self.logger.error("未收到有效的響應")
                return None, None
                
            # 解析匯率數據
            rates = self.parse(response)
            if not rates:
                self.logger.warning("未找到任何匯率資料")
                return None, None
                
            # 構建結果
            result = {
                'date': date.strftime('%Y-%m-%d') if date else datetime.now().strftime('%Y-%m-%d'),
                'rates': {}
            }
            
            for rate in rates:
                currency = rate['currency']
                result['rates'][currency] = {
                    'buy': rate['buy'],
                    'sell': rate['sell']
                }
                
            self.logger.info(f"成功獲取 LDB {date.strftime('%Y-%m-%d')} 的匯率")
            return result, date
            
        except Exception as e:
            self.logger.error(f"獲取 LDB 匯率時發生錯誤: {str(e)}")
            return None, None
            
    def _get_previous_business_day(self, date: datetime) -> datetime:
        """
        獲取上一個營業日
        
        Args:
            date (datetime): 當前日期
            
        Returns:
            datetime: 上一個營業日
        """
        while True:
            date = date - timedelta(days=1)
            if not self._is_holiday(date):
                return date
                
    def _is_holiday(self, date: datetime) -> bool:
        """
        檢查日期是否為假日
        
        Args:
            date (datetime): 要檢查的日期
            
        Returns:
            bool: 如果日期為假日則返回 True，否則返回 False
        """
        # 檢查是否為週末
        if date.weekday() >= 5:  # 5是週六，6是週日
            return True
            
        # 檢查是否為國定假日
        date_str = date.strftime('%m-%d')
        return date_str in self.holidays 