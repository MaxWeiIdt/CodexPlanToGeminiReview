# Codex Implementation Plan Prompt

請依目前任務與實際檔案異動，更新 `.codex/review/implementation-plan.md`。

必須使用以下章節，並以繁體中文撰寫：

```md
# Implementation Plan

## Task Goal
說明本次任務要解決什麼問題，包含使用者要求與預期成果。

## Files To Change
列出已修改或預計修改的檔案，並簡述每個檔案的責任。

## Implementation Strategy
說明主要實作方式、文件整理方式、設定調整方式或流程變更方式。

## Verification
列出已執行或預計執行的檢查，例如測試、lint、人工閱讀、文件連結確認、review script。

## Risks
列出本次異動可能影響的行為、資料格式、外部相依、部署或維護風險。
```

維護要求：

- 不要只寫檔名，需說明為什麼改這些檔案。
- 若使用者要求 `[NEW_GEMINI_REVIEW_SESSION]`，必須把該字串保留在 `implementation-plan.md`。
- 若本次任務只改文件，也要說明文件用途、資料來源與維護風險。
- 若尚未執行驗證，需明確寫出原因與預計驗證方式。
