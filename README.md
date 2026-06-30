# Gemini Review Gate 工作流程

此文件整理 `$gemini-review` skill 的實際工作流程，供後續維護者或外部專案導入者理解 Codex 在修改程式、設定、批次流程、API 流程、資料處理流程或技術文件後，如何透過 Gemini/Antigravity backend 進行 Review Gate。此流程負責保存 review 狀態、產生實作計畫、維持同一個 reviewer session，並在 reviewer 明確核准後才寫入核准標記；它不負責取代人工需求確認，也不應用來跳過未處理的 review 意見。

本資料夾同時提供提示詞、專案內 `.codex/review/` 檔案範本，以及使用者環境 `%USERPROFILE%` 下需要部署的 `.codex`、`.agents`、hooks 範例檔。實際執行時，review script 會依專案狀態自動新增或更新部分檔案，Codex 仍需負責先寫好 `implementation-plan.md`，並在 reviewer 要求修改時持續修正與重跑審查。

## 1. 功能概要

| 功能 | 說明 |
|---|---|
| Review Gate 狀態保存 | 使用專案內的 `.codex/review/` 保存啟用狀態、實作計畫、review session、最後審查結果與核准標記。 |
| 實作計畫紀錄 | 每次 review 前都要更新 `.codex/review/implementation-plan.md`，說明目標、異動檔案、策略、驗證與風險。 |
| Gemini/Antigravity 審查 | 透過 `gemini_review.py` 讀取本機設定，選擇 `agy_cli` 或 `api` backend 執行審查。 |
| 同 session 追蹤 | 使用 `.codex/review/gemini-session.json` 保存 `agy_conversation_id` 或 `previous_interaction_id`，避免每輪 review 斷開上下文。 |
| 核准標記 | 每次 review 前先將 `.codex/review/approval.marker` 重設為 `[REVIEW_PENDING]`，只有明確通過後才寫入 `[REVIEW_APPROVED]`。 |

## 2. 使用情境

此流程適用於 Codex 實際修改專案內容的任務，例如：

| 任務類型 | 是否需要 Gemini Review Gate | 說明 |
|---|---:|---|
| 修改程式碼 | 是 | 包含 bug fix、重構、新增功能或批次流程調整。 |
| 修改設定檔 | 是 | 包含 `appsettings.json`、`NLog.config`、部署參數或 API 設定。 |
| 新增或修改技術文件 | 是 | 包含 wiki、README、維護文件與流程說明。 |
| 調整 API 或資料處理流程 | 是 | 包含查詢條件、匯入規則、統計邏輯與回寫流程。 |
| 單純回答問題 | 否 | 沒有修改檔案時不需要執行。 |

若使用者在同一則任務訊息明確加入：

```text
[SKIP_GEMINI_REVIEW]
```

本次任務可以跳過 Gemini Review Gate。

若使用者明確要求開新 review session，或在同一則任務訊息加入：

```text
[NEW_GEMINI_REVIEW_SESSION]
```

Codex 需把此字串寫入 `.codex/review/implementation-plan.md`，由 `gemini_review.py` 在 review 前清除目前 backend 對應的 session id。

## 3. 主要檔案與責任

| 檔案 | 建立者 | 責任 |
|---|---|---|
| `.codex/review/enabled` | script 或 Codex | 表示此專案啟用 Stop Hook review gate。 |
| `.codex/review/implementation-plan.md` | Codex | 紀錄本次任務目標、異動範圍、實作策略、驗證與風險。 |
| `.codex/review/gemini-session.json` | script | 保存 `agy_cli` 或 `api` backend 的 session id。 |
| `.codex/review/approval.marker` | Codex/script | review 前重設為 `[REVIEW_PENDING]`，核准後最後一行寫入 `[REVIEW_APPROVED]`。 |
| `.codex/review/last-review.md` | script | 保存最近一次 Gemini/Antigravity review 結果。 |
| `.codex/review/agy-review-prompt.md` | script | `agy_cli` 模式使用的 review prompt，script 會用絕對路徑要求 Antigravity 讀取。 |
| `.codex/review/external-review-consent.md` | Codex | 專案層級外送同意紀錄；存在時可視為允許 Gemini Review Gate 外送必要 context。 |

## 4. 初始化與自動新增

