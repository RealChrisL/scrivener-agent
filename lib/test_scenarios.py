"""
Unit tests for tier classification scenarios and alerting system.
Run: python3 test_scenarios.py

Customize SERVICE_KWS and HP_PATTERNS to match your business's service areas
and urgency signals, then update the test cases in TIER 2 and 高優先 sections.
"""
import re, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
results = []

def check(label, got, expected):
    ok = got == expected
    status = PASS if ok else FAIL
    print(f"  {status}  {label}")
    if not ok:
        print(f"         got={got!r}, expected={expected!r}")
    results.append(ok)

# ── Inline classifier (mirrors CLAUDE.md rules) ───────────────────────────────

TIER1_PATTERNS = [
    # Payment confirmed
    r"已匯款.{0,20}[\d,，萬元$]",
    r"已轉帳.{0,20}[\d,，萬元$]",
    r"付了.{0,10}款",
    r"付款了",
    # Prior relationship signals
    r"上次(您|你)說", r"之前(您|你)說",
    r"(您|你)給我的文件",
    # Receipt confirmation
    r"收到(您|你)寄的", r"收到文件了", r"收到印章了",
    # Appointment reference
    r"今天約幾點", r"明天幾點見", r"明天.{0,5}見",
]
TIER1_GUARDS = [r"^(謝謝|好的|OK|ok|收到|了解|沒問題|感謝)[\s\W]*$"]

# ⚠️ Replace with your own service area keywords from business_guide.json
SERVICE_KWS = [
    "服務A",  # replace with your service A keywords
    "服務B",  # replace with your service B keywords
    "服務C",  # replace with your service C keywords
]

TIER2_PATTERNS = [
    r"(費用|收費|多少錢|怎麼收費|報價)",
    r"(流程|怎麼辦|如何辦|怎麼處理|步驟)",
    r"(請問|想問|想諮詢|想了解).{0,20}(辦|辦理|幫|代辦|服務)",
    r"(我想|我需要|我要).{0,10}(辦|委託|諮詢)",
]

HP_PATTERNS = [
    # Strong purchase intent
    r"(委託|要辦|決定要辦|確定要辦)",
    r"(很急|非常急|急迫|很急迫|緊急|趕快)", r"^急$",
    r"(費用多少|多少錢|怎麼收費|什麼時候可以辦)",
    # Contact / commitment
    r"0[89]\d{8}",          # phone number — adjust regex for your country format
    r"(約時間|預約|什麼時候方便)",
    # ⚠️ Add your domain-specific urgency signals below:
    # r"([urgency signal specific to your service area A])",
    # r"([urgency signal specific to your service area B])",
    # r"([deadline or time-pressure signal])",
    # r"([missing party or unresponsive party signal])",
    # r"([active legal or regulatory proceeding signal])",
    # r"([financial risk threshold signal])",
]

def tier(text, has_history=False):
    if has_history: return "returning"
    t = text.strip()
    if any(re.match(g, t, re.I) for g in TIER1_GUARDS): pass
    elif any(re.search(p, t) for p in TIER1_PATTERNS): return "tier1"
    if any(kw in t for kw in SERVICE_KWS): return "tier2"
    if any(re.search(p, t) for p in TIER2_PATTERNS): return "tier2"
    return "tier3"

def hp(text):
    return any(re.search(p, text) for p in HP_PATTERNS)


# ── TEST SUITE ────────────────────────────────────────────────────────────────

print("\n══════════════════════════════════════════")
print("  TIER 1 — Existing client (should be silent)")
print("══════════════════════════════════════════")
check("已匯款 10,050元",         tier("已匯款 10,050元"),          "tier1")
check("已轉帳給您了",             tier("已轉帳9000元給您"),          "tier1")
check("付款了",                   tier("付款了謝謝"),                "tier1")
check("上次您說要準備...",         tier("上次您說要準備文件"),         "tier1")
check("之前你說...",              tier("之前你說要帶過去"),            "tier1")
check("收到您寄的",               tier("收到您寄的文件了"),            "tier1")
check("收到文件了",               tier("收到文件了謝謝"),              "tier1")
check("今天約幾點",               tier("今天約幾點到您那邊"),          "tier1")
check("明天幾點見",               tier("明天幾點見請告知"),            "tier1")

