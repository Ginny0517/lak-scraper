"""共用配置文件"""

# HTTP 客戶端設定
HTTP_TIMEOUT = 30  # 請求超時時間（秒）
HTTP_MAX_RETRIES = 3  # 最大重試次數
HTTP_RETRY_BACKOFF_FACTOR = 0.5  # 重試間隔因子
HTTP_MIN_REQUEST_INTERVAL = 1.0  # 最小請求間隔（秒）

# 寮國國定假日列表 (格式: MM-DD)
HOLIDAYS = [
    '01-01',  # 元旦
    '01-20',  # 寮國人民軍建軍節
    '03-08',  # 國際婦女節
    '04-14',  # 寮國新年
    '04-15',  # 寮國新年
    '04-16',  # 寮國新年
    '05-01',  # 勞動節
    '12-02',  # 國慶節
]

# 銀行 API 設定
BANK_CONFIGS = {
    'BCEL': {
        'base_url': 'https://www.bcel.com.la/bcel',
        'headers': {
            'Accept': 'application/json',
            'Referer': 'https://www.bcel.com.la/'
        }
    },
    'BOL': {
        'base_url': 'https://www.bol.gov.la/en/ExchangRate.php',
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.bol.gov.la/en/ExchangRate.php'
        }
    },
    'LDB': {
        'base_url': 'https://vegw.ldblao.la/api/v1/ldb-web/exchange',
        'headers': {
            'Accept': 'application/json',
            'Referer': 'https://www.ldblao.la/'
        },
        'auth': ('LdbWebsitePublic', 'LDBweb17012024')
    },
    'APB': {
        'base_url': 'https://excwebs.apblao.com:40756/api/v1/exchange-rates/history',
        'headers': {
            'Accept': 'application/json',
            'Referer': 'https://www.apblao.com/'
        }
    },
    'LVB': {
        'base_url': 'https://www.laovietbank.com.la/en_US/exchange/exchange-rate.html',
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.laovietbank.com.la/en_US/exchange/exchange-rate.html'
        }
    }
} 