若專案尚未存在 `.codex/review/`，需先執行：

```powershell
python "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
```

實際自動新增內容會依 `gemini_review.py` 當下版本與 backend 設定而定，通常包含：

| 自動新增或更新項目 | 說明 |
|---|---|
| `.codex/review/` | Review Gate 狀態資料夾。 |
| `.codex/review/enabled` | 啟用 Stop Hook review gate。 |
| `.codex/review/gemini-session.json` | 第一次 review 後寫入 backend session 狀態。 |
| `.codex/review/last-review.md` | 每次 review 後更新最後審查結果。 |
| `.codex/review/agy-review-prompt.md` | `agy_cli` backend 執行時產生或更新。 |
| `.codex/review/approval.marker` | 每輪 review 前應回到 `[REVIEW_PENDING]`。 |

`implementation-plan.md` 不應空白依賴 script 補齊。Codex 在 review 前必須主動填寫，否則 reviewer 無法可靠判斷本次異動意圖。

## 5. Review 執行流程

1. 確認本次任務是否需要 Gemini Review Gate。
2. 若專案沒有 `.codex/review/`，執行 `gemini_review.py` 初始化。
3. 若需要外送 Gemini/Antigravity backend，且專案沒有 `.codex/review/external-review-consent.md`，先向使用者取得明確同意。
4. 修改程式、設定或文件。
5. 更新 `.codex/review/implementation-plan.md`。
6. 將 `.codex/review/approval.marker` 重設為 `[REVIEW_PENDING]`。
7. 執行 review script：

```powershell
python "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
```

8. 閱讀 `.codex/review/last-review.md` 或 script 輸出。
9. 若 reviewer 要求修改，完成修改、補驗證，並用同一個 session 重跑 review。
10. 只有 reviewer 明確核准、沒有 blocking issue，且 Codex 完成必要驗證後，才將 `.codex/review/approval.marker` 最後一行寫成 `[REVIEW_APPROVED]`。

完整流程樹：

```text
判斷任務是否需 review
  -> 初始化 .codex/review/
  -> 確認外送同意
  -> 完成實作或文件異動
  -> 更新 implementation-plan.md
  -> approval.marker = [REVIEW_PENDING]
  -> 執行 gemini_review.py
      -> 讀取 gemini-review.secrets.json
      -> 選擇 agy_cli 或 api backend
      -> 使用 gemini-session.json 延續同 session
      -> 產生 last-review.md
  -> 若有 blocking issue
      -> 修正
      -> 驗證
      -> 同 session 重跑 review
  -> 若明確 approved
      -> approval.marker 最後一行 = [REVIEW_APPROVED]
```

## 6. Backend 與 session 規則

`gemini_review.py` 會讀取：

```text
%USERPROFILE%\.codex\gemini-review.secrets.json
```

| Backend | session 欄位 | 說明 |
|---|---|---|
| `agy_cli` | `agy_conversation_id` | 使用 Antigravity CLI，並以 `agy --conversation` 延續同一個對話。 |
| `api` | `previous_interaction_id` | 使用 Gemini API，並延續前一次 interaction。 |

維護規則：

| 規則 | 說明 |
|---|---|
| 不刪除 `gemini-session.json` | 不可用刪除 session 的方式繞過前一次 reviewer 意見。 |
| reviewer 要求修改時維持同 session | 讓 reviewer 能追蹤上一輪問題是否已修正。 |
| 只有明確新 session 指令才重開 | 使用 `[NEW_GEMINI_REVIEW_SESSION]` 時，script 只清除目前 backend 對應欄位。 |

## 7. 提示詞說明

本資料夾的 `prompts/` 放的是可維護提示詞範本，實際用途如下：

| 檔案 | 用途 |
|---|---|
| `prompts/codex-implementation-plan-prompt.md` | 要求 Codex 產生或更新 `.codex/review/implementation-plan.md` 的提示詞。 |
| `prompts/gemini-review-request-prompt.md` | 給 Gemini/Antigravity reviewer 的審查提示詞範本，重點是找 blocking issue、風險與漏驗證。 |

使用方式：

