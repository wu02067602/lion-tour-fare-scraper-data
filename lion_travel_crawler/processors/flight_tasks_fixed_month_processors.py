from config.config_manager import ConfigManager
from datetime import datetime
import calendar
from typing import Dict, List
import copy

class FlightTasksFixedMonthProcessors:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def process_flight_tasks(self) -> List[Dict]:
        """
        處理固定月份日期爬蟲任務列表

        返回:
            List[Dict]: 處理後的 API 任務列表
            範例格式
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
        current_date = datetime.now()

        for task in fixed_month_task_list:
            processed_task = self._process_single_task(task, current_date)
            if processed_task:
                processed_flight_tasks.append(processed_task)
            
        return processed_flight_tasks

    def _process_single_task(self, task: Dict, current_date: datetime) -> Dict:
        """處理單個固定月份任務"""
        api_params_template = task.get("api_params")
        if not api_params_template:
            return None

        month_offset = api_params_template.get("Month", 0)
        target_year = current_date.year
        target_month = current_date.month + month_offset

        while target_month > 12:
            target_month -= 12
            target_year += 1
            
        days_in_month = calendar.monthrange(target_year, target_month)[1]
        
        dep_day = int(api_params_template.get("DepDate1", 1))
        return_day = int(api_params_template.get("DepDate2", 1))
        
        dep_day = min(dep_day, days_in_month)
        return_day = min(return_day, days_in_month)
            
        dep_date_str = f"{target_year}-{target_month:02d}-{dep_day:02d}"
        return_date_str = f"{target_year}-{target_month:02d}-{return_day:02d}"

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
        
        return processed_task

    def _get_fixed_month_task_list(self) -> List[Dict]:
        """
        獲取固定月份日期爬蟲任務列表

        返回:
            List[Dict]: 固定月份日期爬蟲任務列表
        """
        return self.config_manager.get_flight_tasks_fixed_month()
