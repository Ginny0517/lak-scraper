from bcel_scraper import BCELScraper
from bol_scraper import BOLScraper
from db_manager import ExchangeRateDB
import logging
from datetime import datetime
import argparse

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 貨幣代碼映射
CURRENCY_MAPPING = {
    'ໂດລາ': 'USD',  # 寮文美元
    'ບາດ': 'THB',   # 寮文泰銖
}

def parse_date(date_str):
    """解析日期字串"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"無效的日期格式: {date_str}。請使用 YYYY-MM-DD 格式")

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
    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 解析命令行參數
    parser = argparse.ArgumentParser(description='獲取銀行匯率並比較')
    parser.add_argument('--date', type=str, help='指定查詢日期 (YYYY-MM-DD)')
    args = parser.parse_args()
    
    # 初始化數據庫
    db = ExchangeRateDB()
    
    try:
        # 解析日期
        query_date = None
        if args.date:
            try:
                query_date = datetime.strptime(args.date, '%Y-%m-%d')
                logging.info(f"查詢日期: {query_date.strftime('%Y-%m-%d')}")
            except ValueError:
                logging.error(f"無效的日期格式: {args.date}")
                return
        
        # 獲取BCEL匯率
        logging.info("開始獲取BCEL匯率...")
        bcel_scraper = BCELScraper()
        bcel_rates, bcel_date = bcel_scraper.fetch_bcel_rate(date=query_date)
        logging.info(f"BCEL匯率獲取結果: {bcel_rates}")
        
        # 獲取BOL匯率
        logging.info("開始獲取BOL匯率...")
        bol_scraper = BOLScraper()
        effective_bol_query_date = bcel_date if bcel_date else query_date
        bol_rates, bol_date = bol_scraper.fetch_bol_rate(date=effective_bol_query_date)
        logging.info(f"BOL匯率獲取結果: {bol_rates} for date {bol_date}")
        
        if bcel_rates:
            # 保存BCEL匯率到資料庫
            logging.info("保存BCEL匯率到資料庫...")
            for currency, rate in bcel_rates.items():
                db.save_rate(currency, rate, bcel_date, 'BCEL')
            
            # 保存BOL匯率到資料庫（如果有）
            if bol_rates:
                logging.info("保存BOL匯率到資料庫...")
                for currency, rate in bol_rates.items():
                    db.save_rate(currency, rate, bol_date, 'BOL')
            
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

            # 顯示實際數據日期
            if bcel_date:
                print(f"BCEL 數據日期: {bcel_date.strftime('%Y-%m-%d')}")
            if bol_date:
                print(f"BOL 數據日期: {bol_date.strftime('%Y-%m-%d')}")

            if query_date:
                print(f"查詢日期: {query_date.strftime('%Y-%m-%d')}")
                bcel_mismatch = bcel_date and query_date.date() != bcel_date.date()
                bol_mismatch = bol_date and query_date.date() != bol_date.date()

                if bcel_mismatch and bol_mismatch and bcel_date.date() == bol_date.date():
                    print(f"注意：BCEL 和 BOL 於 {query_date.strftime('%Y-%m-%d')} 皆無資料，均顯示最近營業日 {bcel_date.strftime('%Y-%m-%d')} 的匯率。")
                else:
                    if bcel_mismatch:
                        print(f"注意：BCEL 於 {query_date.strftime('%Y-%m-%d')} 無資料，顯示的是最近營業日 {bcel_date.strftime('%Y-%m-%d')} 的匯率。")
                    if bol_mismatch:
                        print(f"注意：BOL 於 {query_date.strftime('%Y-%m-%d')} 無資料，顯示的是最近營業日 {bol_date.strftime('%Y-%m-%d')} 的匯率。")
            elif bcel_date and bol_date and bcel_date.date() != bol_date.date():
                # 如果沒有查詢日期，但兩者日期不一致，也提示一下
                print(f"注意：BCEL 和 BOL 的數據日期不一致。")
        else:
            print("無法獲取BCEL匯率數據")
            logging.error("無法獲取BCEL匯率")
        
    except Exception as e:
        logging.error(f"發生錯誤: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    main() 