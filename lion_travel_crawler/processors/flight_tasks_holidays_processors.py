from config.config_manager import ConfigManager
from services.date_calculation_service import DateCalculationService
from utils.log_manager import LogManager
from datetime import datetime
from typing import Dict, List, Optional
import copy

class FlightTasksHolidaysProcessors:
    """
    節日航班任務處理器
    
    負責處理節日相關的航班爬蟲任務，透過日期計算服務獲取節日日期資訊。
    
    屬性:
        config_manager (ConfigManager): 配置管理器實例
        log_manager (LogManager): 日誌管理器實例
        date_calculation_service (DateCalculationService): 日期計算服務實例
    """
    
    def __init__(self, config_manager: ConfigManager, log_manager: LogManager):
        """
        初始化節日航班任務處理器
        
        參數:
            config_manager (ConfigManager): 配置管理器實例
            log_manager (LogManager): 日誌管理器實例
        """
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.date_calculation_service = DateCalculationService(config_manager, log_manager)

    def process_flight_tasks(self) -> List[Dict]:
        """
        處理節日爬蟲任務列表

        返回:
            List[Dict]: 處理後的 API 任務列表
            範例格式:
            [
                {
                    'name': '台北到新加坡 行憲紀念日 2025-12-21出發 2025-12-25回程',
                    'api_params': {
                        'Rtow': '1',
                        'ClsType': '0',
                        ...
                        'SeekDestinations': [
                            {'DepartDate': '2025-12-21', ...},
                            {'DepartDate': '2025-12-25', ...}
                        ]
                    }
                }
            ]
        """
        holidays_task_list = self._get_holidays_task_list()
        processed_flight_tasks = []

        for base_task in holidays_task_list:
            month_offset = base_task["api_params"]["Month"]
            
            # 呼叫日期計算服務獲取節日日期
            holiday_data = self.date_calculation_service.calculate_holiday_dates(month_offset)
            
            if not holiday_data:
                self.log_manager.log_error(
                    f"任務 '{base_task.get('name')}' 節日日期計算失敗，跳過處理"
                )
                continue
            
            holidays = holiday_data.get('holidays', [])
            
            for holiday in holidays:
                processed_task = self._create_processed_task_from_api(base_task, holiday)
                if processed_task:
                    processed_flight_tasks.append(processed_task)
                    
        return processed_flight_tasks
    
    def _create_processed_task_from_api(self, base_task: Dict, holiday: Dict) -> Optional[Dict]:
        """
        根據基本任務和 API 返回的節日信息，創建一個處理過的任務字典
        
        參數:
            base_task (Dict): 基本任務配置，包含 api_params 等參數
            holiday (Dict): 從 API 獲取的節日信息字典，包含：
                - holiday_name: 節日名稱
                - holiday_date: 節日日期
                - departure_date: 出發日期
                - return_date: 回程日期
                - weekday: 星期幾
            
        返回:
            Optional[Dict]: 處理後的任務字典，如果處理失敗則返回 None
        """
        dep_date_str = holiday.get('departure_date')
        ret_date_str = holiday.get('return_date')
        holiday_name = holiday.get('holiday_name', '')
        
        if not dep_date_str or not ret_date_str:
            self.log_manager.log_warning(
                f"節日 '{holiday_name}' 缺少必要的日期資訊，跳過處理"
            )
            return None

        final_api_params = copy.deepcopy(base_task["api_params"])

        final_api_params["SeekDestinations"] = [
            {
                "DepartDate": dep_date_str,
                "DepartCity": final_api_params.get("DepCity1"),
                "DepartAirport": "",
                "DepartCountry": final_api_params.get("DepCountry1"),
                "ArriveCity": final_api_params.get("ArrCity1"),
                "ArriveAirport": "",
                "ArriveCountry": final_api_params.get("ArrCountry1"),
            },
            {
                "DepartDate": ret_date_str,
                "DepartCity": final_api_params.get("ArrCity1"),
                "DepartAirport": "",
                "DepartCountry": final_api_params.get("ArrCountry1"),
                "ArriveCity": final_api_params.get("DepCity1"),
                "ArriveAirport": "",
                "ArriveCountry": final_api_params.get("DepCountry1"),
            }
        ]
        
        keys_to_remove = ["Month", "DepCountry1", "ArrCountry1"]
        for key in keys_to_remove:
            if key in final_api_params:
                del final_api_params[key]

        dep_city = base_task["api_params"].get("DepCity1", "")
        arr_city = base_task["api_params"].get("ArrCity1", "")
        
        processed_task = {
            "name": f"{dep_city}到{arr_city} {holiday_name} {dep_date_str}出發 {ret_date_str}回程",
            "api_params": final_api_params
        }
        
        self.log_manager.log_info(
            f"成功處理節日任務: {processed_task['name']}"
        )
        
        return processed_task

    def _get_holidays_task_list(self) -> List[Dict]:
        """
        獲取節日爬蟲任務列表

        返回:
            List[Dict]: 節日爬蟲任務列表
        """
        return self.config_manager.get_flight_tasks_holidays()