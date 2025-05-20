from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from bs4 import BeautifulSoup
import json
from ..core.base_scraper import BaseScraper
from ..core.config import HOLIDAYS, BANK_CONFIGS

class BCELScraper(BaseScraper):
    """BCEL 匯率爬蟲"""
    
    def __init__(self):
        """初始化爬蟲"""
        config = BANK_CONFIGS['BCEL']
        super().__init__(config['base_url'])
        self.headers = config['headers']
        
    @property
    def holidays(self) -> List[str]:
        """獲取假日列表"""
        return HOLIDAYS
        
    def parse(self, raw_data: Dict) -> List[Dict]:
        """
        解析原始數據 (根據實際 BCEL 匯率表格結構)
        Args:
            raw_data: 原始數據 (dict, 需含 'html' 欄)
        Returns:
            List[Dict]: 解析後的匯率數據列表
        """
        rates = []
        try:
            soup = BeautifulSoup(raw_data['html'], 'html.parser')
            table = soup.find('table', {'id': 'fxRateAll'})
            if not table:
                self.logger.error("未找到匯率表格")
                return rates
            rows = table.find_all('tr')
            for row in rows:
                # 跳過表頭
                if row.find('th'):
                    continue
                cols = row.find_all('td')
                if len(cols) < 7:
                    continue
                currency_code_text = cols[2].get_text(strip=True)
                if not currency_code_text or len(currency_code_text) < 3:
                    continue
                currency = currency_code_text[:3]
                denomination = currency_code_text[3:].strip()
                buy_str = cols[3].get_text(strip=True)
                sell_str = cols[6].get_text(strip=True)
                # 除錯日誌
                self.logger.info(f"解析行: 幣別欄='{currency_code_text}', 幣別='{currency}', 面額='{denomination}', 買入='{buy_str}', 賣出='{sell_str}'")
                if buy_str == '-' or sell_str == '-':
                    continue
                try:
                    buy = float(buy_str.replace(',', ''))
                    sell = float(sell_str.replace(',', ''))
                except Exception as e:
                    self.logger.warning(f"解析匯率失敗: {currency_code_text}, 買入: {buy_str}, 賣出: {sell_str}, 錯誤: {e}")
                    continue
                if currency in ['USD', 'EUR']:
                    if ('50-100' in denomination) or ('50-500' in denomination):
                        rates.append({'currency': currency, 'buy': buy, 'sell': sell})
                        self.logger.info(f"成功解析 {currency} {denomination} 匯率: 買入 {buy}, 賣出 {sell}")
                else:
                    rates.append({'currency': currency, 'buy': buy, 'sell': sell})
                    self.logger.info(f"成功解析 {currency} 匯率: 買入 {buy}, 賣出 {sell}")
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
            # 如果提供了日期，檢查是否為假日
            if date:
                if self._is_holiday(date):
                    self.logger.info(f"BCEL: {date.strftime('%Y-%m-%d')} 是假日，嘗試獲取前一個工作日的匯率")
                    date = self._get_previous_business_day(date)
                    self.logger.info(f"BCEL: 使用前一個工作日 {date.strftime('%Y-%m-%d')}")
            else:
                date = datetime.now()
                if self._is_holiday(date):
                    date = self._get_previous_business_day(date)
                    self.logger.info(f"BCEL: 使用前一個工作日 {date.strftime('%Y-%m-%d')}")
                    
            # 發送請求
            params = {
                'exDate': date.strftime('%Y-%m-%d'),
                'round': '1',
                'lang': 'en'
            }
            
            response = self.http_client.fetch(
                endpoint='detail-exchange-rate',
                method='POST',
                data=params,
                headers=self.headers
            )
            
            if not response:
                self.logger.error("未收到有效的響應")
                return None, None
                
            # 解析 HTML 響應
            rates = self.parse({'html': response})
            
            if not rates:
                self.logger.warning(f"未找到 {date.strftime('%Y-%m-%d')} 的匯率資料")
                return None, None
                
            # 整理數據格式
            result = {
                'date': date.strftime('%Y-%m-%d'),
                'rates': {}
            }
            
            for rate in rates:
                currency = rate['currency']
                result['rates'][currency] = {
                    'buy': rate['buy'],
                    'sell': rate['sell']
                }
                
            self.logger.info(f"成功獲取 BCEL {date.strftime('%Y-%m-%d')} 的匯率")
            return result, date
            
        except Exception as e:
            self.logger.error(f"獲取 BCEL 匯率時發生錯誤: {str(e)}")
            return None, None
            
    def _parse_rate(self, rate_str: str) -> float:
        """
        解析匯率字串為浮點數
        
        Args:
            rate_str: 匯率字串
            
        Returns:
            float: 解析後的匯率
        """
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
            
    def _parse_rate_table(self, soup: BeautifulSoup, date: datetime) -> Dict[str, float]:
        """解析匯率表格，獲取買入和賣出價格
        
        Args:
            soup: BeautifulSoup 物件
            date: 查詢日期
            
        Returns:
            Dict[str, float]: 包含匯率數據的字典
        """
        rates = {}
        table = soup.find('table', class_='table')
        if not table:
            self.logger.warning(f"未找到匯率表格 (日期: {date.strftime('%Y-%m-%d')})")
            return rates
            
        rows = table.find_all('tr')
        self.logger.info(f"表格找到 {len(rows)} 行 (包括表頭)")
        
        # 跳過表頭行
        for row in rows[2:]:  # 跳過前兩行（標題和列名）
            # 使用 data-title 屬性來獲取正確的欄位
            currency_td = row.find('td', attrs={'data-title': 'Currency Code'})
            note_td = row.find('td', attrs={'data-title': 'NOTE'})
            sell_td = row.find('td', attrs={'data-title': 'Sell Rates'})
            
            if not currency_td:
                continue
                
            # 提取貨幣信息
            currency_text = currency_td.text.strip()
            if not currency_text or currency_text == 'NOTE':
                continue
                
            # 提取幣種代碼
            currency_match = re.search(r'([A-Z]{3})', currency_text)
            if not currency_match:
                continue
                
            currency = currency_match.group(1)
            
            # 檢查是否為 USD 50-100 或 EUR 50-500
            if currency == 'USD' and '50-100' not in currency_text:
                continue
            if currency == 'EUR' and '50-500' not in currency_text:
                continue
                
            # 提取買入和賣出價格
            try:
                # 使用現鈔買入價（NOTE）作為買入價
                buy_rate = self._extract_rate_from_text(note_td.text.strip(), currency) if note_td else None
                # 使用賣出價（Sell Rates）
                sell_rate = self._extract_rate_from_text(sell_td.text.strip(), currency) if sell_td else None
                
                # 特殊處理 HKD 和 VND
                if currency in ['HKD', 'VND']:
                    if sell_rate is not None:
                        rates[f"{currency}_sell"] = sell_rate
                else:
                    if buy_rate is not None:
                        rates[f"{currency}_buy"] = buy_rate
                        rates[f"{currency}_sell"] = sell_rate if sell_rate is not None else buy_rate
                    
                if buy_rate is not None or sell_rate is not None:
                    self.logger.info(f"成功解析 {currency} 匯率 - 買入(現鈔): {buy_rate}, 賣出: {sell_rate}")
            except (ValueError, IndexError) as e:
                self.logger.warning(f"解析 {currency} 匯率時發生錯誤: {str(e)}")
                continue
        
        if not rates:
            self.logger.warning(f"未找到任何有效的匯率數據 (日期: {date.strftime('%Y-%m-%d')})")
        else:
            self.logger.info(f"成功解析所有匯率: {rates} (日期: {date.strftime('%Y-%m-%d')})")
            
        return rates 