from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from bs4 import BeautifulSoup
import re
from ..core.base_scraper import BaseScraper
from ..core.config import HOLIDAYS, BANK_CONFIGS
import logging

class BOLScraper(BaseScraper):
    """寮國央行匯率爬蟲"""
    
    def __init__(self):
        """初始化爬蟲"""
        config = BANK_CONFIGS['BOL']
        super().__init__(config['base_url'])
        self.headers = config['headers']
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
            raw_data: 原始數據
            
        Returns:
            List[Dict]: 解析後的匯率數據列表
        """
        rates = []
        try:
            html = raw_data.get('html', '')
            self.logger.info("開始解析 HTML 響應")
            self.logger.debug(f"HTML 響應內容: {html[:1000]}...")  # 記錄前 1000 個字符
            
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table')
            
            if not table:
                self.logger.error("未找到匯率表格")
                return rates
                
            tbody = table.find('tbody')
            if not tbody:
                self.logger.error("未找到表格主體")
                return rates
                
            rows = tbody.find_all('tr')
            self.logger.info(f"<tbody> 內找到 {len(rows)} 行")
            
            for i, row in enumerate(rows):
                cols = row.find_all('td')
                self.logger.debug(f"行 {i} 欄位數: {len(cols)}")
                if len(cols) < 6:
                    self.logger.warning(f"行 {i} 欄位數不足，跳過。實際欄位數: {len(cols)}")
                    continue
                currency = cols[3].text.strip()
                buy_rate_text = cols[4].text.strip()
                sell_rate_text = cols[5].text.strip()
                # 跳過標題列或空白列
                if not currency or currency.lower() in ["currency", "currencies"]:
                    continue
                buy_rate = self._extract_rate_from_text(buy_rate_text, currency)
                sell_rate = self._extract_rate_from_text(sell_rate_text, currency)
                if buy_rate is not None or sell_rate is not None:
                    rates.append({
                        'currency': currency,
                        'buy': buy_rate,
                        'sell': sell_rate
                    })
                    self.logger.debug(f"成功解析匯率: {currency} - 買入: {buy_rate}, 賣出: {sell_rate}")
            return rates
        except Exception as e:
            self.logger.error(f"解析數據時發生錯誤: {str(e)}")
            return rates
            
    def fetch_rate(self, date: Optional[datetime] = None) -> Tuple[Optional[Dict], Optional[datetime]]:
        """
        獲取匯率數據
        
        Args:
            date: 要查詢的日期，如果為 None 則獲取當前匯率
            
        Returns:
            Tuple[Optional[Dict], Optional[datetime]]: (匯率數據, 日期) 或 (None, None)
        """
        try:
            # 檢查是否為假日
            if date and self._is_holiday(date):
                self.logger.info(f"{date.strftime('%Y-%m-%d')} 是假日，嘗試獲取上一個營業日的匯率")
                date = self._get_previous_business_day(date)
                
            # 準備請求參數
            files = {}
            if date:
                files['date'] = (None, date.strftime('%d-%m-%Y'))
                
            # 發送請求
            response = self.http_client.fetch(
                endpoint='',
                method='POST',
                files=files,
                headers=self.headers
            )
            
            if not response:
                self.logger.error("未收到有效的響應")
                return None, None
                
            # 解析匯率數據
            rates = self.parse({'html': response})
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
                
            return result, date if date else datetime.now()
            
        except Exception as e:
            self.logger.error(f"獲取匯率時發生錯誤: {str(e)}")
            return None, None
            
    def _extract_rate_from_text(self, text: str, currency_code: str = None) -> Optional[float]:
        """
        從文本中提取匯率
        
        Args:
            text: 匯率文本
            currency_code: 貨幣代碼
            
        Returns:
            Optional[float]: 解析後的匯率
        """
        original_text = text
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
        
        # 3. 確保移除非數字和非小數點的字符
        standardized_text = re.sub(r'[^\d.]', '', standardized_text)
        
        if not standardized_text:
            self.logger.warning(f"BOL: 標準化後文本為空: {original_text}")
            return None
            
        try:
            rate = float(standardized_text)
        except ValueError:
            self.logger.error(f"BOL: 無法將 '{standardized_text}' 轉換為 float")
            return None
            
        # BOL 特定的調整邏輯
        parsed_rate_before_adjustment = rate
        adjustment_applied = False
        
        if currency_code == 'CNY':
            # BOL 的 CNY 匯率 (例如 "2.965" 來自 "2.965" 或 "2.965,00")
            if 0 < rate < 10:
                rate *= 1000
                adjustment_applied = True
                
        if adjustment_applied:
            self.logger.info(f"BOL 特定調整: '{original_text}' (幣種: {currency_code}) -> 初步解析: {parsed_rate_before_adjustment} -> 調整後: {rate}")
        else:
            self.logger.info(f"BOL 解析結果: '{original_text}' (幣種: {currency_code}) -> {rate}")
            
        return rate

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
                
    def _is_holiday(self, date: datetime) -> bool:
        """
        檢查日期是否為假日
        
        Args:
            date (datetime): 要檢查的日期
            
        Returns:
            bool: 如果日期為假日則返回 True，否則返回 False
        """
        return date.strftime('%Y-%m-%d') in self.holidays
        
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