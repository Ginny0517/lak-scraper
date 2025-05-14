from db_manager import ExchangeRateDB
import argparse
from datetime import datetime
import logging

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def format_rate(currency: str, rate: float) -> str:
    """格式化匯率顯示"""
    if currency in ['USD', 'CNY']:
        return f"{rate:,.0f}"
    else:  # THB
        return f"{rate:.2f}"

def view_all_rates():
    """查看所有匯率記錄"""
    db = ExchangeRateDB()
    try:
        # 查詢所有記錄
        db.cursor.execute('''
            SELECT currency, rate, date, created_at, bank
            FROM exchange_rates
            ORDER BY date DESC, currency ASC, bank ASC
        ''')
        
        records = db.cursor.fetchall()
        if not records:
            print("數據庫中沒有匯率記錄")
            return
            
        # 顯示記錄
        current_date = None
        current_currency = None
        
        print("\n匯率記錄：")
        print("-" * 50)
        
        for currency, rate, date, created_at, bank in records:
            # 如果是新的日期，打印分隔線
            if date != current_date:
                if current_date:
                    print("-" * 50)
                print(f"\n日期: {date}")
                current_date = date
                current_currency = None
                
            # 如果是新的貨幣，打印貨幣名稱
            if currency != current_currency:
                print(f"\n{currency}:")
                current_currency = currency
                
            # 格式化匯率顯示
            formatted_rate = format_rate(currency, rate)
            print(f"  {bank}: {formatted_rate} LAK (更新時間: {created_at})")
            
    finally:
        db.close()

def view_currency_history(currency: str):
    """查看特定貨幣的歷史記錄"""
    db = ExchangeRateDB()
    try:
        # 查詢特定貨幣的所有記錄
        db.cursor.execute('''
            SELECT rate, date, created_at, bank
            FROM exchange_rates
            WHERE currency = ?
            ORDER BY date DESC, bank ASC
        ''', (currency,))
        
        records = db.cursor.fetchall()
        if not records:
            print(f"數據庫中沒有 {currency} 的匯率記錄")
            return
            
        # 顯示記錄
        print(f"\n{currency} 匯率歷史記錄：")
        print("-" * 50)
        
        current_date = None
        for rate, date, created_at, bank in records:
            # 如果是新的日期，打印分隔線
            if date != current_date:
                if current_date:
                    print("-" * 50)
                print(f"\n日期: {date}")
                current_date = date
                
            formatted_rate = format_rate(currency, rate)
            print(f"{bank}: {formatted_rate} LAK")
            print(f"更新時間: {created_at}")
            print("-" * 50)
            
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='查看匯率數據庫記錄')
    parser.add_argument('--currency', type=str, help='指定要查看的貨幣代碼（例如：USD）')
    args = parser.parse_args()
    
    if args.currency:
        view_currency_history(args.currency.upper())
    else:
        view_all_rates()

if __name__ == '__main__':
    main() 