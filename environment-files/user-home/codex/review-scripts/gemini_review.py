from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
CONFIG_PATH = HOME / ".codex" / "gemini-review.secrets.json"
AGY_HOME = HOME / ".gemini" / "antigravity-cli"
AGY_BRAIN = AGY_HOME / "brain"
REVIEW_DIR = Path(".codex") / "review"
ENABLED = REVIEW_DIR / "enabled"
PLAN = REVIEW_DIR / "implementation-plan.md"
SESSION = REVIEW_DIR / "gemini-session.json"
MARKER = REVIEW_DIR / "approval.marker"
LAST_REVIEW = REVIEW_DIR / "last-review.md"
RAW_RESPONSE = REVIEW_DIR / "gemini-raw-response.json"
AGY_PROMPT = REVIEW_DIR / "agy-review-prompt.md"

DEFAULT_MODEL = "gemini-3.5-flash"
DEFAULT_APPROVED = "[REVIEW_APPROVED]"
DEFAULT_PENDING = "[REVIEW_PENDING]"
DEFAULT_MAX_DIFF_CHARS = 60000
NEW_SESSION_COMMAND = "[NEW_GEMINI_REVIEW_SESSION]"
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "summary": {"type": "string"},
        "blocking_issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string"},
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "issue": {"type": "string"},
                    "recommendation": {"type": "string"},
                },
                "required": ["severity", "issue", "recommendation"],
            },
        },
        "non_blocking_suggestions": {"type": "array", "items": {"type": "string"}},
        "verification_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["approved", "summary", "blocking_issues", "non_blocking_suggestions", "verification_notes"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return dict(default)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_git(args: list[str], max_chars: int | None = None) -> str:
    try:
        completed = subprocess.run(
            ["git", "-c", "safe.directory=*", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except Exception as exc:
        return f"[git {' '.join(args)} failed: {exc}]"

    output = completed.stdout.strip()
    if completed.stderr.strip():
        output = (output + "\n" if output else "") + completed.stderr.strip()
    if not output:
        output = "[no output]"
    if max_chars and len(output) > max_chars:
        omitted = len(output) - max_chars
        output = output[:max_chars] + f"\n\n[diff truncated: {omitted} chars omitted]"
    return output


def extract_plan_files(plan_text: str) -> list[str]:
    """Return file paths listed in the implementation plan's Files To Change table."""
    match = re.search(r"^## Files To Change\s*(.*?)(?=^## |\Z)", plan_text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return []

    files: list[str] = []
    seen: set[str] = set()
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.count("|") < 3:
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue

        path_cell = cells[0]
        if not path_cell or path_cell.lower() == "file" or set(path_cell) <= {"-", " "}:
            continue

        path_match = re.search(r"`([^`]+)`", path_cell)
        path = path_match.group(1) if path_match else path_cell
        path = path.strip().replace("\\", "/")

        if not path or path.lower() in {"todo", "n/a"}:
            continue
        if path not in seen:
            seen.add(path)
            files.append(path)
    return files


def build_untracked_file_diff(paths: list[str], max_chars: int | None = None) -> str:
    """Include contents for untracked files that normal git diff would omit."""
    chunks: list[str] = []
    for path in paths:
        status = run_git(["status", "--short", "--", path])
        if not any(line.startswith("?? ") for line in status.splitlines()):
            continue

        file_path = Path(path)
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            chunks.append(f"# Untracked file could not be read: {path}\n# {exc}")
            continue

        diff_lines = [
            f"diff --git a/{path} b/{path}",
            "new file mode 100644",
            "index 0000000..0000000",
            "--- /dev/null",
            f"+++ b/{path}",
            "@@",
        ]
        diff_lines.extend(f"+{line}" for line in content.splitlines())
        chunks.append("\n".join(diff_lines))

    output = "\n\n".join(chunks).strip()
    if not output:
        return "[no output]"
    if max_chars and len(output) > max_chars:
        omitted = len(output) - max_chars
        output = output[:max_chars] + f"\n\n[untracked diff truncated: {omitted} chars omitted]"
    return output


def ensure_review_files(pending_marker: str) -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    ENABLED.touch()
    if not PLAN.exists():
        PLAN.write_text(
            "# Implementation Plan\n\n"
            "## Task Goal\nTODO: Codex should describe the task goal.\n\n"
            "## Files To Change\nTODO: Codex should list changed files.\n\n"
            "## Implementation Strategy\nTODO: Codex should describe the implementation strategy.\n\n"
            "## Verification\nTODO: Codex should list tests, checks, or manual validation.\n\n"
            "## Risks\nTODO: Codex should list risks.\n",
            encoding="utf-8",
        )
    if not SESSION.exists():
        write_json(
            SESSION,
            {
                "backend": "agy_cli",
                "agy_conversation_id": None,
                "previous_interaction_id": None,
                "round": 0,
                "approved": False,
                "last_review_at": None,
            },
        )
    MARKER.write_text(pending_marker + "\n", encoding="utf-8")


def plan_requests_new_session() -> bool:
    if not PLAN.exists():
        return False
    return NEW_SESSION_COMMAND in PLAN.read_text(encoding="utf-8-sig", errors="replace")


def reset_backend_session_if_requested(config: dict[str, Any], session: dict[str, Any]) -> bool:
    if not plan_requests_new_session():
        return False

    mode = config["mode"]
    if mode in {"agy", "agy_cli", "cli", "antigravity"}:
        session["agy_conversation_id"] = None
    elif mode == "api":
        session["previous_interaction_id"] = None
    else:
        return False

    session.update(
        {
            "approved": False,
            "last_review_at": now_iso(),
            "new_session_requested_at": now_iso(),
            "new_session_command": NEW_SESSION_COMMAND,
        }
    )
    write_json(SESSION, session)
    return True


def load_config() -> dict[str, Any]:
    config = read_json(CONFIG_PATH, {})
    config["mode"] = str(config.get("mode") or "agy_cli").strip().lower()
    config["api_key"] = str(config.get("api_key") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    config["model"] = str(config.get("model") or DEFAULT_MODEL).strip()
    config["cli_command"] = str(config.get("cli_command") or "agy").strip()
    config["agy_project"] = str(config.get("agy_project") or config.get("project") or "").strip()
    config["agy_add_dir"] = bool(config.get("agy_add_dir", True))
    config["approval_marker"] = str(config.get("approval_marker") or DEFAULT_APPROVED).strip()
    config["pending_marker"] = str(config.get("pending_marker") or DEFAULT_PENDING).strip()
    try:
        config["max_diff_chars"] = int(config.get("max_diff_chars") or DEFAULT_MAX_DIFF_CHARS)
    except (TypeError, ValueError):
        config["max_diff_chars"] = DEFAULT_MAX_DIFF_CHARS
    return config


def build_review_prompt(plan: str, status: str, diff: str, session: dict[str, Any]) -> str:
    schema_json = json.dumps(REVIEW_SCHEMA, ensure_ascii=False, indent=2)
    session_json = json.dumps(session, ensure_ascii=False, indent=2)
    return f"""
You are an independent senior code reviewer for a Codex implementation.

Review rules:
- Approve only when the implementation is correct enough to finish.
- Focus on blocking bugs, behavior regressions, missing required validation, unsafe assumptions, and serious maintainability risks.
- Avoid style-only or overengineering feedback.
- If the previous review asked for changes, verify whether this round resolved them.
- The summary must be freshly written for this review round and describe only the current Implementation plan and current Git diff.
- Do not reuse, paraphrase, or carry forward summaries, verification notes, suggestions, or conclusions from previous rounds unless they are directly relevant to the current Git diff.
- If the current Git diff is comment-only or documentation-only, explicitly say so in the summary.
- If the summary, verification_notes, or suggestions do not match the current Implementation plan and current Git diff, set approved to false and explain the mismatch as a blocking issue.
- Write all human-readable JSON string fields in Traditional Chinese.
- Return only valid JSON. Do not wrap it in Markdown fences.

Required JSON schema:
```json
{schema_json}
```

Current review session state:
```json
{session_json}
```

Implementation plan:
```md
{plan}
```

Git status:
```text
{status}
```

Git diff:
```diff
{diff}
```
""".strip()


def collect_review_material(config: dict[str, Any], session: dict[str, Any]) -> str:
    plan_text = PLAN.read_text(encoding="utf-8", errors="replace")
    review_files = extract_plan_files(plan_text)

    if review_files:
        git_status = run_git(["status", "--short", "--", *review_files])
        git_diff = run_git(["diff", "--", *review_files], max_chars=config["max_diff_chars"])
        staged_diff = run_git(["diff", "--cached", "--", *review_files], max_chars=config["max_diff_chars"])
        untracked_diff = build_untracked_file_diff(review_files, max_chars=config["max_diff_chars"])

        scope = "# Review file scope\n" + "\n".join(f"- {path}" for path in review_files)
        git_diff = scope + "\n\n" + git_diff
        if untracked_diff != "[no output]":
            git_diff = git_diff + "\n\n# Untracked files from implementation plan\n" + untracked_diff
    else:
        git_status = run_git(["status", "--short"])
        git_diff = run_git(["diff", "--"], max_chars=config["max_diff_chars"])
        staged_diff = run_git(["diff", "--cached", "--"], max_chars=config["max_diff_chars"])

    if staged_diff != "[no output]":
        git_diff = git_diff + "\n\n# Staged diff\n" + staged_diff
    return build_review_prompt(plan_text, git_status, git_diff, session)


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(stripped[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError(f"Review output was not valid JSON: {text[:1000]}")


def normalize_review(review: dict[str, Any]) -> dict[str, Any]:
    review.setdefault("approved", False)
    review.setdefault("summary", "")
    review.setdefault("blocking_issues", [])
    review.setdefault("non_blocking_suggestions", [])
    review.setdefault("verification_notes", [])
    if not isinstance(review["blocking_issues"], list):
        review["blocking_issues"] = [str(review["blocking_issues"])]
    if not isinstance(review["non_blocking_suggestions"], list):
        review["non_blocking_suggestions"] = [str(review["non_blocking_suggestions"])]
    if not isinstance(review["verification_notes"], list):
        review["verification_notes"] = [str(review["verification_notes"])]
    return review


def newest_brain_id(after: float | None = None) -> str | None:
    if not AGY_BRAIN.exists():
        return None
    candidates = [p for p in AGY_BRAIN.iterdir() if p.is_dir()]
    if after is not None:
        candidates = [p for p in candidates if p.stat().st_mtime >= after]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime).name


def latest_planner_response(conversation_id: str, after: float | None = None) -> str:
    transcript = AGY_BRAIN / conversation_id / ".system_generated" / "logs" / "transcript.jsonl"
    if not transcript.exists():
        raise RuntimeError(f"Antigravity transcript not found: {transcript}")

    if after is not None and transcript.stat().st_mtime < after:
        raise RuntimeError("Antigravity CLI completed but did not write any new response (no changes since last run).")

    latest = None
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("source") == "MODEL" and item.get("type") == "PLANNER_RESPONSE":
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                latest = content
    if latest is None:
        raise RuntimeError(f"No model PLANNER_RESPONSE found in {transcript}")
    return latest


def run_agy_review(config: dict[str, Any], session: dict[str, Any]) -> tuple[dict[str, Any], str]:
    project_root = Path.cwd().resolve()
    prompt_path = (project_root / AGY_PROMPT).resolve()
    prompt_text = collect_review_material(config, session)
    AGY_PROMPT.write_text(prompt_text + "\n", encoding="utf-8")

    conversation_id = session.get("agy_conversation_id")
    if conversation_id is not None:
        conversation_id = str(conversation_id).strip() or None

    # Keep the command-line prompt small, but use an absolute path so Antigravity cannot
    # accidentally read a stale same-name prompt from its scratch directory.
    cli_prompt = (
        f"Set your working directory to this project root: {project_root}. "
        f"Read the updated file at this absolute path: {prompt_path} (updated at {now_iso()}) "
        "and perform a fresh review based on the new Git diff. "
        "You MUST call view_file on that exact absolute path and read the file again. "
        "Do not search scratch directories for agy-review-prompt.md. "
        "Do not reuse your previous response. "
        "Return only the required JSON object. Do not include Markdown fences."
    )

    command = [config["cli_command"]]
    if config.get("agy_project"):
        command.extend(["--project", str(config["agy_project"])])
    if config.get("agy_add_dir"):
        command.extend(["--add-dir", str(project_root)])
    if conversation_id:
        command.extend(["--conversation", conversation_id])
    command.extend(["--print", cli_prompt, "--print-timeout", "5m"])

    before = datetime.now().timestamp()
    completed = subprocess.run(
        command,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=360,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "Antigravity CLI failed with exit code "
            f"{completed.returncode}: {completed.stderr or completed.stdout}"
        )

    if not conversation_id:
        conversation_id = newest_brain_id(after=before) or newest_brain_id()
        if not conversation_id:
            raise RuntimeError("Could not determine Antigravity conversation id after CLI run.")

    output = completed.stdout.strip()
    if not output:
        output = latest_planner_response(conversation_id, after=before)

    RAW_RESPONSE.write_text(
        json.dumps(
            {
                "backend": "agy_cli",
                "conversation_id": conversation_id,
                "project_root": str(project_root),
                "prompt_path": str(prompt_path),
                "command": command,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "parsed_output": output,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    review = normalize_review(extract_json_object(output))
    return review, conversation_id


def call_gemini_api(api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            response_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini API request failed: {exc}") from exc

    parsed = json.loads(response_body)
    if isinstance(parsed, dict):
        return parsed
    raise RuntimeError("Gemini API returned an unexpected JSON shape.")


def extract_api_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    if "approved" in response and "blocking_issues" in response:
        return json.dumps(response, ensure_ascii=False)

    texts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                texts.append(text)
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(response.get("steps", []))
    if texts:
        return "\n".join(texts)
    raise RuntimeError("Could not find Gemini output text in the API response.")


def run_api_review(config: dict[str, Any], session: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if not config["api_key"]:
        raise RuntimeError(f"Missing API key. Add api_key to {CONFIG_PATH} or set GEMINI_API_KEY.")

    prompt_text = collect_review_material(config, session)
    payload: dict[str, Any] = {
        "model": config["model"],
        "system_instruction": "You are a strict but practical code reviewer. Return only valid JSON matching the schema. Write all human-readable fields in Traditional Chinese.",
        "input": prompt_text,
        "generation_config": {"temperature": 0.1, "thinking_level": "low"},
        "response_format": {"type": "text", "mime_type": "application/json", "schema": REVIEW_SCHEMA},
    }
    previous_id = session.get("previous_interaction_id")
    if previous_id:
        payload["previous_interaction_id"] = previous_id

    response = call_gemini_api(config["api_key"], payload)
    RAW_RESPONSE.write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_text = extract_api_output_text(response)
    review = normalize_review(extract_json_object(output_text))
    interaction_id = response.get("id") if isinstance(response.get("id"), str) else previous_id
    return review, interaction_id


def extract_token_usage() -> dict[str, Any] | None:
    if not RAW_RESPONSE.exists():
        return None
    try:
        response = json.loads(RAW_RESPONSE.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(response, dict):
        return None
    usage = response.get("usage") or response.get("usageMetadata") or response.get("usage_metadata")
    return usage if isinstance(usage, dict) else None


def write_review_report(
    review: dict[str, Any],
    backend: str,
    model: str,
    session_id: str | None,
    approved: bool,
    token_usage: dict[str, Any] | None,
) -> None:
    lines = [
        "# Gemini Review 審查結果",
        "",
        f"- 審查時間：`{now_iso()}`",
        f"- Backend：`{backend}`",
        f"- Model：`{model}`",
        f"- Session ID：`{session_id or ''}`",
        f"- 是否通過：`{str(approved).lower()}`",
        "",
        "## 摘要",
        review.get("summary") or "",
        "",
        "## 阻擋問題",
    ]

    blocking = review.get("blocking_issues") or []
    if blocking:
        for issue in blocking:
            if isinstance(issue, dict):
                location = issue.get("file") or ""
                if issue.get("line"):
                    location += f":{issue['line']}"
                lines.append(f"- [{issue.get('severity', 'unknown')}] {location} {issue.get('issue', '')}".strip())
                if issue.get("recommendation"):
                    lines.append(f"  建議處理方式：{issue['recommendation']}")
            else:
                lines.append(f"- {issue}")
    else:
        lines.append("- 無")

    lines.extend(["", "## 非阻擋建議"])
    suggestions = review.get("non_blocking_suggestions") or []
    lines.extend([f"- {item}" for item in suggestions] or ["- 無"])

    lines.extend(["", "## 驗證備註"])
    notes = review.get("verification_notes") or []
    lines.extend([f"- {item}" for item in notes] or ["- 無"])

    lines.extend(["", "## Token 使用量"])
    if token_usage:
        token_labels = {
            "total_tokens": "總 token",
            "total_input_tokens": "輸入 token",
            "total_output_tokens": "輸出 token",
            "total_cached_tokens": "快取 token",
            "total_tool_use_tokens": "工具使用 token",
            "total_thought_tokens": "思考 token",
        }
        for key, label in token_labels.items():
            if key in token_usage:
                lines.append(f"- {label}：`{token_usage[key]}`")
    else:
        lines.append("- 此 backend 未回傳 token 使用量")

    LAST_REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    config = load_config()
    ensure_review_files(config["pending_marker"])

    session = read_json(
        SESSION,
        {
            "backend": config["mode"],
            "agy_conversation_id": None,
            "previous_interaction_id": None,
            "round": 0,
            "approved": False,
            "last_review_at": None,
        },
    )
    reset_backend_session_if_requested(config, session)

    try:
        if config["mode"] in {"agy", "agy_cli", "cli", "antigravity"}:
            backend = "agy_cli"
            review, session_id = run_agy_review(config, session)
            session["agy_conversation_id"] = session_id
        elif config["mode"] == "api":
            backend = "api"
            review, session_id = run_api_review(config, session)
            session["previous_interaction_id"] = session_id
        else:
            raise RuntimeError(f"Unsupported review mode: {config['mode']}")
    except Exception as exc:
        session.update(
            {
                "backend": config["mode"],
                "approved": False,
                "last_review_at": now_iso(),
                "last_error": str(exc),
            }
        )
        write_json(SESSION, session)
        LAST_REVIEW.write_text(
            "# Gemini Review\n\n"
            f"Review failed at `{now_iso()}`.\n\n"
            f"```text\n{exc}\n```\n",
            encoding="utf-8-sig",
        )
        print(f"Gemini review failed: {exc}")
        return 1

    blocking = review.get("blocking_issues") or []
    approved = bool(review.get("approved")) and len(blocking) == 0

    session.update(
        {
            "backend": backend,
            "round": int(session.get("round") or 0) + 1,
            "approved": approved,
            "last_review_at": now_iso(),
            "model": config["model"],
        }
    )
    session.pop("last_error", None)
    write_json(SESSION, session)
    write_review_report(review, backend, config["model"], session_id, approved, extract_token_usage())

    if approved:
        MARKER.write_text(config["approval_marker"] + "\n", encoding="utf-8")
        print("Gemini review approved. approval.marker updated.")
        return 0

    MARKER.write_text(config["pending_marker"] + "\n", encoding="utf-8")
    print("Gemini review did not approve yet. See .codex/review/last-review.md.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

