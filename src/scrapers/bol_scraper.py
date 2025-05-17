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

class BOLScraper:
    def __init__(self):
        """初始化爬蟲"""
        self.base_url = "https://www.bol.gov.la/en/ExchangRate.php"
        self.min_request_interval = 5  # 最小請求間隔（秒）
        self.last_request_time = 0
        self.timeout = 30  # 請求超時時間（秒）
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.verify = False  # 禁用SSL驗證
        self.session.headers.update(self._get_random_headers())
        
    def _get_random_headers(self) -> Dict[str, str]:
        """生成隨機請求頭"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.bol.gov.la/'
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
        self.logger.debug(f"BOL: 原始文本 '{original_text}' (幣種: {currency_code})")

        if not isinstance(text, str):
            self.logger.warning(f"BOL: 輸入文本非字串: {original_text}")
            return None

        cleaned_text = text.strip()
        if cleaned_text == '-' or not cleaned_text:
            self.logger.warning(f"BOL: 文本為 '-' 或空: {original_text}")
            return None

        # BOL 規則: 點是千分位，逗號是小數點
        # 1. 移除所有點 (千分位分隔符)
        text_no_dots = cleaned_text.replace('.', '')
        
        # 2. 將所有逗號替換為點 (小數點)
        standardized_text = text_no_dots.replace(',', '.')

        # 3. 確保移除非數字和非小數點的字符，以防萬一
        standardized_text = re.sub(r'[^\d.]', '', standardized_text)

        if not standardized_text:
            self.logger.warning(f"BOL: 標準化後文本為空: {original_text} (處理後: {cleaned_text} -> {text_no_dots} -> {standardized_text})")
            return None

        try:
            rate = float(standardized_text)
        except ValueError:
            self.logger.error(f"BOL: 無法將 '{standardized_text}' (來自 '{original_text}') 轉換為 float.")
            return None

        # ---- BOL 特定的調整邏輯 ----
        parsed_rate_before_adjustment = rate
        adjustment_applied = False

        # 對於BOL，上述轉換應該能直接得到正確的數值，例如：
        # "21.510" (USD原始) -> no_dots "21510" -> standardized "21510" -> rate 21510.0
        # "642,68" (THB原始) -> no_dots "642,68" -> standardized "642.68" -> rate 642.68
        # "23.456,78" (EUR原始) -> no_dots "23456,78" -> standardized "23456.78" -> rate 23456.78
        
        # 因此，之前針對USD乘以1000的調整可能不再需要。
        if currency_code == 'USD':
            # 檢查一下，如果解析出來的USD仍然異常小，比如小於1000但大於0 (可能是某種未預料的格式)
            # 這種情況下，我們可能需要更詳細的日誌或特定處理，但暫時不自動調整。
            if 0 < rate < 1000:
                self.logger.warning(f"BOL USD: 解析值異常小 '{rate}' (來自 '{original_text}'). 可能需要檢查BOL的USD格式.")
                # No automatic adjustment for now, to avoid incorrect scaling.
                pass

        elif currency_code == 'CNY':
            # BOL的CNY (例如 "2.965" 來自 "2.965" 或 "2.965,00")
            # 上述解析應該能得到正確的小數 2.965 或 2965.0 (如果原始是 "2.965,00")
            # 如果解析結果為 2.9xx，則乘以 1000
            if 0 < rate < 10: 
                rate *= 1000
                adjustment_applied = True
        
        # KRW 在 BOL 這邊不需要特殊調整單位，假設其直接是 LAK per 1 KRW

        if adjustment_applied:
            self.logger.info(f"BOL 特定調整: '{original_text}' (幣種: {currency_code}) -> 初步解析: {parsed_rate_before_adjustment} -> 調整後: {rate}")
        else:
            self.logger.info(f"BOL 解析結果: '{original_text}' (幣種: {currency_code}) -> {rate}")
            
        return rate
            
    def _parse_rate_table(self, html_content: str, query_date: datetime = None) -> tuple:
        """
        解析匯率表格
        
        Args:
            html_content (str): HTML內容
            query_date (datetime, optional): 查詢的日期
            
        Returns:
            tuple: (匯率字典, 日期) 或 (None, None)
        """
        try:
            # with open('bol_raw.html', 'w', encoding='utf-8') as f:
            #     f.write(html_content)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')
            if not table:
                self.logger.warning("BOL: 無法找到匯率表格")
                return None, None
            
            if query_date:
                parsed_date = query_date
                self.logger.info(f"BOL: 使用查詢日期: {parsed_date.strftime('%Y-%m-%d')}")
            else:
                date_text_element = soup.find('div', string=re.compile(r'Date:')) # 更明確的變數名
                if date_text_element:
                    self.logger.info(f"BOL: 找到日期文本元素: {date_text_element.text}")
                    date_str_match = re.search(r'Date:\s*(\d{4}-\d{2}-\d{2})', date_text_element.text)
                    if date_str_match:
                        date_str = date_str_match.group(1)
                        try:
                            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                            self.logger.info(f"BOL: 網頁顯示的日期: {parsed_date.strftime('%Y-%m-%d')}")
                        except ValueError:
                            self.logger.warning(f"BOL: 無法解析日期字串: {date_str}")
                            # 如果無法解析網頁日期，但提供了 query_date，是否應該用 query_date？
                            # 目前策略是如果無法解析網頁日期則返回 None，這可能導致無數據。
                            # 或者，如果 query_date 存在，即使網頁日期解析失敗也使用 query_date。
                            # 但如果 query_date 為 None 且網頁日期解析失敗，則確實應該返回 None。
                            if not query_date: # 只有在 query_date 也為 None 時才返回失敗
                                 return None, None
                            # parsed_date = query_date # Fallback if needed, but risky if date mismatch
                    else:
                        self.logger.warning(f"BOL: 未能在文本中找到日期格式: {date_text_element.text}")
                        if not query_date: return None, None 
                        # parsed_date = query_date # Fallback
                else:
                    self.logger.warning("BOL: 無法在網頁中找到日期信息元素")
                    if not query_date: return None, None
                    # parsed_date = query_date # Fallback
            
            if parsed_date is None and query_date: # 確保如果前面邏輯出錯但有query_date，則使用它
                parsed_date = query_date
                self.logger.info(f"BOL: 回退使用提供的查詢日期: {parsed_date.strftime('%Y-%m-%d')}")
            elif parsed_date is None and not query_date:
                 self.logger.error("BOL: 日期解析完全失敗，無可用日期。")
                 return None, None

            rates = {}
            rows = table.find_all('tr')
            self.logger.info(f"BOL: 表格找到 {len(rows)} 行")
            for i, row in enumerate(rows[1:]):  # 跳過表頭
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 6:
                    currency_code = cols[3].text.strip()
                    buy_rate_text = cols[4].text.strip()
                    sell_rate_text = cols[5].text.strip()
                    self.logger.info(f"BOL: 行 {i+1} - 幣別: {currency_code}, 買入: {buy_rate_text}, 賣出: {sell_rate_text}")
                    buy_rate = self._extract_rate_from_text(buy_rate_text, currency_code)
                    sell_rate = self._extract_rate_from_text(sell_rate_text, currency_code)
                    if buy_rate is not None:
                        rates[f"{currency_code}_buy"] = buy_rate
                    if sell_rate is not None:
                        rates[f"{currency_code}_sell"] = sell_rate
                else:
                    self.logger.warning(f"BOL: 行 {i+1} 欄位數不足，跳過。實際欄位數: {len(cols)}")
            
            if not rates:
                self.logger.warning(f"BOL: 未找到任何有效的匯率數據 (日期: {parsed_date.strftime('%Y-%m-%d')})")
                return None, None # 保持返回 None, None 以觸發後續的上一個營業日邏輯
                
            self.logger.info(f"BOL: 成功解析所有匯率: {rates} (日期: {parsed_date.strftime('%Y-%m-%d')})")
            return rates, parsed_date
                
        except Exception as e:
            self.logger.error(f"BOL: 解析匯率表格時發生嚴重錯誤: {str(e)}")
            return None, None
            
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
                
    def fetch_bol_rate(self, currency=None, date=None):
        """
        獲取寮國央行匯率
        
        Args:
            currency (str, optional): 貨幣代碼，如果為None則返回所有貨幣的匯率
            date (datetime, optional): 指定查詢日期
        Returns:
            tuple: (匯率字典, 日期) 或 (None, None)
        """
        try:
            self._wait_for_next_request()
            if date:
                if date.weekday() >= 5:
                    date = self._get_previous_business_day(date)
                    self.logger.info(f"查詢日期為非營業日，使用上一個營業日: {date.strftime('%Y-%m-%d')}")
            params = {}
            if date:
                params['date'] = date.strftime('%d-%m-%Y')
            response = self.session.post(self.base_url, data=params, timeout=self.timeout)
            response.raise_for_status()
            flat_rates, parsed_date = self._parse_rate_table(response.text, date)
            if not flat_rates:
                self.logger.error("BOL: 沒有解析到任何匯率數據")
                return None, None
            rates = {'date': parsed_date.strftime('%Y-%m-%d'), 'rates': {}}
            for k, v in flat_rates.items():
                if k.endswith('_buy'):
                    code = k[:-4]
                    if code not in rates['rates']:
                        rates['rates'][code] = {}
                    rates['rates'][code]['buy'] = v
                elif k.endswith('_sell'):
                    code = k[:-5]
                    if code not in rates['rates']:
                        rates['rates'][code] = {}
                    rates['rates'][code]['sell'] = v
            self.logger.info(f"BOL: 統一格式匯率: {rates}")
            return rates, parsed_date
        except requests.exceptions.RequestException as e:
            self.logger.error(f"BOL: 請求失敗: {str(e)}")
            return None, None
        except Exception as e:
            self.logger.error(f"BOL: 發生未預期的錯誤: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None, None 