1. 實作前或 review 前，可用 `codex-implementation-plan-prompt.md` 要求 Codex 補齊實作計畫。
2. 若需要人工檢查 review prompt，可參考 `gemini-review-request-prompt.md` 的審查重點。
3. 實際 `agy_cli` 模式通常由 script 自動產生 `.codex/review/agy-review-prompt.md`，不需要手動複製此範本。

## 8. 範本檔案說明

本資料夾的 `templates/` 放的是 `.codex/review/` 常見檔案內容範本：

| 檔案 | 對應目標 | 說明 |
|---|---|---|
| `templates/project-review/implementation-plan.md` | `.codex/review/implementation-plan.md` | 每次 review 前由 Codex 更新。 |
| `templates/project-review/external-review-consent.md` | `.codex/review/external-review-consent.md` | 使用者同意外送 review context 後建立。 |
| `templates/project-review/approval.marker` | `.codex/review/approval.marker` | review 前 pending、核准後 approved。 |
| `templates/project-review/gemini-session.json` | `.codex/review/gemini-session.json` | session 狀態示意，不建議手動重設。 |
| `templates/project-review/last-review.md` | `.codex/review/last-review.md` | review 結果格式示意，實際內容由 script 更新。 |
| `templates/project-review/enabled` | `.codex/review/enabled` | 啟用 gate 的空檔或標記檔。 |

## 9. 使用者環境建置

外部使用者導入此流程時，需要把 `environment-files/user-home/` 下的檔案放到自己的使用者家目錄。此資料夾用 `user-home` 表示 `%USERPROFILE%`，不要保留任何特定人員的本機路徑。

建議部署結果：

```text
%USERPROFILE%
  .codex
    AGENTS.md
    hooks.json
    gemini-review.secrets.json
    hooks
      stop_review_gate.py
    review-scripts
      gemini_review.py
  .agents
    skills
      gemini-review
        SKILL.md
```

本文件包提供的環境檔案：

| 文件包檔案 | 目標位置 | 說明 |
|---|---|---|
| `environment-files/user-home/codex/AGENTS.md` | `%USERPROFILE%\.codex\AGENTS.md` | Codex 使用者層級規則，定義 Gemini Review Gate 的觸發條件、外送同意與跳過指令。 |
| `environment-files/user-home/codex/hooks.example.json` | `%USERPROFILE%\.codex\hooks.json` | Codex hooks 設定範本，註冊 Stop hook 來檢查 review gate。 |
| `environment-files/user-home/codex/hooks/stop_review_gate.py` | `%USERPROFILE%\.codex\hooks\stop_review_gate.py` | Stop hook 實作；在 Codex 結束回合前檢查專案 `.codex/review/approval.marker`。 |
| `environment-files/user-home/codex/review-scripts/gemini_review.py` | `%USERPROFILE%\.codex\review-scripts\gemini_review.py` | 實際呼叫 Gemini/Antigravity backend 的 review script。 |
| `environment-files/user-home/codex/gemini-review.secrets.example.json` | `%USERPROFILE%\.codex\gemini-review.secrets.json` | backend 設定範本；複製後移除 `.example` 並填入使用者自己的設定。 |
| `environment-files/user-home/agents/skills/gemini-review/SKILL.md` | `%USERPROFILE%\.agents\skills\gemini-review\SKILL.md` | Codex skill 規則，讓 Codex 知道何時與如何執行 Gemini Review Gate。 |

`gemini-review.secrets.json` 設定鍵：

| 設定鍵 | 用途 |
|---|---|
| `mode` | backend 類型；常用 `agy_cli` 或 `api`。 |
| `model` | Gemini API backend 使用的模型名稱；`agy_cli` 模式可保留預設。 |
| `agy_project` | 需要指定 Antigravity project 時填寫；不需要時留空字串。 |
| `agy_add_dir` | 是否在 `agy_cli` 模式帶入 `--add-dir <project-root>`。 |
| `api_key` | `api` 模式使用；也可改用環境變數 `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`。 |

### 9.1 Hooks 設定

`hooks.json` 是讓 Review Gate 真正具備阻擋效果的使用者環境設定。`$gemini-review` skill 負責執行 review，而 Stop hook 會在 Codex 準備結束回合時檢查目前專案是否已通過 review。

