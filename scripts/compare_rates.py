from src.scrapers.bcel_scraper import BCELScraper
from src.scrapers.bol_scraper import BOLScraper
import logging
from datetime import datetime
import argparse

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
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
    # 解析命令行參數
    parser = argparse.ArgumentParser(description='快速比較銀行匯率')
    parser.add_argument('--date', type=parse_date, help='指定查詢日期 (格式: YYYY-MM-DD)')
    args = parser.parse_args()
    
    try:
        # 解析日期
        query_date = args.date if args.date else datetime.now()
        logging.info(f"查詢日期: {query_date.strftime('%Y-%m-%d')}")
        
        # 獲取BCEL匯率
        logging.info("開始獲取BCEL匯率...")
        bcel_scraper = BCELScraper()
        bcel_rates, bcel_date = bcel_scraper.fetch_bcel_rate(date=query_date)
        logging.info(f"BCEL匯率獲取結果: {bcel_rates}")
        
        # 獲取BOL匯率
        logging.info("開始獲取BOL匯率...")
        bol_scraper = BOLScraper()
        bol_rates, bol_date = bol_scraper.fetch_bol_rate(date=query_date)
        logging.info(f"BOL匯率獲取結果: {bol_rates}")
        
        if bcel_rates or bol_rates:
            logging.info("\n匯率比較：")
            logging.info("----------------------------------------")
            logging.info(f"{'貨幣':<6} {'BOL匯率':>12} {'BCEL匯率':>12} {'差異':>12} {'差異%':>8}")
            logging.info("----------------------------------------")
            
            # 以BCEL幣別為主組合比較表，只比對BOL買入價
            for currency, bcel_rate in bcel_rates.items():
                bol_rate = bol_rates.get(f"{currency}_buy") if bol_rates else None
                diff = bcel_rate - bol_rate if bol_rate is not None else None
                diff_percent = (diff / bol_rate * 100) if bol_rate not in (None, 0) else None
                logging.info(f"{currency:<6} "
                      f"{format_rate(bol_rate):>12} "
                      f"{format_rate(bcel_rate):>12} "
                      f"{format_difference(diff):>12} "
                      f"{format_percentage(diff_percent):>8}")
            logging.info("----------------------------------------")
            
            # 顯示日期信息
            if args.date:
                logging.info(f"查詢日期: {args.date.strftime('%Y-%m-%d')}")
            if bcel_date:
                logging.info(f"BCEL 數據日期: {bcel_date.strftime('%Y-%m-%d')}")
            if bol_date:
                logging.info(f"BOL 數據日期: {bol_date.strftime('%Y-%m-%d')}")
                
            # 檢查日期是否一致
            if bcel_date and bol_date and bcel_date.date() != bol_date.date():
                logging.warning(f"注意：BCEL 和 BOL 的數據日期不一致。")
        else:
            logging.error("無法獲取任何匯率數據")
            
    except Exception as e:
        logging.error(f"發生錯誤: {str(e)}")

if __name__ == "__main__":
    main() 