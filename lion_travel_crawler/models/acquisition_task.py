"""
雄獅旅遊機票資料爬蟲系統 - 爬蟲任務模型

此模組定義了爬蟲任務 (CrawlTask) 資料模型，用於表示單個爬蟲任務的狀態與結果。
"""
from datetime import datetime
from typing import Dict, List, Optional
from .flight_info import FlightInfo
from dataclasses import dataclass, field

@dataclass
class AcquisitionTask:
    """
    表示單個資料擷取任務的數據類別
    """
    task_id: str
    parameters: Dict
    status: str = "initialized"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[List[FlightInfo]] = field(default_factory=list)
    error_info: Optional[Dict] = None

    def to_dict(self):
        """
        將任務對象轉換為字典
        """
        return {
            "task_id": self.task_id,
            "parameters": self.parameters,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "result": [flight.to_dict() for flight in self.result] if self.result else None,
            "error_info": self.error_info
        }