| 檔案或狀態 | 說明 |
|---|---|
| `%USERPROFILE%\.codex\hooks.json` | 註冊 Codex `Stop` hook，指向 `stop_review_gate.py`。 |
| `%USERPROFILE%\.codex\hooks\stop_review_gate.py` | 檢查目前專案 `.codex/review/` 狀態。 |
| `.codex/review/enabled` | 專案 opt-in 標記；不存在時 hook 直接放行，避免一般問答被擋。 |
| `.codex/review/approval.marker` | 最後一行必須是 `[REVIEW_APPROVED]`，Stop hook 才會放行。 |
| `.codex/review/skip-once` | 單次跳過標記；只有使用者明確要求跳過時才可建立，hook 讀到後會刪除並放行一次。 |

`hooks.example.json` 內的 `command` 使用 `%USERPROFILE%` 作為可攜式範例：

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python %USERPROFILE%\\.codex\\hooks\\stop_review_gate.py",
            "timeout": 30,
            "statusMessage": "Checking Gemini review gate"
          }
        ]
      }
    ]
  }
}
```

若 Codex 執行環境沒有展開 `%USERPROFILE%`，請把 `command` 改成使用者自己的絕對路徑，例如 `python C:\Users\<user>\.codex\hooks\stop_review_gate.py`。對外文件不應填入特定人員帳號。


### 9.2 自動部署腳本

若使用者本機已安裝 Node.js，可直接執行部署腳本，將本文件包內的 Codex skill、review script、Stop hook 與設定範本複製到使用者環境。請在下載後的 repo 根目錄執行，不要切到 `%USERPROFILE%\.codex` 目錄，因為腳本會從 repo 內的 `environment-files/` 讀取來源檔案：

```powershell
node scripts/install-skill.js
```

`scripts/install-skill.js` 會處理以下目標位置：

| 來源 | 目標 | 覆蓋規則 |
|---|---|---|
| `environment-files/user-home/agents/skills/gemini-review/` | `%USERPROFILE%\.agents\skills\gemini-review\` | 直接同步 skill 檔案。 |
| `environment-files/user-home/codex/review-scripts/gemini_review.py` | `%USERPROFILE%\.codex\review-scripts\gemini_review.py` | 直接更新 review script。 |
| `environment-files/user-home/codex/hooks/stop_review_gate.py` | `%USERPROFILE%\.codex\hooks\stop_review_gate.py` | 直接更新 Stop hook。 |
| `environment-files/user-home/codex/hooks.example.json` | `%USERPROFILE%\.codex\hooks.json` | 目標不存在才建立，避免覆蓋既有 hooks。 |
| `environment-files/user-home/codex/gemini-review.secrets.example.json` | `%USERPROFILE%\.codex\gemini-review.secrets.json` | 目標不存在才建立，避免覆蓋金鑰設定。 |
| `environment-files/user-home/codex/AGENTS.md` | `%USERPROFILE%\.codex\AGENTS.md` | 目標不存在才建立，避免覆蓋既有 Codex 規則。 |

腳本不會自動填寫 API key，也不會覆蓋既有 `hooks.json`、`gemini-review.secrets.json` 或 `AGENTS.md`。若這些檔案已存在，請手動合併本文件包提供的 Gemini Review Gate 區塊。

若要手動部署，才需要依下列步驟把檔案複製到 `%USERPROFILE%\.codex` 與 `%USERPROFILE%\.agents`：

建置步驟：

1. 建立 `%USERPROFILE%\.codex\hooks\`、`%USERPROFILE%\.codex\review-scripts\` 與 `%USERPROFILE%\.agents\skills\gemini-review\`。
2. 複製 `AGENTS.md` 到 `%USERPROFILE%\.codex\AGENTS.md`；若使用者已有既有規則，請合併 Gemini Review Gate 章節，不要直接覆蓋。
3. 複製 `hooks.example.json` 為 `%USERPROFILE%\.codex\hooks.json`，並確認 `command` 可在該使用者環境執行。
4. 複製 `stop_review_gate.py` 到 `%USERPROFILE%\.codex\hooks\stop_review_gate.py`。
5. 複製 `gemini_review.py` 到 `%USERPROFILE%\.codex\review-scripts\gemini_review.py`。
6. 複製 `gemini-review.secrets.example.json` 為 `%USERPROFILE%\.codex\gemini-review.secrets.json`。
7. 依使用 backend 修改 `gemini-review.secrets.json`；若使用 `api` 模式，不要把 API key 提交到任何專案版本庫。
8. 複製 `SKILL.md` 到 `%USERPROFILE%\.agents\skills\gemini-review\SKILL.md`。
9. 在要啟用 Review Gate 的專案中，依本文件的 `.codex/review/` 流程初始化專案狀態。

可用以下 PowerShell 檢查部署後的檔案是否存在：

```powershell
Test-Path "$env:USERPROFILE\.codex\AGENTS.md"
Test-Path "$env:USERPROFILE\.codex\hooks.json"
Test-Path "$env:USERPROFILE\.codex\hooks\stop_review_gate.py"
Test-Path "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
Test-Path "$env:USERPROFILE\.codex\gemini-review.secrets.json"
Test-Path "$env:USERPROFILE\.agents\skills\gemini-review\SKILL.md"
```

注意事項：

- `gemini-review.secrets.json` 可能包含 API key 或 backend project 設定，只能存在於使用者自己的 `%USERPROFILE%\.codex`。
- 文件包只提供 `gemini-review.secrets.example.json`，不應包含任何真實金鑰。
- `AGENTS.md` 可能已有使用者自己的長期規則，導入時應合併 Gemini Review Gate 區塊，避免覆蓋既有工作習慣或安全規則。
- `environment-files/user-home/agents/skills/gemini-review/SKILL.md` 已使用 `%USERPROFILE%`，可交給外部使用者，不含個人路徑。

## 10. 使用範例

以下範例以外部使用者自己的 Windows 使用者環境為前提，命令中的 `$env:USERPROFILE` 代表目前登入者的家目錄。若使用 cmd、Git Bash 或其他 shell，需要自行轉換環境變數語法。

### 10.1 第一次部署到使用者環境

此範例適合把本文件包交給新使用者時使用。目標是先把 `AGENTS.md`、`SKILL.md`、`gemini_review.py` 與 secrets 範本放到正確位置。

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.codex\hooks"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.codex\review-scripts"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills\gemini-review"

Copy-Item -Path ".\environment-files\user-home\codex\AGENTS.md" -Destination "$env:USERPROFILE\.codex\AGENTS.md"
Copy-Item -Path ".\environment-files\user-home\codex\hooks.example.json" -Destination "$env:USERPROFILE\.codex\hooks.json"
Copy-Item -Path ".\environment-files\user-home\codex\hooks\stop_review_gate.py" -Destination "$env:USERPROFILE\.codex\hooks\stop_review_gate.py"
Copy-Item -Path ".\environment-files\user-home\codex\review-scripts\gemini_review.py" -Destination "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
Copy-Item -Path ".\environment-files\user-home\codex\gemini-review.secrets.example.json" -Destination "$env:USERPROFILE\.codex\gemini-review.secrets.json"
Copy-Item -Path ".\environment-files\user-home\agents\skills\gemini-review\SKILL.md" -Destination "$env:USERPROFILE\.agents\skills\gemini-review\SKILL.md"
```

