# claim-gate

A publish gate for [ctaio.dev](https://ctaio.dev). One model step, one
deterministic step, and a ledger of everything it killed.

The model writes the draft. The gate decides what ships. Nothing reaches
`out/post.md` unless a machine fetched the cited page and found the quoted
string in it.

## The pipeline

```
  draft.md
     |
     v
+----------------+   model step (claude -p)
|  1. EXTRACT    |   draft prose -> [{claim, quote, source_url}]
|   extract.py   |   recorded output committed as claims.json
+----------------+
     |
     v  claims.json
+----------------+   deterministic. no model. stdlib only.
|  2. VERIFY     |   GET each source_url (5s, real UA) -> strip tags ->
|   verify.py    |   normalize -> is `quote` literally in the page?
+----------------+
     |               VERIFIED | UNSUPPORTED | DEAD
     v  out/verdicts.json
+----------------+
|  3. PUBLISH    |   VERIFIED  -> out/post.md
|   publish.py   |   everything else -> out/kill-ledger.md, with its reason
+----------------+
```

## The design point: DEAD is not UNSUPPORTED

Three outcomes, and the third one is why this repo exists.

| status | what happened | what it means | effect |
|---|---|---|---|
| `VERIFIED` | page loaded, quote found | evidence for the claim | published |
| `UNSUPPORTED` | page loaded, quote absent | evidence *against* the claim | dropped, logged |
| `DEAD` | 404 / timeout / TLS / DNS | **we learned nothing** | **abstains**, logged separately |

A dead link is not a refutation. If the gate scored `DEAD` the same as
`UNSUPPORTED`, ordinary link rot would silently be recorded as "the author made
this up" — and every future run would inherit that lie. The gate refuses to
judge a claim it could not check. Missing evidence is not disproof.

## Run it

Python 3, standard library only. No pip install, no API key, no network
credentials.

```bash
python verify.py claims.json > out/verdicts.json   # step 2, hits the live web
python publish.py out/verdicts.json                # step 3
```

Step 1 is optional and needs the `claude` CLI on PATH:

```bash
python extract.py draft.md > claims.json           # step 1, the model step
```

`claims.json` in this repo is the **recorded output of step 1**, committed so
the repo runs end to end without a model or an API bill. `extract.py` is the
real extractor, not a stub — it shells out to `claude -p`, parses the array out
of a fenced or unfenced response, and drops any claim missing a field or a
valid URL.

## Results (real run, 2026-08-23, committed in `out/`)

**8 claims in — 4 VERIFIED, 3 UNSUPPORTED, 1 DEAD (abstained).**

| # | source | outcome |
|---|---|---|
| 1 | anthropic.com/engineering/building-effective-agents | VERIFIED |
| 2 | docs.anthropic.com/en/docs/claude-code/overview | UNSUPPORTED |
| 3 | arxiv.org/abs/2405.15793 (SWE-agent) | VERIFIED |
| 4 | arxiv.org/abs/2308.07201 (ChatEval) | VERIFIED |
| 5 | simonwillison.net/2025/Sep/18/agents/ | VERIFIED |
| 6 | modelcontextprotocol.io/introduction | UNSUPPORTED |
| 7 | docs.cursor.com/context/rules-for-ai | UNSUPPORTED |
| 8 | docs.anthropic.com/en/docs/build-with-claude/agents | DEAD (HTTP 404) |

Half the draft did not survive. That is the expected result, not a bug — the
three UNSUPPORTED claims cite pages whose wording has drifted since the quote
was written, which is exactly the failure a human skim never catches.

Raw run log: [`out/run.log`](out/run.log). Ledger:
[`out/kill-ledger.md`](out/kill-ledger.md).

## What actually broke while building this

The first run reported `UNSUPPORTED` on the Anthropic quote that is *verbatim*
on the page. Cause: `html_to_text` replaces every tag with a space, so
`<strong>Agents</strong>, on the other hand` becomes `Agents , on the other
hand`. Whitespace collapsing cannot fix that — it is a single legal space
between two tokens. The gate was calling a true claim false.

Fix: `normalize()` now strips whitespace before closing punctuation and after
opening brackets. That one regex moved the run from 3 verified to 4. It is
commented in `verify.py` as load-bearing, because a false `UNSUPPORTED` is the
worst bug a truth gate can have.

## Files

| file | role |
|---|---|
| `draft.md` | the input post, 8 checkable claims |
| `extract.py` | step 1, model — `claude -p` -> claims JSON |
| `claims.json` | recorded output of step 1 |
| `verify.py` | step 2, deterministic fetch + substring check |
| `publish.py` | step 3, writes post + kill ledger |
| `out/verdicts.json` | per-claim verdict with HTTP status and reason |
| `out/post.md` | the published post — verified claims only |
| `out/kill-ledger.md` | every dropped claim, split by UNSUPPORTED vs DEAD |
| `out/run.log` | stderr of the real run |
