import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from typing import Optional, Dict, Any, Union
import time
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import json

# 禁用 SSL 警告
urllib3.disable_warnings(InsecureRequestWarning)

class HttpClient:
    """HTTP 客戶端，處理請求重試和會話管理"""
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
        min_request_interval: float = 1.0
    ):
        """
        初始化 HTTP 客戶端
        
        Args:
            base_url: 基礎 URL
            timeout: 請求超時時間（秒）
            max_retries: 最大重試次數
            retry_backoff_factor: 重試間隔因子
            min_request_interval: 最小請求間隔（秒）
        """
        self.base_url = base_url
        self.timeout = timeout
        self.min_request_interval = min_request_interval
        self.last_request_time = 0
        self.logger = logging.getLogger(__name__)
        
        # 設置重試策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        # 創建會話
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.verify = False  # 禁用 SSL 驗證
        
    def _get_random_headers(self) -> Dict[str, str]:
        """生成隨機請求頭"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        }
        
    def _wait_for_next_request(self) -> None:
        """確保請求間隔"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        self.last_request_time = time.time()
        
    def fetch_json(
        self,
        endpoint: str,
        method: str = 'GET',
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        headers: Optional[Dict[str, str]] = None,
        force_json: bool = False
    ) -> Union[Dict[str, Any], str]:
        """
        發送 HTTP 請求並返回 JSON 響應或原始文本
        
        Args:
            endpoint: API 端點
            method: HTTP 方法
            params: URL 參數
            data: 表單數據
            json_data: JSON 數據
            auth: 認證信息
            headers: 自定義請求頭
            force_json: 是否強制要求 JSON 響應
            
        Returns:
            Union[Dict[str, Any], str]: JSON 響應數據或原始文本
            
        Raises:
            requests.RequestException: 請求失敗時拋出
            json.JSONDecodeError: 當 force_json=True 且響應不是有效的 JSON 時拋出
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        self._wait_for_next_request()
        
        # 合併請求頭
        request_headers = self._get_random_headers()
        if headers:
            request_headers.update(headers)
            
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                auth=auth,
                headers=request_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 嘗試解析 JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                if force_json:
                    raise
                self.logger.warning(f"響應不是有效的 JSON，返回原始文本: {response.text[:100]}...")
                return response.text
            
        except requests.RequestException as e:
            self.logger.error(f"請求失敗: {str(e)}")
            raise 

    def fetch(
        self,
        endpoint: str,
        method: str = 'GET',
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        auth: Optional[tuple] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """
        發送 HTTP 請求並返回原始響應文本
        
        Args:
            endpoint: API 端點
            method: HTTP 方法
            params: URL 參數
            data: 表單數據
            json_data: JSON 數據
            files: 文件數據
            auth: 認證信息
            headers: 自定義請求頭
            
        Returns:
            str: 響應文本
            
        Raises:
            requests.RequestException: 請求失敗時拋出
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        self._wait_for_next_request()
        
        # 合併請求頭
        request_headers = self._get_random_headers()
        if headers:
            request_headers.update(headers)
            
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                files=files,
                auth=auth,
                headers=request_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            self.logger.error(f"請求失敗: {str(e)}")
            raise 