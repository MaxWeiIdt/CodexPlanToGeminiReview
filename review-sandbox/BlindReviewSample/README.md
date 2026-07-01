# BlindReviewSample

`BlindReviewSample` 是 Gemini Review Gate 能力測試用的 C# sandbox 專案。它以去識別化的資料模型模擬正式專案中的同步規則，讓 reviewer 在隔離環境中辨識錯誤或可疑邏輯。

## 檔案說明

| 檔案 | 用途 |
| --- | --- |
| `BlindSyncService.cs` | 測試用同步邏輯，包含 lookup、座標 fallback、關聯鍵與一般更新分支。 |
| `SoilRecord.cs` | 測試用來源資料模型。 |
| `CollectioRecord.cs` | 測試用關聯資料模型。 |
| `ResultFeature.cs` | 測試用輸出 feature 模型。 |
| `BlindReviewSample.csproj` | 最小化 C# 專案檔，方便語法與 build 檢查。 |

## 最後保留狀態

目前 `BlindSyncService.BuildGeneralUpdate` 保留 `land_process_log` 寫入一般更新分支的可疑行為。這不是正式建議寫法，而是用來說明測試曾聚焦在「地籍專屬欄位是否不應出現在 general update」這類能力邊界。

若未來要新增測試案例，建議每一輪都同步保存：

- `.codex/review/implementation-plan.md`
- `.codex/review/last-review.md`
- 該輪 Git diff 或測試檔副本
- reviewer session metadata
