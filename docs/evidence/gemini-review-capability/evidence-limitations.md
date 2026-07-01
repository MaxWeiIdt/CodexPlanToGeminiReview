# Evidence Limitations

本次 Gemini Review Gate 能力測試是在其他專案進行後，事後整理成公開報告。測試期間未逐輪保存完整 evidence，因此本報告需以下列限制解讀。

## 已保留內容

| 類型 | 路徑 | 說明 |
| --- | --- | --- |
| 回顧式報告 | `docs/gemini-review-capability-report.md` | 根據測試過程觀察整理。 |
| Sandbox 原始碼 | `review-sandbox/BlindReviewSample/` | 保留最後測試狀態，用於說明測試設計。 |
| 本限制說明 | `docs/evidence/gemini-review-capability/evidence-limitations.md` | 說明證據保存缺口。 |

## 未保存內容

| 未保存項目 | 影響 |
| --- | --- |
| 每輪 `implementation-plan.md` | 無法完整判斷每輪 plan 是否提示可疑欄位。 |
| 每輪 `last-review.md` | 無法逐字驗證 reviewer 每輪回覆。 |
| 每輪 Git diff | 無法完整重播每次負向測試變更。 |
| 每輪 session id 與原始 prompt | 無法完整追溯同 session 中的上下文收斂。 |

## 解讀方式

此報告可作為 `Gemini Review Gate` 能力觀察與測試方法紀錄，但不應被解讀為完整可重播的科學實驗紀錄。若未來要做正式 benchmark，應在每輪測試後即時保存 plan、diff、last-review 與 session metadata。
