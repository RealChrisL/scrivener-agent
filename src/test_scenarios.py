"""
Unit tests for ServiceFlow-Agent — tier classification and alert system.
Run: python3 src/test_scenarios.py  (from repo root)
   or: python3 test_scenarios.py   (from SERVICEFLOW_DATA_DIR after deployment)

Customize SERVICE_KWS and HP_PATTERNS to match your business areas and urgency
signals, then update the corresponding test cases below.
"""
import re
import sys
import os

# Support both repo and deployed locations
DATA_DIR = os.environ.get("SERVICEFLOW_DATA_DIR", os.path.expanduser("~/.claude/channels/line"))
_src = os.path.join(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)
sys.path.insert(0, DATA_DIR)

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
results = []


def check(label, got, expected):
    ok = got == expected
    print(f"  {PASS if ok else FAIL}  {label}")
    if not ok:
        print(f"         got={got!r}, expected={expected!r}")
    results.append(ok)


# ── Inline classifier (mirrors CLAUDE.md routing rules) ───────────────────────

# Tier 1: existing client signals — agent goes silent, human handles
# These patterns are tuned for a chat-based intake flow. Adjust for your
# channel's language and typical client signals.
TIER1_PATTERNS = [
    r"already paid",
    r"payment (sent|made|done|confirmed)",
    r"you (told|mentioned|said) (me |us )?(last time|previously|before)",
    r"received (the |your )?(documents?|files?|stamp)",
    r"(what|which) time (today|tomorrow)",
    r"(see you|meeting) (at |on )?(today|tomorrow)",
    # Add your own returning-client signals here
]
TIER1_GUARDS = [
    r"^(thanks?|thank you|ok|okay|got it|noted|sure|yes|no)[\s\W]*$"
]

# ⚠️ Replace with your own service area keywords from business_guide.example.json
SERVICE_KWS = [
    "service a",    # replace with your actual service area names
    "service b",
    "service c",
]

TIER2_PATTERNS = [
    r"(how much|what('s| is) the (cost|fee|price|rate)|pricing|quote)",
    r"(process|how (do|does|can) (i|we)|steps|procedure)",
    r"(i('d| would) like to|i (want|need) to).{0,20}(help|assist|service|consult)",
    r"(can you|could you).{0,20}(help|assist|handle|take care)",
    r"(i am|i'm).{0,20}(looking for|interested in|in need of)",
]

# ⚠️ High-priority signals — customize for your business domain
HP_PATTERNS = [
    r"\burgent\b|\basap\b|\bimmediately\b|\btime.sensitive\b",
    r"\bdeadline\b.{0,20}\b(today|tomorrow|this week|soon)\b",
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",   # phone number (North American format — adjust for your country)
    r"\+\d{1,3}[-.\s]?\d{3,}",               # international phone
    r"\b(ready to|want to|looking to) (hire|engage|retain|proceed|sign)\b",
    r"\bschedule (a |an )?(call|meeting|consultation|appointment)\b",
    # Add your domain-specific urgency signals below:
    # r"([regulatory deadline signal])",
    # r"([financial risk signal])",
    # r"([active legal proceeding signal])",
    # r"([missing/unresponsive party signal])",
]


def tier(text, has_history=False):
    if has_history:
        return "returning"
    t = text.strip()
    if any(re.match(g, t, re.I) for g in TIER1_GUARDS):
        pass
    elif any(re.search(p, t, re.I) for p in TIER1_PATTERNS):
        return "tier1"
    if any(kw.lower() in t.lower() for kw in SERVICE_KWS):
        return "tier2"
    if any(re.search(p, t, re.I) for p in TIER2_PATTERNS):
        return "tier2"
    return "tier3"


def hp(text):
    return any(re.search(p, text, re.I) for p in HP_PATTERNS)


# ── TEST SUITE ────────────────────────────────────────────────────────────────

print("\n══════════════════════════════════════════")
print("  TIER 1 — Existing client (agent silent)")
print("══════════════════════════════════════════")
check("payment confirmed",           tier("payment confirmed, thank you"),       "tier1")
check("already paid",                tier("I already paid yesterday"),            "tier1")
check("you told me last time",       tier("you told me last time to bring ID"),   "tier1")
check("received the documents",      tier("I received the documents"),            "tier1")
check("what time today",             tier("what time today are we meeting?"),     "tier1")
check("see you tomorrow",            tier("see you tomorrow at 3pm"),             "tier1")

