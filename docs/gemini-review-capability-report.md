# Gemini Review Gate 能力邊界測試報告

本文件整理 `HdareSoilCadastral` 專案中，針對 `Gemini Review Gate` 所進行的一系列盲測、負向測試與修正後再審驗證觀察。本報告是根據測試過程中的人工觀察與目前仍保留的 sandbox 狀態整理，屬於回顧式實測報告，並非逐輪完整審查紀錄。

測試重點不是驗證正式業務邏輯是否正確，而是觀察 reviewer 是否能在不同提示強度、不同錯誤粒度下，主動指出與現有程式規則不一致的內容。本次測試皆使用隔離式 sandbox 專案 `review-sandbox/BlindReviewSample/` 或測試文件進行，不直接污染正式批次流程。正式主專案與正式 wiki 未隨本 repo 附上；本 repo 僅保留去識別化後的測試觀察、sandbox 範例與證據保存狀態說明。

## 1. 測試目的

| 項目 | 說明 |
| --- | --- |
| 核心目標 | 驗證 `Gemini Review Gate` 是否能主動辨識與主專案規則不一致的程式或文件內容。 |
| 次要目標 | 觀察 reviewer 對明顯錯誤、隱晦邏輯錯誤、部分欄位更新錯誤與地籍專屬欄位誤用的敏感度。 |
| 驗證方式 | 建立隔離式測試檔案或獨立 sandbox 專案，分多輪送審，觀察是否被阻擋以及阻擋理由是否合理。 |
| 不在範圍 | 不驗證正式生產程式碼是否需修改，也不把 sandbox 結果當作正式重構建議。 |

## 2. 測試環境與方法

| 項目 | 說明 |
| --- | --- |
| Review Backend | `agy_cli` |
| 主要測試載體 | `review-sandbox/BlindReviewSample/BlindSyncService.cs` |
| 正式規則基準 | `sample_soi_globalid`、`parentrowid -> uniquerowid`、座標 fallback 順序、地籍重算分類規則、一般更新不得碰 geometry/地籍處理欄位 |
| 驗證方式 | 每輪變更後執行 sandbox build，再跑 `Gemini Review Gate`。目前 repo 不保留 build 產物。 |
| session 策略 | 同時觀察新 session 純盲測與同 session 修正後是否收斂。 |

## 3. 證據保存狀態

本次測試為事後整理的回顧式報告，測試期間未逐輪保存 `round-01`、`round-02` 等審查快照。因此本報告不宣稱可完整重播每一輪 Gemini Review 對話，也不把目前 `.codex/review/last-review.md` 視為本次能力測試的完整證據。

目前可保存的證據包含：

| 類型 | 路徑 | 說明 |
| --- | --- | --- |
| 測試回顧報告 | `docs/gemini-review-capability-report.md` | 根據測試過程觀察與目前保留的 sandbox 狀態整理。 |
| 證據限制說明 | `docs/evidence/gemini-review-capability/evidence-limitations.md` | 明確列出未保存項目與對報告可信度的影響。 |
| Sandbox 程式 | `review-sandbox/BlindReviewSample/` | 保留最後測試狀態，用於說明測試設計與 reviewer 能力邊界。 |

未保存內容與影響：

| 未保存項目 | 影響 |
| --- | --- |
| 每輪 `implementation-plan.md` | 無法完整重建每輪提示強度與 plan 是否提示可疑欄位。 |
| 每輪 `last-review.md` | 無法逐字驗證 reviewer 每輪回覆。 |
| 每輪 Git diff | 無法完整重播所有負向測試變更。 |
| 每輪 session id 與原始 prompt | 無法完整追溯 reviewer 在同 session 中的上下文收斂過程。 |

因此，本報告的定位是「能力觀察與測試方法紀錄」，不是可逐步重播的完整實驗紀錄。

## 4. 測試案例矩陣

| 案例類型 | 測試內容 | reviewer 結果 | 觀察 |
| --- | --- | --- | --- |
| 文件明顯錯誤 | 故意把同步主鍵、座標順序、關聯鍵、專案類型寫錯 | 擋下 | 對明顯與現況矛盾的內容非常敏感。 |
| 程式明顯錯誤 | sandbox 中將 lookup key、fallback、關聯鍵、general update 行為全部寫錯 | 擋下 | 可辨識純程式邏輯錯誤，不只會看文件。 |
| 修正後再審 | sandbox 邏輯改正後再送審 | 通過 | 可形成「先擋下 -> 修正 -> 放行」的閉環。 |
| 隱晦條件錯誤 | `ShouldRecalculateLand` 用 `&&` 導致單欄異動漏判 | 擋下 | 對條件過嚴、可能漏判的規則錯誤有辨識力。 |
| 部分欄位更新錯誤 | 一般更新只改 `county` | 擋下 | 有抓到異常，但理由偏向「更新不完整」。 |
| 地籍欄位誤用 | 一般更新寫入 `land_process_log` | 擋下 | 在提示較少時，最後能收斂到「一般更新不應處理地籍欄位」的業務規則。 |

## 5. 主要輪次觀察

### 5.1 文件型負向測試

初期先以 Markdown 文件進行測試，故意寫入與專案現況不符的敘述，例如同步主鍵寫成 `sample_id`、一般更新寫成會更新 geometry、關聯鍵寫錯、專案型態寫成 ASP.NET MVC Web。在有提示與盲測兩種條件下，reviewer 都能成功擋下，且能點出錯誤欄位或錯誤規則。

### 5.2 程式型明顯錯誤測試

