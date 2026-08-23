#!/usr/bin/env python3
"""Step 2 of claim-gate: VERIFY. Deterministic. No model.

For each claim: fetch source_url (5s timeout, real User-Agent), strip the page
to text, normalize whitespace, and ask whether `quote` literally appears.

Three outcomes, and the distinction between the last two is the whole point:

    VERIFIED    page loaded, quote found.
    QUOTE_NOT_FOUND page loaded, but the quote string was absent from the bytes
                    fetched. That is a failure to find evidence, not a proof the
                    claim is false.
    DEAD            non-200, timeout, TLS error, DNS failure. Nothing was learned.

A DEAD source ABSTAINS. Missing evidence is not disproof. Scoring a dead link
the same as a missing quote silently converts "the internet rotted" into
"the author lied", and that error compounds every time the gate runs.

Usage:
    python verify.py claims.json > out/verdicts.json
"""

import gzip
import io
import json
import re
import socket
import sys
import urllib.error
import urllib.request

TIMEOUT = 5
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

VERIFIED = "VERIFIED"
QUOTE_NOT_FOUND = "QUOTE_NOT_FOUND"
DEAD = "DEAD"

_SCRIPT = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

_ENTITIES = {
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&quot;": '"', "&#39;": "'", "&rsquo;": "'", "&lsquo;": "'",
    "&ldquo;": '"', "&rdquo;": '"', "&mdash;": "-", "&ndash;": "-",
    "&hellip;": "...", "&#x27;": "'", "&#x2F;": "/",
}


_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?)\]])")
_SPACE_AFTER_OPEN = re.compile(r"([(\[])\s+")


def html_to_text(html: str) -> str:
    text = _SCRIPT.sub(" ", html)
    text = _TAG.sub(" ", text)
    for ent, rep in _ENTITIES.items():
        text = text.replace(ent, rep)
    return _WS.sub(" ", text).strip()


def normalize(s: str) -> str:
    """Whitespace + typography normalization, so a curly quote in the page
    does not fail a straight quote in the claim."""
    s = _WS.sub(" ", s)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'),
                 ("”", '"'), ("—", "-"), ("–", "-"),
                 (" ", " ")):
        s = s.replace(a, b)
    # NOT cosmetic: replacing every tag with a space turns
    # `<strong>Agents</strong>, on the other hand` into `Agents , on the other
    # hand`. That phantom space is a single legal space between two tokens, so
    # whitespace collapsing cannot remove it, and the gate then reports
    # QUOTE_NOT_FOUND on a quote that is verbatim present -- the worst possible
    # failure for a tool whose whole job is telling true from false.
    s = _SPACE_BEFORE_PUNCT.sub(r"\1", s)
    s = _SPACE_AFTER_OPEN.sub(r"\1", s)
    return s.strip().lower()


def fetch(url: str):
    """Return (text, status). Raises on anything that means nothing was learned."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace"), resp.status


def check(claim: dict) -> dict:
    url = claim["source_url"]
    result = {**claim, "status": None, "http_status": None, "detail": ""}
    try:
        html, status = fetch(url)
    except urllib.error.HTTPError as exc:
        result.update(status=DEAD, http_status=exc.code,
                      detail=f"HTTP {exc.code} {exc.reason}")
        return result
    except urllib.error.URLError as exc:
        result.update(status=DEAD, detail=f"URLError: {exc.reason}")
        return result
    except socket.timeout:
        result.update(status=DEAD, detail=f"timeout after {TIMEOUT}s")
        return result
    except Exception as exc:  # noqa: BLE001 - network boundary
        result.update(status=DEAD, detail=f"{type(exc).__name__}: {exc}")
        return result

    result["http_status"] = status
    page = normalize(html_to_text(html))
    if normalize(claim["quote"]) in page:
        result.update(status=VERIFIED, detail=f"quote found in {len(page)} chars of page text")
    else:
        result.update(status=QUOTE_NOT_FOUND,
                      detail=f"page loaded ({len(page)} chars) but quote absent")
    return result


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "claims.json"
    with open(path, encoding="utf-8") as fh:
        claims = json.load(fh)

    verdicts = []
    for i, claim in enumerate(claims, 1):
        v = check(claim)
        verdicts.append(v)
        print(f"[{i}/{len(claims)}] {v['status']:<12} {v['source_url']}  -- {v['detail']}",
              file=sys.stderr)

    counts = {s: sum(1 for v in verdicts if v["status"] == s)
              for s in (VERIFIED, QUOTE_NOT_FOUND, DEAD)}
    print(f"\n{len(claims)} claims in | {counts[VERIFIED]} verified | "
          f"{counts[QUOTE_NOT_FOUND]} quote_not_found | {counts[DEAD]} dead (abstain)",
          file=sys.stderr)

    json.dump(verdicts, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
