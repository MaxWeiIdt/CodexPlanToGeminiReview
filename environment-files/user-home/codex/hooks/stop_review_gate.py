from pathlib import Path
import sys

REVIEW_DIR = Path(".codex") / "review"
ENABLED = REVIEW_DIR / "enabled"
SKIP_ONCE = REVIEW_DIR / "skip-once"
PLAN = REVIEW_DIR / "implementation-plan.md"
SESSION = REVIEW_DIR / "gemini-session.json"
MARKER = REVIEW_DIR / "approval.marker"

APPROVED = "[REVIEW_APPROVED]"

# Projects opt in by creating .codex/review/enabled.
# This avoids blocking normal Q&A in projects that do not use the review gate.
if not ENABLED.exists():
    sys.exit(0)

# Explicit one-time escape hatch. Codex may create this only when the user
# includes [SKIP_GEMINI_REVIEW] or explicitly asks to skip Gemini Review Gate.
if SKIP_ONCE.exists():
    try:
        SKIP_ONCE.unlink()
    except OSError as exc:
        print(f"Gemini Review Gate skip requested, but could not remove skip-once: {exc}")
        sys.exit(1)

    print("Gemini Review Gate skipped for this turn via .codex/review/skip-once.")
    sys.exit(0)

missing = []

if not PLAN.exists():
    missing.append("Missing .codex/review/implementation-plan.md")

if not SESSION.exists():
    missing.append("Missing .codex/review/gemini-session.json")

if not MARKER.exists():
    missing.append("Missing .codex/review/approval.marker")
else:
    lines = MARKER.read_text(encoding="utf-8").splitlines()
    if not lines or lines[-1].strip() != APPROVED:
        missing.append("approval.marker final line is not [REVIEW_APPROVED]")

if missing:
    print("Gemini Review Gate did not pass:")
    for item in missing:
        print(f"- {item}")

    print("""
Do not finish the task yet. Run the $gemini-review skill now:

1. Create or update .codex/review/implementation-plan.md.
2. Run Gemini code review.
3. If Gemini requests changes, fix them and review again in the same Gemini session.
4. Only after Gemini explicitly approves, write [REVIEW_APPROVED] as the final line of .codex/review/approval.marker.

To intentionally skip this gate for one turn, the user must explicitly include [SKIP_GEMINI_REVIEW] or ask to skip Gemini Review Gate, and Codex must create .codex/review/skip-once.
""")
    sys.exit(1)

sys.exit(0)