from db_manager import ExchangeRateDB
import logging
import os

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def clean_test_data():
    """清理測試數據"""
    db = ExchangeRateDB()
    try:
        # 刪除測試數據（2025年的數據）
        db.cursor.execute('''
            DELETE FROM exchange_rates
            WHERE date LIKE '2025%'
        ''')
        
        deleted_count = db.cursor.rowcount
        db.conn.commit()
        
        print(f"已刪除 {deleted_count} 條測試數據")
        
        # 顯示剩餘的數據
        db.cursor.execute('''
            SELECT COUNT(*) FROM exchange_rates
        ''')
        remaining_count = db.cursor.fetchone()[0]
        print(f"數據庫中還有 {remaining_count} 條有效數據")
        
    finally:
        db.close()

def rebuild_database():
    """完全重建數據庫"""
    db_path = 'exchange_rates.db'
    
    # 如果數據庫文件存在，先刪除
    if os.path.exists(db_path):
        os.remove(db_path)
        print("已刪除舊的數據庫文件")
    
    # 重新初始化數據庫
    db = ExchangeRateDB()
    try:
        print("數據庫已重建")
    finally:
        db.close()

if __name__ == '__main__':
    rebuild_database() 