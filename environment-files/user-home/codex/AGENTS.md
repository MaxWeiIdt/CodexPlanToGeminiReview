# Gemini Review Gate Instructions

本檔案是使用者層級的 Codex `AGENTS.md` 範本，建議放在：

```text
%USERPROFILE%\.codex\AGENTS.md
```

若專案已經有自己的 `AGENTS.md`，請確認專案規則與本檔案不衝突；若有衝突，通常以專案層級規則為優先。

## Gemini Review Gate

當使用者要求修改程式、重構、調整設定、撰寫或修改技術文件時，必須遵守以下流程。

### 觸發條件

若任務包含以下任一情境，必須執行 Gemini Review Gate：

- 修改程式碼。
- 重構既有邏輯。
- 新增或調整設定檔。
- 新增或修改技術文件。
- 調整批次流程、匯入流程、API 流程或資料處理流程。

若只是單純回答問題、解釋程式、查詢概念，且沒有修改檔案，不需要執行。

### 執行流程

1. 若目前專案尚未存在 `.codex/review/`，先執行以下命令初始化：

   ```powershell
   python "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
   ```

2. 每次 review 前必須更新 `.codex/review/implementation-plan.md`，至少包含：

   ```md
   # Implementation Plan

   ## Task Goal
   Describe what this task is trying to solve.

   ## Files To Change
   List the files planned or already changed.

   ## Implementation Strategy
   Describe the main implementation choices and tradeoffs.

   ## Verification
   List tests, checks, or manual validation performed or planned.

   ## Risks
   List risks to existing behavior, data formats, integrations, or deployment.
   ```

3. 每次 review 前必須將 `.codex/review/approval.marker` 重設為：

   ```text
   [REVIEW_PENDING]
   ```

4. 執行 Gemini Review Gate：

   ```powershell
   python "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
   ```

5. 若 reviewer 回報 blocking issue、required changes 或不確定，Codex 必須修正後用同一個 review session 重新送審。

6. 只有 reviewer 明確核准、沒有 blocking issue，且 Codex 已完成必要修正與合理驗證後，才可將 `.codex/review/approval.marker` 最後一行寫為：

   ```text
   [REVIEW_APPROVED]
   ```

## Gemini Review Gate External Consent

為了避免每次執行 Gemini Review Gate 都重複詢問是否同意外送 review context，採用「專案層級同意」規則。

1. 若目前專案不存在 `.codex/review/external-review-consent.md`，且 Gemini Review Gate 需要透過 Gemini/Antigravity backend 審查，Codex 必須先向使用者說明會傳送 workspace plan/diff、review prompt 或相關檔案摘要到外部 backend，並取得明確同意。
2. 若使用者明確同意此專案後續 Gemini Review Gate 可外送 plan/diff，Codex 應自動建立 `.codex/review/external-review-consent.md`。
3. 若目前專案已存在 `.codex/review/external-review-consent.md`，Codex 可視為此專案已同意 Gemini/Antigravity Review Gate 外送必要 review context，不需要每次重複詢問。
4. 同意範圍僅限 Gemini Review Gate，不代表允許其他任務任意外送專案資料。
5. 若使用者刪除或修改 `.codex/review/external-review-consent.md`，或明確要求撤回同意，Codex 必須停止沿用該專案同意，下一次執行 Gemini Review Gate 前需重新詢問。

建議由 Codex 建立的 `.codex/review/external-review-consent.md` 格式：

```md
# External Review Consent

This project allows Codex to run Gemini Review Gate through the configured Gemini/Antigravity backend.

Scope:

- May send `.codex/review/implementation-plan.md`
- May send generated review prompt and relevant workspace diff/context
- Applies only to this project
- Applies only to Gemini Review Gate

Revocation:

- Delete this file, edit this file, or tell Codex to revoke consent.

Approved by user on: {yyyy-MM-dd}
```

## Gemini Review Gate Skip Command

若使用者在同一則任務訊息中明確包含以下字串，則本次任務可以跳過 Gemini Review Gate：

```text
[SKIP_GEMINI_REVIEW]
```

## Gemini Review Gate New Session Command

若使用者在同一則任務訊息中明確包含以下字串，表示本次 Gemini Review Gate 要開新的 review session：

```text
[NEW_GEMINI_REVIEW_SESSION]
```

執行規則：

1. Codex 應將 `[NEW_GEMINI_REVIEW_SESSION]` 寫入 `.codex/review/implementation-plan.md`。
2. `gemini_review.py` 會在 review 前依目前 backend 清除對應 session id：
   - `agy_cli`：清除 `.codex/review/gemini-session.json` 的 `agy_conversation_id`。
   - `api`：清除 `.codex/review/gemini-session.json` 的 `previous_interaction_id`。
3. 不要刪除整個 `gemini-session.json`，只重開目前 backend 的 session。
4. 只有使用者明確提出 `[NEW_GEMINI_REVIEW_SESSION]` 或要求開新 Gemini Review session 時才使用。
