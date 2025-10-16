# 雄獅旅遊機票資料爬蟲系統

## 專案概述

本專案是一個自動化爬蟲系統，用於從雄獅旅遊網站抓取機票價格及相關資訊。系統採用動態爬蟲技術，透過Selenium模擬使用者行為，並利用非同步處理技術高效處理多組查詢任務。抓取的資料將存儲至Google Cloud Storage及BigQuery以便後續分析。

## 功能特點

- **動態爬蟲功能**：使用Selenium模擬真實用戶行為，支援指定航班編號、去程日期、回程日期等參數
- **高效非同步處理**：支援多任務並行執行，顯著提高爬蟲效率
- **智能任務調度**：內建任務佇列機制，確保任務有序且可控地執行
- **雲端資料儲存**：將抓取的資料結構化後存入BigQuery和Cloud Storage
- **錯誤重試機制**：當爬蟲失敗時能自動重試，提高系統可靠性
- **任務監控通知**：提供任務執行狀態的即時監控，並在任務完成或出現異常時發送通知

## 系統架構

本系統採用模組化設計，包括以下核心組件：

- **爬蟲控制器 (CrawlerController)**：系統的中央控制器，負責協調各組件
- **任務管理器 (TaskManager)**：管理爬蟲任務的排程與執行
- **瀏覽器控制器 (BrowserController)**：控制Selenium WebDriver的行為
- **網頁解析器 (WebParser)**：負責解析網頁內容，提取機票資訊
- **數據處理器 (DataProcessor)**：處理與轉換爬取的資料
- **存儲管理器 (StorageManager)**：管理數據的存儲操作
- **配置管理器 (ConfigManager)**：集中管理系統配置
- **日誌管理器 (LogManager)**：處理系統日誌記錄

## 目錄結構

```
lion_travel_crawler/
│
├── main.py                      # 主程式入口點
├── .env                         # 環境變量
├── requirements.txt             # 專案依賴
├── README.md                    # 專案說明文件
│
├── config/                      # 配置文件目錄
│   ├── __init__.py
│   ├── config.yaml              # 主要配置文件
│   └── config_manager.py        # 配置管理器類
│
├── controllers/                 # 控制器目錄
│   ├── __init__.py
│   ├── crawler_controller.py    # 爬蟲控制器
│   ├── browser_controller.py    # 瀏覽器控制器
│   └── task_manager.py          # 任務管理器
│
├── models/                      # 數據模型目錄
│   ├── __init__.py
│   ├── flight_info.py           # 航班信息類
│   ├── flight_segment.py        # 航班段類
│   └── crawl_task.py            # 爬蟲任務類
│
├── parsers/                     # 解析器目錄
│   ├── __init__.py
│   └── web_parser.py            # 網頁解析器
│
├── processors/                  # 處理器目錄
│   ├── __init__.py
│   └── data_processor.py        # 數據處理器
│
├── storage/                     # 存儲管理目錄
│   ├── __init__.py
│   └── storage_manager.py       # 存儲管理器
│
└── utils/                       # 工具類目錄
    ├── __init__.py
    └── log_manager.py           # 日誌管理器
```

## 快速開始

### 環境需求

- Python 3.8+
- Google Cloud專案（用於BigQuery和Cloud Storage）
- Chrome或Firefox瀏覽器（用於Selenium）

### 安裝步驟

1. 克隆此專案到本地:
   ```bash
   git clone <專案庫URL>
   cd lion_travel_crawler
   ```

2. 安裝所需依賴:
   ```bash
   pip install -r requirements.txt
   ```

3. 配置環境變數:
   - 填入相應的API金鑰和配置參數
   - 【注意】在雲端部署時，如設定環境變數 `PROJECT_ID`，系統將使用該值覆蓋 `config.yaml` 中的 `storage.bigquery.project_id` 設定，以提高部署彈性。

4. 使用Docker部署（推薦）:
   本專案已提供Dockerfile，可以直接使用Docker進行打包和部署:
   
   ```bash
   # 構建Docker鏡像
   docker build -t lion-travel-crawler .
   
   # 運行容器
   docker run -d --name crawler lion-travel-crawler
   
   # 查看容器日誌
   docker logs -f crawler
   ```

### 使用方法

#### 通過config.yaml配置爬蟲任務

系統的爬蟲任務可以通過修改`config/config.yaml`文件來設定，無需修改程式碼：

```yaml
# 爬蟲任務配置範例
flight_tasks:
  - name: "台北到新加坡 2025-04-02出發 2025-04-06回程"
    url_params:
      DepCity1: "TPE"  # 出發機場
      ArrCity1: "SIN"  # 抵達機場
      DepCountry1: "TW"  # 出發城市
      ArrCountry1: "SG"  # 抵達城市
      DepDate1: "2025-04-02"  # 出發日期
      DepDate2: "2025-04-06"  # 回程日期
      Rtow: 1  # 來回程
      
  - name: "台北到東京 2025-04-10出發 2025-04-15回程"
    url_params:
      DepCity1: "TPE"
      ArrCity1: "HND"
      DepCountry1: "TW"
      ArrCountry1: "JP"
      DepDate1: "2025-04-10"
      DepDate2: "2025-04-15"
      Rtow: 1
```

您可以透過以下方式配置系統：

1. **添加爬蟲任務**：在`flight_tasks`列表中添加新的任務項目
2. **修改瀏覽器設置**：調整`browser`部分的設置，如是否使用無頭模式、頁面加載超時時間等
3. **調整並行處理**：通過`task.max_concurrent_tasks`設置最大並行任務數
4. **配置存儲設置**：修改`storage`部分，設置Google Cloud Storage和BigQuery的參數
5. **自定義重試策略**：在`retry`部分設置重試次數、間隔等參數

## 效能與限制

- 系統設計支持最多4個並行爬蟲任務
- 能在2小時內完成100~144組不同參數組合的抓取任務
- 單一任務的平均執行時間不超過10分鐘
- 爬蟲行為遵循目標網站的robots.txt規則

## 故障排除

### 常見問題

1. **Selenium WebDriver錯誤**
   - 確認Chrome/Firefox版本與WebDriver版本兼容
   - 檢查WebDriver是否正確安裝且在PATH中

2. **任務執行超時**
   - 檢查網絡連接以及是否進入無限迴圈之中
   - 調整配置文件中的超時設定

3. **資料儲存失敗**
   - 驗證Google Cloud憑證是否有效
   - 確認擁有適當的BigQuery和Cloud Storage權限

## 內部文檔

詳細的系統設計和技術文檔位於`docs/`目錄:

- `class_diagram.md` - 系統類別圖和組件關係
- `sequence_diagram.md` - 系統操作流程序列圖
- `project_structure.md` - 專案結構說明
- `PRD.md` - 產品需求文檔

## 開發者

本專案由可樂旅遊資訊團隊開發維護，僅限內部使用。

## 聯繫方式

有關此專案的問題或建議，請聯繫資訊團隊。
