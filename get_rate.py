from lak_scraper import LAKScraper
import logging
from datetime import datetime
import argparse

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_date(date_str):
    """解析日期字串"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"無效的日期格式: {date_str}。請使用 YYYY-MM-DD 格式")

def main():
    # 設置命令行參數
    parser = argparse.ArgumentParser(description='查詢寮國央行匯率')
    parser.add_argument('--date', type=parse_date, help='指定查詢日期 (格式: YYYY-MM-DD)')
    args = parser.parse_args()

    scraper = LAKScraper()
    currencies = ['USD', 'CNY', 'THB']
    
    print('寮國央行匯率：')
    print('-' * 40)
    
    # 一次獲取所有貨幣的匯率
    rates, date = scraper.fetch_lak_rate(date=args.date)
    
    if rates:
        for currency in currencies:
            if currency in rates:
                rate = rates[currency]
                # 根據貨幣類型格式化匯率
                if currency in ['USD', 'CNY']:
                    # 對於 USD 和 CNY，使用逗號作為千分位分隔符
                    formatted_rate = f"{rate:,.0f}"
                else:  # THB
                    # 對於 THB，使用點作為小數點
                    formatted_rate = f"{rate:.2f}"
                print(f'1 {currency} = {formatted_rate} LAK')
            else:
                print(f'無法獲取 {currency} 匯率')
    else:
        print('無法獲取匯率數據')
    
    print('-' * 40)
    if args.date:
        print(f'查詢日期: {args.date.strftime("%Y-%m-%d")}')
    else:
        print(f'更新時間: {datetime.now().strftime("%Y-%m-%d")}')

if __name__ == '__main__':
    main() 