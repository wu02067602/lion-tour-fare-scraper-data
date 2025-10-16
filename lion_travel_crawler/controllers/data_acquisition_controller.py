from clients.api_client import APIClient
from config.config_manager import ConfigManager
from utils.log_manager import LogManager
from parsers.api_parser import ApiParser
from processors.data_processor import DataProcessor
from storage.storage_manager import StorageManager
from .task_manager import TaskManager
import uuid
import datetime
import time
import threading
from typing import List, Dict, Optional

class DataAcquisitionController:
    """
    資料擷取控制器，作為系統的主要入口點，協調整個資料擷取流程，管理任務執行
    """
    
    def __init__(self):
        """
        初始化資料擷取控制器
        """
        self.config_manager = ConfigManager()
        self.config_manager.load_config("lion_travel_crawler/config/config.yaml")
        
        self.log_manager = LogManager(self.config_manager)
        
        self.storage_manager = StorageManager(
            config_manager=self.config_manager, 
            log_manager=self.log_manager
        )
        self.data_processor = DataProcessor(
            log_manager=self.log_manager,
            storage_manager=self.storage_manager
        )
        self.api_client = APIClient(
            config_manager=self.config_manager,
            log_manager=self.log_manager
        )
        self.api_parser = ApiParser(log_manager=self.log_manager)

        self.task_manager = TaskManager(
            max_concurrent_tasks=self.config_manager.config["task"]["max_concurrent_tasks"]
        )
        self.task_manager.set_acquisition_callback(self._execute_acquisition_task)
        self.log_manager.log_info("資料擷取控制器初始化完成")
    
    def _execute_acquisition_task(self, task_id):
        """
        執行單個資料擷取任務的內部方法，用作任務管理器的回調函數
        
        Args:
            task_id: 任務ID
            
        Returns:
            任務執行結果
        """
        task = None
        try:
            task = self.task_manager.get_task_status(task_id)
            if task is None:
                return {"status": "error", "message": f"找不到任務 {task_id}"}
            
            task["start_time"] = datetime.datetime.now()
            self.log_manager.log_info(f"開始執行資料擷取任務 {task_id}")
            
            if "original_start_time" not in task:
                task["original_start_time"] = task["start_time"]
            
            task["status"] = "running"
            self.log_manager.log_task_status(task_id, "running")
            
            params = task.get("api_params", {})
            if not params:
                raise ValueError(f"任務 {task_id}缺少 'api_params'")

            # 1. 透過 API Client 獲取資料
            json_data = self.api_client.fetch_flight_data(params)
            
            # 2. 解析 API 回應
            structured_data = self.api_parser.parse_response(json_data)
            
            # 3. 處理並儲存資料
            self.data_processor.get_data(data=structured_data)
            json_result = self.data_processor.convert_to_json()
            table_result = self.data_processor.convert_to_table()
            self.data_processor.save_to_storage(filename=f"flight_data_{task_id}")
            self.data_processor.save_row_data_json_to_storage(row_data=json_data)
            
            # 更新任務狀態為已完成
            task["status"] = "completed"
            task["end_time"] = datetime.datetime.now()
            self.log_manager.log_task_status(task_id, "completed")
            
            original_start = task.get("original_start_time")
            total_execution_time = (task["end_time"] - original_start).total_seconds()
            
            task["result"] = {
                "message": f"Successfully processed {len(structured_data)} flight infos.",
                "total_execution_time": f"{total_execution_time:.2f} 秒"
            }
            
            self.log_manager.log_debug(f"資料擷取任務 {task_id} 完成，耗時 {total_execution_time:.2f} 秒")
                
            return {"status": "success", "task_id": task_id, "result": task["result"]}
            
        except Exception as e:
            error_message = f"資料擷取任務 {task_id} 執行出錯: {str(e)}"
            self.log_manager.log_error(error_message, e)
            
            if task:
                task["status"] = "failed"
                task["end_time"] = datetime.datetime.now()
                task["error"] = str(e)
                self.log_manager.log_task_status(task_id, "failed")
            
            return self.handle_error(e, task_id)

    def initialize(self, api_params: Dict) -> Dict:
        """
        初始化資料擷取參數
        
        Args:
            api_params: API 請求的參數字典
            
        Returns:
            包含任務ID和初始狀態的字典
        """
        task_id = str(uuid.uuid4())
        created_time = datetime.datetime.now()
        task_data = {
            "task_id": task_id,
            "api_params": api_params,
            "status": "initialized",
            "created_time": created_time,
            "start_time": None,
            "end_time": None,
            "result": None
        }
        
        self.log_manager.log_info(f"初始化資料擷取任務 {task_id}")
        self.task_manager.add_task(task_data)
        
        return {"task_id": task_id, "status": "initialized", "created_time": created_time}

    def start_acquisition(self, task_id: str = None) -> Dict:
        """
        開始單個資料擷取任務
        
        Args:
            task_id: 任務ID
            
        Returns:
            任務執行結果
        """
        if task_id is None:
            task = self.task_manager.get_next_task()
            if task is None:
                return {"status": "error", "message": "沒有可執行的任務"}
            task_id = task["task_id"]
        
        try:
            result = self._execute_acquisition_task(task_id)
            return result
        finally:
            self.task_manager.release_task_slot()
    
    def batch_acquisition(self, task_list: List[Dict]) -> Dict:
        """
        批次執行多個資料擷取任務
        
        Args:
            task_list: 任務參數列表，每個字典包含 'api_params'
            
        Returns:
            批次任務執行結果
        """
        task_ids = []
        batch_id = f"batch_{str(uuid.uuid4())[:8]}"
        self.log_manager.log_info(f"開始批次任務 {batch_id} 的任務初始化")
        
        for task_params_item in task_list:
            # The item from config contains 'name' and 'api_params'
            api_params = task_params_item.get('api_params', {})
            task_data = {
                "task_id": str(uuid.uuid4()),
                "api_params": api_params,
                "name": task_params_item.get('name', 'untitled'),
                "status": "initialized",
                "created_time": datetime.datetime.now(),
                "start_time": None,
            }
            self.task_manager.add_task(task_data)
            task_ids.append(task_data["task_id"])

        self.log_manager.log_info(f"批次任務 {batch_id} 初始化完成，共 {len(task_ids)} 個任務，開始處理")
        self.task_manager.process_batch_tasks()
        
        # 等待任務完成或超時
        max_wait_time = self.config_manager.config["task"]["task_timeout"] * 60
        start_time = time.time()
        
        self.task_manager.wait_for_all_tasks(timeout=max_wait_time)
        
        elapsed_time = time.time() - start_time
        
        # 收集結果
        results = {
            "batch_id": batch_id,
            "total_tasks": len(task_ids),
            "elapsed_time": f"{elapsed_time:.2f} 秒",
            "tasks": {}
        }
        
        completed_count = 0
        for task_id in task_ids:
            task = self.task_manager.get_task_status(task_id)
            if task:
                if task["status"] in ["completed", "failed"]:
                    completed_count += 1
                results["tasks"][task_id] = {
                    "status": task["status"],
                    "name": task.get("name"),
                    "created_time": task.get("created_time"),
                    "start_time": task.get("start_time"),
                    "end_time": task.get("end_time")
                }
                if task.get("error"):
                    results["tasks"][task_id]["error"] = task["error"]

        results["completed_tasks"] = completed_count
        if completed_count < len(task_ids):
             self.log_manager.log_error(f"批次任務 {batch_id} 已超時，有 {len(task_ids) - completed_count} 個任務未完成")
             results["timeout"] = True
        
        self.log_manager.log_info(f"批次任務 {batch_id} 執行完成，耗時 {elapsed_time:.2f} 秒")
        return results

    def get_task_status(self, task_id: str) -> Dict:
        """
        獲取特定任務的狀態
        
        Args:
            task_id: 任務ID
            
        Returns:
            任務狀態信息
        """
        task = self.task_manager.get_task_status(task_id)
        if task:
            status_info = {
                "task_id": task_id,
                "status": task["status"],
                "has_result": "result" in task and task["result"] is not None,
                "created_time": task.get("created_time"),
                "start_time": task.get("start_time"),
                "end_time": task.get("end_time"),
                "original_start_time": task.get("original_start_time")
            }
            
            if status_info.get("end_time") and status_info.get("original_start_time"):
                total_time = (status_info["end_time"] - status_info["original_start_time"]).total_seconds()
                status_info["total_execution_time"] = f"{total_time:.2f} 秒"
            
            return status_info
        else:
            return {"status": "error", "message": f"找不到任務 {task_id}"}

    def handle_error(self, exception: Exception, task_id: Optional[str] = None) -> Dict:
        """
        處理錯誤情況，並執行重試邏輯
        """
        # (This method can be kept as is, its logic is generic)
        error_message = str(exception)
        error_type = type(exception).__name__
        
        self.log_manager.log_error(f"錯誤: {error_message}", exception)
        
        retry_config = self.config_manager.get_retry_config()
        should_retry = error_type in retry_config.get("retry_on_errors", [])
        
        if task_id and should_retry:
            task = self.task_manager.get_task_status(task_id)
            if task:
                retry_count = task.get("retry_count", 0)
                max_attempts = retry_config.get("max_attempts", 3)
                
                if retry_count < max_attempts:
                    backoff_factor = retry_config.get("backoff_factor", 2.0)
                    retry_interval = retry_config.get("interval", 5) * (backoff_factor ** retry_count)
                    
                    task["retry_count"] = retry_count + 1
                    task["status"] = "retrying"
                    self.log_manager.log_task_status(task_id, "retrying")
                    task["last_error"] = error_message
                    
                    self.log_manager.log_info(f"任務 {task_id} 將在 {retry_interval:.2f} 秒後重試 (嘗試 {retry_count + 1}/{max_attempts})")
                    
                    timer = threading.Timer(retry_interval, self._schedule_retry_task, args=[task_id])
                    timer.daemon = True
                    timer.start()
                    
                    return {"status": "retrying", "task_id": task_id, "retry_in": retry_interval}
        
        return {"status": "error", "error_type": error_type, "error_message": error_message, "task_id": task_id}

    def _schedule_retry_task(self, task_id: str) -> None:
        """
        將重試任務加入任務管理器的隊列
        """
        task = self.task_manager.get_task_status(task_id)
        if not task or task["status"] != "retrying":
            self.log_manager.log_info(f"任務 {task_id} 狀態已變更，取消重試")
            return
            
        self.log_manager.log_info(f"重新排程任務 {task_id} (第 {task.get('retry_count', 0)} 次嘗試)")
        
        task["status"] = "initialized"
        self.log_manager.log_task_status(task_id, "initialized")
        task["start_time"] = None
        
        self.task_manager.add_task(task)
        self.task_manager.process_batch_tasks()
