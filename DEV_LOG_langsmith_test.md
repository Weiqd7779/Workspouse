# Development Log: feat/langsmith-test

### 🎯 任務摘要

建立整合測試腳本 `tests/test_langsmith_monitoring.py`，用於驗證 LLM 代理（Agent）在多輪對話與工具呼叫過程中的追蹤與監控能力，並確保能正確將 Persona 設定（YAML）注入到模型執行中。

---

### 🛠️ 詳細改動清單 (Technical Breakdown)

1.  **環境自動化配置 (Tracing Config)**：
    - 整合 `langsmith` 與 `dotenv`，自動生成唯一的 `LANGCHAIN_PROJECT` ID。
    - 強制啟用 `LANGCHAIN_TRACING_V2` 以確保每一筆呼叫都能正確傳輸至 LangSmith 儀表板。

2.  **基於 Schema 的 Persona 驅動架構**：
    - **Fail-fast 驗證**：在讀取 `personas/counter.yaml` 時，透過 `Persona.model_validate` 進行 Pydantic 架構驗證，防止語法錯誤的配置進入執行階段。
    - **屬性注入**：動態地將 `temperature`, `max_tokens`, `stop` 等推論參數從 YAML 傳遞至 `ChatOpenAI` 實例。

3.  **核心代理模擬邏輯 (`simulate_agent_run`)**：
    - **Message Stack 管理**：實施「系統提示詞優先」原則，將 Persona 的 System Message 始終固定在 `inputs` 的首位。
    - **工具執行追蹤**：使用 `@traceable` 裝飾器定義為 `chain` 類型，清楚記錄 Agent 的思考過程、工具呼叫及其結果的合成回覆。

4.  **壓力測試 (Scenarios)**：
    - **Scenario 1**：5 輪對話壓力測試，包含 3 個連續工具呼叫（天氣、計算、設定）。
    - **Scenario 2 & 3**：單輪對話與單一工具調用的基礎功能驗證。
    - **Scenario 4**：刻意拋出異常（User ID 999），測試系統的錯誤捕捉與防禦性邏輯。
    - **Scenario 5**：模擬平行/多工具請求的處理路徑。

---

### ⚠️ 潛在影響/注意事項

- **Git 追蹤風險**：目前的 `tests/` 與 `personas/` 在 `.gitignore` 中是被排除的。本次已透過 `git add -f` 強制追蹤該測試檔案。
- **API 消耗**：執行此腳本會產生多次 LLM API 呼叫。
