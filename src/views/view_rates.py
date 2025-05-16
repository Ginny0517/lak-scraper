import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db_manager import ExchangeRateDB
import argparse
from datetime import datetime
import logging
import sqlite3
from typing import Dict, List, Optional
from tabulate import tabulate

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

def view_all_rates(db_path: str = "exchange_rates.db") -> None:
    """View all exchange rate records"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all exchange rate records
        cursor.execute('''
            SELECT currency, rate, rate_type, date, bank
            FROM exchange_rates
            ORDER BY date DESC, bank, currency, rate_type
        ''')
        
        records = cursor.fetchall()
        if not records:
            print("No exchange rate records found")
            return
            
        # Organize data
        rates_by_date = {}
        for record in records:
            currency, rate, rate_type, date, bank = record
            if date not in rates_by_date:
                rates_by_date[date] = {}
            if bank not in rates_by_date[date]:
                rates_by_date[date][bank] = {}
            if currency not in rates_by_date[date][bank]:
                rates_by_date[date][bank][currency] = {}
            rates_by_date[date][bank][currency][rate_type] = rate
        
        # Display results
        for date in sorted(rates_by_date.keys(), reverse=True):
            print(f"\nDate: {date}")
            print("=" * 80)
            
            for bank in sorted(rates_by_date[date].keys()):
                print(f"\n{bank} Rates:")
                print("-" * 80)
                
                # Prepare table data
                table_data = []
                headers = ["Currency", "Buy Rate", "Sell Rate"]
                
                for currency in sorted(rates_by_date[date][bank].keys()):
                    rates = rates_by_date[date][bank][currency]
                    buy_rate = f"{rates.get('buy', 'N/A'):,.2f}" if 'buy' in rates else 'N/A'
                    sell_rate = f"{rates.get('sell', 'N/A'):,.2f}" if 'sell' in rates else 'N/A'
                    table_data.append([currency, buy_rate, sell_rate])
                
                # Display table using tabulate
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
                print()
            
    except Exception as e:
        logging.error(f"Error viewing exchange rate records: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def view_currency_history(currency: str, db_path: str = "exchange_rates.db") -> None:
    """View historical rates for a specific currency"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get historical rates for the specified currency
        cursor.execute('''
            SELECT date, bank, rate_type, rate
            FROM exchange_rates
            WHERE currency = ?
            ORDER BY date DESC, bank, rate_type
        ''', (currency,))
        
        records = cursor.fetchall()
        if not records:
            print(f"No historical rate records found for {currency}")
            return
            
        # Organize data
        history_by_date = {}
        for record in records:
            date, bank, rate_type, rate = record
            if date not in history_by_date:
                history_by_date[date] = {}
            if bank not in history_by_date[date]:
                history_by_date[date][bank] = {}
            history_by_date[date][bank][rate_type] = rate
        
        # Display results
        print(f"\n{currency} Historical Rates:")
        print("=" * 80)
        
        for date in sorted(history_by_date.keys(), reverse=True):
            print(f"\nDate: {date}")
            print("-" * 80)
            
            # Prepare table data
            table_data = []
            headers = ["Bank", "Buy Rate", "Sell Rate"]
            
            for bank in sorted(history_by_date[date].keys()):
                rates = history_by_date[date][bank]
                buy_rate = f"{rates.get('buy', 'N/A'):,.2f}" if 'buy' in rates else 'N/A'
                sell_rate = f"{rates.get('sell', 'N/A'):,.2f}" if 'sell' in rates else 'N/A'
                table_data.append([bank, buy_rate, sell_rate])
            
            # Display table using tabulate
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            print()
            
    except Exception as e:
        logging.error(f"Error viewing currency history: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def view_date_rates(date: datetime, db_path: str = "exchange_rates.db") -> None:
    """View exchange rates for a specific date"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get exchange rates for the specified date
        date_str = date.strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT currency, bank, rate_type, rate
            FROM exchange_rates
            WHERE date = ?
            ORDER BY bank, currency, rate_type
        ''', (date_str,))
        
        records = cursor.fetchall()
        if not records:
            print(f"No exchange rate records found for {date_str}")
            return
            
        # Organize data
        rates_by_bank = {}
        for record in records:
            currency, bank, rate_type, rate = record
            if bank not in rates_by_bank:
                rates_by_bank[bank] = {}
            if currency not in rates_by_bank[bank]:
                rates_by_bank[bank][currency] = {}
            rates_by_bank[bank][currency][rate_type] = rate
        
        # Display results
        print(f"\n{date_str} Exchange Rates:")
        print("=" * 80)
        
        for bank in sorted(rates_by_bank.keys()):
            print(f"\n{bank} Rates:")
            print("-" * 80)
            
            # Prepare table data
            table_data = []
            headers = ["Currency", "Buy Rate", "Sell Rate"]
            
            for currency in sorted(rates_by_bank[bank].keys()):
                rates = rates_by_bank[bank][currency]
                buy_rate = f"{rates.get('buy', 'N/A'):,.2f}" if 'buy' in rates else 'N/A'
                sell_rate = f"{rates.get('sell', 'N/A'):,.2f}" if 'sell' in rates else 'N/A'
                table_data.append([currency, buy_rate, sell_rate])
            
            # Display table using tabulate
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            print()
            
    except Exception as e:
        logging.error(f"Error viewing date rates: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

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