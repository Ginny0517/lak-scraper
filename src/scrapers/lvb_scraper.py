import requests
import datetime
import logging
import time
import urllib3
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class LVBScraper:
    """LaoVietBank 匯率爬蟲"""
    
    def __init__(self):
        self.base_url = "https://www.laovietbank.com.la/en_US/exchange/exchange-rate.html"
        self.request_interval = 1  # 請求間隔（秒）
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.laovietbank.com.la',
            'Referer': 'https://www.laovietbank.com.la/en_US/exchange/exchange-rate.html'
        }
        
    def _ensure_request_interval(self):
        """確保請求間隔"""
        time.sleep(self.request_interval)
        
    def _format_date(self, date: datetime.datetime) -> str:
        """格式化日期為 DD-MM-YYYY"""
        return date.strftime('%d-%m-%Y')
        
    def _parse_rate(self, rate_str: str) -> float:
        """解析匯率字串為浮點數"""
        try:
            # 移除所有空格
            rate_str = rate_str.strip()
            # 移除所有點 (千分位分隔符)
            rate_str = rate_str.replace('.', '')
            # 將所有逗號替換為點 (小數點)
            rate_str = rate_str.replace(',', '.')
            return float(rate_str)
        except (ValueError, AttributeError):
            return 0.0
            
    def _is_holiday(self, date: datetime.datetime) -> bool:
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
        
    def _get_previous_business_day(self, date: datetime.datetime) -> datetime.datetime:
        """
        獲取上一個營業日
        
        Args:
            date (datetime): 當前日期
            
        Returns:
            datetime: 上一個營業日
        """
        while True:
            date = date - datetime.timedelta(days=1)
            if not self._is_holiday(date):
                return date
            
    def fetch_lvb_rate(self, date: Optional[datetime.datetime] = None) -> Tuple[Optional[Dict], Optional[datetime.datetime]]:
        """獲取 LVB 匯率
        
        Args:
            date: 指定日期，如果為 None 則使用當前日期
            
        Returns:
            Tuple[Optional[Dict], Optional[datetime.datetime]]: (匯率資料, 日期物件)
        """
        if date is None:
            date = datetime.datetime.now()
            
        # 檢查是否為假日，如果是則獲取上一個營業日
        if self._is_holiday(date):
            self.logger.info(f"LVB: {date.strftime('%Y-%m-%d')} 是假日，嘗試獲取前一個工作日的匯率")
            date = self._get_previous_business_day(date)
            self.logger.info(f"LVB: 使用前一個工作日 {date.strftime('%Y-%m-%d')}")
            
        date_str = self._format_date(date)
        self.logger.info(f"正在獲取 LVB {date_str} 的匯率...")
        
        try:
            self._ensure_request_interval()
            
            # 先進行 GET 請求獲取頁面
            response = self.session.get(
                self.base_url,
                headers=self._get_random_headers(),
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            
            self._ensure_request_interval()
            
            # 準備 POST 請求資料
            data = {
                'date': date_str
            }
            
            # 發送 POST 請求
            response = self.session.post(
                self.base_url,
                data=data,
                headers=self._get_random_headers(),
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            
            # 保存響應內容以供調試
            with open('lvb_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # 解析 HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找匯率表格
            table = soup.find('table', {'class': 'table-bordered'})
            
            if not table:
                self.logger.error("未找到匯率表格")
                return None, None
                
            # 解析匯率資料
            rates = {}
            rows = table.find_all('tr')
            self.logger.info(f"找到 {len(rows)} 行數據")
            
            # 跳過表頭和說明行
            for row in rows[2:]:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    currency_text = cols[0].text.strip()
                    if '/' in currency_text:
                        currency = currency_text.split('/')[0].strip()
                        if currency:
                            try:
                                # 用 stripped_strings 取得所有面額行
                                denomination_lines = list(cols[1].stripped_strings)
                                buy_lines = list(cols[2].stripped_strings)
                                sell_lines = list(cols[5].stripped_strings)

                                if currency in ['USD', 'EUR']:
                                    # 直接取第二個買價和最後一個賣價
                                    buy_lines = list(cols[2].stripped_strings)
                                    if len(buy_lines) >= 2:
                                        buy_rate = self._parse_rate(buy_lines[1])  # 第二個價格
                                        sell_rate = self._parse_rate(cols[5].text.strip())  # 最後一個賣價
                                        if buy_rate and sell_rate:
                                            rates[currency] = {
                                                'buy': buy_rate,
                                                'sell': sell_rate
                                            }
                                            self.logger.info(f"成功解析 {currency} 50-100面額: 買入 {buy_rate}, 賣出 {sell_rate}")
                                        else:
                                            self.logger.warning(f"{currency} 50-100面額解析失敗")
                                    else:
                                        self.logger.warning(f"{currency} 沒有兩組現金價格")
                                else:
                                    # 其他幣種直接取第一行
                                    buy_rate = self._parse_rate(buy_lines[0]) if buy_lines else None
                                    sell_rate = self._parse_rate(sell_lines[0]) if sell_lines else None
                                    if buy_rate and sell_rate:
                                        rates[currency] = {
                                            'buy': buy_rate,
                                            'sell': sell_rate
                                        }
                                        self.logger.info(f"成功解析 {currency} 匯率: 買入 {buy_rate}, 賣出 {sell_rate}")
                            except Exception as e:
                                self.logger.error(f"解析 {currency} 匯率時發生錯誤: {str(e)}")
            
            if not rates:
                self.logger.warning(f"未找到 {date_str} 的匯率資料")
                return None, None
                
            self.logger.info(f"成功獲取 LVB {date_str} 的匯率")
            return {'date': date, 'rates': rates}, date
            
        except requests.RequestException as e:
            self.logger.error(f"請求 LVB 匯率時發生錯誤: {str(e)}")
            return None, None
        except Exception as e:
            self.logger.error(f"處理 LVB 匯率時發生錯誤: {str(e)}")
            return None, None

if __name__ == '__main__':
    # 測試爬蟲
    scraper = LVBScraper()
    rates, date = scraper.fetch_lvb_rate()
    logging.info(f"日期: {date}")
    logging.info("匯率:")
    if rates:
        for currency, rate_data in rates['rates'].items():
            logging.info(f"{currency}: 買入 {rate_data['buy']}, 賣出 {rate_data['sell']}")
    else:
        logging.error("無資料") 