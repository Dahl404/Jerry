#!/usr/bin/env python3
"""
3-step semantic compression/decompression test via llama-server on port 8080.
No shared context between steps. Raw strings only.

Usage:
  python compress_test.py all        <input_file>
  python compress_test.py compress   <input_file>
  python compress_test.py decompress <input_file>.compressed
  python compress_test.py compare    <original> <decompressed>
"""

import argparse
import json
import textwrap
from pathlib import Path
import requests

BASE_URL = "http://localhost:8080/v1/chat/completions"
MODEL    = "qwen3"
MAX_ITER = 64

HEADERS = {"Content-Type": "application/json"}


def chat(messages, tools=None, tool_choice=None):
    payload = {"model": MODEL, "messages": messages}
    if tools:
        payload["tools"] = tools
    if tool_choice:
        payload["tool_choice"] = tool_choice
    r = requests.post(BASE_URL, headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


# ── Tools ─────────────────────────────────────────────────────────────────────
REMEMBER_TOOL = {
    "type": "function",
    "function": {
        "name": "remember",
        "description": "Store a compressed memory fragment.",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {"type": "string", "description": "Compressed fragment to store"},
            },
            "required": ["value"],
        },
    },
}

DONE_TOOL = {
    "type": "function",
    "function": {
        "name": "done",
        "description": "Signal that all memories have been stored.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

# ── System prompts ────────────────────────────────────────────────────────────
COMPRESS_SYS = (
    "Store only what cannot be inferred. "
    "Compress to the irreducible semantic delta from baseline.\n\n"
    "You will store memories in maximally compressed notation. "
    "Invent and consistently use abbreviations, symbols, and telegraphic syntax. "
    "Prioritize semantic fidelity over human readability. You are the only reader.\n\n"
    "Call remember(value) for each fragment. When finished, call done()."
)

DECOMPRESS_SYS = (
    "You are a decompression engine. "
    "You will receive raw compressed memory fragments produced by a compression pass. "
    "Reconstruct the original document as completely and accurately as possible. "
    "Expand every abbreviation, symbol, and telegraphic fragment into full prose. "
    "Output ONLY the reconstructed document — no commentary, no preamble."
)

COMPARE_SYS = textwrap.dedent("""
    You are a semantic fidelity auditor.
    You will receive an ORIGINAL document and a RECONSTRUCTED document.

    Produce a structured report:

    SEMANTIC_SIMILARITY: <integer 0-100>
    FACTS_PRESERVED:
      - <bullet list of key facts that survived>
    FACTS_LOST:
      - <bullet list of key facts that were dropped or distorted>
    STRUCTURAL_FIDELITY: <brief note on format/structure preservation>
    COMPRESSION_ARTIFACTS:
      - <any hallucinations or introduced errors>
    VERDICT: <one-sentence overall assessment>
""").strip()


# ── Step 1: Compress ──────────────────────────────────────────────────────────
def step_compress(input_path: Path) -> Path:
    text = input_path.read_text(errors="replace")
    print(f"[compress] {input_path}  ({len(text):,} chars)")

    fragments = []
    messages = [
        {"role": "system", "content": COMPRESS_SYS},
        {"role": "user",   "content": text},
    ]

    for i in range(MAX_ITER):
        msg = chat(messages, tools=[REMEMBER_TOOL, DONE_TOOL], tool_choice="auto")
        messages.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            print(f"[compress] text reply at iter {i+1} — treating as done")
            if msg.get("content"):
                fragments.append(msg["content"])
            break

        finished = False
        for tc in tool_calls:
            fn   = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])

            if fn == "remember":
                frag = args["value"]
                fragments.append(frag)
                print(f"[compress]   +{len(frag)} chars")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": "stored",
                })

            elif fn == "done":
                print(f"[compress] done — {len(fragments)} fragments")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": "acknowledged",
                })
                finished = True

        if finished:
            break
    else:
        print(f"[compress] WARNING: hit MAX_ITER={MAX_ITER}")

    out_path = input_path.with_suffix(input_path.suffix + ".compressed")
    out_path.write_text("\n".join(fragments))
    print(f"[compress] → {out_path}  ({out_path.stat().st_size:,} bytes)")
    return out_path


# ── Step 2: Decompress ────────────────────────────────────────────────────────
def step_decompress(compressed_path: Path) -> Path:
    compressed = compressed_path.read_text()
    print(f"[decompress] {compressed_path}  ({len(compressed):,} chars)")

    msg = chat([
        {"role": "system", "content": DECOMPRESS_SYS},
        {"role": "user",   "content": compressed},
    ])
    result = msg.get("content") or ""

    stem     = compressed_path.name.replace(".compressed", "")
    out_path = compressed_path.parent / (stem + ".decompressed")
    out_path.write_text(result)
    print(f"[decompress] → {out_path}  ({len(result):,} chars)")
    return out_path


# ── Step 3: Compare ───────────────────────────────────────────────────────────
def step_compare(original_path: Path, decompressed_path: Path) -> None:
    original     = original_path.read_text(errors="replace")
    decompressed = decompressed_path.read_text()
    print(f"[compare] original={len(original):,}  decompressed={len(decompressed):,}")

    msg = chat([
        {"role": "system", "content": COMPARE_SYS},
        {"role": "user",   "content": f"=== ORIGINAL ===\n{original}\n\n=== RECONSTRUCTED ===\n{decompressed}"},
    ])
    report = msg.get("content") or ""

    print("\n" + "═" * 60)
    print(report)
    print("═" * 60 + "\n")

    report_path = decompressed_path.with_suffix(".report")
    report_path.write_text(report)
    print(f"[compare] → {report_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("compress",   help="Step 1").add_argument("input",      type=Path)
    sub.add_parser("decompress", help="Step 2").add_argument("compressed", type=Path)

    p_cmp = sub.add_parser("compare", help="Step 3")
    p_cmp.add_argument("original",     type=Path)
    p_cmp.add_argument("decompressed", type=Path)

    p_all = sub.add_parser("all", help="All 3 steps")
    p_all.add_argument("input", type=Path)

    args = parser.parse_args()

    if args.cmd == "compress":
        step_compress(args.input)
    elif args.cmd == "decompress":
        step_decompress(args.compressed)
    elif args.cmd == "compare":
        step_compare(args.original, args.decompressed)
    elif args.cmd == "all":
        c = step_compress(args.input)
        d = step_decompress(c)
        step_compare(args.input, d)


if __name__ == "__main__":
    main()