print("\n══════════════════════════════════════════")
print("  TIER 1 FALSE POSITIVE GUARDS (should NOT be tier1)")
print("══════════════════════════════════════════")
check("謝謝 alone → NOT tier1",   tier("謝謝"),                      "tier3")
check("好的 alone → NOT tier1",   tier("好的"),                      "tier3")
check("OK alone → NOT tier1",     tier("OK"),                        "tier3")
check("收到 alone → NOT tier1",   tier("收到"),                      "tier3")
check("Image alone → NOT tier1",  tier("[IMAGE]"),                   "tier3")
check("文件 alone → NOT tier1",   tier("我有一些文件想處理"),          "tier3")

print("\n══════════════════════════════════════════")
print("  TIER 2 — New client (should get welcome)")
print("  ⚠️  Update these tests with your own SERVICE_KWS")
print("══════════════════════════════════════════")
check("服務A inquiry",            tier("我想詢問服務A"),               "tier2")
check("服務B inquiry",            tier("代辦服務B怎麼辦"),             "tier2")
check("服務C inquiry",            tier("想了解服務C費用"),              "tier2")
check("費用多少",                  tier("費用多少錢"),                  "tier2")
check("怎麼辦",                   tier("這個怎麼辦理"),                "tier2")
check("我想委託",                  tier("我想委託你們幫我辦"),          "tier2")
check("我要辦理",                  tier("我需要辦理諮詢"),              "tier2")

print("\n══════════════════════════════════════════")
print("  TIER 3 — Ambiguous (short natural response)")
print("══════════════════════════════════════════")
check("你好",                     tier("你好"),                       "tier3")
check("請問",                     tier("請問"),                       "tier3")
check("一般情況描述",              tier("我想諮詢一下"),                "tier3")
check("有空嗎",                   tier("請問有空嗎"),                  "tier3")

print("\n══════════════════════════════════════════")
print("  RETURNING USER (has history log)")
print("══════════════════════════════════════════")
check("returning user ignores tier", tier("你好", has_history=True), "returning")
check("returning even w/ T1 signal", tier("已匯款100元", has_history=True), "returning")

print("\n══════════════════════════════════════════")
print("  高優先 SIGNALS")
print("  ⚠️  Add your domain-specific urgency signal tests here")
print("══════════════════════════════════════════")
check("委託",          hp("我想委託你們"),           True)
check("要辦",          hp("我要辦服務A"),             True)
check("很急",          hp("很急需要辦"),             True)
check("急迫",          hp("情況很急迫"),              True)
check("多少錢",        hp("請問費用多少錢"),           True)
check("手機號碼",      hp("0912345678"),             True)
check("約時間",        hp("想約時間來諮詢"),           True)
check("pure greeting → NOT hp", hp("你好"),         False)
check("謝謝 → NOT hp",         hp("謝謝"),           False)
check("一般描述 → NOT hp",     hp("我想了解一下"),     False)

print("\n══════════════════════════════════════════")
print("  ALERT MANAGER")
print("══════════════════════════════════════════")
from alert_manager import add_alert, clear_all_alerts, handle_acknowledgment, _load_alerts

clear_all_alerts()
check("clear starts empty",          len(_load_alerts()) == 0, True)
add_alert("U_TEST_1", "🔴 Test alert 1")
add_alert("U_TEST_2", "🔴 Test alert 2")
check("two alerts added",            len(_load_alerts()) == 2, True)
check("已處理 is ack",               handle_acknowledgment("已處理"), True)
check("已看到 is ack",               handle_acknowledgment("已看到"), True)
check("ok is ack",                   handle_acknowledgment("ok"),     True)
check("好 is ack",                   handle_acknowledgment("好"),      True)
check("random text NOT ack",         handle_acknowledgment("什麼事"),  False)
check("empty string NOT ack",        handle_acknowledgment(""),        False)
clear_all_alerts()
check("clear empties alerts",        len(_load_alerts()) == 0, True)

# ── Summary ───────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(results)
failed = total - passed
print(f"\n══════════════════════════════════════════")
print(f"  Results: {passed}/{total} passed", "✅" if failed == 0 else f"❌ {failed} failed")
print(f"══════════════════════════════════════════\n")
sys.exit(0 if failed == 0 else 1)
