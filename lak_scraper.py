import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re
import time
from typing import Optional, Tuple, Dict
import random
from fake_useragent import UserAgent
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import json

# 禁用SSL警告
urllib3.disable_warnings(InsecureRequestWarning)

class LAKScraper:
    def __init__(self):
        """初始化爬蟲"""
        self.base_url = "https://www.bol.gov.la/en/ExchangRate.php"
        self.api_url = "https://www.bol.gov.la/en/ExchangRate.php"
        self.min_request_interval = 5  # 最小請求間隔（秒）
        self.last_request_time = 0
        self.timeout = 30  # 請求超時時間（秒）
        self.proxies = None  # 代理設置
        self.manual_rates = {}  # 手動設置的匯率
        self.manual_date = None  # 手動設置的日期
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.verify = False  # 禁用SSL驗證
        self.session.headers.update(self._get_random_headers())
        
    def _get_random_headers(self) -> Dict[str, str]:
        """生成隨機請求頭"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.bol.gov.la/en/index'
        }
        
    def _wait_for_next_request(self) -> None:
        """確保請求間隔"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        self.last_request_time = time.time()
        
    def _extract_rate_from_text(self, text: str, currency: str = None) -> Optional[float]:
        """從文本中提取匯率數字
        
        Args:
            text (str): 包含匯率的文本
            currency (str, optional): 貨幣代碼
            
        Returns:
            Optional[float]: 解析後的匯率
        """
        try:
            # 移除所有非數字、小數點和逗號的字符
            cleaned_text = re.sub(r'[^\d.,]', '', text)
            if not cleaned_text:
                self.logger.warning(f"清理後的文本為空: {text}")
                return None
                
            # 在寮國格式中，點是千分位，逗號是小數點
            # 先移除千分位點
            cleaned_text = cleaned_text.replace('.', '')
            # 將逗號轉換為小數點
            cleaned_text = cleaned_text.replace(',', '.')
            
            # 嘗試解析為浮點數
            try:
                rate = float(cleaned_text)
                self.logger.debug(f"成功將文本 '{text}' 轉換為匯率: {rate}")
                return rate
            except ValueError:
                self.logger.warning(f"無法將文本 '{text}' 轉換為浮點數")
                return None
                
        except Exception as e:
            self.logger.error(f"從文本提取匯率時發生錯誤: {str(e)}, 文本: {text}")
            return None
            
    def _parse_rate_table(self, html_content):
        """
        解析匯率表格
        
        Args:
            html_content (str): HTML內容
            
        Returns:
            tuple: (匯率字典, 日期) 或 (None, None)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找匯率表格
            table = soup.find('table')
            if not table:
                self.logger.warning("無法找到匯率表格")
                return None, None
                
            # 獲取日期
            date_input = soup.find('input', {'name': 'date', 'class': 'date'})
            if date_input and 'value' in date_input.attrs:
                date_str = date_input['value']
                try:
                    date = datetime.strptime(date_str, '%d-%m-%Y')
                except ValueError:
                    date = datetime.now()
            else:
                date = datetime.now()
            
            # 解析所有貨幣的匯率
            rates = {}
            for row in table.find_all('tr')[1:]:  # 跳過表頭
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 6:
                    try:
                        currency_code = cols[3].text.strip()
                        rate_text = cols[4].text.strip()
                        self.logger.debug(f"找到貨幣: {currency_code}, 匯率文本: {rate_text}")
                        
                        rate = self._extract_rate_from_text(rate_text, currency_code)
                        if rate is not None:
                            rates[currency_code] = rate
                            self.logger.info(f"成功解析 {currency_code} 匯率: {rate}")
                        else:
                            self.logger.warning(f"無法解析 {currency_code} 的匯率文本: {rate_text}")
                    except Exception as e:
                        self.logger.error(f"解析行時發生錯誤: {str(e)}")
                        continue
            
            if not rates:
                self.logger.warning("未找到任何有效的匯率數據")
                return None, None
                
            self.logger.info(f"成功解析所有匯率: {rates}")
            return rates, date
                
        except Exception as e:
            self.logger.error(f"解析匯率表格時發生錯誤: {str(e)}")
            return None, None
            
    def _extract_update_time(self, soup: BeautifulSoup) -> Optional[datetime]:
        """從網頁提取更新時間"""
        try:
            # 查找日期選擇器或更新時間元素
            date_element = soup.find('input', {'type': 'date'})
            if date_element and 'value' in date_element.attrs:
                date_str = date_element['value']
                return datetime.strptime(date_str, '%Y-%m-%d')
                
            # 如果找不到日期選擇器，嘗試其他可能的時間元素
            time_selectors = [
                {'class': 'update-time'},
                {'class': 'last-updated'},
                {'id': 'last-update'},
                {'class': 'date'}
            ]
            
            for selector in time_selectors:
                time_element = soup.find(['div', 'span', 'p'], selector)
                if time_element:
                    time_text = time_element.text.strip()
                    # 嘗試解析各種可能的時間格式
                    time_formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d %H:%M',
                        '%d/%m/%Y %H:%M:%S',
                        '%d/%m/%Y %H:%M'
                    ]
                    
                    for time_format in time_formats:
                        try:
                            return datetime.strptime(time_text, time_format)
                        except ValueError:
                            continue
                            
            return None
            
        except Exception as e:
            logging.error(f"提取更新時間時發生錯誤: {str(e)}")
            return None
            
    def _extract_update_time_from_text(self, time_text: str) -> Optional[datetime]:
        """從文本中提取時間"""
        try:
            # 嘗試解析日期格式
            try:
                return datetime.strptime(time_text, '%d-%m-%Y')
            except ValueError:
                return None
        except Exception as e:
            logging.error(f"從文本提取時間時發生錯誤: {str(e)}")
            return None
            
    def _try_alternative_urls(self) -> list:
        """嘗試其他可能的URL"""
        return [
            "https://www.bol.gov.la/en/ExchangRate.php",
            "http://www.bol.gov.la/en/ExchangRate.php",
            "https://bol.gov.la/en/ExchangRate.php",
            "http://bol.gov.la/en/ExchangRate.php"
        ]
        
    def set_manual_rate(self, rate: float, date: Optional[datetime] = None, currency: str = 'USD'):
        """
        手動設置匯率
        
        Args:
            rate (float): 匯率
            date (datetime, optional): 日期，預設為當前時間
            currency (str): 貨幣代碼，預設為'USD'
        """
        if date is None:
            date = datetime.now()
            
        self.manual_rates = {currency: rate}
        self.manual_date = date
        
    def _fetch_rate_from_api(self, currency):
        """從 API 獲取匯率數據"""
        try:
            headers = self._get_random_headers()
            response = self.session.get(
                self.api_url,
                headers=headers,
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and currency in data:
                        rate = float(data[currency])
                        if 10 < rate < 30:
                            self.logger.info(f"從 API 成功獲取 {currency} 匯率: {rate}")
                            return rate, datetime.now()
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"解析 API 響應時發生錯誤: {str(e)}")
                    
            return None
            
        except Exception as e:
            self.logger.warning(f"API 請求失敗: {str(e)}")
            return None
            
    def _fetch_rate_from_web(self, currency='USD'):
        """
        從網頁獲取匯率
        
        Args:
            currency (str): 貨幣代碼，預設為'USD'
            
        Returns:
            tuple: (匯率, 日期) 或 (None, None)
        """
        try:
            response = self.session.get(self.base_url, timeout=self.timeout)
            response.raise_for_status()
            
            # 直接解析匯率表格，不儲存網頁內容
            rate, date = self._parse_rate_table(response.text)
            if rate is not None and date is not None:
                self.logger.info(f"從網頁成功找到 {currency} 匯率: {rate}, 日期: {date}")
                return rate, date
                
            self.logger.warning(f"無法從網頁找到 {currency} 匯率")
            return None, None
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"網頁請求失敗: {str(e)}")
            return None, None
            
    def _make_request(self, url: Optional[str] = None, date: Optional[str] = None) -> Optional[requests.Response]:
        """發送HTTP請求獲取網頁內容
        
        Args:
            url: 目標URL，如果為None則使用默認URL
            date: 日期字串，格式為 DD-MM-YYYY
            
        Returns:
            requests.Response 或 None
        """
        try:
            target_url = url or self.base_url
            headers = self._get_random_headers()
            
            # 準備POST數據
            data = None
            if date:
                data = {'date': date}
            
            # 發送請求
            if data:
                response = requests.post(target_url, headers=headers, data=data, verify=False)
            else:
                response = requests.get(target_url, headers=headers, verify=False)
                
            response.raise_for_status()
            
            # 檢查響應內容
            if not response.text:
                self.logger.error("響應內容為空")
                return None
                
            self.logger.info(f"成功獲取網頁內容，長度: {len(response.text)}")
            return response
            
        except requests.RequestException as e:
            self.logger.error(f"請求失敗: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"發送請求時發生錯誤: {str(e)}")
            return None

    def _get_previous_business_day(self, date: datetime) -> datetime:
        """
        獲取上一個營業日
        
        Args:
            date (datetime): 當前日期
            
        Returns:
            datetime: 上一個營業日
        """
        # 週六和週日不是營業日
        while True:
            date = date - timedelta(days=1)
            if date.weekday() < 5:  # 0-4 是週一到週五
                return date
                
    def fetch_lak_rate(self, currency=None, date=None):
        """
        獲取寮國基普匯率
        
        Args:
            currency (str, optional): 貨幣代碼，如果為None則返回所有貨幣的匯率
            date (datetime, optional): 指定查詢日期
            
        Returns:
            tuple: (匯率字典或單個匯率, 日期) 或 (None, None)
        """
        try:
            # 如果指定了日期，構建日期字串
            date_str = None
            if date:
                date_str = date.strftime('%d-%m-%Y')
            
            self.logger.info(f"正在請求匯率數據，日期: {date_str or '今日'}")
            response = self._make_request(self.base_url, date=date_str)
            if not response:
                return None, None
            
            # 解析匯率表格
            rates, parsed_date = self._parse_rate_table(response.text)
            
            # 如果沒有找到數據，可能是假日，嘗試上一個營業日
            if not rates and not date:
                self.logger.info("今日可能是假日，嘗試獲取上一個營業日的匯率")
                previous_day = self._get_previous_business_day(datetime.now())
                date_str = previous_day.strftime('%d-%m-%Y')
                
                self.logger.info(f"正在請求上一個營業日的匯率數據，日期: {date_str}")
                response = self._make_request(self.base_url, date=date_str)
                if response:
                    rates, parsed_date = self._parse_rate_table(response.text)
            
            # 如果指定了特定貨幣，只返回該貨幣的匯率
            if currency and rates:
                return rates.get(currency), parsed_date
                
            return rates, parsed_date
            
        except Exception as e:
            self.logger.error(f"獲取匯率時發生錯誤: {str(e)}")
            return None, None
            
    def _extract_date(self, html_content):
        """從HTML內容中提取日期"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 嘗試從日期輸入框中獲取
            date_input = soup.find('input', {'name': 'date'})
            if date_input and 'value' in date_input.attrs:
                date_str = date_input['value']
                return datetime.strptime(date_str, '%d-%m-%Y')
                
            # 如果找不到日期輸入框，使用當前日期
            return datetime.now()
            
        except Exception as e:
            self.logger.error(f"提取日期時發生錯誤: {str(e)}")
            return datetime.now()  # 如果出錯，返回當前日期 