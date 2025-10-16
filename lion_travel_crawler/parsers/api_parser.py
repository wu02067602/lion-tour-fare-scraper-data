#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API 解析器模組

此模組提供 API 解析器，用於解析從雄獅旅遊 API 回傳的 JSON 資料。
"""

from datetime import datetime
from utils.log_manager import LogManager
from models.flight_info import FlightInfo
from models.flight_segment import FlightSegment

class ApiParser:
    """
    API 解析器類別
    
    負責解析 API 回傳的 JSON 資料，並將其轉換為結構化的資料模型。
    """

    def __init__(self, log_manager: LogManager):
        """
        初始化 API 解析器
        """
        self.log_manager = log_manager
        self.structured_data = []

    def parse_response(self, json_data: dict) -> list[FlightInfo]:
        """
        解析 API 的 JSON 響應。

        Args:
            json_data: 從 API 獲取的原始 JSON 字典。

        Returns:
            一個包含 FlightInfo 物件的列表。
        """
        self.structured_data = []
        flight_infos = json_data.get('FlightInfos', [])

        if not flight_infos:
            self.log_manager.log_warning("API response does not contain 'FlightInfos' or it is empty.")
            return []

        for flight_data in flight_infos:
            try:
                flight_info = self._extract_flight_info(flight_data)
                if flight_info:
                    self.structured_data.append(flight_info)
            except Exception as e:
                self.log_manager.log_error(f"Error parsing flight data: {flight_data}. Error: {e}", e)
        
        self.log_manager.log_info(f"Successfully parsed {len(self.structured_data)} flight info items.")
        return self.structured_data

    def _extract_flight_info(self, flight_data: dict) -> FlightInfo | None:
        """
        從單個航班資料區塊中提取資訊。
        """
        fare_infos = flight_data.get('FareInfos')
        if not fare_infos:
            return None

        # 以第一個票價選項為主
        main_fare = fare_infos[0]
        
        price = main_fare.get('TotalPrice')
        price_without_tax = main_fare.get('TotalPriceWithoutTax')
        tax = price - price_without_tax if price is not None and price_without_tax is not None else 0.0

        itinerary_infos = flight_data.get('ItineraryInfos', [])
        if not itinerary_infos:
            return None

        # 提取出發與返回日期
        departure_date_str = itinerary_infos[0].get('DepDateTime')
        departure_date = datetime.strptime(departure_date_str, "%Y-%m-%dT%H:%M:%S").date() if departure_date_str else None
        
        return_date = None
        if len(itinerary_infos) > 1:
            return_date_str = itinerary_infos[1].get('DepDateTime')
            return_date = datetime.strptime(return_date_str, "%Y-%m-%dT%H:%M:%S").date() if return_date_str else None

        flight_info = FlightInfo(
            price=price_without_tax,
            tax=tax,
            departure_date=departure_date,
            return_date=return_date
        )

        # 為了快速查找，將 SegmentDetailInfos 轉換為字典
        segment_details_map = {
            (detail.get('SeqNo'), detail.get('SegSeqNo')): detail
            for detail in main_fare.get('SegmentDetailInfos', [])
        }

        for itinerary in itinerary_infos:
            journey_seq_no = itinerary.get('SeqNo')
            # 根據 SeqNo 判斷是去程還是回程
            target_segments_list = flight_info.outbound_segments if journey_seq_no == 1 else flight_info.inbound_segments

            for segment_info in itinerary.get('SegmentInfos', []):
                segment_seq_no = segment_info.get('SegSeqNo')
                
                # 使用組合鍵查找對應的票價細節
                segment_detail = segment_details_map.get((journey_seq_no, segment_seq_no), {})

                # 決定艙等：優先使用 CabinName，其次是 FareFamilyName，最後是 BookingClass
                cabin_class = f"{segment_detail.get('CabinName')}{segment_detail.get('BookingClass')}"
                
                # 處理航班編號補零：將數字部分補零至3位
                airline_code = segment_info.get('MarketingAirline', '')
                flight_no = segment_info.get('FlightNo', '')
                
                # 如果航班號碼是純數字，則補零至3位
                if flight_no.isdigit():
                    flight_no = flight_no.zfill(3) # 確保這裡使用了 zfill(3)
                
                flight_number = f"{airline_code}{flight_no}"
                
                segment = FlightSegment(
                    flight_number=flight_number,
                    cabin_class=cabin_class
                )
                target_segments_list.append(segment)

        return flight_info

    def get_structured_data(self) -> list[FlightInfo]:
        """
        獲取結構化的數據。

        Returns:
            解析後的結構化數據列表。
        """
        return self.structured_data
