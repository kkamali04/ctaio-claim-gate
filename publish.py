#!/usr/bin/env python3
"""Step 3 of claim-gate: PUBLISH.

Reads verdicts.json and writes:
    out/post.md         only VERIFIED claims, each with its source link
    out/kill-ledger.md  every dropped claim, its status, HTTP code, and reason

Usage:
    python publish.py out/verdicts.json
"""

import json
import os
import sys
from datetime import datetime, timezone

OUT = "out"


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "verdicts.json")
    with open(path, encoding="utf-8") as fh:
        verdicts = json.load(fh)

    os.makedirs(OUT, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    verified = [v for v in verdicts if v["status"] == "VERIFIED"]
    unsupported = [v for v in verdicts if v["status"] == "UNSUPPORTED"]
    dead = [v for v in verdicts if v["status"] == "DEAD"]

    post = [
        "# What agentic coding actually is",
        "",
        f"*Published by claim-gate {stamp}. "
        f"{len(verified)} of {len(verdicts)} drafted claims survived verification.*",
        "",
    ]
    for v in verified:
        post.append(f"- {v['claim']}")
        post.append(f'  > "{v["quote"]}"')
        post.append(f"  — [source]({v['source_url']})")
        post.append("")
    if not verified:
        post.append("_No claim survived the gate. Nothing was published._")
        post.append("")
    post.append("---")
    post.append(f"{len(unsupported)} claims were dropped as unsupported. "
                f"{len(dead)} abstained on a dead source. See `kill-ledger.md`.")

    with open(os.path.join(OUT, "post.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(post) + "\n")

    ledger = [
        "# Kill ledger",
        "",
        f"*Run {stamp}.* Every claim that did not make it into `post.md`, and why.",
        "",
        f"- **{len(verdicts)}** claims in",
        f"- **{len(verified)}** VERIFIED (published)",
        f"- **{len(unsupported)}** UNSUPPORTED (page loaded, quote absent — dropped as wrong)",
        f"- **{len(dead)}** DEAD (source unreachable — **abstained**, not judged)",
        "",
        "> A DEAD source is not evidence against the claim. The gate refuses to",
        "> score it. Missing evidence is not disproof; it is missing evidence.",
        "",
        "## UNSUPPORTED — the source did not say this",
        "",
    ]
    if unsupported:
        ledger.append("| claim | url | http | reason |")
        ledger.append("|---|---|---|---|")
        for v in unsupported:
            ledger.append(
                f"| {v['claim'][:90]} | {v['source_url']} | {v['http_status']} | {v['detail']} |"
            )
    else:
        ledger.append("_none_")

    ledger += ["", "## DEAD — abstained, source unreachable", ""]
    if dead:
        ledger.append("| claim | url | http | failure |")
        ledger.append("|---|---|---|---|")
        for v in dead:
            ledger.append(
                f"| {v['claim'][:90]} | {v['source_url']} | "
                f"{v['http_status'] if v['http_status'] is not None else '-'} | {v['detail']} |"
            )
    else:
        ledger.append("_none_")
    ledger.append("")

    with open(os.path.join(OUT, "kill-ledger.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(ledger) + "\n")

    print(f"wrote {OUT}/post.md ({len(verified)} claims) and {OUT}/kill-ledger.md "
          f"({len(unsupported)} unsupported, {len(dead)} dead)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
