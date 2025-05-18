import requests
from datetime import datetime, timedelta
import logging
import time
from typing import Optional, Dict
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# 禁用SSL警告
urllib3.disable_warnings(InsecureRequestWarning)

class APBScraper:
    def __init__(self):
        """初始化爬蟲"""
        self.base_url = "https://excwebs.apblao.com:40756/api/v1/exchange-rates/history"
        self.min_request_interval = 5  # 最小請求間隔（秒）
        self.last_request_time = 0
        self.timeout = 30  # 請求超時時間（秒）
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.verify = False  # 禁用SSL驗證
        self.session.headers.update(self._get_random_headers())
        
        # 寮國國定假日列表 (格式: MM-DD)
        self.holidays = [
            '01-01',  # 元旦
            '01-20',  # 寮國人民軍建軍節
            '03-08',  # 國際婦女節
            '04-14',  # 寮國新年
            '04-15',  # 寮國新年
            '04-16',  # 寮國新年
            '05-01',  # 勞動節
            '12-02',  # 國慶節
        ]
        
    def _get_random_headers(self) -> Dict[str, str]:
        """生成隨機請求頭"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.apblao.com/'
        }
        
    def _wait_for_next_request(self) -> None:
        """確保請求間隔"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        self.last_request_time = time.time()
        
    def _is_holiday(self, date: datetime) -> bool:
        """
        判斷是否為國定假日
        
        Args:
            date (datetime): 要檢查的日期
            
        Returns:
            bool: 是否為國定假日
        """
        # 檢查是否為週末
        if date.weekday() >= 5:  # 5是週六，6是週日
            return True
            
        # 檢查是否為國定假日
        date_str = date.strftime('%m-%d')
        return date_str in self.holidays
        
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
                
    def _format_date(self, date: datetime) -> str:
        """Format date to DD/MM/YYYY format"""
        return date.strftime("%d/%m/%Y")
    
    def _parse_rate(self, rate_str: str) -> float:
        """Parse rate string to float"""
        try:
            # 移除所有空格
            rate_str = rate_str.strip()
            # 移除所有逗號 (千分位分隔符)
            rate_str = rate_str.replace(',', '')
            return float(rate_str)
        except (ValueError, AttributeError):
            return 0.0
    
    def fetch_apb_rate(self, date=None):
        """
        獲取 APB 匯率
        
        Args:
            date (datetime, optional): 查詢日期
            
        Returns:
            tuple: (匯率字典, 日期) 或 (None, None)
        """
        try:
            self._wait_for_next_request()
            
            # 如果提供了日期，檢查是否為假日
            if date:
                if self._is_holiday(date):
                    self.logger.info(f"APB: {date.strftime('%Y-%m-%d')} 是假日，嘗試獲取前一個工作日的匯率")
                    date = self._get_previous_business_day(date)
                    self.logger.info(f"APB: 使用前一個工作日 {date.strftime('%Y-%m-%d')}")
            else:
                date = datetime.now()
                if self._is_holiday(date):
                    date = self._get_previous_business_day(date)
                    self.logger.info(f"APB: 使用前一個工作日 {date.strftime('%Y-%m-%d')}")
            
            # 構建請求的 payload
            payload = {
                "type": "one",
                "date": self._format_date(date)
            }
            
            self.logger.info(f"APB: 請求 URL: {self.base_url}, Payload: {payload}")
            
            # 發送 POST 請求
            response = self.session.post(
                self.base_url,
                json=payload,
                headers=self._get_random_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 檢查響應內容
            if not response.text:
                self.logger.error("APB: 收到空響應")
                return None, None
                
            self.logger.debug(f"APB: 響應內容: {response.text[:500]}...")  # 只記錄前500個字符
            
            # 解析 JSON 響應
            rates_data = response.json()
            
            # 統一格式的匯率字典
            rates = {
                'date': date.strftime('%Y-%m-%d'),
                'rates': {}
            }
            
            for item in rates_data:
                currency = item.get('ccy')
                buy_rate = item.get('buy')
                sell_rate = item.get('sale')
                
                if currency and buy_rate is not None and sell_rate is not None:
                    rates['rates'][currency] = {
                        'buy': self._parse_rate(buy_rate),
                        'sell': self._parse_rate(sell_rate)
                    }
            
            self.logger.info(f"APB: 成功解析匯率: {rates}")
            return rates, date
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"APB: 請求失敗: {str(e)}")
            return None, None
        except Exception as e:
            self.logger.error(f"APB: 發生未預期的錯誤: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None, None

if __name__ == "__main__":
    # 設置日誌
    logging.basicConfig(level=logging.INFO)
    
    # 創建爬蟲實例
    scraper = APBScraper()
    
    # 獲取匯率
    rates, date = scraper.fetch_apb_rate()
    
    # 打印結果
    print(rates, date) 