若使用者已經有 `%USERPROFILE%\.codex\AGENTS.md`，不要直接覆蓋。應手動把 `environment-files/user-home/codex/AGENTS.md` 內的 Gemini Review Gate 章節合併進既有檔案。


### 10.2 使用部署腳本安裝

若只要快速安裝到目前使用者環境，請先切換到本 repo 根目錄，再執行：

```powershell
node scripts/install-skill.js
```

執行後仍需檢查 `%USERPROFILE%\.codex\gemini-review.secrets.json`，確認 `mode`、`api_key`、`agy_project` 或其他 backend 設定符合本機環境。若 `%USERPROFILE%\.codex\hooks.json` 已存在，部署腳本不會覆蓋，需自行確認是否已包含 Stop hook 設定。

### 10.3 使用 Antigravity CLI 作為 reviewer

`agy_cli` 適合已安裝並登入 Antigravity CLI 的環境。設定檔可維持不填 API key：

```json
{
  "mode": "agy_cli",
  "model": "gemini-3.5-flash",
  "agy_project": "",
  "agy_add_dir": true,
  "api_key": ""
}
```

若 Antigravity CLI 需要指定 project，可填入 `agy_project`：

```json
{
  "mode": "agy_cli",
  "model": "gemini-3.5-flash",
  "agy_project": "my-project",
  "agy_add_dir": true,
  "api_key": ""
}
```

