from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import logging
from .http_client import HttpClient

class BaseScraper(ABC):
    """爬蟲基類，定義基本接口和共用功能"""
    
    def __init__(self, base_url: str):
        """
        初始化爬蟲
        
        Args:
            base_url: 基礎 URL
        """
        self.base_url = base_url
        self.http_client = HttpClient(base_url)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def parse(self, raw_data: Dict) -> List[Dict]:
        """
        解析原始數據
        
        Args:
            raw_data: 原始數據
            
        Returns:
            List[Dict]: 解析後的匯率數據列表
        """
        pass
        
    @abstractmethod
    def fetch_rate(self, date: Optional[datetime] = None) -> Tuple[Optional[Dict], Optional[datetime]]:
        """
        獲取匯率數據
        
        Args:
            date: 查詢日期
            
        Returns:
            Tuple[Optional[Dict], Optional[datetime]]: (匯率數據, 日期)
        """
        pass
        
    def _is_holiday(self, date: datetime) -> bool:
        """
        判斷是否為假日
        
        Args:
            date: 要檢查的日期
            
        Returns:
            bool: 是否為假日
        """
        # 檢查是否為週末
        if date.weekday() >= 5:  # 5是週六，6是週日
            return True
            
        # 檢查是否為國定假日
        date_str = date.strftime('%m-%d')
        return date_str in self.holidays
        
    def _get_previous_business_day(self, date: datetime) -> datetime:
        """
        獲取上一個營業日
        
        Args:
            date: 當前日期
            
        Returns:
            datetime: 上一個營業日
        """
        while True:
            date = date - datetime.timedelta(days=1)
            if not self._is_holiday(date):
                return date
                
    @property
    @abstractmethod
    def holidays(self) -> List[str]:
        """
        獲取假日列表
        
        Returns:
            List[str]: 假日列表（格式：MM-DD）
        """
        pass 