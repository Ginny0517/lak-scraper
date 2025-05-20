import logging
from datetime import datetime
from src.scrapers.bol_scraper import BOLScraper

# 設置日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_bol_scraper():
    """測試 BOLScraper"""
    scraper = BOLScraper()
    
    # 測試獲取當前匯率
    print("\n測試獲取當前匯率:")
    result, date = scraper.fetch_rate()
    if result:
        print(f"日期: {result['date']}")
        print("匯率:")
        for currency, rates in result['rates'].items():
            print(f"  {currency}: 買入={rates['buy']}, 賣出={rates['sell']}")
    else:
        print("獲取當前匯率失敗")
        
    # 測試獲取指定日期的匯率
    test_date = datetime(2024, 3, 1)  # 使用一個已知的日期
    print(f"\n測試獲取 {test_date.strftime('%Y-%m-%d')} 的匯率:")
    result, date = scraper.fetch_rate(test_date)
    if result:
        print(f"日期: {result['date']}")
        print("匯率:")
        for currency, rates in result['rates'].items():
            print(f"  {currency}: 買入={rates['buy']}, 賣出={rates['sell']}")
    else:
        print(f"獲取 {test_date.strftime('%Y-%m-%d')} 的匯率失敗")
        
if __name__ == "__main__":
    test_bol_scraper() 