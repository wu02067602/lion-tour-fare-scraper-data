from config.config_manager import ConfigManager
from datetime import datetime, timedelta
from typing import Dict, List
import requests
import copy
import json

class FlightTasksHolidaysProcessors:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def process_flight_tasks(self) -> List[Dict]:
        """
        處理節日爬蟲任務列表

        返回:
            List[Dict]: 處理後的 API 任務列表
        """
        holidays_task_list = self._get_holidays_task_list()
        processed_flight_tasks = []
        current_date = datetime.now()

        for base_task in holidays_task_list:
            month_offset = base_task["api_params"]["Month"]
            target_year, target_month = self._calculate_target_month(current_date, month_offset)
            
            taiwan_holidays = self._fetch_taiwan_holidays(target_year, target_month)
            
            for holiday in taiwan_holidays:
                if not holiday.get('description') or self._is_skip_holiday(holiday, base_task):
                    continue
                    
                date_ranges = self._get_crawl_date_ranges(holiday)
                dep_date, ret_date = date_ranges
                
                processed_task = self._create_processed_task(base_task, holiday, dep_date, ret_date)
                processed_flight_tasks.append(processed_task)
                    
        return processed_flight_tasks
    
    def _create_processed_task(self, base_task: Dict, holiday: Dict, dep_date: datetime, ret_date: datetime) -> Dict:
        """
        根據基本任務和假日信息，創建一個處理過的任務字典
        
        Args:
            base_task (Dict): 基本任務配置，包含 api_params 等參數
            holiday (Dict): 假日信息字典，包含 description 等假日詳情
            dep_date (datetime): 出發日期
            ret_date (datetime): 回程日期
            
        Returns:
            Dict: 處理後的任務字典，包含：
                - name: 任務名稱，格式為 "{出發城市}到{到達城市} {假日描述} {出發日期}出發 {回程日期}回程"
                - api_params: 處理後的 API 參數，包含：
                    - SeekDestinations: 包含去程和回程的詳細行程資訊
                    - 其他從 base_task 繼承的參數（排除 Month、DepCountry1、ArrCountry1）
        """
        dep_date_str = dep_date.strftime("%Y-%m-%d")
        ret_date_str = ret_date.strftime("%Y-%m-%d")

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
        holiday_desc = holiday.get('description', '')
        
        return {
            "name": f"{dep_city}到{arr_city} {holiday_desc} {dep_date_str}出發 {ret_date_str}回程",
            "api_params": final_api_params
        }

    def _calculate_target_month(self, current_date: datetime, month_offset: int) -> tuple[int, int]:
        """
        計算目標年月
        
        根據當前日期和月份偏移量，計算目標的年月。當月份偏移後超過12月時，
        會自動調整為下一年對應的月份。
        
        Args:
            current_date (datetime): 當前日期
            month_offset (int): 月份偏移量，正數表示往後偏移，負數表示往前偏移
            
        Returns:
            tuple[int, int]: 包含目標年份和月份的元組 (year, month)
        """
        target_month = current_date.month + month_offset
        target_year = current_date.year
        
        while target_month > 12:
            target_month -= 12
            target_year += 1
        return target_year, target_month

    def _is_skip_holiday(self, holiday: Dict, base_task: Dict) -> bool:
        """
        判斷是否要根據特殊規則跳過此節假日日期
        
        根據業務需求，系統需要爬取特定日期範圍的航班資料：
        - 往後第2個月的5號～10號
        - 往後第6個月的24號～28號
        
        此函數會檢查節假日的日期是否落在這些指定範圍內，如果是則返回 True 表示需要跳過，
        因為這些日期會透過其他機制處理。
        
        Args:
            holiday (Dict): 節假日資料字典，包含日期等資訊
            base_task (Dict): 基礎任務配置，包含 api_params 等參數
            
        Returns:
            bool: True 表示需要跳過此日期，False 表示不需要跳過
        """
        month = base_task["api_params"].get("Month", None)
        date_str = holiday.get('date', '')
        holiday_date = datetime.strptime(date_str, "%Y%m%d")
        day = holiday_date.day

        if any(keyword in holiday.get('description', '') for keyword in ['春節', '農曆除夕']):
            return True

        # HACK: 需求中描述 爬取「往後第2個月的5號～10號」以及「往後第6個月的24號～28號」
        # 為滿足此需求因此如此設計
        if month == 2 and 5 <= day <= 10:
            return True
        elif month == 6 and 24 <= day <= 28:
            return True
        else:
            return False

    def _get_holidays_task_list(self) -> List[Dict]:
        """
        獲取節日爬蟲任務列表

        返回:
            List[Dict]: 節日爬蟲任務列表
        """
        return self.config_manager.get_flight_tasks_holidays()
    
    def _fetch_taiwan_holidays(self, target_year: int, target_month: int) -> List[Dict]:
        """
        從外部API獲取指定年月的台灣節假日資料

        Args:
            target_year (int): 目標年份
            target_month (int): 目標月份

        返回:
            List[Dict]: 台灣節假日資料列表
        """
        url = f"https://cdn.jsdelivr.net/gh/ruyut/TaiwanCalendar/data/{target_year}.json"
        holidays_data = []
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            year_data = response.content.decode('utf-8-sig')
            year_data = json.loads(year_data)
            for holiday in year_data:
                if (holiday.get('isHoliday') and 
                    holiday.get('description') != '' and
                    holiday['date'].startswith(f"{target_year}{target_month:02d}")):
                    holidays_data.append(holiday)
            holidays_data = self._remove_holiday_with_compensatory_day(holidays_data)
        except requests.RequestException as e:
            print(f"無法獲取 {target_year} 年 {target_month} 月節假日資料: {e}")
                
        return holidays_data

    def _remove_holiday_with_compensatory_day(self, holidays_data: List[Dict]) -> List[Dict]:
        """
        剔除API描述中補假的國定假日

        如果資料中包含"補"這個字，則剔除
        
        參數:
            holidays_data: 節假日資料列表
            
        返回:
            List[Dict]: 剔除補假後的節假日資料列表
        """
        return [holiday for holiday in holidays_data if '補' not in holiday.get('description')]

    def _get_crawl_date_ranges(self, holiday: Dict) -> tuple:
        """
        根據節假日和星期幾，返回需要爬取的日期範圍

        Args:
            holiday (Dict): 節假日資料字典，包含日期等資訊

        Returns:
            tuple: 包含需要爬取的日期範圍的元組 (start_date, end_date)
        """
        date_str = holiday['date']
        holiday_date = datetime.strptime(date_str, "%Y%m%d")
        weekday = holiday['week']
        description = holiday.get('description', '')
        
        # 預設規則
        crawl_dates = (holiday_date - timedelta(days=2), holiday_date + timedelta(days=2))

        if '開國紀念日' in description and weekday == '三':
            crawl_dates = (holiday_date - timedelta(days=4), holiday_date)
        elif '小年夜' in description:
            # 以小年夜為基準
            if weekday in ['一', '四', '五']:
                crawl_dates = (holiday_date - timedelta(days=2), holiday_date + timedelta(days=4))
            elif weekday in ['二', '三']:
                crawl_dates = (holiday_date - timedelta(days=4), holiday_date + timedelta(days=2))
            elif weekday in ['六', '日']:
                 crawl_dates = (holiday_date - timedelta(days=2), holiday_date + timedelta(days=3))
        else: # 一般國定假日
            if weekday in ['一', '二', '日']:
                crawl_dates = (holiday_date - timedelta(days=4), holiday_date)
            elif weekday == '三':
                crawl_dates = (holiday_date, holiday_date + timedelta(days=3))
            elif weekday == '四':
                crawl_dates = (holiday_date - timedelta(days=1), holiday_date + timedelta(days=3))
            elif weekday == '五':
                crawl_dates = (holiday_date - timedelta(days=2), holiday_date + timedelta(days=2))
            elif weekday == '六':
                crawl_dates = (holiday_date - timedelta(days=3), holiday_date + timedelta(days=1))
                
        return crawl_dates
 