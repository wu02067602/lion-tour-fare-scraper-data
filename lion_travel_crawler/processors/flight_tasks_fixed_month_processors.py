from config.config_manager import ConfigManager
from services.date_calculation_service import DateCalculationService
from utils.log_manager import LogManager
from typing import Dict, List, Optional
import copy

class FlightTasksFixedMonthProcessors:
    """
    固定月份航班任務處理器
    
    負責處理固定月份日期的航班爬蟲任務，透過日期計算服務獲取日期資訊。
    
    屬性:
        config_manager (ConfigManager): 配置管理器實例
        log_manager (LogManager): 日誌管理器實例
        date_calculation_service (DateCalculationService): 日期計算服務實例
    """
    
    def __init__(self, config_manager: ConfigManager, log_manager: LogManager):
        """
        初始化固定月份航班任務處理器
        
        參數:
            config_manager (ConfigManager): 配置管理器實例
            log_manager (LogManager): 日誌管理器實例
        """
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.date_calculation_service = DateCalculationService(config_manager, log_manager)

    def process_flight_tasks(self) -> List[Dict]:
        """
        處理固定月份日期爬蟲任務列表

        返回:
            List[Dict]: 處理後的 API 任務列表
            範例格式:
            [
                {
                    'name': '範例：台北到新加坡...',
                    'api_params': {
                        'Rtow': '1',
                        'ClsType': '0',
                        ...
                        'SeekDestinations': [
                            {'DepartDate': '2025-07-21', ...},
                            {'DepartDate': '2025-07-27', ...}
                        ]
                    }
                }
            ]
        """
        fixed_month_task_list = self._get_fixed_month_task_list()
        processed_flight_tasks = []

        for task in fixed_month_task_list:
            processed_task = self._process_single_task(task)
            if processed_task:
                processed_flight_tasks.append(processed_task)
            
        return processed_flight_tasks

    def _process_single_task(self, task: Dict) -> Optional[Dict]:
        """
        處理單個固定月份任務
        
        透過日期計算服務獲取日期資訊，並構建完整的任務參數。
        
        參數:
            task (Dict): 原始任務配置
            
        返回:
            Optional[Dict]: 處理後的任務字典，如果處理失敗則返回 None
        """
        api_params_template = task.get("api_params")
        if not api_params_template:
            self.log_manager.log_warning(f"任務 '{task.get('name')}' 缺少 api_params，跳過處理")
            return None

        # 從配置中提取參數
        month_offset = api_params_template.get("Month", 0)
        dep_day = int(api_params_template.get("DepDate1", 1))
        return_day = int(api_params_template.get("DepDate2", 1))
        
        # 呼叫日期計算服務
        date_info = self.date_calculation_service.calculate_dates(
            month_offset=month_offset,
            dep_day=dep_day,
            return_day=return_day
        )
        
        if not date_info:
            self.log_manager.log_error(
                f"任務 '{task.get('name')}' 日期計算失敗，跳過處理"
            )
            return None
        
        # 從 API 響應中提取日期
        dep_date_str = date_info.get("departure_date")
        return_date_str = date_info.get("return_date")
        
        if not dep_date_str or not return_date_str:
            self.log_manager.log_error(
                f"任務 '{task.get('name')}' 日期計算響應缺少必要欄位"
            )
            return None

        # 創建一個新的 api_params 字典，避免修改原始配置
        final_api_params = copy.deepcopy(api_params_template)

        # 填充 SeekDestinations
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
                "DepartDate": return_date_str,
                "DepartCity": final_api_params.get("ArrCity1"),
                "DepartAirport": "",
                "DepartCountry": final_api_params.get("ArrCountry1"),
                "ArriveCity": final_api_params.get("DepCity1"),
                "ArriveAirport": "",
                "ArriveCountry": final_api_params.get("DepCountry1"),
            }
        ]
        
        # 移除臨時參數
        keys_to_remove = ["Month", "DepDate1", "DepDate2", "DepCountry1", "ArrCountry1"]
        for key in keys_to_remove:
            if key in final_api_params:
                del final_api_params[key]

        dep_city = api_params_template.get("DepCity1", "")
        arr_city = api_params_template.get("ArrCity1", "")
        
        processed_task = {
            "name": f"{dep_city}到{arr_city} {dep_date_str}出發 {return_date_str}回程",
            "api_params": final_api_params
        }
        
        self.log_manager.log_info(
            f"成功處理任務: {processed_task['name']}"
        )
        
        return processed_task

    def _get_fixed_month_task_list(self) -> List[Dict]:
        """
        獲取固定月份日期爬蟲任務列表

        返回:
            List[Dict]: 固定月份日期爬蟲任務列表
        """
        return self.config_manager.get_flight_tasks_fixed_month()
