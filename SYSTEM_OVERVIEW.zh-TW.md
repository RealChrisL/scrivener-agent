<div align="right">

🌐 [English](SYSTEM_OVERVIEW.md) | **繁體中文**

</div>

# LINE Agent — 系統總覽

---

## ✨ 系統價值

- **24/7 全天候**自動接待新客戶，零漏接
- 智能問卷引導（1-2 題/輪），自動建立 Airtable CRM 記錄
- 高優先案件**立即通知**{{YOUR_TEAM_NAME}}，低優先每日摘要統整
- {{YOUR_TEAM_NAME}}只需聚焦高價值案件，日常分流與記錄全自動化

---

## 🔧 系統模式（改 CLAUDE.md）

| 模式 | 當前值 | 說明 |
|------|--------|------|
| `WHITELIST_MODE` | `true` | `true` = 白名單模式 / `false` = 正式開放 |
| `EXISTING_CLIENT_DETECTION` | `true` | `true` = 自動辨識既有客戶 / `false` = 全視為新客戶 |

---

## 📱 客戶路由邏輯（第一則訊息）

| Tier | 觸發條件 | 代理行為 |
|------|---------|---------|
| **Tier 1** 既有客戶 | 已匯款/之前說明的內容/收到您寄的/今天約幾點 | 靜默，CRM 記錄（人工接管中），{{YOUR_TEAM_NAME}} OA Manager 處理 |
| **Tier 2** 新客戶 | 詢問業務/費用/流程，說明情況 | 歡迎詞 + 問卷引導 + CRM |
| **Tier 3** 模糊 | 你好/請問/一般描述 | 自然短回應，視情況進入問卷 |

**返回用戶**（有 history log）→ 讀取對話記錄，依 `bot_mode` 決定回應

---

## 🔔 通知架構

| 類型 | 觸發 | 接收人 |
|------|------|--------|
| 🔴 高優先即時通知 + 快速指令 | 急/委託/電話/[依您的業務自訂緊急信號] | 開發者 + {{YOUR_TEAM_NAME}} |
| 📋 每日 08:30 跟進摘要 | 排程 cron（01:00 UTC） | 開發者 + {{YOUR_TEAM_NAME}} |
| ⏰ 警報未確認重發 | 15 分鐘/次，最多 3 次 | 開發者 + {{YOUR_TEAM_NAME}} |

---

## 📲 指令手冊（LINE 傳送）

| 指令 | 功能 |
|------|------|
| `查 [姓名]` | 查詢 Airtable 客戶記錄 |
| `接管 [姓名]` | 代理靜默 + 通知客戶專人接手（省略姓名 = 自動最近高優先案件）|
| `恢復 [姓名]` | 代理重新自動回覆 |
| `結案 [姓名]` | 案件完成，代理退出 |
| `緊急關閉` | 立即回到 WHITELIST_MODE=true |
| `已處理` / `ok` / `好` | 清除所有待發警報 |

---

## ⚠️ 注意事項

1. **OA Manager 回覆前先傳「接管」** — 避免代理與{{YOUR_TEAM_NAME}}同時回覆客戶
2. **Tier 1 完全自動靜默** — {{YOUR_TEAM_NAME}}無需任何操作，直接從 OA Manager 處理
3. **「已完成」為終態** — 結案後記錄不再更新，代理完全退出
4. **緊急關閉** — 上線後如遇問題，任何時間傳「緊急關閉」即可立即回到白名單模式

---

## 🚀 未來發展方向

**近期**
- `business_guide.json` 補充具體費用數字，讓代理直接回答收費問題
- `WHITELIST_MODE = false` → 正式上線

**中期**
- 預約系統整合，代理自動整理預約時間表
- AI 費用試算功能

**長期**
- 多案件並行追蹤儀表板
- 客戶流失預警（長時間未回覆自動提醒）
- SEO 行銷素材自動生成（客戶場景描述已自動建立）

---

## 📊 系統架構

| 元件 | 說明 |
|------|------|
| LINE Agent | @your_line_oa_handle，Claude Code session 驅動 |
| Airtable CRM | 自動建檔，17 個欄位，含問卷/場景/待辦 |
| Per-user logs | 各用戶獨立對話記錄，cron 每分鐘更新 |
| Cron jobs | split_history (1min) / alert_resend (15min) / daily_followup (08:30) |
| 測試覆蓋 | 53 unit tests ✅ + 6 E2E scenarios ✅ |

---

*Maintained via Claude Code*
