import logging
from datetime import datetime
from src.scrapers.bcel_scraper import BCELScraper
from src.scrapers.bol_scraper import BOLScraper
from src.scrapers.ldb_scraper import LDBScraper
from src.scrapers.apb_scraper import APBScraper
from src.scrapers.lvb_scraper import LVBScraper
from src.database.db_manager import ExchangeRateDB
import argparse

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
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
        apb_scraper = APBScraper()
        lvb_scraper = LVBScraper()
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
        
        # 獲取APB匯率
        apb_rates, apb_date = apb_scraper.fetch_apb_rate(date=current_date)
        if apb_rates and apb_date:
            logger.info(f"成功獲取APB匯率: {apb_rates}")
            
            # 保存到資料庫
            for currency, rates in apb_rates['rates'].items():
                if 'buy' in rates:
                    db.save_rate(currency, rates['buy'], 'buy', apb_date, 'APB')
                if 'sell' in rates:
                    db.save_rate(currency, rates['sell'], 'sell', apb_date, 'APB')
        else:
            logger.warning("無法獲取APB匯率")
        
        # 獲取LVB匯率
        lvb_rates, lvb_date = lvb_scraper.fetch_lvb_rate(date=current_date)
        if lvb_rates and lvb_date:
            logger.info(f"成功獲取LVB匯率: {lvb_rates}")
            for currency, rates in lvb_rates['rates'].items():
                if 'buy' in rates:
                    db.save_rate(currency, rates['buy'], 'buy', lvb_date, 'LVB')
                if 'sell' in rates:
                    db.save_rate(currency, rates['sell'], 'sell', lvb_date, 'LVB')
        else:
            logger.warning("無法獲取LVB匯率")
        
        return bcel_rates, bcel_date, bol_rates, bol_date, ldb_rates, ldb_date, apb_rates, apb_date, lvb_rates, lvb_date
            
    except Exception as e:
        logger.error(f"獲取匯率時發生錯誤: {str(e)}")
        return None, None, None, None, None, None, None, None, None, None
    finally:
        if 'db' in locals():
            db.close()

def format_rate(rate: float, currency: str = None) -> str:
    """格式化匯率顯示"""
    if rate is None:
        return "N/A"
    if currency == 'VND':
        return f"{rate:,.4f}"  # VND 保留 4 位小數
    return f"{rate:,.2f}"  # 其他幣種保留 2 位小數

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
        bcel_rates, bcel_date, bol_rates, bol_date, ldb_rates, ldb_date, apb_rates, apb_date, lvb_rates, lvb_date = fetch_and_save_rates(args.date)
        
        # 顯示匯率比較
        if bcel_rates or bol_rates or ldb_rates or apb_rates or lvb_rates:
            logging.info("\n匯率比較：")
            banks = [
                ('BOL', bol_rates),
                ('BCEL', bcel_rates),
                ('LDB', ldb_rates),
                ('APB', apb_rates),
                ('LVB', lvb_rates)
            ]
            col_width = 13
            # 第一行：銀行名稱
            header = f"{'貨幣':<6}" + ''.join(f"{bank:<{col_width*2}}" for bank, _ in banks)
            logging.info(header)
            # 第二行：買入/賣出
            sub_header = f"{'':<6}" + ''.join(f"{'Buy':>{col_width}}{'Sell':>{col_width}}" for _ in banks)
            logging.info(sub_header)
            logging.info("-" * (6 + col_width * 2 * len(banks)))
            for currency in CURRENCY_LIST:
                row = f"{currency:<6}"
                for bank, rates in banks:
                    if bank == 'LDB':
                        if currency == 'USD':
                            buy = format_rate(rates['rates'].get('USD CASH 50-100', {}).get('buy'), currency) if rates else 'N/A'
                            sell = format_rate(rates['rates'].get('USD CASH 50-100', {}).get('sell'), currency) if rates else 'N/A'
                        elif currency == 'THB':
                            buy = format_rate(rates['rates'].get('THB CASH', {}).get('buy'), currency) if rates else 'N/A'
                            sell = format_rate(rates['rates'].get('THB CASH', {}).get('sell'), currency) if rates else 'N/A'
                        else:
                            buy = format_rate(rates['rates'].get(currency, {}).get('buy'), currency) if rates else 'N/A'
                            sell = format_rate(rates['rates'].get(currency, {}).get('sell'), currency) if rates else 'N/A'
                    else:
                        buy = format_rate(rates['rates'].get(currency, {}).get('buy'), currency) if rates else 'N/A'
                        sell = format_rate(rates['rates'].get(currency, {}).get('sell'), currency) if rates else 'N/A'
                    row += f"{buy:>{col_width}}{sell:>{col_width}}"
                logging.info(row)
            logging.info("-" * (6 + col_width * 2 * len(banks)))
            # 日期資訊
            if args.date:
                logging.info(f"查詢日期: {args.date.strftime('%Y-%m-%d')}")
            if bcel_date:
                logging.info(f"BCEL 數據日期: {bcel_date.strftime('%Y-%m-%d')}")
            if bol_date:
                logging.info(f"BOL 數據日期: {bol_date.strftime('%Y-%m-%d')}")
            if ldb_date:
                logging.info(f"LDB 數據日期: {ldb_date.strftime('%Y-%m-%d')}")
            if apb_date:
                logging.info(f"APB 數據日期: {apb_date.strftime('%Y-%m-%d')}")
            if lvb_date:
                logging.info(f"LVB 數據日期: {lvb_date.strftime('%Y-%m-%d')}")
        else:
            logging.error("無法獲取任何匯率數據")
            
    except Exception as e:
        logging.error(f"程式執行時發生錯誤: {str(e)}")
        raise

if __name__ == "__main__":
    main() 