"""
數據處理器模組 - 負責處理、轉換和驗證來自網頁解析器的資料
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import time

from models import FlightInfo
from storage.storage_manager import StorageManager
from utils.log_manager import LogManager

class DataProcessor:
    """處理爬取的原始數據，轉換為標準格式並準備儲存"""
    
    def __init__(self,
                 storage_manager: Optional[StorageManager] = None,
                 log_manager: Optional[LogManager] = None):
        """
        初始化數據處理器
        
        Args:
            storage_manager: 儲存管理器實例，用於數據儲存操作
            log_manager: 日誌管理器實例，用於記錄操作和錯誤
        """
        self.log_manager = log_manager
        self.storage_manager = storage_manager
        self.raw_data = None
        self.processed_data = None
        self.json_data = None
        self.table_data = None

    def get_data(self, data: List[Dict[str, Any]]) -> List[FlightInfo]:
        """
        獲取數據
        """
        self.processed_data = data

    def convert_to_json(self) -> str:
        """
        將處理後的數據轉換為 JSON 字符串
        
        Returns:
            包含所有航班信息的 JSON 字符串
        """
        if not self.processed_data:
            self.log_manager.log_info("嘗試轉換空數據為JSON")
            return "[]"
        
        flight_dicts = []
        for flight in self.processed_data:
            flight_dicts.append(flight.to_json())
        
        self.json_data = json.dumps(flight_dicts, ensure_ascii=False, indent=2)
        return self.json_data
    
    def convert_to_table(self) -> pd.DataFrame:
        """
        將處理後的數據轉換為適合儲存到資料庫表的格式
        
        Returns:
            DataFrame: 表格格式的數據列表
        """
        if not self.processed_data:
            self.log_manager.log_error("嘗試轉換空數據為表格格式", Exception("嘗試轉換空數據為表格格式"))
            raise ValueError("嘗試轉換空數據為表格格式")
            
        table_data = []
        current_timestamp = time.time()
        
        for flight in self.processed_data:
            row = {
                # 基本信息
                "去程日期": flight.departure_date.strftime("%Y-%m-%d") if flight.departure_date else None,
                "回程日期": flight.return_date.strftime("%Y-%m-%d") if flight.return_date else None,
                "票面價格": int(flight.price) if flight.price else None,
                "稅金": int(flight.tax) if flight.tax else None,
                "crawl_time": current_timestamp,
            }
            
            # 處理去程航段 (最多3個航段)
            for i in range(min(3, len(flight.outbound_segments))):
                segment = flight.outbound_segments[i]
                segment_num = i + 1
                
                row[f"去程航班編號{segment_num}"] = segment.flight_number
                row[f"去程艙等{segment_num}"] = segment.cabin_class
            
            # 處理回程航段 (最多3個航段)
            for i in range(min(3, len(flight.inbound_segments))):
                segment = flight.inbound_segments[i]
                segment_num = i + 1
                
                row[f"回程航班編號{segment_num}"] = segment.flight_number
                row[f"回程艙等{segment_num}"] = segment.cabin_class
            
            # 確保所有航班編號和艙等欄位都存在
            # 去程航段 2-3
            for segment_num in range(len(flight.outbound_segments) + 1, 4):
                row[f"去程航班編號{segment_num}"] = None
                row[f"去程艙等{segment_num}"] = None
            
            # 回程航段 2-3
            for segment_num in range(len(flight.inbound_segments) + 1, 4):
                row[f"回程航班編號{segment_num}"] = None
                row[f"回程艙等{segment_num}"] = None
            
            table_data.append(row)
        
        # 轉換為pandas DataFrame
        self.table_data = pd.DataFrame(table_data)
        return self.table_data
    
    def save_to_storage(self, filename: str) -> bool:
        """
        將處理後的數據保存到儲存系統
        
        Args:
            filename: 儲存的文件名
            
        Returns:
            操作是否成功
        """
        if not self.storage_manager:
            self.log_manager.log_error("未配置儲存管理器，無法保存數據", Exception("未配置儲存管理器"))
            return False

        # 確保已經有處理好的數據
        if not self.processed_data:
            raise ValueError("沒有處理好的數據")
        
        # 確保已轉換為JSON和表格格式
        if not self.json_data:
            self.log_manager.log_error("沒有轉換為JSON格式，重新轉換", Exception("沒有轉換為JSON格式"))
            self.convert_to_json()
        
        if not hasattr(self, 'table_data') and not self.table_data.empty:
            self.log_manager.log_error("沒有轉換為表格格式，重新轉換", Exception("沒有轉換為表格格式"))
            self.convert_to_table()

        # 保存到Cloud Storage
        gcs_path = f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        success_gcs, error_message_gcs = self.storage_manager.save_to_cloud_storage(json_data=self.json_data,
                                            filename=gcs_path
                                            )
        
        # 保存到BigQuery
        success_bq, error_message_bq = self.storage_manager.save_to_bigquery(table_data=self.table_data)
        if not success_gcs:
            self.log_manager.log_error(f"保存到Cloud Storage時發生錯誤，堆疊: {error_message_gcs}", Exception("保存到Cloud Storage時發生錯誤"))
            raise IOError(f"保存到Cloud Storage時發生錯誤: {error_message_gcs}")

        elif not success_bq:
            self.log_manager.log_error(f"保存到BigQuery時發生錯誤，堆疊: {error_message_bq}", Exception("保存到BigQuery時發生錯誤"))
            raise IOError(f"保存到BigQuery時發生錯誤: {error_message_bq}")

        self.log_manager.log_info(f"成功將數據保存到 {filename}")
        return True
    
    def save_row_data_json_to_storage(self, row_data: Dict[str, Any]) -> bool:
        """
        將api回傳的資料轉換為json格式，並保存到儲存系統

        Args:
            row_data: api回傳的資料
            
        Returns:
            操作是否成功
        """
        gcs_path = f"api_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        # 將 row_data 轉換為 JSON 格式
        json_data = json.dumps(row_data, ensure_ascii=False, indent=2)
        success_gcs, error_message_gcs = self.storage_manager.save_to_cloud_storage(json_data=json_data,
                                            filename=gcs_path
                                            )
        if not success_gcs:
            self.log_manager.log_error(f"row_data保存到Cloud Storage時發生錯誤，堆疊: {error_message_gcs}", Exception("row_data保存到Cloud Storage時發生錯誤"))

        self.log_manager.log_info(f"成功將api回傳的資料保存到 {gcs_path}")
