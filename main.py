import logging
from datetime import datetime
from src.scrapers.bcel_scraper import BCELScraper
from src.scrapers.bol_scraper import BOLScraper
from src.scrapers.ldb_scraper import LDBScraper
from src.database.db_manager import ExchangeRateDB
import argparse

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 貨幣列表
CURRENCY_LIST = [
    'USD', 'THB', 'EUR', 'GBP', 'AUD', 'CAD', 'JPY', 'CHF', 'CNY', 'SGD', 'KRW', 'HKD', 'MYR', 'VND'
]

# LDB 貨幣對應表
LDB_CURRENCY_MAP = {
    'USD': 'USD CASH 50-100',  # 使用 USD CASH 50-100 的數據
    'THB': 'THB CASH',         # 使用 THB CASH 的數據
    'EUR': 'EUR',
    'GBP': 'GBP',
    'AUD': 'AUD',
    'CAD': 'CAD',
    'JPY': 'JPY',
    'CHF': 'CHF',
    'CNY': 'CNY',
    'SGD': 'SGD',
    'KRW': 'KRW',
    'HKD': 'HKD',
    'MYR': 'MYR',
    'VND': 'VND',
}

def parse_date(date_str):
    """解析日期字串"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"無效的日期格式: {date_str}。請使用 YYYY-MM-DD 格式")

def fetch_and_save_rates(query_date=None):
    """獲取並保存匯率"""
    try:
        # 初始化爬蟲和資料庫
        bcel_scraper = BCELScraper()
        bol_scraper = BOLScraper()
        ldb_scraper = LDBScraper()
        db = ExchangeRateDB()
        
        # 使用指定日期或當前日期
        current_date = query_date if query_date else datetime.now()
        
        # 獲取BCEL匯率
        bcel_rates, bcel_date = bcel_scraper.fetch_bcel_rate(date=current_date)
        if bcel_rates and bcel_date:
            logger.info(f"成功獲取BCEL匯率: {bcel_rates}")
            
            # 保存到資料庫
            for currency, rates in bcel_rates['rates'].items():
                if 'buy' in rates:
                    db.save_rate(currency, rates['buy'], 'buy', bcel_date, 'BCEL')
                if 'sell' in rates:
                    db.save_rate(currency, rates['sell'], 'sell', bcel_date, 'BCEL')
        else:
            logger.warning("無法獲取BCEL匯率")
        
        # 獲取BOL匯率
        bol_rates, bol_date = bol_scraper.fetch_bol_rate(date=current_date)
        if bol_rates and bol_date:
            logger.info(f"成功獲取BOL匯率: {bol_rates}")
            
            # 保存到資料庫
            for currency, rates in bol_rates['rates'].items():
                if 'buy' in rates:
                    db.save_rate(currency, rates['buy'], 'buy', bol_date, 'BOL')
                if 'sell' in rates:
                    db.save_rate(currency, rates['sell'], 'sell', bol_date, 'BOL')
        else:
            logger.warning("無法獲取BOL匯率")
            
        # 獲取LDB匯率
        ldb_rates, ldb_date = ldb_scraper.fetch_ldb_rate(date=current_date)
        if ldb_rates and ldb_date:
            logger.info(f"成功獲取LDB匯率: {ldb_rates}")
            
            # 保存到資料庫
            for currency, rates in ldb_rates['rates'].items():
                if 'buy' in rates:
                    db.save_rate(currency, rates['buy'], 'buy', ldb_date, 'LDB')
                if 'sell' in rates:
                    db.save_rate(currency, rates['sell'], 'sell', ldb_date, 'LDB')
        else:
            logger.warning("無法獲取LDB匯率")
            
        return bcel_rates, bcel_date, bol_rates, bol_date, ldb_rates, ldb_date
            
    except Exception as e:
        logger.error(f"獲取匯率時發生錯誤: {str(e)}")
        return None, None, None, None, None, None
    finally:
        if 'db' in locals():
            db.close()

def format_rate(rate: float) -> str:
    """格式化匯率顯示"""
    if rate is None:
        return "N/A"
    return f"{rate:,.2f}"

def format_difference(diff: float) -> str:
    """格式化差異顯示"""
    if diff is None:
        return "N/A"
    return f"{diff:+,.2f}"

def format_percentage(percent: float) -> str:
    """格式化百分比顯示"""
    if percent is None:
        return "N/A"
    return f"{percent:+.2f}%"

def main():
    """主程式入口"""
    try:
        # 解析命令行參數
        parser = argparse.ArgumentParser(description='獲取並比較銀行匯率')
        parser.add_argument('--date', type=parse_date, help='指定查詢日期 (格式: YYYY-MM-DD)')
        args = parser.parse_args()
        
        # 獲取並保存匯率
        bcel_rates, bcel_date, bol_rates, bol_date, ldb_rates, ldb_date = fetch_and_save_rates(args.date)
        
        # 顯示匯率比較
        if bcel_rates or bol_rates or ldb_rates:
            print("\n匯率比較：")
            print("-" * 100)
            print(f"{'貨幣':<8} {'BOL買入':>12} {'BOL賣出':>12} {'BCEL買入':>12} {'BCEL賣出':>12} {'LDB買入':>12} {'LDB賣出':>12}")
            print("-" * 100)
            
            for currency in CURRENCY_LIST:
                # 獲取各銀行的匯率
                bol_buy = bol_rates['rates'].get(currency, {}).get('buy', 'N/A') if bol_rates else 'N/A'
                bol_sell = bol_rates['rates'].get(currency, {}).get('sell', 'N/A') if bol_rates else 'N/A'
                
                # BCEL 特殊處理：HKD 和 VND 可能只有賣價
                if currency in ['HKD', 'VND']:
                    bcel_buy = 'N/A'
                    bcel_sell = bcel_rates['rates'].get(currency, {}).get('sell', 'N/A') if bcel_rates else 'N/A'
                else:
                    bcel_buy = bcel_rates['rates'].get(currency, {}).get('buy', 'N/A') if bcel_rates else 'N/A'
                    bcel_sell = bcel_rates['rates'].get(currency, {}).get('sell', 'N/A') if bcel_rates else 'N/A'
                
                # LDB 使用對應表獲取正確的貨幣代碼
                ldb_key = LDB_CURRENCY_MAP.get(currency, currency)
                ldb_buy = ldb_rates['rates'].get(ldb_key, {}).get('buy', 'N/A') if ldb_rates else 'N/A'
                ldb_sell = ldb_rates['rates'].get(ldb_key, {}).get('sell', 'N/A') if ldb_rates else 'N/A'
                
                print(f"{currency:<8} {bol_buy:>12} {bol_sell:>12} {bcel_buy:>12} {bcel_sell:>12} {ldb_buy:>12} {ldb_sell:>12}")
            
            print("-" * 100)
            
            # 顯示日期信息
            if args.date:
                print(f"查詢日期: {args.date.strftime('%Y-%m-%d')}")
            if bcel_date:
                print(f"BCEL 數據日期: {bcel_date.strftime('%Y-%m-%d')}")
            if bol_date:
                print(f"BOL 數據日期: {bol_date.strftime('%Y-%m-%d')}")
            if ldb_date:
                print(f"LDB 數據日期: {ldb_date.strftime('%Y-%m-%d')}")
        else:
            print("無法獲取任何匯率數據")
            
    except Exception as e:
        logging.error(f"程式執行時發生錯誤: {str(e)}")
        raise

if __name__ == "__main__":
    main() 