若本機 CLI 不支援 `--add-dir`，將 `agy_add_dir` 改成 `false`。

### 10.4 使用 Gemini API 作為 reviewer

`api` 適合不透過 Antigravity CLI、直接呼叫 Gemini API 的環境。API key 可放在 `%USERPROFILE%\.codex\gemini-review.secrets.json`：

```json
{
  "mode": "api",
  "model": "gemini-3.5-flash",
  "agy_project": "",
  "agy_add_dir": true,
  "api_key": "YOUR_API_KEY"
}
```

也可以不要把 key 寫進檔案，改用環境變數：

```powershell
$env:GEMINI_API_KEY = "YOUR_API_KEY"
python "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
```

維護建議是優先使用環境變數或安全的 secrets 管理方式，不要把真實 API key 放進專案資料夾或文件包。

### 10.5 專案第一次啟用 Review Gate

在要啟用 Review Gate 的專案根目錄執行：

```powershell
python "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
```

初始化後，專案內通常會出現：

```text
.codex
  review
    enabled
    approval.marker
    implementation-plan.md
    last-review.md
    gemini-session.json
```

接著在實作完成後更新 `.codex/review/implementation-plan.md`，再重新執行 review script。若專案沒有 `.codex/review/external-review-consent.md`，Codex 必須先取得使用者明確同意，才可送到 Gemini/Antigravity backend。

### 10.6 一次文件修改任務的 review 流程

例如使用者要求「幫我新增 README 的部署說明」，Codex 應維護以下狀態：

```text
修改 README.md
  -> 更新 .codex/review/implementation-plan.md
  -> .codex/review/approval.marker = [REVIEW_PENDING]
  -> 執行 gemini_review.py
  -> 若 reviewer 要求修改
      -> 修正 README.md
      -> 更新 Verification / Risks
      -> 同 session 再跑 gemini_review.py
  -> reviewer 明確 Approved
      -> approval.marker 最後一行寫入 [REVIEW_APPROVED]
```

`implementation-plan.md` 可參考：

```md
# Implementation Plan

## Task Goal
新增 README 部署說明，讓外部維護者知道如何安裝 Gemini Review Gate。

## Files To Change
| File | Purpose |
|---|---|
| `README.md` | 補充環境建置、設定檔與 review 流程。 |

## Implementation Strategy
保留既有章節，新增部署範例與注意事項。

## Verification
檢查 Markdown 章節編號、路徑是否使用 `%USERPROFILE%`，並確認沒有真實 API key。

## Risks
若外部使用者已有 `AGENTS.md`，直接覆蓋可能造成既有規則遺失。
```

### 10.7 reviewer 要求修改時

若 `.codex/review/last-review.md` 顯示 `Not Approved`，不要寫入 `[REVIEW_APPROVED]`。應依意見修正後，用同一個 session 再跑：

```powershell
python "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
```

不可刪除 `.codex/review/gemini-session.json` 來重開上下文。只有使用者明確要求新 session 時，才使用 `[NEW_GEMINI_REVIEW_SESSION]`。

### 10.8 跳過本次 Review Gate

若使用者明確在同一則任務訊息加入：

```text
[SKIP_GEMINI_REVIEW]
```

本次任務可跳過 Gemini Review Gate。此指令只適用於該次任務，不代表永久停用 Review Gate。

### 10.9 開新的 review session

若 reviewer session 已經不適合延續，必須由使用者明確要求，例如：

```text
請本次開新的 Gemini Review session [NEW_GEMINI_REVIEW_SESSION]
```

Codex 需把 `[NEW_GEMINI_REVIEW_SESSION]` 寫入 `.codex/review/implementation-plan.md`。`gemini_review.py` 會依目前 backend 只清除對應 session 欄位，不會刪除整個 `gemini-session.json`。

## 11. 外送同意規則

Gemini Review Gate 可能會把以下內容送到 Gemini/Antigravity backend：

| 可能外送內容 | 說明 |
|---|---|
| `.codex/review/implementation-plan.md` | 本次任務目標、異動檔案、策略、驗證與風險。 |
| workspace diff/context | reviewer 需要理解的檔案差異與相關上下文。 |
| generated review prompt | script 產生的 review 指令。 |

