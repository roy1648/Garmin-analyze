# 專案簡介：Garmin TCX AI-ready Converter

## 1. 專案目標

建立一個小型、個人使用的 Python 工具，將 Garmin Connect 匯出的
TCX 檔案轉換成適合 AI 後續分析跑步訓練資料的格式。

第一版必須專注在穩定的資料轉換，而不是建立完整的 AI 教練平台。

## 2. 背景

使用者會從 Garmin Connect 手動匯出 TCX 檔案。這些檔案包含訓練資料，
例如：

- 活動類型
- 開始時間與單圈時間
- 距離
- 心率
- 配速與速度
- 海拔
- GPS 座標
- Garmin 擴充欄位，例如可用時的跑步步頻、速度與功率

TCX 是以 XML 為基礎的格式，適合作為匯出格式，但不適合讓 AI 直接讀取。
本專案應該把 TCX 轉換成更容易讓 ChatGPT、Claude、NotebookLM，以及
未來本機分析工具讀取的格式。

## 3. 主要使用者

主要使用者是一位獨立開發者，正在建立個人工作流程。

因此本專案應該優先考量：

- 簡單的結構
- 低維護成本
- 清楚的檔案與契約
- 容易與 Codex Agent 協作
- 以本機資料處理為優先
- 避免過早設計成平台

## 4. MVP 範圍

MVP 支援：

- Garmin Connect 匯出的 `.tcx` 檔案
- 只支援跑步活動
- 單一檔案轉換
- 以資料夾為單位的批次轉換
- 轉換成 AI 可讀與機器可讀的輸出
- 可設定的 GPS 隱私處理方式

MVP 不包含：

- Web UI
- 資料庫儲存
- Garmin 帳號登入
- Garmin API 整合
- 雲端同步
- 多使用者支援
- 完整 AI 教練或醫療等級訓練建議

## 5. AI-ready 輸出策略

主要的 AI-ready 輸出應結合：

- Markdown，方便人類與 AI 閱讀
- JSON，方便結構化、驗證與未來程式化工作流程使用

CSV 仍然適合試算表形式的分析，但不是主要的 AI 交付格式。

## 6. 隱私立場

Garmin 活動資料可能包含敏感的健康與位置資訊。

對 MVP 而言：

- 原始 TCX 檔案絕不能被修改。
- 心率、配速與距離會保留在輸出中。
- GPS 座標預設會保留，因為選定的預設政策是 `keep`。
- 工具仍必須支援 GPS policy 參數，讓使用者能選擇更安全的輸出模式。
- AI-ready 輸出必須明確記錄使用了哪一種 GPS policy。

支援的 GPS policies：

- `keep`：保留所有 GPS 座標。
- `remove`：從 AI-ready 輸出移除所有 GPS 座標。
- `redact_start_end`：遮蔽路線前 300 公尺與後 300 公尺的
  GPS 座標；距離資料不足時，改用前 10% 與後 10% trackpoints。

## 7. 未來路線圖

第一版不應實作資料庫或 API 整合，但架構應保留未來擴充空間。

未來候選方向：

- 小型個人 SQLite 活動資料庫。
- GarminDB: https://github.com/tcgoetz/GarminDB
- python-garminconnect: https://github.com/cyberjunky/python-garminconnect

這些只是研究與擴充路徑。它們不能影響 MVP 的要求：手動匯出的 TCX 檔案
仍然必須是第一個支援的輸入來源。
