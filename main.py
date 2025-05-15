import logging
from datetime import datetime
from src.scrapers.bcel_scraper import BCELScraper
from src.scrapers.bol_scraper import BOLScraper
from src.views import view_rates
import sqlite3
import argparse

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_date(date_str):
    """解析日期字串"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"無效的日期格式: {date_str}。請使用 YYYY-MM-DD 格式")

def init_database():
    """初始化資料庫"""
    conn = sqlite3.connect('exchange_rates.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS exchange_rates (
            date TEXT,
            bank TEXT,
            currency TEXT,
            rate REAL,
            PRIMARY KEY (date, bank, currency)
        )
    ''')
    conn.commit()
    conn.close()

def fetch_and_save_rates(query_date=None):
    """獲取並保存匯率"""
    try:
        # 初始化爬蟲
        bcel_scraper = BCELScraper()
        bol_scraper = BOLScraper()
        
        # 使用指定日期或當前日期
        current_date = query_date if query_date else datetime.now()
        
        # 獲取BCEL匯率
        bcel_rates, bcel_date = bcel_scraper.fetch_bcel_rate(date=current_date)
        if bcel_rates and bcel_date:
            logger.info(f"成功獲取BCEL匯率: {bcel_rates}")
            
            # 保存到資料庫
            conn = sqlite3.connect('exchange_rates.db')
            c = conn.cursor()
            for currency, rate in bcel_rates.items():
                c.execute('''
                    INSERT OR REPLACE INTO exchange_rates (date, bank, currency, rate)
                    VALUES (?, ?, ?, ?)
                ''', (bcel_date.strftime('%Y-%m-%d'), 'BCEL', currency, rate))
            conn.commit()
            conn.close()
        else:
            logger.warning("無法獲取BCEL匯率")
        
        # 獲取BOL匯率
        bol_rates, bol_date = bol_scraper.fetch_bol_rate(date=current_date)
        if bol_rates and bol_date:
            logger.info(f"成功獲取BOL匯率: {bol_rates}")
            
            # 保存到資料庫
            conn = sqlite3.connect('exchange_rates.db')
            c = conn.cursor()
            for currency, rate in bol_rates.items():
                c.execute('''
                    INSERT OR REPLACE INTO exchange_rates (date, bank, currency, rate)
                    VALUES (?, ?, ?, ?)
                ''', (bol_date.strftime('%Y-%m-%d'), 'BOL', currency, rate))
            conn.commit()
            conn.close()
        else:
            logger.warning("無法獲取BOL匯率")
            
        return bcel_rates, bcel_date, bol_rates, bol_date
            
    except Exception as e:
        logger.error(f"獲取匯率時發生錯誤: {str(e)}")
        return None, None, None, None

def main():
    """主程式入口"""
    try:
        # 解析命令行參數
        parser = argparse.ArgumentParser(description='獲取並比較銀行匯率')
        parser.add_argument('--date', type=parse_date, help='指定查詢日期 (格式: YYYY-MM-DD)')
        args = parser.parse_args()
        
        # 初始化資料庫
        init_database()
        
        # 獲取並保存匯率
        bcel_rates, bcel_date, bol_rates, bol_date = fetch_and_save_rates(args.date)
        
        # 顯示匯率比較
        if bcel_rates or bol_rates:
            print("\n匯率比較：")
            print("----------------------------------------")
            print(f"{'貨幣':<6} {'BOL匯率':>12} {'BCEL匯率':>12} {'差異':>12} {'差異%':>8}")
            print("----------------------------------------")
            
            # 以BCEL幣別為主組合比較表，只比對BOL買入價
            for currency, bcel_rate in bcel_rates.items():
                bol_rate = bol_rates.get(f"{currency}_buy") if bol_rates else None
                diff = bcel_rate - bol_rate if bol_rate is not None else None
                diff_percent = (diff / bol_rate * 100) if bol_rate not in (None, 0) else None
                print(f"{currency:<6} "
                      f"{format_rate(bol_rate):>12} "
                      f"{format_rate(bcel_rate):>12} "
                      f"{format_difference(diff):>12} "
                      f"{format_percentage(diff_percent):>8}")
            print("----------------------------------------")
            
            # 顯示日期信息
            if args.date:
                print(f"查詢日期: {args.date.strftime('%Y-%m-%d')}")
            if bcel_date:
                print(f"BCEL 數據日期: {bcel_date.strftime('%Y-%m-%d')}")
            if bol_date:
                print(f"BOL 數據日期: {bol_date.strftime('%Y-%m-%d')}")
        else:
            print("無法獲取任何匯率數據")
        
    except Exception as e:
        logger.error(f"程式執行時發生錯誤: {str(e)}")

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

if __name__ == "__main__":
    main() 