print("\n══════════════════════════════════════════")
print("  TIER 1 FALSE POSITIVE GUARDS (NOT tier1)")
print("══════════════════════════════════════════")
check("thanks alone → NOT tier1",    tier("thanks"),                              "tier3")
check("ok alone → NOT tier1",        tier("ok"),                                  "tier3")
check("got it alone → NOT tier1",    tier("got it"),                              "tier3")
check("image alone → NOT tier1",     tier("[IMAGE]"),                             "tier3")

print("\n══════════════════════════════════════════")
print("  TIER 2 — New client (welcome + questionnaire)")
print("  ⚠️  Update with your own SERVICE_KWS")
print("══════════════════════════════════════════")
check("service a inquiry",           tier("I want to know about service a"),      "tier2")
check("service b inquiry",           tier("service b — how do I get started?"),   "tier2")
check("pricing question",            tier("how much does it cost?"),              "tier2")
check("process question",            tier("what's the process for this?"),        "tier2")
check("i'd like help",               tier("I'd like to get some help please"),    "tier2")

print("\n══════════════════════════════════════════")
print("  TIER 3 — Ambiguous (natural short reply)")
print("══════════════════════════════════════════")
check("hello",                       tier("hello"),                               "tier3")
check("hi there",                    tier("hi there"),                            "tier3")
check("excuse me",                   tier("excuse me"),                           "tier3")
check("general inquiry",             tier("I have a question"),                   "tier3")

print("\n══════════════════════════════════════════")
print("  RETURNING USER (has prior history log)")
print("══════════════════════════════════════════")
check("returning ignores tier",      tier("hello", has_history=True),             "returning")
check("returning even w/ T1 signal", tier("payment confirmed", has_history=True), "returning")

print("\n══════════════════════════════════════════")
print("  HIGH-PRIORITY SIGNALS")
print("  ⚠️  Add domain-specific urgency signal tests")
print("══════════════════════════════════════════")
check("urgent",                      hp("this is urgent, please help"),           True)
check("asap",                        hp("I need this asap"),                      True)
check("deadline today",              hp("I have a deadline today"),               True)
check("phone number (US)",           hp("call me at 555-867-5309"),               True)
check("intl phone",                  hp("my number is +1 555 867 5309"),          True)
check("ready to proceed",            hp("we're ready to proceed"),                True)
check("schedule a call",             hp("can we schedule a call?"),               True)
check("pure greeting → NOT hp",      hp("hello"),                                 False)
check("thanks → NOT hp",             hp("thanks"),                                False)
check("general question → NOT hp",   hp("I have a question"),                     False)

print("\n══════════════════════════════════════════")
print("  ALERT MANAGER")
print("══════════════════════════════════════════")
from alert_manager import add_alert, clear_all_alerts, handle_acknowledgment, _load_alerts

clear_all_alerts()
check("clear starts empty",          len(_load_alerts()) == 0,                    True)
add_alert("U_TEST_1", "🔴 Test alert 1")
add_alert("U_TEST_2", "🔴 Test alert 2")
check("two alerts added",            len(_load_alerts()) == 2,                    True)
check("'acknowledged' is ack",       handle_acknowledgment("acknowledged"),       True)
check("'ack' is ack",                handle_acknowledgment("ack"),                True)
check("'ok' is ack",                 handle_acknowledgment("ok"),                 True)
check("'noted' is ack",              handle_acknowledgment("noted"),              True)
check("random text NOT ack",         handle_acknowledgment("what happened?"),     False)
check("empty string NOT ack",        handle_acknowledgment(""),                   False)
clear_all_alerts()
check("clear empties alerts",        len(_load_alerts()) == 0,                    True)

# ── Summary ───────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(results)
failed = total - passed
print(f"\n══════════════════════════════════════════")
print(f"  Results: {passed}/{total} passed", "✅" if failed == 0 else f"❌ {failed} failed")
print(f"══════════════════════════════════════════\n")
sys.exit(0 if failed == 0 else 1)
