from typing import Dict
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class RateComparator:
    def display_comparison(self, rates: Dict[str, Dict[str, float]], date: datetime = None) -> None:
        """
        顯示匯率比較結果
        
        Args:
            rates (Dict[str, Dict[str, float]]): 匯率字典
            date (datetime, optional): 查詢日期
        """
        if not rates:
            self.logger.warning("沒有匯率數據可供比較")
            return
            
        logging.info("\n匯率比較：")
        logging.info("-" * 40)
        logging.info(f"{'貨幣':<12} {'BOL匯率':<12} {'BCEL匯率':<12} {'差異':<12} {'差異%':<8}")
        logging.info("-" * 40)
        
        # 獲取所有貨幣代碼
        currencies = set()
        for bank_rates in rates.values():
            for key in bank_rates.keys():
                if key != 'date':  # 排除日期字段
                    # 從 key 中提取貨幣代碼（例如 'USD_buy' -> 'USD'）
                    currency = key.split('_')[0]
                    currencies.add(currency)
        
        # 按貨幣代碼排序
        for currency in sorted(currencies):
            # 比較買入價格
            bol_buy = rates.get('BOL', {}).get(f"{currency}_buy")
            bcel_buy = rates.get('BCEL', {}).get(f"{currency}_buy")
            
            # 顯示買入價格比較
            bol_buy_str = f"{bol_buy:,.2f}" if bol_buy is not None else "N/A"
            bcel_buy_str = f"{bcel_buy:,.2f}" if bcel_buy is not None else "N/A"
            
            if bol_buy is not None and bcel_buy is not None:
                diff = bcel_buy - bol_buy
                diff_percent = (diff / bol_buy) * 100 if bol_buy != 0 else 0
                diff_str = f"{diff:,.2f}"
                diff_percent_str = f"{diff_percent:.2f}%"
            else:
                diff_str = "N/A"
                diff_percent_str = "N/A"
                
            logging.info(f"{currency}_buy {bol_buy_str:>12} {bcel_buy_str:>12} {diff_str:>12} {diff_percent_str:>8}")
            
            # 比較賣出價格
            bol_sell = rates.get('BOL', {}).get(f"{currency}_sell")
            bcel_sell = rates.get('BCEL', {}).get(f"{currency}_sell")
            
            # 顯示賣出價格比較
            bol_sell_str = f"{bol_sell:,.2f}" if bol_sell is not None else "N/A"
            bcel_sell_str = f"{bcel_sell:,.2f}" if bcel_sell is not None else "N/A"
            
            if bol_sell is not None and bcel_sell is not None:
                diff = bcel_sell - bol_sell
                diff_percent = (diff / bol_sell) * 100 if bol_sell != 0 else 0
                diff_str = f"{diff:,.2f}"
                diff_percent_str = f"{diff_percent:.2f}%"
            else:
                diff_str = "N/A"
                diff_percent_str = "N/A"
                
            logging.info(f"{currency}_sell {bol_sell_str:>12} {bcel_sell_str:>12} {diff_str:>12} {diff_percent_str:>8}")
        
        logging.info("-" * 40)
        if date:
            logging.info(f"查詢日期: {date.strftime('%Y-%m-%d')}")
            
        # 顯示各銀行的數據日期
        for bank, bank_rates in rates.items():
            if bank_rates and 'date' in bank_rates:
                logging.info(f"{bank} 數據日期: {bank_rates['date'].strftime('%Y-%m-%d')}")

    def _get_rates_from_scrapers(self, date: datetime = None) -> Dict[str, Dict[str, float]]:
        """
        從爬蟲獲取匯率數據
        
        Args:
            date (datetime, optional): 查詢日期
            
        Returns:
            Dict[str, Dict[str, float]]: 匯率字典
        """
        rates = {}
        
        # 獲取 BCEL 匯率
        try:
            bcel_rates, bcel_date = self.bcel_scraper.fetch_bcel_rate(date=date)
            if bcel_rates:
                rates['BCEL'] = bcel_rates
                rates['BCEL']['date'] = bcel_date
                self.logger.info(f"成功獲取BCEL匯率: {bcel_rates}")
            else:
                self.logger.warning("無法獲取BCEL匯率")
        except Exception as e:
            self.logger.error(f"獲取BCEL匯率時發生錯誤: {str(e)}")
            
        # 獲取 BOL 匯率
        try:
            bol_rates, bol_date = self.bol_scraper.fetch_bol_rate(date=date)
            if bol_rates:
                rates['BOL'] = bol_rates
                rates['BOL']['date'] = bol_date
                self.logger.info(f"成功獲取BOL匯率: {bol_rates}")
            else:
                self.logger.warning("無法獲取BOL匯率")
        except Exception as e:
            self.logger.error(f"獲取BOL匯率時發生錯誤: {str(e)}")
            
        return rates 