之後建立獨立 sandbox 專案 `review-sandbox/BlindReviewSample/`，將 `BuildLookupKey`、`ResolveCoordinateKey`、`MatchCollectio`、`BuildGeneralUpdate` 等規則故意寫錯。reviewer 逐項點出錯誤後，將內容改回正確規則，再次送審即通過。這代表 reviewer 對純程式碼邏輯的審查不是只停留在表面命名。

### 5.3 隱晦條件錯誤測試

後續測試 `ShouldRecalculateLand`，將判斷式從應有的「任一欄位異動就重算」寫成兩個條件都變動才重算：

```csharp
return currentCounty != incoming.County && currentTown2 != incoming.Town2;
```

reviewer 成功指出這會造成單一欄位變更時漏判，並建議改回等價於正式規則的邏輯。

### 5.4 單一欄位局部更新測試

再往下壓縮測試範圍，只在 `BuildGeneralUpdate` 中保留一個可疑欄位，例如 `county`。這時 reviewer 依然會擋下，但其理由多半偏向只更新單一欄位或其他欄位沒有一起更新。這表示 reviewer 對局部欄位更新異常有敏感度，但初期不一定會直接從業務規則角度指出分支責任錯誤。

### 5.5 地籍專屬欄位誤用測試

最後將測試壓縮到只剩一個更明確屬於地籍處理分支的欄位：

```csharp
result.Attributes["land_process_log"] = soil.LandProcessLog;
```

在 `implementation-plan.md` 中性化、不再點名欄位後，reviewer 仍能指出 `land_process_log` 不應出現在一般更新分支，且理由開始收斂到正式業務規則：`land_process_log` 屬於地籍重算處理範疇，不應在 general update 中被直接覆寫。

## 6. 測試結果總結

| 能力面向 | 結果 | 說明 |
| --- | --- | --- |
| 辨識明顯錯誤 | 成功 | 對主鍵、關聯鍵、fallback 順序、專案型態等明顯矛盾內容非常敏感。 |
| 辨識隱晦邏輯錯誤 | 成功 | 對 `&&` 導致漏判這類條件錯誤有抓到。 |
| 辨識局部欄位更新異常 | 部分成功 | 會擋下，但早期理由較偏向「更新不完整」，未必一開始就能從分支責任角度說明。 |
| 辨識地籍專屬欄位誤用 | 成功 | 在中性 plan 的純盲測下，仍能點名 `land_process_log` 並指出不應位於 general update。 |
| 修正後與 reviewer 收斂 | 成功 | 在同 session 反覆修正後，reviewer 的理由有機會從表層異常收斂到更貼近業務規則的說法。 |

## 7. 能力邊界與限制

| 類型 | 觀察 |
| --- | --- |
| plan 提示影響 | 若 `implementation-plan.md` 直接點名可疑欄位，reviewer 可能受到提示影響，降低純盲測價值。 |
| diff 可見性 | 未追蹤檔案若不出現在 Git diff，reviewer 可能先卡在「無可審內容」，因此測試前需確保 diff 可見。 |
| 局部更新理由偏差 | 對單一欄位更新錯誤，reviewer 有時會先從「更新不完整」切入，而不是直接用正式業務分支規則描述。 |
| sandbox 與正式邏輯距離 | sandbox 越抽象，reviewer 越可能從一般程式設計直覺而非專案特定規則出發。 |
| 證據保存限制 | 未逐輪保存 plan、last-review 與 diff，因此本報告不可作為完整可重播 benchmark。 |

## 8. 結論

本次回顧式測試觀察可得出以下結論：

1. `Gemini Review Gate` 具備辨識文件與程式邏輯錯誤的能力，並非只做格式或表面比對。
2. 對明顯錯誤與條件型隱晦錯誤，辨識效果相對穩定。
3. 對單一欄位局部更新這類較細的問題，reviewer 通常也能察覺異常，但其說明理由不一定一開始就最貼近業務規則。
4. 經過更乾淨的測試設計與 plan 中性化後，reviewer 最終能在純盲測情境下單獨點名 `land_process_log`，並指出其不應出現在一般更新分支。
5. 若後續仍要驗證 reviewer 能力，建議持續採用 `review-sandbox/` 這種隔離式方式，並在每輪保存完整 evidence。

## 9. 路徑與檔案

| 路徑 | 用途 |
| --- | --- |
| `docs/gemini-review-capability-report.md` | 本回顧式測試報告。 |
| `docs/evidence/gemini-review-capability/README.md` | 證據資料夾說明。 |
| `docs/evidence/gemini-review-capability/evidence-limitations.md` | 證據保存限制說明。 |
| `review-sandbox/README.md` | 說明 sandbox 的定位、限制與不屬於正式功能。 |
| `review-sandbox/BlindReviewSample/README.md` | 說明 C# sandbox 專案的測試目的與最後保留狀態。 |
| `review-sandbox/BlindReviewSample/BlindSyncService.cs` | 本次多輪程式盲測的主要測試檔。 |
| `review-sandbox/BlindReviewSample/SoilRecord.cs` | sandbox 測試用資料模型。 |
| `.codex/review/last-review.md` | Gemini Review Gate 的暫態輸出；未作為本報告逐輪證據保存。 |
| `.codex/review/implementation-plan.md` | Gemini Review Gate 的暫態 plan；未逐輪保存，因此僅作為流程說明。 |

## 10. 維護建議

- 若未來測試結束後要保留結果，應同步保存每輪 plan、diff、last-review 與 session metadata。
- 若未來要做更高階驗證，可再測試多個看似合理但組合後違反規則的情境。
- 若要驗證 reviewer 是否能在完全無 plan 提示下自行發現問題，需特別確保 `implementation-plan.md` 採中性描述，且 Git diff 內容完整可見。
- `review-sandbox/` 應持續標示為測試用資料夾，避免被誤認為正式模組。