#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日期計算服務模組

此模組提供日期計算服務，透過呼叫日期計算 API 來獲取航班日期。
"""

import requests
import json
from typing import Dict, Optional
from config.config_manager import ConfigManager
from utils.log_manager import LogManager


class DateCalculationService:
    """
    日期計算服務類別
    
    負責與日期計算 API 互動，獲取計算後的航班日期資訊。
    
    屬性:
        config_manager (ConfigManager): 配置管理器實例
        log_manager (LogManager): 日誌管理器實例
        base_url (str): API 基礎 URL
        timeout (int): 請求超時時間（秒）
        calculate_dates_endpoint (str): 計算日期的端點路徑
    """

    def __init__(self, config_manager: ConfigManager, log_manager: LogManager):
        """
        初始化日期計算服務
        
        參數:
            config_manager (ConfigManager): 配置管理器實例
            log_manager (LogManager): 日誌管理器實例
        """
        self.config_manager = config_manager
        self.log_manager = log_manager
        self._load_config()

    def _load_config(self) -> None:
        """
        載入日期計算 API 配置
        
        從配置管理器中獲取日期計算 API 的相關配置。
        """
        api_config = self.config_manager.get_date_calculation_api_config()
        self.base_url = api_config.get('base_url', 'http://localhost:8000')
        self.timeout = api_config.get('timeout', 10)
        endpoints = api_config.get('endpoints', {})
        self.calculate_dates_endpoint = endpoints.get('calculate_dates', '/calculate_dates')
        self.calculate_holiday_dates_endpoint = endpoints.get('calculate_holiday_dates', '/calculate_holiday_dates')

    def calculate_dates(self, month_offset: int, dep_day: int, return_day: int) -> Optional[Dict]:
        """
        計算航班日期
        
        透過呼叫日期計算 API 來計算出發和回程日期。
        
        參數:
            month_offset (int): 月份偏移量（從當前月份開始計算幾個月後）
            dep_day (int): 出發日期（該月的第幾天）
            return_day (int): 回程日期（該月的第幾天）
            
        返回:
            Optional[Dict]: 包含計算結果的字典，格式如下：
                {
                    "departure_date": "2025-12-05",
                    "return_date": "2025-12-10",
                    "target_year": 2025,
                    "target_month": 12
                }
                如果 API 呼叫失敗則返回 None
                
        異常:
            requests.exceptions.RequestException: 當 API 請求失敗時
        """
        url = f"{self.base_url}{self.calculate_dates_endpoint}"
        payload = {
            "month_offset": month_offset,
            "dep_day": dep_day,
            "return_day": return_day
        }
        
        self.log_manager.log_info(
            f"正在呼叫日期計算 API: {url}，參數: month_offset={month_offset}, "
            f"dep_day={dep_day}, return_day={return_day}"
        )
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            # 檢查 HTTP 狀態碼
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    data = result.get('data', {})
                    self.log_manager.log_info(
                        f"成功獲取日期計算結果: 出發日期={data.get('departure_date')}, "
                        f"回程日期={data.get('return_date')}"
                    )
                    return data
                else:
                    error_msg = result.get('error', '未知錯誤')
                    self.log_manager.log_error(f"日期計算 API 返回錯誤: {error_msg}")
                    return None
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get('error', '請求參數錯誤')
                self.log_manager.log_error(f"日期計算 API 請求參數錯誤: {error_msg}")
                return None
            else:
                self.log_manager.log_error(
                    f"日期計算 API 返回異常狀態碼: {response.status_code}, "
                    f"響應內容: {response.text}"
                )
                return None
                
        except requests.exceptions.Timeout as e:
            self.log_manager.log_error(f"日期計算 API 請求超時: {e}", e)
            return None
        except requests.exceptions.ConnectionError as e:
            self.log_manager.log_error(f"無法連接到日期計算 API: {e}", e)
            return None
        except requests.exceptions.RequestException as e:
            self.log_manager.log_error(f"呼叫日期計算 API 時發生錯誤: {e}", e)
            return None
        except json.JSONDecodeError as e:
            self.log_manager.log_error(f"解碼日期計算 API 響應失敗: {e.msg}", e)
            return None
        except Exception as e:
            self.log_manager.log_error(f"日期計算服務發生未預期的錯誤: {e}", e)
            return None

    def calculate_holiday_dates(self, month_offset: int) -> Optional[Dict]:
        """
        計算節日航班日期
        
        透過呼叫日期計算 API 來計算指定月份的節日及其出發和回程日期。
        
        參數:
            month_offset (int): 月份偏移量（從當前月份開始計算幾個月後）
            
        返回:
            Optional[Dict]: 包含計算結果的字典，格式如下：
                {
                    "target_year": 2025,
                    "target_month": 12,
                    "holidays": [
                        {
                            "holiday_name": "行憲紀念日",
                            "holiday_date": "2025-12-25",
                            "departure_date": "2025-12-21",
                            "return_date": "2025-12-25",
                            "weekday": "四"
                        }
                    ]
                }
                如果 API 呼叫失敗則返回 None
                
        異常:
            requests.exceptions.RequestException: 當 API 請求失敗時
        """
        url = f"{self.base_url}{self.calculate_holiday_dates_endpoint}"
        payload = {
            "month_offset": month_offset
        }
        
        self.log_manager.log_info(
            f"正在呼叫節日日期計算 API: {url}，參數: month_offset={month_offset}"
        )
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            # 檢查 HTTP 狀態碼
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    data = result.get('data', {})
                    holidays_count = len(data.get('holidays', []))
                    self.log_manager.log_info(
                        f"成功獲取節日日期計算結果: 目標年月={data.get('target_year')}-{data.get('target_month'):02d}, "
                        f"節日數量={holidays_count}"
                    )
                    return data
                else:
                    error_msg = result.get('error', '未知錯誤')
                    self.log_manager.log_error(f"節日日期計算 API 返回錯誤: {error_msg}")
                    return None
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get('error', '請求參數錯誤')
                self.log_manager.log_error(f"節日日期計算 API 請求參數錯誤: {error_msg}")
                return None
            else:
                self.log_manager.log_error(
                    f"節日日期計算 API 返回異常狀態碼: {response.status_code}, "
                    f"響應內容: {response.text}"
                )
                return None
                
        except requests.exceptions.Timeout as e:
            self.log_manager.log_error(f"節日日期計算 API 請求超時: {e}", e)
            return None
        except requests.exceptions.ConnectionError as e:
            self.log_manager.log_error(f"無法連接到節日日期計算 API: {e}", e)
            return None
        except requests.exceptions.RequestException as e:
            self.log_manager.log_error(f"呼叫節日日期計算 API 時發生錯誤: {e}", e)
            return None
        except json.JSONDecodeError as e:
            self.log_manager.log_error(f"解碼節日日期計算 API 響應失敗: {e.msg}", e)
            return None
        except Exception as e:
            self.log_manager.log_error(f"節日日期計算服務發生未預期的錯誤: {e}", e)
            return None
