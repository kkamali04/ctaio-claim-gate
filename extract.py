#!/usr/bin/env python3
"""Step 1 of claim-gate: EXTRACT.

Reads a draft markdown post and emits claims.json:
    [{"claim": ..., "quote": ..., "source_url": ...}]

This is the only model step in the pipeline. It shells out to the `claude`
CLI in headless mode (`claude -p`). If `claude` is not on PATH the script
exits non-zero and tells you to use the committed claims.json, which is the
recorded output of a real run of this script.

Usage:
    python extract.py draft.md > claims.json
"""

import json
import re
import shutil
import subprocess
import sys

PROMPT = """You are the EXTRACT step of a publish gate.

Read the draft blog post below. Emit ONLY a JSON array. Each element:
  {"claim": "<the factual assertion, in your own words>",
   "quote": "<a VERBATIM string that must appear on the source page>",
   "source_url": "<the URL that should contain that quote>"}

Rules:
- Only extract assertions that are checkable against a public web page.
- The `quote` must be a literal substring you expect to find in the page text,
  not a paraphrase. Prefer short, distinctive spans.
- Do not invent URLs. If you do not know the source, skip the claim.
- Output raw JSON. No markdown fence, no prose.

--- DRAFT ---
{draft}
--- END DRAFT ---
"""


def extract(draft_text: str, timeout: int = 180) -> list:
    if shutil.which("claude") is None:
        raise RuntimeError(
            "`claude` CLI not found on PATH. Use the committed claims.json "
            "(the recorded output of this step) and run verify.py directly."
        )

    proc = subprocess.run(
        ["claude", "-p", PROMPT.replace("{draft}", draft_text)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p failed rc={proc.returncode}: {proc.stderr[:400]}")

    return _parse(proc.stdout)


def _parse(raw: str) -> list:
    """Models fence their JSON roughly half the time. Take the first array."""
    raw = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)```", raw, re.S)
    if fenced:
        raw = fenced.group(1).strip()
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON array in model output: {raw[:300]}")
    claims = json.loads(raw[start : end + 1])

    out = []
    for c in claims:
        if not all(k in c for k in ("claim", "quote", "source_url")):
            continue
        if not c["source_url"].startswith(("http://", "https://")):
            continue
        out.append(
            {
                "claim": c["claim"].strip(),
                "quote": c["quote"].strip(),
                "source_url": c["source_url"].strip(),
            }
        )
    return out


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "draft.md"
    with open(path, encoding="utf-8") as fh:
        draft = fh.read()
    try:
        claims = extract(draft)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"extract failed: {exc}", file=sys.stderr)
        return 1
    json.dump(claims, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
