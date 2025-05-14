import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re
import time
from typing import Optional, Dict
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# 禁用SSL警告
urllib3.disable_warnings(InsecureRequestWarning)

class BCELScraper:
    def __init__(self):
        """初始化爬蟲"""
        self.base_url = "https://www.bcel.com.la/bcel/exchange-rate.html?lang=en"
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.bcel.com.la/'
        }
        
    def _wait_for_next_request(self) -> None:
        """確保請求間隔"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        self.last_request_time = time.time()
        
    def _extract_rate_from_text(self, text: str, currency_code: str = None) -> Optional[float]:
        original_text = text # 保存原始文本以便日誌記錄
        self.logger.debug(f"BCEL:原始文本 '{original_text}' (幣種: {currency_code})")

        if not isinstance(text, str):
            self.logger.warning(f"BCEL:輸入文本非字串: {original_text}")
            return None

        cleaned_text = text.strip()
        if cleaned_text == '-' or not cleaned_text:
            self.logger.warning(f"BCEL:文本為 '-' 或空: {original_text}")
            return None

        # BCEL 規則: 逗號是千分位，點是小數點
        # 1. 移除所有逗號 (千分位分隔符)
        standardized_text = cleaned_text.replace(',', '')
        
        # 2. 文本現在應該只包含數字和一個可選的點 (小數點)
        #   確保移除非數字和非小數點的字符，以防萬一
        standardized_text = re.sub(r'[^\d.]', '', standardized_text)

        if not standardized_text:
            self.logger.warning(f"BCEL:標準化後文本為空: {original_text} (處理後: {cleaned_text} -> {standardized_text})")
            return None

        try:
            rate = float(standardized_text)
        except ValueError:
            self.logger.error(f"BCEL:無法將 '{standardized_text}' (來自 '{original_text}') 轉換為 float.")
            return None

        # ---- BCEL 特定的調整邏輯 ----
        parsed_rate_before_adjustment = rate
        adjustment_applied = False

        if currency_code == 'CNY':
            # BCEL 的 CNY 匯率 (例如 "2,930" 解析為 2930) 需要乘以 1000 (假設網站單位是每百元)
            # 但從之前的日誌看， "2,930" 解析為 2.93，然後乘以1000。 
            # 如果現在 "2,930" 直接解析為 2930，這個乘以1000的邏輯可能不再適用或需要調整
            # 我們需要確認BCEL CNY的原始值和期望值。假設原始是 "2.930" 代表2.93，乘以1000得2930
            # 如果standardized_text是"2.930"，rate就是2.93。
            # 如果原始文本是 "2,930"，standardized_text是"2930"，rate是2930。
            if rate < 10 and rate > 0: # 如果rate是2.93
                rate *= 1000
                adjustment_applied = True
            # 如果BCEL的CNY原始值就是2930左右，則不需要乘法了。
            # 這裡的邏輯可能需要根據您對BCEL CNY實際顯示值的了解來確認。
            # 假設：如果解析出來是個位數，則乘以1000。

        elif currency_code == 'KRW':
            # BCEL 的 KRW 匯率 (如 14,500) 可能表示 LAK per 100 KRW.
            # 解析 "14,500" -> standardized_text "14500" -> rate 14500.0
            # 為與 BOL (LAK per 1 KRW) 統一比較，這裡將其除以 100.
            if rate > 1000: # 14500.0 > 1000
                rate /= 100 # 14500.0 / 100 = 145.0
                adjustment_applied = True
                # self.logger.info(f"BCEL KRW 調整：單位從 LAK per 100 KRW 改為 LAK per 1 KRW ( {parsed_rate_before_adjustment} / 100 = {rate} )")
        
        # 移除了之前對其他貨幣的通用調整 (rate < 100: rate *= 1000)

        if adjustment_applied:
            self.logger.info(f"BCEL 特定調整: '{original_text}' (幣種: {currency_code}) -> 初步解析: {parsed_rate_before_adjustment} -> 調整後: {rate}")
        else:
            self.logger.info(f"BCEL 解析結果: '{original_text}' (幣種: {currency_code}) -> {rate}")
            
        return rate
            
    def _parse_rate_table(self, html_content: str, query_date: datetime = None) -> tuple:
        """
        解析匯率表格，專門獲取現金買入價
        
        Args:
            html_content (str): HTML內容
            query_date (datetime, optional): 查詢的日期
            
        Returns:
            tuple: (匯率字典, 日期) 或 (None, None)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找匯率表格
            table = soup.find('table')
            if not table:
                self.logger.warning("BCEL: 無法找到匯率表格")
                return None, None
                
            # 如果沒有提供查詢日期，則從網頁獲取
            parsed_date = None
            
            # 新增：直接從網頁內容中尋找日期
            self.logger.info("開始解析網頁內容...")
            
            # 嘗試從 label 標籤中尋找日期
            labels = soup.find_all('label')
            self.logger.debug(f"BCEL: 找到 {len(labels)} 個 label 標籤")
            
            for label in labels:
                self.logger.debug(f"BCEL: 檢查 label: {label.text}")
                if label.strong and 'Date:' in label.strong.text:
                    date_str = label.strong.text.split('Date:')[1].strip()
                    self.logger.info(f"找到日期字串: {date_str}")
                    try:
                        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                        self.logger.info(f"成功解析日期: {parsed_date.strftime('%Y-%m-%d')}")
                        break
                    except Exception as e:
                        self.logger.warning(f"無法解析日期: {date_str}, 錯誤: {str(e)}")
            
            # 如果還是找不到日期，使用查詢日期
            if not parsed_date and query_date:
                parsed_date = query_date
                self.logger.info(f"BCEL: 使用提供的查詢日期: {parsed_date.strftime('%Y-%m-%d')}")
            
            if not parsed_date:
                self.logger.error("BCEL: 日期解析完全失敗，無可用日期")
                return None, None
            
            # 解析所有貨幣的匯率
            rates = {}
            rows = table.find_all('tr')
            self.logger.info(f"BCEL: 表格找到 {len(rows)} 行 (包括表頭)")
            for i, row in enumerate(rows[1:]):  # 跳過表頭
                cols = row.find_all(['td', 'th'])
                self.logger.debug(f"BCEL: 正在處理行 {i+1}/{len(rows)-1}, 列數: {len(cols)}")
                if len(cols) >= 4:  # BCEL表格至少有4列 (幣種代號在第3列, 匯率在第4列)
                    try:
                        # 貨幣代碼通常在第3列 (index 2), 匯率在第4列 (index 3)
                        currency_text = cols[2].text.strip()
                        rate_text = cols[3].text.strip()
                        
                        self.logger.info(f"BCEL: 行 {i+1} 原始提取 - 貨幣文本: '{currency_text}', 匯率文本: '{rate_text}'") # 新增日誌

                        currency_code = currency_text # 直接使用，或根據需要處理 "USD 50-100" 等格式
                        
                        if not currency_code or not rate_text or rate_text == '-':
                            self.logger.warning(f"BCEL: 行 {i+1} 跳過，無效數據 - 貨幣文本: '{currency_text}', 匯率文本: '{rate_text}'")
                            continue

                        # 處理特殊格式的貨幣代碼, 例如 "USD 1-20", "USD 50-100"
                        # 我們只關心特定的USD和所有其他基礎貨幣
                        actual_currency_to_log = currency_code # 用於日誌
                        is_target_usd_range = False

                        if ' ' in currency_code: 
                            parts = currency_code.split()
                            base_currency = parts[0]
                            amount_range = parts[1] if len(parts) > 1 else ""
                            actual_currency_to_log = f"{base_currency} ({amount_range})" # 更清晰的日誌
                            
                            if base_currency == 'USD' and amount_range == '50-100':
                                currency_code = 'USD' # 標準化為 USD
                                is_target_usd_range = True
                            elif base_currency != 'USD':
                                currency_code = base_currency # 對於其他如 "EUR (Transfer)"，取EUR
                            else: # 其他USD範圍，非目標
                                self.logger.debug(f"BCEL: 行 {i+1} 跳過非目標USD範圍: {actual_currency_to_log}")
                                continue 
                        
                        # 如果已經解析過這個基礎貨幣 (非特殊USD情況下)，則跳過 (避免重複)
                        if not is_target_usd_range and currency_code in rates and currency_code != 'USD':
                             self.logger.debug(f"BCEL: 行 {i+1} 跳過已處理貨幣 {currency_code}")
                             continue
                        if currency_code == 'USD' and not is_target_usd_range and 'USD' in rates:
                             self.logger.debug(f"BCEL: 行 {i+1} 跳過非目標USD，因已處理目標USD範圍")
                             continue

                        rate = self._extract_rate_from_text(rate_text, currency_code)
                        if rate is not None:
                            # 只有當是目標USD範圍，或者該貨幣尚未被記錄時才添加
                            if currency_code == 'USD' and is_target_usd_range:
                                rates[currency_code] = rate
                            elif currency_code != 'USD' and currency_code not in rates:
                                rates[currency_code] = rate
                            
                            # 日誌記錄移至 _extract_rate_from_text
                            # self.logger.info(f"BCEL: 成功解析 {actual_currency_to_log} 匯率: {rate} (日期: {parsed_date.strftime('%Y-%m-%d')})")
                        else:
                            self.logger.warning(f"BCEL: 行 {i+1} ({actual_currency_to_log}) 的匯率文本 '{rate_text}' 解析為 None")
                    except Exception as e:
                        self.logger.error(f"BCEL: 解析表格行 {i+1} 時發生錯誤: {str(e)}, 行內容: {row.text}")
                        continue
                else:
                    self.logger.warning(f"BCEL: 行 {i+1} 列數不足 ({len(cols)})，已跳過。內容: {row.text}")
            
            if not rates:
                self.logger.warning(f"BCEL: 未找到任何有效的匯率數據 (日期: {parsed_date.strftime('%Y-%m-%d')})")
                return None, None
                
            self.logger.info(f"BCEL: 成功解析所有匯率: {rates} (日期: {parsed_date.strftime('%Y-%m-%d')})")
            return rates, parsed_date
                
        except Exception as e:
            self.logger.error(f"BCEL: 解析匯率表格時發生嚴重錯誤: {str(e)}")
            return None, None
            
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
                
    def fetch_bcel_rate(self, currency=None, date=None):
        """
        獲取BCEL銀行匯率
        
        Args:
            currency (str, optional): 貨幣代碼，如果為None則返回所有貨幣的匯率
            date (datetime, optional): 指定查詢日期
            
        Returns:
            tuple: (匯率字典或單個匯率, 日期) 或 (None, None)
        """
        try:
            self._wait_for_next_request()
            
            # 如果指定了日期，檢查是否為營業日
            if date:
                self.logger.info(f"查詢日期: {date.strftime('%Y-%m-%d')}, 星期: {date.weekday() + 1}")
                # 如果是假日，直接獲取上一個營業日
                if self._is_holiday(date):
                    date = self._get_previous_business_day(date)
                    self.logger.info(f"查詢日期為假日，使用上一個營業日: {date.strftime('%Y-%m-%d')}")
                else:
                    self.logger.info(f"查詢日期為營業日: {date.strftime('%Y-%m-%d')}")
            
            # 構建URL參數
            params = {}
            if date:
                params['date'] = date.strftime('%Y-%m-%d')
            
            response = self.session.get(self.base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析匯率表格
            rates, parsed_date = self._parse_rate_table(response.text, date)
            
            # 如果沒有找到數據，嘗試前一天的匯率
            if not rates:
                self.logger.info(f"無法找到 {date.strftime('%Y-%m-%d')} 的匯率數據，嘗試獲取前一天的匯率")
                previous_day = date - timedelta(days=1)
                params['date'] = previous_day.strftime('%Y-%m-%d')
                
                response = self.session.get(self.base_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                rates, parsed_date = self._parse_rate_table(response.text, previous_day)
                
                # 如果前一天也沒有數據，嘗試大前天的匯率
                if not rates:
                    self.logger.info(f"無法找到 {previous_day.strftime('%Y-%m-%d')} 的匯率數據，嘗試獲取大前天的匯率")
                    two_days_ago = previous_day - timedelta(days=1)
                    params['date'] = two_days_ago.strftime('%Y-%m-%d')
                    
                    response = self.session.get(self.base_url, params=params, timeout=self.timeout)
                    response.raise_for_status()
                    
                    rates, parsed_date = self._parse_rate_table(response.text, two_days_ago)
                    if rates:
                        self.logger.info(f"成功獲取大前天 {two_days_ago.strftime('%Y-%m-%d')} 的匯率數據")
                        parsed_date = two_days_ago
                    else:
                        self.logger.warning(f"無法找到 {two_days_ago.strftime('%Y-%m-%d')} 的匯率數據，查無資料")
                        return None, None
                else:
                    self.logger.info(f"成功獲取前一天 {previous_day.strftime('%Y-%m-%d')} 的匯率數據")
                    parsed_date = previous_day
            
            # 如果指定了特定貨幣，只返回該貨幣的匯率
            if currency and rates:
                return rates.get(currency), parsed_date
                
            return rates, parsed_date
            
        except Exception as e:
            self.logger.error(f"獲取匯率時發生錯誤: {str(e)}")
            return None, None 