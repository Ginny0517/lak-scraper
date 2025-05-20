from db_manager import ExchangeRateDB
import logging
from datetime import datetime, timedelta

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def test_database():
    """測試數據庫功能"""
    db = ExchangeRateDB()
    
    try:
        # 測試數據保存
        logging.info("\n測試數據保存...")
        test_date = datetime.now().strftime('%Y-%m-%d')
        test_rates = {
            'USD': 20000.0,
            'CNY': 3000.0,
            'THB': 500.0
        }
        
        for currency, rate in test_rates.items():
            db.save_rate(currency, rate, test_date)
            logging.info(f"已保存 {currency} 匯率: {rate}")
            
        # 測試即時查詢
        logging.info("\n測試即時查詢...")
        for currency in test_rates.keys():
            rate = db.get_rate(currency)
            logging.info(f"查詢到 {currency} 最新匯率: {rate}")
            
        # 測試歷史數據查詢
        logging.info("\n測試歷史數據查詢...")
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        for currency in test_rates.keys():
            historical_rates = db.get_historical_rates(currency, start_date, end_date)
            logging.info(f"\n{currency} 的歷史匯率:")
            for date, rate in historical_rates:
                logging.info(f"日期: {date}, 匯率: {rate}")
                
    finally:
        db.close()
        logging.info("\n測試完成，數據庫連接已關閉")

if __name__ == '__main__':
    test_database() 