若專案不存在 `.codex/review/external-review-consent.md`，Codex 必須先向使用者說明外送範圍並取得明確同意。若使用者同意，Codex 可依 `templates/project-review/external-review-consent.md` 建立專案層級同意檔。

撤回方式：

```text
刪除 .codex/review/external-review-consent.md
或修改該檔
或明確告知 Codex 撤回同意
```

## 12. 錯誤處理與例外情境

| 情境 | 處理方式 |
|---|---|
| `.codex/review/` 不存在 | 先執行 `gemini_review.py` 初始化。 |
| Stop hook 沒有生效 | 確認 `%USERPROFILE%\.codex\hooks.json` 存在，且 `command` 指向可執行的 `stop_review_gate.py`。 |
| Stop hook 擋住結束 | 依訊息檢查 `implementation-plan.md`、`gemini-session.json` 與 `approval.marker`，完成 review 後再結束。 |
| 沒有外送同意檔 | 先取得使用者明確同意，再建立 `external-review-consent.md`。 |
| reviewer 回報 blocking issue | 修正問題、補驗證、同 session 重跑 review。 |
| reviewer 沒有明確核准 | 不可寫入 `[REVIEW_APPROVED]`。 |
| `gemini-session.json` 損毀 | 不要直接刪除繞過；先確認是否需保留原 session，必要時請使用者明確要求新 session。 |
| backend CLI 不支援 `--add-dir` | 在 `gemini-review.secrets.json` 設定 `agy_add_dir` 為 `false`。 |
| 需要指定 Antigravity project | 在 `gemini-review.secrets.json` 設定 `agy_project` 或 `project`。 |

## 13. 路徑與檔案

| 路徑 | 用途 |
|---|---|
| `./README.md` | 本工作流程主文件。 |
| `./scripts/install-skill.js` | 本機部署腳本，可安裝 skill、review script、Stop hook 與設定範本。 |
| `./prompts/` | Codex 與 Gemini reviewer 提示詞範本。 |
| `./templates/` | `.codex/review/` 目標檔案範本。 |
| `./environment-files/user-home/codex/` | 使用者 `%USERPROFILE%\.codex` 需要部署的 hooks、script 與設定範本。 |
| `./environment-files/user-home/agents/` | 使用者 `%USERPROFILE%\.agents` 需要部署的 skill 範本。 |
| `.codex/review/` | 專案 review gate 狀態資料夾。 |
| `%USERPROFILE%\.codex\AGENTS.md` | Codex 使用者層級規則，包含 Gemini Review Gate 觸發與外送同意流程。 |
| `%USERPROFILE%\.codex\hooks.json` | Codex Stop hook 設定，負責呼叫 `stop_review_gate.py`。 |
| `%USERPROFILE%\.codex\hooks\stop_review_gate.py` | Stop hook 實作，負責在結束前檢查 review 是否通過。 |
| `%USERPROFILE%\.agents\skills\gemini-review\SKILL.md` | `$gemini-review` skill 規則。 |
| `%USERPROFILE%\.codex\review-scripts\gemini_review.py` | 實際執行 review backend 的 script。 |
| `%USERPROFILE%\.codex\gemini-review.secrets.json` | backend 選擇與 CLI/API 連線設定。 |

## 14. 維護風險與建議

- 不要把舊的 `[REVIEW_APPROVED]` 留給下一次任務使用；每次 review 前都要重設為 `[REVIEW_PENDING]`。
- 不要用刪除 `gemini-session.json` 的方式逃避 reviewer 上一輪意見；只有使用者明確要求新 session 才可重開。
- `implementation-plan.md` 要跟實際異動同步，否則 reviewer 會審錯範圍。
- 外送同意只適用於 Gemini Review Gate，不代表其他任務可以任意外送專案資料。
- 若 review script、Stop hook 或 backend 設定有更新，需同步檢查本文件與 `prompts/`、`templates/`、`environment-files/` 是否仍符合實際行為。
- 對外提供文件包前，應使用 `rg -uu "C:\\Users\\|<local-user-name>" .` 檢查是否殘留個人路徑或本機識別資訊。











