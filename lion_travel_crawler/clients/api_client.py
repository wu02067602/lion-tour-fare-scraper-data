import requests
import json
from config.config_manager import ConfigManager
from utils.log_manager import LogManager

class APIClient:
    """
    用於與雄獅旅遊 API 互動的客戶端。

    此類別封裝了與雄獅旅遊機票搜尋 API 的所有互動細節，
    包括請求的發送、標頭的設定以及錯誤處理。
    """
    def __init__(self, config_manager: ConfigManager, log_manager: LogManager):
        """
        初始化 APIClient。

        Args:
            config_manager (ConfigManager): 設定管理器實例，用於獲取 API 相關設定。
            log_manager (LogManager): 日誌管理器實例，用於記錄日誌。
        """
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.api_config = self.config_manager.get_api_config()
        self.base_url = self.api_config['base_url']
        self.headers = self.api_config['headers']
        self.timeout = self.api_config.get('timeout', 30)

    def fetch_flight_data(self, params: dict) -> dict:
        """
        從雄獅旅遊 API 獲取航班數據。

        此方法會根據提供的參數，向機票搜尋的端點發送一個 POST 請求。

        Args:
            params (dict): 包含在請求主體中的搜尋參數字典。

        Returns:
            dict: 從 API 返回的 JSON 響應，解析為字典。

        Raises:
            requests.exceptions.HTTPError: 如果 API 返回一個錯誤的 HTTP 狀態碼。
            requests.exceptions.RequestException: 如果發生請求相關的錯誤（例如，網絡問題）。
            json.JSONDecodeError: 如果無法解碼 API 的響應為 JSON。
        """
        url = f"{self.base_url}{self.api_config['endpoints']['search']}"
        
        self.log_manager.log_info(f"正在向 {url} 發送 API 請求，參數為: {params}")

        try:
            response = self._send_request(url=url, body=params)
            response.raise_for_status()
            self.log_manager.log_info(f"成功從 {url} 收到 API 響應")
            return response.json()

        except requests.exceptions.HTTPError as e:
            self.log_manager.log_error(f"發生 HTTP 錯誤: {e.response.status_code} - {e.response.text}", e)
            raise
        except requests.exceptions.RequestException as e:
            self.log_manager.log_error(f"呼叫雄獅旅遊 API 時發生錯誤: {e}", e)
            raise
        except json.JSONDecodeError as e:
            self.log_manager.log_error(f"解碼 JSON 響應失敗: {e.msg}", e)
            self.log_manager.log_debug(f"響應文本: {response.text}")
            raise

    def _send_request(self, url: str, body: dict) -> requests.Response:
        """
        內部方法，用於發送 HTTP POST 請求。

        Args:
            url (str): 要發送請求的目標 URL。
            body (dict): 請求的主體內容，將被轉換為 JSON 字符串。

        Returns:
            requests.Response: requests 庫返回的 Response 物件。
        """
        return requests.post(url, headers=self.headers, data=json.dumps(body), timeout=self.timeout)