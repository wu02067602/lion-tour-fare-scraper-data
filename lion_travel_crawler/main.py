from controllers.data_acquisition_controller import DataAcquisitionController
import json
from processors.flight_tasks_fixed_month_processors import FlightTasksFixedMonthProcessors
from processors.flight_tasks_holidays_processors import FlightTasksHolidaysProcessors

def main():
    """
    雄獅旅遊機票資料擷取系統主入口
    """
    controller = DataAcquisitionController()
    config_manager = controller.config_manager
    log_manager = controller.log_manager

    # 處理固定月份日期爬蟲任務
    flight_tasks_fixed_month_processors = FlightTasksFixedMonthProcessors(config_manager, log_manager)
    # 處理節日爬蟲任務
    flight_tasks_holidays_processors = FlightTasksHolidaysProcessors(config_manager, log_manager)
    
    try:
        # 從配置中獲取預定義任務
        flight_tasks = config_manager.config.get("flight_tasks", [])
        flight_tasks_fixed_month = flight_tasks_fixed_month_processors.process_flight_tasks()
        flight_tasks.extend(flight_tasks_fixed_month)
        flight_tasks_holidays = flight_tasks_holidays_processors.process_flight_tasks()
        flight_tasks.extend(flight_tasks_holidays)
        
        if flight_tasks:
            print(f"從配置中讀取到 {len(flight_tasks)} 個預定義任務")
            result = controller.batch_acquisition(flight_tasks)
            print(f"批量任務執行狀態: 總計 {result['total_tasks']} 個任務，已完成 {result['completed_tasks']} 個")
            return result
        else:
            print("錯誤: 配置中沒有預定義任務")
            return {"status": "error", "message": "未提供任務參數"}
    except Exception as e:
        print(f"執行預定義任務出錯: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    result = main()
    
    # 將結果輸出為JSON格式
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
