import logging
from datetime import datetime
from src.scrapers.bcel_scraper import BCELScraper
from src.scrapers.bol_scraper import BOLScraper
from src.database.db_manager import ExchangeRateDB
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

def fetch_and_save_rates(query_date=None):
    """獲取並保存匯率"""
    try:
        # 初始化爬蟲和資料庫
        bcel_scraper = BCELScraper()
        bol_scraper = BOLScraper()
        db = ExchangeRateDB()
        
        # 使用指定日期或當前日期
        current_date = query_date if query_date else datetime.now()
        
        # 獲取BCEL匯率
        bcel_rates, bcel_date = bcel_scraper.fetch_bcel_rate(date=current_date)
        if bcel_rates and bcel_date:
            logger.info(f"成功獲取BCEL匯率: {bcel_rates}")
            
            # 保存到資料庫
            for key, rate in bcel_rates.items():
                # 解析貨幣代碼和匯率類型
                parts = key.split('_')
                if len(parts) == 2:
                    currency, rate_type = parts
                    db.save_rate(currency, rate, rate_type, bcel_date, 'BCEL')
                else:
                    # 如果沒有匯率類型，假設是買入價
                    db.save_rate(key, rate, 'buy', bcel_date, 'BCEL')
        else:
            logger.warning("無法獲取BCEL匯率")
        
        # 獲取BOL匯率
        bol_rates, bol_date = bol_scraper.fetch_bol_rate(date=current_date)
        if bol_rates and bol_date:
            logger.info(f"成功獲取BOL匯率: {bol_rates}")
            
            # 保存到資料庫
            for key, rate in bol_rates.items():
                # 解析貨幣代碼和匯率類型
                parts = key.split('_')
                if len(parts) == 2:
                    currency, rate_type = parts
                    db.save_rate(currency, rate, rate_type, bol_date, 'BOL')
                else:
                    # 如果沒有匯率類型，假設是買入價
                    db.save_rate(key, rate, 'buy', bol_date, 'BOL')
        else:
            logger.warning("無法獲取BOL匯率")
            
        return bcel_rates, bcel_date, bol_rates, bol_date
            
    except Exception as e:
        logger.error(f"獲取匯率時發生錯誤: {str(e)}")
        return None, None, None, None
    finally:
        if 'db' in locals():
            db.close()

def main():
    """主程式入口"""
    try:
        # 解析命令行參數
        parser = argparse.ArgumentParser(description='獲取並比較銀行匯率')
        parser.add_argument('--date', type=parse_date, help='指定查詢日期 (格式: YYYY-MM-DD)')
        args = parser.parse_args()
        
        # 獲取並保存匯率
        bcel_rates, bcel_date, bol_rates, bol_date = fetch_and_save_rates(args.date)
        
        # 顯示匯率比較
        if bcel_rates or bol_rates:
            print("\n匯率比較：")
            print("----------------------------------------")
            print(f"{'貨幣':<12} {'BOL匯率':<12} {'BCEL匯率':<12} {'差異':<12} {'差異%':<8}")
            print("----------------------------------------")
            
            # 獲取所有貨幣代碼
            currencies = set()
            for bank_rates in [bcel_rates, bol_rates]:
                if bank_rates:
                    for key in bank_rates.keys():
                        currency = key.split('_')[0]  # 例如 'USD_buy' -> 'USD'
                        currencies.add(currency)
            
            # 按貨幣代碼排序
            for currency in sorted(currencies):
                # 比較買入價格
                bol_buy = bol_rates.get(f"{currency}_buy") if bol_rates else None
                bcel_buy = bcel_rates.get(f"{currency}_buy") if bcel_rates else None
                
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
                    
                print(f"{currency}_buy {bol_buy_str:>12} {bcel_buy_str:>12} {diff_str:>12} {diff_percent_str:>8}")
                
                # 比較賣出價格
                bol_sell = bol_rates.get(f"{currency}_sell") if bol_rates else None
                bcel_sell = bcel_rates.get(f"{currency}_sell") if bcel_rates else None
                
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
                    
                print(f"{currency}_sell {bol_sell_str:>12} {bcel_sell_str:>12} {diff_str:>12} {diff_percent_str:>8}")
            
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
        logging.error(f"程式執行時發生錯誤: {str(e)}")
        raise

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