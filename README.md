# Garmin TCX AI

個人 Garmin Connect 資料 ETL 與分析專案的最小 Python scaffold。

目前範圍只包含專案結構、套件初始化與 import smoke test。尚未實作
TCX parser、轉換流程、Garmin API、資料庫、Web UI 或 AI API 整合。

## 專案結構

```text
src/garmin_tcx_ai/      # Python package
scripts/convert_tcx.py  # 未來轉換指令的 placeholder
tests/                  # pytest 測試
tests/fixtures/         # 已提交的最小清理測試資料
data/samples/           # 本機範例資料，避免依賴私人資料
```

## 開發

建議使用 Python 3.12+。

```powershell
python -m pytest
```
