# Workspouse

LLM 驅動的 Agent 天生具有高度不確定性，同一段 Prompt 在不同模型、不同參數下可能產生截然不同的輸出。**Workspouse** 的核心理念是：打造一個**穩定、可追蹤、可評估**的 AI Agent 框架。透過 YAML Persona 設定檔將行為參數化，結合 Pydantic Schema 驗證與 LangSmith 可觀測性，讓每一次對話都能被量化衡量與迭代改進。

## Features

- 🎭 **Persona 系統** — 以 Pydantic Schema 驅動的 YAML 人格設定檔，支援動態切換
- 🌐 **雙接口** — CLI 互動模式 + FastAPI
- 📡 **串流回應** — CLI 模式下逐字串流輸出，即時體驗
- 🔍 **LangSmith 追蹤** — 內建可觀測性，完整記錄每一輪對話與工具呼叫
- 🧩 **OpenAI 相容** — 支援任何 OpenAI API 相容的推論端點（Ollama、vLLM、ngrok tunnel 等）

## Installation

### Prerequisites

- Python 3.10+
- 一個 OpenAI API 相容的推論端點（本地或遠端）

### Environment Variables

在專案根目錄建立 `.env` 檔案：

```env
# LLM Endpoint
BASE_URL=https://your-endpoint.example.com/v1
API_KEY=YOUR_API_KEY
MODEL=your-model-name

# LangSmith Tracking (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ai-wife-chatbot
LANGCHAIN_API_KEY=YOUR_LANGSMITH_API_KEY
```

## Quick Start

### CLI Mode（互動式對話）

```bash
python src/main.py
```

啟動後會顯示當前 Persona 資訊與問候語。可使用以下指令：

| 指令      | 說明                   |
| --------- | ---------------------- |
| `/list`   | 列出所有可用的 Persona |
| `/switch` | 切換到其他 Persona     |
| `/reload` | 重新載入所有 Persona   |
| `/exit`   | 結束對話               |

## Persona System

每個 Persona 由一個 YAML 檔案定義，包含三個區塊：

### Schema

| 區塊         | 欄位              | 型別           | 說明                       |
| ------------ | ----------------- | -------------- | -------------------------- |
| **metadata** | `id`              | `str`          | 唯一識別碼（如 `counter`） |
|              | `version`         | `str`          | 語意化版本號               |
|              | `target_model`    | `str`          | 對應的 LLM 模型名稱        |
|              | `author`          | `str`          | 作者                       |
|              | `description`     | `str`          | 人格簡述                   |
|              | `tags`            | `List[str]`    | 標籤分類                   |
| **prompts**  | `system`          | `str`          | 系統提示詞（核心人格定義） |
|              | `greeting`        | `str`          | 對話開始時的問候語         |
|              | `uncensored_mode` | `bool`         | 是否啟用非審查模式         |
| **config**   | `temperature`     | `float [0, 2]` | 生成溫度                   |
|              | `max_tokens`      | `int`          | 最大生成長度               |
|              | `top_p`           | `float`        | Top-P 取樣                 |
|              | `stop`            | `List[str]?`   | 停止序列                   |
