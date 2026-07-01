# Review Sandbox

此資料夾保存 Gemini Review Gate 能力測試使用的隔離式 sandbox。這些檔案不是正式產品程式，也不代表建議的業務實作方式。

## 目的

| 項目 | 說明 |
| --- | --- |
| 隔離測試 | 避免把負向測試案例直接放進正式專案。 |
| 能力觀察 | 觀察 reviewer 是否能辨識主鍵、關聯鍵、fallback、地籍欄位分支等規則錯誤。 |
| 可讀範例 | 讓 GitHub 讀者理解測試設計，而不是重播完整 review 歷程。 |

## 注意事項

- `BlindReviewSample/` 保留最後測試狀態，其中可能包含刻意保留的可疑邏輯。
- 本資料夾不包含逐輪 review transcript。
- `bin/`、`obj/` 等 build 產物不應提交到 GitHub。
